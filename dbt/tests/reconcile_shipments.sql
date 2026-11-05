select 1 as failure
where (select sum(shipments) from {{ ref('mart_depots') }})
  <> (select count(*) from {{ ref('fct_shipments') }})
