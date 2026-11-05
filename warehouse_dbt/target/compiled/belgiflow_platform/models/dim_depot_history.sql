select entity_id,surrogate_key,cast(effective_at as timestamptz) as valid_from,
  cast(valid_to as timestamptz) as valid_to,is_current,capacity,radius_m,deleted
from "warehouse"."main"."depot_history"