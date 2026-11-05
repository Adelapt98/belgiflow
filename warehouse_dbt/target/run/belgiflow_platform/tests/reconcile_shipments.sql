
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select 1 as failure where
 (select sum(shipments) from "warehouse"."main"."mart_delivery_sla") <>
 (select count(distinct shipment_id) from "warehouse"."main"."raw_events")
  
  
      
    ) dbt_internal_test