select source_date,depot_id,count(*) as shipments,
  sum(case when delivered_at is not null and cancelled=0 then 1 else 0 end) as delivered,
  sum(case when cancelled=1 then 1 else 0 end) as cancelled,
  sum(case when cancelled=0 and delivered_at >= created_at
    and {{ dbt.datediff('created_at','delivered_at','minute') }} <= 1440 then 1 else 0 end) as on_time,
  avg(case when cancelled=0 then {{ dbt.datediff('created_at','delivered_at','minute') }} end) as average_delivery_minutes
from {{ ref('fct_shipments') }} group by source_date,depot_id
