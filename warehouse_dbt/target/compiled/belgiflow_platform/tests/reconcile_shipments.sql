select 1 as failure where
 (select sum(shipments) from "warehouse"."main"."mart_delivery_sla") <>
 (select count(distinct shipment_id) from "warehouse"."main"."raw_events")