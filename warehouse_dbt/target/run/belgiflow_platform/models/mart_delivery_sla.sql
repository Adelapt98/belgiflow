
    

    create  table
      "warehouse"."main"."mart_delivery_sla__dbt_tmp"
  
    
    as (
      select source_date,depot_id,count(*) as shipments,
  sum(case when delivered_at is not null and cancelled=0 then 1 else 0 end) as delivered,
  sum(case when cancelled=1 then 1 else 0 end) as cancelled,
  sum(case when cancelled=0 and delivered_at >= created_at
    and 
        (date_diff('minute', created_at::timestamp, delivered_at::timestamp ))
     <= 1440 then 1 else 0 end) as on_time,
  avg(case when cancelled=0 then 
        (date_diff('minute', created_at::timestamp, delivered_at::timestamp ))
     end) as average_delivery_minutes
from "warehouse"."main"."fct_shipments" group by source_date,depot_id
    );
    
  