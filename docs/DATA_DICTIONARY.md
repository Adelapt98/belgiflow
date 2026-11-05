# Data dictionary and contracts

| Dataset | Grain and identity | Time and update behavior |
| --- | --- | --- |
| Raw map sample | Feature ID within theme and pinned release | Immutable observed release, checksum-verified reuse |
| Silver map features | Unique feature ID per clipped output | Clipped against the Belgian land polygon |
| Event ledger | Event ID, highest accepted revision | Event time is timezone-aware, batch observation is UTC |
| Quarantine | Batch content hash and rejected position | Blocks publication until investigated |
| Outbox | PostgreSQL change ID | Written in the same transaction as the depot change |
| CDC journal | Source change ID for one source and consumer | Committed locally before source acknowledgement |
| Depot history | Entity ID and effective timestamp | Half-open validity intervals, current flag, stable surrogate key |
| Shipment coverage | Shipment ID | Uses the service policy effective when the shipment was created |
| dbt shipment fact | Shipment ID | Creation, delivery, and cancellation derived from accepted events |
| Depot mart | Depot ID | Shipment, delivered, and on-time counts |

## Time and correction semantics

Timestamps are UTC with timezone offsets. Brussels business-time conversion must account for daylight-saving changes. A higher event revision replaces an earlier version of the same logical event. Equal revisions with conflicting payloads are rejected rather than selecting an arbitrary winner.

Cancellation excludes a shipment from delivered and on-time counts. On-time delivery requires delivery between creation and the synthetic 24-hour commitment. Incomplete shipments remain in total shipments.

Historical depot changes rebuild effective-time intervals so a late-effective update can split existing history. CDC deletions use their observed deletion time as the effective tombstone because the source delete operation supplies no separate business-effective timestamp.

## Consistency limits

The source outbox is transactional. Source-to-journal delivery is at least once with idempotent inserts. Per-row acknowledgements avoid skipping a transaction that commits after a higher change ID has already been processed.

There is no distributed transaction across PostgreSQL, SQLite, Parquet, DuckDB, and publication. Derived outputs can be rebuilt from durable accepted inputs. Publication uses immutable content files and an atomic local pointer. The warehouse and dashboard support a single active local writer.

The current event ledger rejects incompatible data. A general automatic schema-migration framework is not implemented. Unknown geographic reporting regions, full road-network topology, and routed travel distances are outside the initial operational mart.
