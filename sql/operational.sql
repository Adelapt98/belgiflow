CREATE TABLE IF NOT EXISTS depot (
  entity_id text PRIMARY KEY,
  capacity integer NOT NULL CHECK (capacity > 0),
  effective_at timestamptz NOT NULL,
  revision integer NOT NULL CHECK (revision > 0)
);
CREATE TABLE IF NOT EXISTS outbox (
  change_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entity_id text NOT NULL,
  operation text NOT NULL,
  payload jsonb NOT NULL,
  observed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS delivery_ack (
  consumer text NOT NULL,
  change_id bigint NOT NULL REFERENCES outbox(change_id),
  PRIMARY KEY(consumer, change_id)
);
CREATE OR REPLACE FUNCTION capture_depot() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    INSERT INTO outbox(entity_id,operation,payload) VALUES(OLD.entity_id,TG_OP,to_jsonb(OLD));
    RETURN OLD;
  ELSE
    INSERT INTO outbox(entity_id,operation,payload) VALUES(NEW.entity_id,TG_OP,to_jsonb(NEW));
    RETURN NEW;
  END IF;
END;
$$;
DROP TRIGGER IF EXISTS depot_changes ON depot;
CREATE TRIGGER depot_changes AFTER INSERT OR UPDATE OR DELETE ON depot
FOR EACH ROW EXECUTE FUNCTION capture_depot();
