"""Local vertical slice producing Parquet, SQL inputs, history, and coverage."""
from datetime import datetime, timezone
import json
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point, shape, mapping

from .batch import Ledger
from .events import generate
from .history import scd2
from .storage import publish, read_current


DEPOTS = [dict(entity_id=f'DEPOT-{i}', longitude=x, latitude=y)
          for i,(x,y) in enumerate([(4.35,50.85),(4.36,50.84),(4.37,50.85)])]


def policies():
    return [dict(entity_id=d['entity_id'],effective_at=f'2026-01-{day:02}T00:00:00+00:00',
                 revision=1,capacity=capacity,radius_m=radius)
            for d in DEPOTS for day,capacity,radius in [(1,100,1000),(2,150,1800)]]


def run(root='data', shipments=1000):
    root = Path(root)
    ledger = Ledger(root / 'ledger.sqlite')
    try:
        ledger.ingest(generate(shipments))
        events = ledger.events()
        if ledger.db.execute('SELECT count(*) FROM quarantine').fetchone()[0]:
            raise ValueError('unresolved quarantine blocks pipeline')
        silver = root / 'silver'
        silver.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.Table.from_pylist(events),silver/'events.parquet')
        history = scd2(policies())
        pq.write_table(pa.Table.from_pylist(history),silver/'depot_history.parquet')
        from .spatial import distance_meters
        coverage = []
        by_shipment = {}
        for event in events:
            if event['status']=='created':
                by_shipment[event['shipment_id']] = event
        for event in by_shipment.values():
            matches = [p for p in history if p['entity_id']==event['depot_id']
                       and p['effective_at'] <= event['event_time']
                       and (p['valid_to'] is None or event['event_time'] < p['valid_to'])]
            if len(matches)!=1:
                raise ValueError('historical policy lookup must match exactly once')
            policy=matches[0]
            depot=next(d for d in DEPOTS if d['entity_id']==event['depot_id'])
            distance=distance_meters((event['longitude'],event['latitude']),(depot['longitude'],depot['latitude']))
            coverage.append(dict(shipment_id=event['shipment_id'],depot_id=event['depot_id'],
                                 distance_m=distance,covered=distance<=policy['radius_m'],
                                 policy_key=policy['surrogate_key']))
        pq.write_table(pa.Table.from_pylist(coverage),silver/'coverage.parquet')
        con=duckdb.connect(str(root/'warehouse.duckdb'))
        try:
            for name,rows in [('raw_events',events),('dim_depot_history',history),('shipment_coverage',coverage)]:
                con.register('incoming',pa.Table.from_pylist(rows))
                con.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT * FROM incoming')
                con.unregister('incoming')
        finally:
            con.close()
        ledger.publish(root/'published')
        report=read_current(root/'published')
        boundary_path=root/'reference/belgium.geojson'
        country=json.loads(boundary_path.read_text()) if boundary_path.exists() else None
        report.update(dict(coverage=dict(total=len(coverage),outside=sum(not r['covered'] for r in coverage)),
                           depots=DEPOTS,policies=history,
                           map_boundary=country,geography='live Overture' if country else 'synthetic local coordinates',
                           generated_at=datetime.now(timezone.utc).isoformat()))
        publish(root/'dashboard',report)
        return report
    finally:
        ledger.close()
