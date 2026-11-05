{{ config(materialized='incremental', unique_key='shipment_id', incremental_strategy='delete+insert') }}
select shipment_id, min(depot_id) as depot_id, min(source_date) as source_date,
  min(case when status='created' then cast(event_time as timestamptz) end) as created_at,
  max(case when status='delivered' then cast(event_time as timestamptz) end) as delivered_at,
  max(case when status='cancelled' then 1 else 0 end) as cancelled,
  min(longitude) as longitude,min(latitude) as latitude
from {{ source('operations','raw_events') }}
{% if is_incremental() %}
where shipment_id in (select shipment_id from {{ source('operations','source_changed_shipments') }})
{% endif %}
group by shipment_id
