# Runbook

## Local profiles

The default demo is deterministic and does not download map data. `--full-demo` also writes Parquet, historical coverage, the warehouse, and an offline HTML dashboard. `scripts/verify_dagster.py` runs the complete operational workflow through dbt validation before final dashboard publication.

The real-map demo is intentionally small. `--refresh-map demo` obtains the national polygon and three feature samples. A raw rectangle is not the national boundary. Silver outputs are clipped against the Belgian land polygon.

The `belgium` profile is experimental. It requests substantially more data and may hit the one-gigabyte DuckDB memory limit or five-minute query deadline. National tiling, aggregate deduplication, resumable partition scheduling, and full-country performance validation remain planned work. Do not interpret the presence of a national option as evidence of national-scale execution.

## Replay and backfill

`Ledger.ingest` identifies batches by their content hash and retains the highest accepted event revision. Replaying the same batch does not add duplicate events. Ingest a corrected batch with higher logical event revisions to change accepted records.

Operational Parquet and warehouse tables are derived snapshots. Rebuild them by rerunning the pipeline. Do not manually edit published JSON files. The publication pointer verifies its referenced file checksum.

A production date-partitioned backfill scheduler is not implemented. Use the ledger API for bounded historical batches and validate the resulting snapshots. The Dagster job currently orchestrates a complete local refresh of accepted operational data.

## Failures and recovery

- Failed source download: the final manifest is absent. Rerun the same pinned release and extent. Completed checksummed files are reused. An incomplete Parquet file is not treated as complete.
- Invalid source geometry: exact clipping fails rather than silently publishing it.
- Bad operational record: inspect `quarantine` in the SQLite ledger. A critical quarantine blocks new publication. Fix the source and resolve the quarantine explicitly after review. There is no automatic discard command.
- Conflicting revision: the entire incremental batch rolls back. Supply an unambiguous higher revision.
- Crash before CDC acknowledgement: replay the unacknowledged changes. Local journal primary keys deduplicate them.
- Lost CDC journal: do not reuse the existing source acknowledgement identity. Restore the journal from backup or deliberately initialize a new consumer and replay all retained source changes.
- Failure after a warehouse write: rerun from the durable ledger. Do not run concurrent local writers.
- Failed dbt check: the final Dagster dashboard asset does not execute. A previous dashboard may still exist and must not be mistaken for a successful current run.

Source outbox retention is intentionally not automated. Never purge source changes required by a consumer or an audit rebuild.

## Tests

```bash
python -m pytest tests -q
python scripts/verify_dagster.py
```

The PostgreSQL integration test is skipped unless `BELGIFLOW_TEST_DSN` is set. It truncates project tables in the selected database. Use only a separate disposable test database. Never point it at a source database you want to retain.

CI defines a disposable PostgreSQL service and a separate Spark job. GitHub execution remains unverified until publication.

## Docker

```bash
docker build -t belgiflow:local .
docker run --rm belgiflow:local
```

Mount a writable local data directory at `/app/data` to retain outputs. The image runs as an unprivileged user. Without a volume, output is discarded when the container is removed.

## Optional AWS deployment

Terraform configuration under `infra` declares private S3 storage, encryption, versioning, incomplete-upload cleanup, ECR, CloudWatch logs, IAM roles, an ECS cluster, and a Fargate task definition.

Validation does not create infrastructure:

```bash
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
```

Deployment has not been executed. It requires explicit authorization, standard local AWS credentials, a unique bucket name, and a valid immutable image URI. Build and push the application to ECR, then set `container_image` to its digest. Deploy storage and ECR first using an intentional staged deployment if needed.

Run an ECS task in subnets and security groups you control. The repository does not create a VPC or NAT gateway. Provide network access for ECR image retrieval, CloudWatch logging, and S3 publication. Do not expose PostgreSQL or the dashboard publicly by default.

When `BELGIFLOW_BUCKET` is set, the application uploads the generated dashboard files and checksum pointer under `belgiflow/dashboard`. S3 remains private. The container's default command runs the synthetic workflow, not national map ingestion or Spark.

Charges can include Fargate runtime, ECR storage, logs, S3 versions, requests, and network services. No cost estimate is claimed without a selected workload and region. Before teardown, retain anything needed, remove ECS tasks and ECR images, and explicitly empty all S3 object versions if deleting the bucket. Terraform does not force-delete retained data.

Kubernetes, Glue, Athena, and Sedona have not been added merely as placeholders. Their inclusion requires a concrete workload and further validation.
