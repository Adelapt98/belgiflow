select depot_id,source_date,policy_key,capacity,shipments,outside_coverage,
  utilization,excess_shipments from {{ source('operations','capacity_plan') }}
