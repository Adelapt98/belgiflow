# Development roadmap

## Working local release

- Real pinned Overture building, road-segment, connector, and national-boundary ingestion.
- Exact polygon filtering and projected straight-line distance calculations.
- Incremental synthetic event ledger, correction handling, replay, quarantine, and publication checksums.
- Transactional PostgreSQL change capture with commit-order and interruption tests.
- Effective-time depot history connected to service coverage.
- Parquet and DuckDB outputs, dbt shipment models and reconciliation.
- Dagster workflow and a dashboard published from tested dbt marts.
- Executed Spark batch processing and pipeline-Parquet integration.
- Docker packaging, locked dependencies, CI configuration, and locally validated Terraform.

## Reliability and national coverage

Build a tile planner with resource estimates, per-partition retries, restartable scheduling, and nation-wide feature deduplication. Verify Belgian national workloads on measured disk and memory budgets. Add region-level marts and explicit treatment of cross-border road-network references.

Extend source schema contracts and compatibility checks across retained releases. Add connector integrity checks and actual two-release map-change reports. The current snapshot comparison has synthetic fixture coverage.

## Historical operations

Add date-partitioned event ingestion and Dagster backfill jobs, configurable service commitments, and richer synthetic cancellation and correction scenarios. Add bitemporal reporting where business-effective time differs from observation time.

Develop a reviewed quarantine resolution workflow and multi-consumer outbox retention policies. Add source-instance identity checks and disaster-recovery drills for journal loss and database restoration.

## Distributed geospatial processing

Measure the threshold where spatial SQL becomes a bottleneck. Evaluate Sedona for large spatial joins, compare outputs against the local reference, and only adopt it when results and operational costs justify the additional runtime.

## Product and deployment

Add regional filters, service-zone overlays, coverage exception inspection, and persistent run-health reporting to the dashboard. Keep synthetic and public geographic records visibly distinct.

Execute an authorized AWS deployment, test actual ECR-to-Fargate execution and S3 publication, and verify teardown and costs. Add cloud recovery and access-control tests before calling it a supported deployment.

These are genuine future engineering milestones. No users, production deployment, national-scale performance, or program acceptance is claimed.
