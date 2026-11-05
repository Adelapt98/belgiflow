"""Thirteen partitioned data-product pipelines with an explicit dependency graph."""
import os
from dagster import asset, AssetSelection, ConfigurableResource, DailyPartitionsDefinition, Definitions, MetadataValue, define_asset_job
from .platform.store import Store
from .platform import operations as op, geography as geo
from .platform.catalog import PIPELINES

PARTITIONS=DailyPartitionsDefinition(start_date='2026-01-01',timezone='Europe/Brussels')

class Platform(ConfigurableResource):
    root: str = os.getenv('BELGIFLOW_PLATFORM_ROOT','data/platform')
    source_mode: str = os.getenv('BELGIFLOW_SOURCE_MODE','cached')
    shipments: int = int(os.getenv('BELGIFLOW_SHIPMENTS','300'))
    backend: str = os.getenv('BELGIFLOW_BACKEND','local')

    def store(self,context):
        if self.backend not in {'local','aws'}:
            raise ValueError('backend must be local or aws')
        if not 1<=self.shipments<=10000:
            raise ValueError('local scenario supports 1 to 10000 shipments per cohort')
        return Store(self.root,context.partition_key)

COMMON=dict(partitions_def=PARTITIONS,op_tags={'dagster/concurrency_key':'belgiflow_writer'})

@asset(group_name='geographic_reference',description='Pinned Belgian boundary with public or fixture provenance.',**COMMON)
def geographic_reference(context,platform: Platform):
    return geo.geographic_reference(platform.store(context),platform.source_mode)

@asset(group_name='geographic_reference',deps=[geographic_reference],description='Buildings, roads and connectors clipped to the Belgian land boundary.',**COMMON)
def map_features(context,platform: Platform):
    return geo.map_features(platform.store(context),platform.source_mode)

@asset(group_name='shipment_ingestion',description='Daily shipment cohort with duplicates and corrected events.',**COMMON)
def shipment_source(context,platform: Platform):
    return op.shipment_source(platform.store(context),platform.shipments)

@asset(group_name='shipment_ingestion',deps=[shipment_source],description='Durable incremental event ledger, highest revisions, and quarantine.',**COMMON)
def accepted_events(context,platform: Platform):
    return op.accepted_events(platform.store(context))

@asset(group_name='reference_cdc',description='Transactional PostgreSQL outbox or explicitly labeled offline change fixtures.',**COMMON)
def reference_changes(context,platform: Platform):
    return op.reference_changes(platform.store(context),os.getenv('BELGIFLOW_DSN'))

@asset(group_name='reference_cdc',deps=[reference_changes],description='Effective-time SCD Type 2 depot policies.',**COMMON)
def depot_history(context,platform: Platform):
    return op.depot_history(platform.store(context))

@asset(group_name='service_coverage',deps=[accepted_events,depot_history],description='Historical metric service-radius decisions for each shipment.',**COMMON)
def service_coverage(context,platform: Platform):
    return op.service_coverage(platform.store(context))

@asset(group_name='capacity_planning',deps=[service_coverage],description='Depot capacity utilization, overload, and coverage exceptions.',**COMMON)
def capacity_plan(context,platform: Platform):
    return op.capacity_plan(platform.store(context))

@asset(group_name='delivery_analytics',deps=[accepted_events,depot_history,service_coverage,capacity_plan],**COMMON)
def warehouse_inputs(context,platform: Platform):
    return op.prepare_warehouse(platform.store(context))

@asset(group_name='delivery_analytics',deps=[warehouse_inputs],description='dbt affected-key incremental shipment facts, SLA marts, and relational tests.',**COMMON)
def delivery_sla(context,platform: Platform):
    from .platform.warehouse import build_marts
    return build_marts(platform.store(context))

@asset(group_name='geographic_accessibility',deps=[map_features],description='Spatial-index nearest sampled road distance for each building.',**COMMON)
def building_accessibility(context,platform: Platform):
    return geo.building_accessibility(platform.store(context))

@asset(group_name='map_audit',deps=[map_features],description='Snapshot additions, removals and geometry changes. Default change scenario is synthetic.',**COMMON)
def map_change_audit(context,platform: Platform):
    return geo.map_change_audit(platform.store(context))

@asset(group_name='distributed_processing',deps=[accepted_events],description='Execute PySpark through the local worker or AWS Glue with source reconciliation.',**COMMON)
def spark_compaction(context,platform: Platform):
    from .platform.spark import compact
    return compact(platform.store(context),backend='glue' if platform.backend=='aws' else 'local',
                   glue_job=os.getenv('BELGIFLOW_GLUE_JOB'),bucket=os.getenv('BELGIFLOW_BUCKET'))

@asset(group_name='data_quality',deps=[delivery_sla,building_accessibility,map_change_audit],**COMMON)
def quality_report(context,platform: Platform):
    from .platform.quality import assess
    report=assess(platform.store(context))
    context.add_output_metadata({'shipments':report['shipments'],'events':report['events'],'status':report['status']})
    return report

@asset(group_name='data_quality',deps=[quality_report],description='Freshness, row counts, byte sizes and verified checksums.',**COMMON)
def observability(context,platform: Platform):
    from .platform.quality import observability as measure
    return measure(platform.store(context))

@asset(group_name='lake_delivery',deps=[observability],description='Immutable product bundle, manifests and completion pointer, locally or in S3.',**COMMON)
def lake_publication(context,platform: Platform):
    from .platform.cloud import publish_lake
    bucket=os.getenv('BELGIFLOW_BUCKET') if platform.backend=='aws' else None
    if platform.backend=='aws' and not bucket:
        raise ValueError('AWS publication needs BELGIFLOW_BUCKET')
    return publish_lake(platform.store(context),bucket=bucket)

@asset(group_name='warehouse_delivery',deps=[lake_publication],description='Idempotent serving replication, local DuckDB or transactional Redshift COPY.',**COMMON)
def warehouse_replication(context,platform: Platform):
    from .platform.cloud import replicate
    return replicate(platform.store(context),bucket=os.getenv('BELGIFLOW_BUCKET') if platform.backend=='aws' else None,
                     workgroup=os.getenv('BELGIFLOW_REDSHIFT_WORKGROUP'),
                     database=os.getenv('BELGIFLOW_REDSHIFT_DATABASE','belgiflow'),
                     role_arn=os.getenv('BELGIFLOW_REDSHIFT_COPY_ROLE'))

@asset(group_name='operational_review',deps=[observability],description='Quality-gated business dashboard and educational pipeline catalog.',**COMMON)
def operations_dashboard(context,platform: Platform):
    from .platform.dashboard import render
    target=render(platform.store(context))
    context.add_output_metadata({'dashboard':MetadataValue.path(target)})
    return target

ASSETS=[geographic_reference,map_features,shipment_source,accepted_events,reference_changes,depot_history,
        service_coverage,capacity_plan,warehouse_inputs,delivery_sla,building_accessibility,map_change_audit,
        spark_compaction,quality_report,observability,lake_publication,warehouse_replication,operations_dashboard]
TERMINALS=[map_features,accepted_events,depot_history,service_coverage,delivery_sla,capacity_plan,
           building_accessibility,map_change_audit,spark_compaction,observability,
           lake_publication,warehouse_replication,operations_dashboard]
JOBS=[define_asset_job(name,selection=AssetSelection.assets(terminal).upstream(),description=purpose+'. '+concepts)
      for (name,purpose,concepts),terminal in zip(PIPELINES,TERMINALS)]
FULL=define_asset_job('full_platform_demo',selection=AssetSelection.assets(*ASSETS),
                      description='All local products including actual Spark compaction and serving replication.')
defs=Definitions(assets=ASSETS,jobs=JOBS+[FULL],resources={'platform':Platform()})
