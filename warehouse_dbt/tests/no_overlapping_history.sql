select a.entity_id from {{ ref('dim_depot_history') }} a
join {{ ref('dim_depot_history') }} b on a.entity_id=b.entity_id
 and a.valid_from < b.valid_from and (a.valid_to is null or a.valid_to > b.valid_from)
