# Data dictionary

| Product | Grain or key | Storage and update behavior |
| --- | --- | --- |
| Geographic reference | One pinned reference per selected cohort | JSON geometry and provenance, public or explicit fixture |
| Map features | Kind and feature ID within release | WKB geometry in Parquet, exact reference-polygon filtering |
| Shipment source | Event delivery in a business-date cohort | Synthetic deterministic batches with duplicate deliveries |
| Accepted events | Scenario and event ID, highest revision | Durable SQLite ledger and partitioned Parquet |
| Reference changes | Source change identity or labeled fixture revision | PostgreSQL outbox journal or offline scenario |
| Depot history | Entity and effective timestamp | Half-open SCD Type 2 intervals and stable surrogate key |
| Service coverage | Shipment ID | Historical policy match and metric radius decision |
| Capacity plan | Date, depot, policy key | Workload, capacity utilization, excess shipment count |
| Shipment fact | Shipment ID | dbt incremental affected-key rebuild |
| Delivery SLA | Date and depot | Shipments, delivered, cancelled, on time, average delivery minutes |
| Building accessibility | Building feature ID | Distance to nearest sampled road |
| Map audit | Feature identity and comparison scope | Added, removed, modified IDs with explicit provenance |
| Observability | Dataset and selected cohort | Artifact age, bytes, row counts, verified checksum |
| Lake generation | Content hash of tables and geographic objects | Immutable files, COPY manifests, completion pointer |
| Serving warehouse | Explicit per-table keys | Local transaction or Redshift staged transactional replacement |
| Catalog partition | Date and generation | Local schema registry or Glue Data Catalog registration |

The cohort date uses Europe/Brussels. Event timestamps are UTC. Events crossing midnight retain their cohort identity. A late revision is not discarded because its event timestamp is old.

Current policy history is effective-time history. Source deletion has no separate business-effective timestamp, so its tombstone uses observed deletion time. Full bitemporal reporting is future work.

The local warehouse accumulates accepted events and shipment facts across dates. Partition artifacts retain coverage and capacity history. Some local staging reference tables represent the currently processed cohort, while serving replication uses explicit date-and-identity keys.

No distributed transaction spans the source database, local journals, object storage, dbt, and serving warehouse. Idempotent writes, retained source identities, checksums, and explicit publication boundaries support recovery.
