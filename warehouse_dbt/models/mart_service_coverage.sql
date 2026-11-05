select source_date,depot_id,count(*) as shipments,
  sum(case when covered then 1 else 0 end) as covered_shipments,
  avg(distance_m) as average_straight_line_m
from {{ source('operations','service_coverage') }} group by source_date,depot_id
