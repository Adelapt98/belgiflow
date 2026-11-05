select depot_id,count(*) as shipments,
  count(*) filter(where delivered_at is not null and not cancelled) as delivered,
  count(*) filter(where not cancelled and delivered_at between created_at and created_at + interval '24 hours') as on_time
from {{ ref('fct_shipments') }} group by depot_id
