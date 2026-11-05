select event_id,shipment_id,depot_id,status,revision,
  cast(event_time as timestamptz) as event_at,longitude,latitude
from raw_events
