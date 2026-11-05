"""User-facing pipeline purposes, outputs, and engineering concepts."""
PIPELINES = [
    ('01_geographic_reference','Belgian reference acquisition','Pinned public map snapshots, exact national clipping, source provenance'),
    ('02_daily_shipment_ingestion','Daily shipment cohorts','Date partitions, deduplication, late revisions, durable incremental ledger'),
    ('03_depot_cdc_history','Depot policy history','Transactional outbox, replay, delete tombstones, effective-time SCD Type 2'),
    ('04_service_coverage','Historical coverage exceptions','Temporal joins, CRS-aware distances, policy-effective service decisions'),
    ('05_delivery_sla','Delivery reliability','dbt incremental affected-key rebuilds, cancellations, on-time metrics'),
    ('06_depot_capacity','Depot workload planning','Capacity utilization, overload identification, correct aggregation grain'),
    ('07_building_accessibility','Map accessibility analysis','Spatial indexing, nearest sampled road, geometric distance'),
    ('08_map_change_audit','Map release audit','Snapshot comparison, additions, removals, geometry changes'),
    ('09_spark_compaction','Large event-batch compaction','PySpark deduplication, partitioned Parquet, local worker or AWS Glue'),
    ('10_quality_observability','Data-product health','Reconciliation, contracts, freshness, checksums, publication gates'),
    ('11_lake_publication','Versioned data-product delivery','Immutable objects, manifests, atomic completion pointer, local store or S3'),
    ('12_warehouse_replication','Warehouse replication','Staging, idempotent replacement, Redshift COPY manifests, transactional merge'),
    ('13_operations_dashboard','Operational review','Quality-gated marts, provenance, capacity and service exceptions'),
    ('14_catalog_registration','Lake schema discovery','Explicit schema registry, Glue Data Catalog, idempotent partition registration'),
]
