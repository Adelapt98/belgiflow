# Development roadmap

## Implemented baseline

Synthetic event generation, correction-aware deduplication, SQL depot summaries, effective-time dimension rebuilding, polygon clipping, metric distances, immutable output publication, and offline CI configuration.

## Next integration milestones

1. Replace broad remote scans with catalog-selected files, bounded timeouts, retry manifests, and restartable tile ingestion.
2. Discover and verify the Belgian national polygon. Integrate exact clipping into source ingestion and validate transportation and building profiles.
3. Build a PostgreSQL transactional outbox with durable consumption and commit-order integration tests. It is not implemented yet.
4. Connect historical service policies and spatial coverage to shipment marts.
5. Execute PySpark event processing and assess Sedona against measured workload needs.
6. Add dbt models, Dagster assets and partitioned recovery, and the operational dashboard.
7. Verify clean-checkout installation, national resource limits, and source licensing details.
8. Prepare and validate an optional Terraform AWS deployment. Kubernetes remains deferred.

These are substantive planned integrations rather than claims of completed functionality. No production or national deployment is claimed.
