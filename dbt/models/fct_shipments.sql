select shipment_id,min(depot_id) as depot_id,
  min(event_at) filter(where status='created') as created_at,
  max(event_at) filter(where status='delivered') as delivered_at,
  count(*) filter(where status='cancelled') > 0 as cancelled,
  min(longitude) as longitude,min(latitude) as latitude
from {{ ref('stg_events') }}
group by shipment_id
