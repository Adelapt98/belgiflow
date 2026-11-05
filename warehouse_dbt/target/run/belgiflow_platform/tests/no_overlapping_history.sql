
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select a.entity_id from "warehouse"."main"."dim_depot_history" a
join "warehouse"."main"."dim_depot_history" b on a.entity_id=b.entity_id
 and a.valid_from < b.valid_from and (a.valid_to is null or a.valid_to > b.valid_from)
  
  
      
    ) dbt_internal_test