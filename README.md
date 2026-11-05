# BelgiFlow

A Belgium-focused batch data platform combining Overture map features with synthetic logistics operations. Built for personal learning and continued development.

Implementation is in progress. No live source ingestion, national coverage, Spark workload, or deployment has been validated yet.

## Design

Python downloads pinned map releases and generates fictional operational events. PostgreSQL captures transactional reference changes. Parquet stores batch inputs. DuckDB and dbt publish analytical marts. Dagster coordinates partitions and recovery. Spark handles larger event batches, with spatial processing added where justified.

Public map data and invented operational records remain separate. No real customer, driver, or shipment records are used. Original software will use MIT. Source datasets retain their own licenses and attribution obligations.
