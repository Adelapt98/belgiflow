# Service-network planner

The planner compares two sets of radius-based service hubs inside a Belgian study area. It is intended for preliminary network comparison, not dispatch or travel-time prediction.

## Inputs

Launch `python -m belgiflow.planner.server --source-mode fixtures` for invented offline geometry, or use `cached` after acquiring public inputs. The default address is localhost:8080. The app is a local single-user workspace without an authentication service.

Each scenario has a name and up to twenty hubs. Hubs have a unique ASCII ID, display name, longitude, latitude, and radius in metres. Radii range from 100 to 50,000 metres. Centres must fall inside the loaded Belgian reference. Study-area bounds are ordered west, south, east, north.

The example request is defined in `src/belgiflow/planner/engine.py`. Edit hubs using the workspace, or export JSON to obtain the complete validated request. Use map extent selects the current map bounds as the study area. Inspect sample zooms to the available public footprints without implying national completeness.

## Geometry and interpretation

The engine projects into EPSG:3812 for metric buffers and area. Hub circles are clipped to the study area and country boundary. Pairwise overlap intersections are unioned, so triple coverage is not counted multiple times. Buildings are represented by interior points and counted once. The nearest covering hub receives the assignment, with stable ID ordering resolving ties.

Gains and losses compare geometric unions, rather than subtracting headline totals. A larger total can still include a lost area elsewhere. Footprints do not measure population or demand. Straight-line radius coverage does not establish road access or travel time.

## Reports and reproduction

Compare saves a report under `data/planner/comparisons/<plan_id>.json`. CSV summarizes scenario metrics and sampled-building assignments. JSON also includes input requests, source identity, assumptions, and output geometry. The plan ID derives from validated inputs and the geographic source identity. Changing inputs marks the interface as needing recalculation and disables stale exports.

Run the corresponding Dagster job with `BELGIFLOW_PLANNING_CONFIG` pointing to the exported JSON file. It accepts a raw request too. An exported report with a different geographic fingerprint is rejected to avoid silently presenting a new source as the original analysis. To intentionally reevaluate against a new reference, provide its raw `request` explicitly.

Job output is `network_plan.json` and `network_plan.csv` in the chosen platform date partition. App comparison files and date-partitioned job outputs serve different workflows.

## Local service boundaries

The server restricts Host and Origin to its local interface, validates request types and sizes, and serves only packaged web assets. It is not prepared as an internet-facing multi-user service. Leaflet is vendored locally. Optional OpenStreetMap tiles are browser requests and can be disabled for vector-only offline inspection.
