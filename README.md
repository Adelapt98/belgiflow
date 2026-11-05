# BelgiFlow

A Belgium-focused batch data platform combining Overture map features with synthetic logistics operations. Built for personal learning and continued development.

Implementation is in progress. No live source ingestion, national coverage, Spark workload, or deployment has been validated yet.

## Run the current baseline

Use Python 3.12 in a virtual environment.

```bash
pip install -e '.[dev]'
python -m pytest tests -q
python -m belgiflow.cli --shipments 1000
```

The demo publishes checksum-verified synthetic summaries beneath `data/published`. It currently covers event normalization and depot-level SQL summaries, not the full planned platform.

Local verification: seven tests passed and a 1,000-shipment demo produced 3,000 normalized events. The live Overture catalog returned release `2026-10-21.0`. A remote building scan was interrupted before completion, so no successful live map download is claimed. PostgreSQL, Spark, dbt, Dagster, dashboard, and cloud integration remain pending.

## Design

Python downloads pinned map releases and generates fictional operational events. PostgreSQL captures transactional reference changes. Parquet stores batch inputs. DuckDB and dbt publish analytical marts. Dagster coordinates partitions and recovery. Spark handles larger event batches, with spatial processing added where justified.

Public map data and invented operational records remain separate. No real customer, driver, or shipment records are used. Original software will use MIT. Source datasets retain their own licenses and attribution obligations.
