select 1 as failure where
 (select sum(shipments) from {{ ref('mart_delivery_sla') }}) <>
 (select count(distinct shipment_id) from {{ source('operations','raw_events') }})
