select * from {{ ref('mart_delivery_sla') }}
where shipments < delivered + cancelled or delivered < on_time or on_time < 0
