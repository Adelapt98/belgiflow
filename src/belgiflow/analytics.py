"""SQL marts at shipment and depot grain."""
import duckdb
import pyarrow as pa


def marts(events):
    con = duckdb.connect()
    try:
        con.register('events', pa.Table.from_pylist(events))
        con.execute("""create table shipments as
          select shipment_id, min(depot_id) depot_id,
            min(try_cast(event_time as timestamptz)) filter(where status='created') created_at,
            max(try_cast(event_time as timestamptz)) filter(where status='delivered') delivered_at,
            count(*) filter(where status='cancelled') > 0 cancelled
          from events group by shipment_id""")
        cursor = con.execute("""select depot_id, count(*) shipments,
          count(*) filter(where delivered_at is not null and not cancelled) delivered,
          count(*) filter(where not cancelled and delivered_at between created_at and created_at + interval '24 hours') on_time
          from shipments group by depot_id order by depot_id""")
        names = [c[0] for c in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
    finally:
        con.close()
