# Development roadmap

## Implemented local platform

Fourteen independently launchable Dagster jobs now cover geographic reference, daily shipment ingestion, depot history, service coverage, delivery SLAs, capacity planning, building accessibility, map audits, Spark compaction, quality, lake publication, warehouse replication, dashboard review, and catalog registration.

Implemented concepts include date partitioning, durable incremental ingestion, transactional CDC, effective-time SCD Type 2, late revisions, affected-key dbt builds, temporal and spatial joins, Parquet compaction, immutable manifests, SDK-backed cloud adapters, and transactional serving replication.

## Reliability and national scale

Implement a resource-aware national tile planner, resumable tile scheduling, and cross-tile feature deduplication. Validate actual Belgian national workloads and road-network references. Extend source schema compatibility checks and quantify the limits of sampled-road accessibility metrics.

Add source-instance identity checks, multi-consumer outbox retention, journal restoration drills, and a reviewed quarantine-resolution workflow. Improve concurrent-writer support beyond the deliberately serialized local setup.

## Richer operational scenarios

Add synthetic transfers between depots, variable service commitments, returns, and capacity changes during the business day. Introduce business-effective versus observation-time reporting where bitemporal semantics are needed. Expand regional reporting using verified geographic divisions.

## Geographic development

Build genuine retained-release map comparisons alongside the controlled teaching scenario. Add road-network topology validation and routing experiments only with clear separation from real traffic or actual travel-time claims.

## Authorized cloud execution

Deploy the implemented optional AWS architecture only after approval. Bootstrap database privileges, execute actual S3 publication and Glue jobs, test Redshift COPY and dbt, verify network routes, and measure costs and recovery. Offline SDK contracts do not substitute for these checks.

## Product and educational use

Add guided exercises that intentionally introduce late corrections, failed contracts, partial uploads, and recoverable warehouse failures. Explain the expected observations in Dagster. Improve the dashboard with partition selection, geographic overlays, coverage exception inspection, and historical run-health comparisons.

This is genuine planned work. The project does not claim production users, a national deployment, live cloud validation, or guaranteed BYOP acceptance.
