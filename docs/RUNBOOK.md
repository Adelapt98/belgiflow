# Runbook

## Start and stop

```bash
docker compose --profile ui up -d --build planner dagster spark-worker
docker compose --profile ui stop planner dagster spark-worker
```

Open http://localhost:8080 for planning, after preparing cached geography. Use the Python fixture command in the README for a fresh offline demo. Open http://localhost:3000 for orchestration. Jobs 01 through 15 are separately launchable. Select a date partition such as `2026-01-03`. Each job includes its upstream dependencies. `full_platform_demo` includes the complete graph and requires the Spark worker.

Do not restart an older manually created `belgiflow-dagster` container on the same port. Use the Compose service `belgiflow-dagster-1`.

The local UI mounts the source tree and the expanded `warehouse_dbt` project. Rebuild the image after dependency changes. Reload the code location or restart the UI after graph changes. Read-only project mounts are compatible with dbt because generated logs and targets go to the selected writable data partition.

## Source modes

- `fixtures`: explicitly synthetic geographic data, no external data access.
- `cached`: previously downloaded Overture boundary and three feature samples.
- `live`: download public samples and pin one release before processing.
- `s3`: read a checksummed immutable geographic bundle from the configured lake bucket.

Public data source details are in SOURCES.md. Operational events are synthetic in every mode.

## Daily partitions and backfills

Use Dagster's date-partition selection and backfill controls. One UI run is allowed at a time because the local warehouse is shared. Different cohorts retain their accepted source events and historical dbt shipment facts. Coverage and capacity Parquet artifacts are independently retained per date.

Replaying an unchanged source cohort does not add duplicate events. Higher event revisions rebuild affected shipment identities. Scenario version is explicit so a changed generator does not silently redefine an existing source identity.

Source changes are journaled before acknowledgement. A restarted consumer replays unacknowledged changes safely. Never purge source outbox rows required by a consumer.

## PostgreSQL

```bash
docker compose up -d postgres
```

The development database uses trust authentication on a localhost-only port. It is disposable local infrastructure. Do not expose it publicly.

Set BELGIFLOW_DSN in the process launching a CLI job, or pass it to the UI container environment. A container reaches a Compose database through `postgres:5432`, not its own localhost. A host process reaches the published development port 55432.

Initialize the source with `belgiflow.cdc.seed_demo`. Without a DSN, the history job uses explicitly labeled versioned change fixtures. The PostgreSQL consumer itself has real transactional integration tests.

The pytest DSN must reference a separate disposable database. Integration tests truncate project tables in that test database.

## Recovery

- A source download without a completed manifest is incomplete. Rerun the pinned request.
- A changed file checksum blocks reading rather than silently accepting corrupted data.
- A conflicting event revision rolls back its incremental batch.
- A quarantine or reconciliation failure blocks downstream publication.
- A failed dbt build retains pending changed shipment IDs for a later retry.
- A failed upload cannot advance the successful completion pointer.
- A failed serving-table load rolls back its local transaction. Redshift uses a transactional Data API batch.
- An interrupted Spark worker requeues claimed requests when its container restarts. Worker requests have a bounded execution deadline and confined file paths.
- A lost CDC journal requires restoration or a deliberately new consumer identity. Do not retain acknowledgements while discarding the corresponding journal.

A previously published dashboard can remain after a failure. Use Dagster run status and the partition's quality timestamp to distinguish old results from a current successful run.

## Locations

- `data/platform/state/`: durable accepted-event and CDC journals.
- `data/platform/partitions/<date>/`: data products, checksums, reports, dbt output, and dashboard snapshots.
- `data/platform/lake/`: local immutable publication backend.
- `data/platform/warehouse.duckdb`: ingestion and analytical build warehouse.
- `data/platform/serving.duckdb`: separately replicated serving warehouse.
- `data/platform/spark_queue/`: Spark requests, completion reports, and logs.
- `data/platform/index.html`: latest operational dashboard.

All are excluded from Git. Back them up when their recovery history matters.

## Tests and cloud

Run `python -m pytest tests -q` and `python scripts/verify_dagster.py`. SDK-stub tests require no AWS account and do not contact AWS. The configured GitHub workflow has not been executed remotely yet.

For optional AWS implementation, read AWS.md. Local tests, parser checks, and Terraform validation are distinct from live Glue or Redshift verification.
