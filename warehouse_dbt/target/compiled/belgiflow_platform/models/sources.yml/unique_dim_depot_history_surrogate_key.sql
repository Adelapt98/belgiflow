
    
    

select
    surrogate_key as unique_field,
    count(*) as n_records

from "warehouse"."main"."dim_depot_history"
where surrogate_key is not null
group by surrogate_key
having count(*) > 1


