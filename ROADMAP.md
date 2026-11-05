# Development roadmap

## Implemented product

BelgiFlow compares current and proposed service-hub networks in Belgium. The local workspace supports editable hubs, map-selected study areas, metric radius coverage, overlap, gaps, sampled-building assignments, and reproducible CSV/JSON reports. Guided alternatives demonstrate expansion, closure and radius changes. The same workspace exposes date-selectable daily operational reports with capacity, service exceptions, delivery reliability, review actions and source-quality evidence. Fifteen Dagster jobs support geographic reference, planning, synthetic operations, dbt, Spark, quality, publication, and serving.

## Reliable comparisons and fuller geography

Build resumable geographic tile acquisition with deduplication across boundaries. Offer explicit sample completeness indicators and source freshness in the planner. Validate larger Belgian workloads and retain source releases so saved plans can be reproduced after updates.

Add scenario import and a searchable scenario library. Show changes per hub and distinguish gains from coverage transferred between hubs. Improve keyboard access, map interaction, and validation feedback. Add recovery checks for interrupted report writes and concurrent local requests.

## Connect planning to operational impact

Evaluate the same synthetic shipment cohort against proposed hubs, showing changed assignment, coverage and capacity together. Keep baseline and proposed policies versioned and show why each shipment changes. Add visible scenario lineage so users can follow a comparison to its source partition and export.

Add configurable staffing and service costs before presenting any financial recommendation. Support explicit user-supplied non-personal aggregate workload rather than treating buildings as demand. Introduce user-defined delivery targets and explain how results change under those targets.

## More useful network decisions

Support exclusion zones, custom service polygons, and explicit geographic constraints. Add side-by-side comparisons of several alternatives and user-defined scoring weights. Explore public non-personal aggregate demand proxies only with clear provenance and coverage limitations.

Investigate road-network coverage and topology validation. Keep route distance, modeled travel time, and straight-line radius results visibly distinct. Add actual retained-release map comparisons and explain their effect on saved network decisions.

## Data reliability and operations

Extend schema compatibility checks, source-instance identity, multi-consumer outbox retention, journal restoration drills, and quarantine resolution. Improve concurrent-writer support beyond the serialized warehouse. Expand synthetic capacity, transfers, returns, and service commitments where they support meaningful operational comparisons.

## Authorized cloud validation

Deploy the optional AWS architecture only after authorization. Exercise real S3 publication, Glue processing, Redshift COPY, dbt serving models, private routing, and database bootstrap. Measure costs, backfill performance, and recovery. Offline contracts are not substitutes for live execution.

## Practical reference material

Document the product decisions behind each pipeline and add focused recovery exercises. Keep the working planner as the main product, with data engineering education as a secondary benefit.

These are genuine future development priorities. National completeness, production users, and live cloud validation are not claimed.
