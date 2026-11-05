# Verification record

Verified locally on 5 November 2026. No AWS resources were provisioned.

| Check | Result |
| --- | --- |
| Full regression suite | 50 passed, including isolated PostgreSQL integration and offline AWS contracts |
| Dagster definitions | Fifteen distinct named jobs, twenty-one assets, plus the full graph |
| Full UI graph | SUCCESS, run `c1ad0619-0df0-43d7-a4e0-2c26569ba0bb` |
| Full-graph cohort | 300 synthetic shipments and 900 accepted events for 2026-01-03 |
| Data quality | Coverage, capacity, SLA, event identities, and policy history reconciled |
| New dbt project | Five models and ten data tests run against the local build and serving targets |
| Incremental corrections | Higher event revision rebuilt one affected shipment, replay preserved counts |
| Multiple partitions | A second cohort retained the first cohort's shipment facts |
| Failed dbt check | Pending changed shipment IDs remained available for retry |
| PostgreSQL CDC | Commit-order inversion, deletes, interruption, and replay verified in a disposable database |
| Spark integration | Dagster dispatched the shared worker and executed the compaction script successfully |
| Earlier Spark workload | 100,000 synthetic shipments and 300,000 events executed in the separate scaling reference job |
| Public geography | Actual Belgian boundary, 58 buildings, 24 road segments, 15 connectors from Overture release 2026-10-21.0 |
| Lake and serving | Immutable local delivery and six replicated serving tables verified |
| S3 publication | Offline success-pointer and failure contracts verified |
| Geographic cloud bundle | Pinned checksum-verified S3-style roundtrip tested offline with source provenance retained |
| Redshift Data API | Real SDK request shape validated offline with Stubber |
| Glue dispatch and catalog | Real SDK request shapes validated offline with Stubber |
| Redshift dbt adapter | Adapter installed and project parsed successfully without a warehouse connection |
| Terraform | Optional Glue, Redshift, network, storage, and IAM configuration validated locally |
| Application image | Expanded image built with locked runtime dependencies |

The full graph is visible in the running Dagster UI. Its initial combined run exposed shared-volume permissions on Windows. The local Compose service was corrected and the next full graph run succeeded. That failure is retained in the genuine run history.

Live AWS execution, IAM/database bootstrap, Glue runtime compatibility, private routing, and cloud costs remain unverified. No SDK-stub test is presented as a real AWS service run. GitHub CI is configured but has not run remotely.

National coverage and performance are not claimed. The map-change teaching scenario is explicitly synthetic unless an actual previous snapshot is supplied. Building accessibility concerns sampled roads, not routing or real travel time.

## Interactive planning product

The complete suite passed after adding the planner: 50 tests in 66.50 seconds, including the disposable PostgreSQL database and offline AWS contracts. Fifteen planner checks cover geometric unions, overlap without triple counting, gains and losses, validation, CSV formula safety, exports, local Host/Origin restrictions, and static path containment.

The actual cached public example produced 6.1569 km² current coverage, 13.2651 km² proposed coverage, 7.1082 km² gained, 0.9335 km² overlap, and 58 sampled buildings covered. These are straight-line radius calculations, not routing or demand estimates.

Browser checks exercised copying the current network, recalculation, resetting the example, inspecting the sample, and choosing the map extent as a study area. The final screenshot is a real interface capture. Job `15_network_planning` succeeded against cached public inputs in run `78c03f57-c305-4d8c-964c-f725818bfe8c`. The local Docker image was rebuilt with the planner and packaged web assets.

A clean temporary application container also loaded the packaged planner, web assets, vendor license, and offline geometry. Saved public reports reproduced the same plan ID, while a changed geographic source fingerprint was rejected.
