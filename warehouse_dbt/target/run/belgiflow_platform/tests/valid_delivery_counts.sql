
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select * from "warehouse"."main"."mart_delivery_sla"
where shipments < delivered + cancelled or delivered < on_time or on_time < 0
  
  
      
    ) dbt_internal_test