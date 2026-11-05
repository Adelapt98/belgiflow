
    

    create  table
      "warehouse"."main"."fct_shipments"
  
    
    as (
      
select shipment_id, min(depot_id) as depot_id, min(source_date) as source_date,
  min(case when status='created' then cast(event_time as timestamptz) end) as created_at,
  max(case when status='delivered' then cast(event_time as timestamptz) end) as delivered_at,
  max(case when status='cancelled' then 1 else 0 end) as cancelled,
  min(longitude) as longitude,min(latitude) as latitude
from "warehouse"."main"."raw_events"

group by shipment_id
    );
    
  
  