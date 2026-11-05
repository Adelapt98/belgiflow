"""Behavioral contracts for the expanded data-product platform."""
import json
from pathlib import Path
import shutil
import duckdb
import pytest
from belgiflow.platform.store import Store
from belgiflow.platform import operations as op, geography as geo
from belgiflow.platform.warehouse import build_marts
from belgiflow.platform.quality import assess,observability
from belgiflow.platform.cloud import publish_lake,replicate,redshift_sql,register_catalog


def prepare(store,count=30):
    for function in [lambda s:op.shipment_source(s,count),op.accepted_events,op.reference_changes,
                     op.depot_history,op.service_coverage,op.capacity_plan,op.prepare_warehouse]:
        function(store)
    geo.geographic_reference(store,'fixtures')
    geo.map_features(store,'fixtures')
    geo.building_accessibility(store)
    geo.map_change_audit(store)
    build_marts(store)
    assess(store)
    observability(store)
    return store


@pytest.fixture(scope='module')
def product(tmp_path_factory):
    return prepare(Store(tmp_path_factory.mktemp('platform'),'2026-01-03'))


@pytest.fixture
def clone(product,tmp_path):
    target=tmp_path/'platform'
    shutil.copytree(product.root,target)
    return Store(target,product.partition)


def test_business_products_have_distinct_grains_and_reconcile(product):
    assert len(product.read('accepted_events'))==90
    assert len(product.read('service_coverage'))==30
    assert len(product.read('capacity_plan'))==3
    assert len(product.read('building_accessibility'))==20
    assert product.read_json('map_change_audit')['counts']==dict(added=1,removed=1,changed=1)
    assert product.read_json('quality_report')['status']=='passed'
    assert sum(r['shipments'] for r in product.read('delivery_sla'))==30


def test_changed_key_correction_is_incremental_and_replay_safe(clone):
    from belgiflow.batch import Ledger
    row=next(r for r in clone.read('accepted_events') if r['status']=='delivered')
    ledger=Ledger(clone.root/'state/events.sqlite')
    ledger.ingest([dict(row,status='cancelled',revision=row['revision']+1)])
    ledger.close()
    op.accepted_events(clone)
    op.service_coverage(clone)
    op.capacity_plan(clone)
    assert op.prepare_warehouse(clone)['changed_shipments']==1
    build_marts(clone)
    assert sum(r['cancelled'] for r in clone.read('delivery_sla'))==2
    assert op.prepare_warehouse(clone)['changed_shipments']==0
    build_marts(clone)
    assert sum(r['shipments'] for r in clone.read('delivery_sla'))==30


def test_another_date_adds_history_without_losing_previous_partition(clone):
    other=prepare(Store(clone.root,'2026-01-04'),30)
    assert sum(r['shipments'] for r in other.read('delivery_sla'))==60
    assert {r['source_date'] for r in other.read('delivery_sla')}=={'2026-01-03','2026-01-04'}
    assert {r['capacity'] for r in other.read('capacity_plan')}=={120}


def test_failed_dbt_quality_check_retains_pending_changes(clone):
    con=duckdb.connect(str(clone.root/'warehouse.duckdb'))
    identity=con.execute("SELECT shipment_id FROM raw_events WHERE status='created' LIMIT 1").fetchone()[0]
    con.execute("UPDATE raw_events SET status='dispatched' WHERE shipment_id=? AND status='created'",[identity])
    con.execute('INSERT INTO source_changed_shipments VALUES (?)',[identity])
    con.close()
    with pytest.raises(RuntimeError,match='dbt build failed'):
        build_marts(clone)
    con=duckdb.connect(str(clone.root/'warehouse.duckdb'))
    assert con.execute('SELECT count(*) FROM source_changed_shipments').fetchone()[0]==1
    con.close()


def test_local_lake_replication_is_idempotent_and_immutable(clone):
    manifest=publish_lake(clone)
    first=replicate(clone)
    assert replicate(clone)['tables']==first['tables']
    assert first['tables']['raw_events']==90
    assert first['tables']['daily_delivery_sla']==3
    immutable=clone.root/'lake'/manifest['tables']['raw_events']['key']
    immutable.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        replicate(clone)


def test_source_identity_and_warehouse_sql_are_constrained(clone):
    manifest=publish_lake(clone)
    statements=redshift_sql(manifest,'example-bucket','arn:aws:iam::123456789012:role/belgiflow-copy')
    assert len(statements)<=40
    assert sum('FORMAT AS PARQUET MANIFEST' in s for s in statements)==6
    with pytest.raises(ValueError):
        redshift_sql(manifest,"bucket';drop table",'arn:aws:iam::123456789012:role/example')
    registered=register_catalog(clone)
    assert registered['backend']=='local_schema_registry'


def test_job_catalog_exposes_distinct_independently_selectable_products():
    from dagster import Definitions
    from belgiflow.definitions import defs,PIPELINES,TERMINALS
    Definitions.validate_loadable(defs)
    assert len(PIPELINES)>=10
    assert len({a.key for a in TERMINALS})==len(PIPELINES)
    available={j.name for j in defs.resolve_all_job_defs()}
    assert {name for name,_,_ in PIPELINES}.issubset(available)
