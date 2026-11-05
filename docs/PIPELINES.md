# Pipeline contracts and learning outcomes

All platform jobs operate on an explicit daily shipment cohort identified by its Europe/Brussels business date. Events are stored in UTC. Events that occur after midnight remain associated with their shipment cohort. This differs from partitioning by event arrival day.

## 01 Geographic reference

Produces a country boundary and selected map features. Public input mode uses a pinned Overture release. Fixture mode uses an explicitly synthetic polygon and geometries. Cached files must match the national boundary's release. A raw rectangular acquisition envelope is never labeled the Belgian national boundary.

## 02 Daily shipment ingestion

Produces raw and accepted event batches. A durable SQLite ledger identifies batches by content hash, deduplicates event identities, and retains higher revisions. Scenario version is explicit in generated identities. A correction can change an old event without passing an event-time watermark.

## 03 Depot CDC history

Uses PostgreSQL's transactional outbox when configured. An offline versioned-change fixture keeps the educational demo independent of a database server and is labeled accordingly. The real consumer acknowledges each source change after committing its local journal, avoiding the commit-order problem of a simple maximum-ID checkpoint.

The derived SCD Type 2 history uses half-open validity intervals. Late-effective changes rebuild affected history. This is effective-time history, not a full bitemporal database.

## 04 Historical service coverage

Joins each shipment to exactly one policy valid at creation time. Metric distances use EPSG:3812. One shipment produces one coverage record. A missing or ambiguous policy fails the job rather than inventing a service decision.

## 05 Delivery SLA

Loads accepted events into DuckDB and records changed shipment identities transactionally. dbt rebuilds those shipment facts using a portable incremental delete-and-insert strategy. Pending identities are acknowledged only after models and tests succeed. Event-time watermarks are deliberately avoided because they can miss late corrections.

SLA metrics distinguish cancellation, successful delivery, and on-time delivery. The initial commitment is a synthetic 24-hour service promise.

## 06 Depot capacity

Groups workload by depot and effective policy. Produces capacity, utilization, excess shipments, and geographic exceptions. Capacity is a fictional operational setting, not an inferred characteristic of real buildings or businesses.

## 07 Building accessibility

Builds a spatial index of sampled roads and measures each building centroid's nearest-road distance. The result concerns the supplied sample. It does not establish national road access, legal accessibility, or a routable delivery path.

## 08 Map change audit

Compares feature identity and normalized geometry across snapshots. The default scenario deliberately creates an added, removed, and modified feature to demonstrate the algorithm. It is labeled synthetic. The library accepts an actual previous snapshot for genuine two-release comparisons.

## 09 Spark compaction

Runs a PySpark job through the local worker or AWS Glue. It validates required fields, rejects equal revisions with different payloads, deduplicates by event identity and revision, writes depot-partitioned Parquet, and reconciles distinct shipment counts. The local worker accepts only confined input and output paths and a fixed script, not arbitrary commands.

## 10 Quality and observability

Reconciles accepted shipments, coverage decisions, capacity workloads, and dbt SLA counts. Checks effective history and lifecycle consistency. Observability records row counts, bytes, checksums, and artifact freshness. Historical business dates are not automatically classified as stale ingestion.

## 11 Lake publication

Exports typed, ordered Parquet serving tables and a pinned geographic bundle. Content-addressed generations distinguish business and map changes. Completion and current pointers are written only after all objects and manifests succeed. Local filesystem execution is a real local delivery backend, not a claim that AWS has been tested.

## 12 Warehouse replication

Loads the immutable published generation into a separate serving warehouse. Locally, a DuckDB transaction stages and replaces matching keys. In AWS, a Redshift Data API transactional batch creates staging tables, uses explicit Parquet COPY manifests with content lengths, and replaces matching target keys. The same dbt models then run against the serving target.

Local execution verifies semantics and outputs. Offline SDK tests validate AWS request shapes. Neither establishes successful Redshift execution without a cloud deployment.

## 13 Operations dashboard

Publishes quality-gated SLA, capacity, coverage, geographic provenance, and the pipeline catalog. It is an educational operational review interface. The dashboard is generated HTML rather than a hosted multi-user application.

## 14 Catalog registration

Registers the raw event schema and immutable partition in the local schema registry or Glue Data Catalog. Existing Glue partitions are treated as idempotent registrations. The table schema follows the exact ordered Parquet export contract.

## Backfills and consistency

Choose a date partition in Dagster to rerun or backfill a cohort. Upstream dependencies are included in each named job. The shared local warehouse supports one writer at a time. Dagster instance configuration limits concurrent runs and writer-pool operations.

There is no distributed transaction across source PostgreSQL, the local journal, Parquet, dbt, S3, and Redshift. Durable inputs and idempotent publication support recovery. Source outbox retention and journal restoration still require an explicit operational policy.
