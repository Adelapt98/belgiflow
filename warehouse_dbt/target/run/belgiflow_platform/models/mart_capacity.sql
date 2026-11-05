
    

    create  table
      "warehouse"."main"."mart_capacity__dbt_tmp"
  
    
    as (
      select depot_id,source_date,policy_key,capacity,shipments,outside_coverage,
  utilization,excess_shipments from "warehouse"."main"."capacity_plan"
    );
    
  