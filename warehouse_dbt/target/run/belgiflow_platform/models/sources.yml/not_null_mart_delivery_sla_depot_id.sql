
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select depot_id
from "warehouse"."main"."mart_delivery_sla"
where depot_id is null



  
  
      
    ) dbt_internal_test