# Verification record

Verified locally on 5 November 2026. Results describe the executed workloads, not production guarantees.

| Check | Result |
| --- | --- |
| Python tests including PostgreSQL CDC | 23 passed, including source-contract and simulated S3 failure checks |
| dbt | Three table models built, nine data tests passed |
| Dagster | Operational ingestion, dbt build, and dashboard asset completed successfully |
| PostgreSQL ordering | Later change ID committed first, earlier transaction still consumed after commit |
| PostgreSQL interruption | Local journal commit followed by simulated pre-ack failure replayed without duplicate changes |
| PostgreSQL to service history | 100 synthetic shipments evaluated through CDC-backed depot history |
| Spark generated workload | 100,000 synthetic shipments, 300,000 events, Spark 3.5.3 local two-worker execution |
| Spark pipeline integration | Read the pipeline's Parquet batch, reconciled 1,000 shipments and 3,000 events, persisted output |
| Overture release | 2026-10-21.0 |
| Live Brussels sample | 58 buildings, 24 transportation segments, 15 connectors |
| Belgian polygon | Retrieved national land boundary, bounding coordinates approximately 2.5455, 49.4970, 6.4081, 51.5051 |
| Source filtering | Live sample geometries clipped against the national polygon |
| Terraform | Initialized and validated locally, no AWS resources created |

The first broad source scan was stopped. STAC item filtering was then implemented and the small downloads succeeded. DuckDB's spatial extension was blocked by Windows application policy, so the working implementation uses Shapely and pyproj for geometry operations and needs only httpfs for remote Parquet.

The dashboard is generated HTML with offline SVG and an interactive depot filter. Its content is covered by an integration test. Cross-browser visual testing has not been performed.

National ingestion, distributed spatial joins, production CDC retention, S3 uploads, and actual Fargate execution have not been validated. The GitHub workflow has not run on GitHub. Do not present those capabilities as demonstrated deployments.

