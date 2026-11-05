
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select source_date
from "warehouse"."main"."mart_delivery_sla"
where source_date is null



  
  
      
    ) dbt_internal_test