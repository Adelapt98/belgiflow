# Learning exercises

Use a separate local data directory for experiments. All operational records in these exercises are synthetic.

## 1. Read the graph before running it

Open Dagster, select job 13, choose partition `2026-01-03`, and inspect its upstream assets. Run it and find accepted events, depot history, service coverage, capacity, SLA models, quality checks, and the dashboard in the event log.

Expected observation: separate data products share dependencies. The dashboard is published after quality checks rather than calculating directly from a raw file.

## 2. Compare capacity before and after a policy change

Run job 06 for `2026-01-03` and `2026-01-04` with 300 shipments per cohort. Inspect the capacity plans and effective policy keys.

Expected observation: the synthetic scenario increases depot capacity from 80 to 120 and expands its radius on the second date. A temporal join should use the correct policy for each shipment rather than today's setting for all history.

## 3. Demonstrate incremental replay

Run job 02 twice for the same date and shipment count. Compare the accepted row count and event identities.

Expected observation: duplicate source delivery does not create additional accepted events. The raw scenario includes duplicates and a higher-revision cancellation.

## 4. Study a late correction

Read `test_changed_key_correction_is_incremental_and_replay_safe` in `tests/test_platform.py`. It submits a new revision of an old event, rebuilds only its affected shipment, and checks that a repeated build does not increase fact counts.

Expected observation: an event-time-only watermark would be insufficient. The ledger and pending changed-shipment set provide the relevant update identities.

## 5. Break a warehouse contract safely

Read or run `test_failed_dbt_quality_check_retains_pending_changes`. It removes a creation status in a temporary test warehouse and executes actual dbt checks.

Expected observation: a failed build retains pending changes. Successful model execution alone is insufficient to acknowledge source work when a relational check fails.

## 6. Trace a CDC interruption

Run the PostgreSQL integration test against a disposable test database. Follow the transaction that obtains a smaller change ID but commits after another transaction. Then examine the simulated interruption before source acknowledgement.

Expected observation: per-change acknowledgements avoid skipped commits, and replay does not duplicate the local journal.

## 7. Compare local SQL and Spark responsibilities

Run job 09 with the Spark worker active. Inspect depot-partitioned event files and status aggregates. Compare its distinct shipment count with the accepted source.

Expected observation: Spark performs real computation and reconciliation. Its small local demonstration does not prove that Spark is faster or necessary at every scale.

## 8. Understand publication boundaries

Read the local lake's generation manifest and completion marker. Run `test_s3_failure_does_not_advance_success_pointer` and `test_local_lake_replication_is_idempotent_and_immutable`.

Expected observation: partial delivery is not a completed data product. Immutable manifests and checksums separate accepted publication from files that merely exist.

## 9. Review the AWS differences

Read AWS.md and identify what local execution cannot validate: IAM grants, private routing, real Glue compatibility, Redshift COPY, and cost. Inspect the SDK-stub tests to see which API shapes are verified offline.

Expected observation: a locally tested adapter and a validated Terraform file are preparation for a cloud deployment, not evidence that it has happened.
