"""Operational data products: ingestion, CDC, SCD2, coverage, and capacity."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import duckdb
import pyarrow as pa
from zoneinfo import ZoneInfo
from ..batch import Ledger
from ..events import generate
from ..history import scd2
from ..spatial import distance_meters
from .store import Store, day

DEPOTS = [dict(entity_id=f'DEPOT-{i}', longitude=x, latitude=y)
          for i, (x, y) in enumerate([(4.35, 50.85), (4.36, 50.84), (4.37, 50.85)])]
SCENARIO='belgium-cet-v1'


def shipment_source(store, count=300):
    """Deterministic day cohorts, with duplicate delivery and a genuine revision."""
    start = datetime.fromisoformat(store.partition).replace(tzinfo=ZoneInfo('Europe/Brussels')).astimezone(timezone.utc)
    rows = generate(count, seed=int(store.partition.replace('-', '')))
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for row in rows:
        row['event_id'] = SCENARIO + ':' + store.partition + ':' + row['event_id']
        row['shipment_id'] = 'SYN-' + SCENARIO + '-' + store.partition + '-' + row['shipment_id'][4:]
        row['event_time'] = (start + (datetime.fromisoformat(row['event_time']) - base)).isoformat()
        row['source_date'] = store.partition
        row['scenario'] = SCENARIO
        row['ingested_at'] = (start + timedelta(days=3)).isoformat()
    # Correct an originally delivered shipment to cancelled, without adding a new logical event.
    delivered = next(row for row in rows if row['status'] == 'delivered')
    rows.append(dict(delivered, revision=2, status='cancelled'))
    return store.write('shipment_source', rows, dict(kind='synthetic', seed=store.partition))


def accepted_events(store):
    ledger = Ledger(store.root / 'state' / 'events.sqlite')
    try:
        batch = ledger.ingest(store.read('shipment_source'))
        rejected = ledger.db.execute('SELECT count(*) FROM quarantine WHERE batch=?', (batch,)).fetchone()[0]
        if rejected:
            raise ValueError('source partition has quarantined rows')
        rows = [r for r in ledger.events() if r.get('source_date') == store.partition and r.get('scenario')==SCENARIO]
        return store.write('accepted_events', rows, dict(batch=batch, strategy='highest_revision_per_event'))
    finally:
        ledger.close()


def reference_changes(store, dsn=None):
    """Use a real PostgreSQL outbox when configured, or explicit offline CDC fixtures."""
    if dsn:
        from ..cdc import consume, effective_changes
        journal = store.root / 'state' / 'reference.sqlite'
        consumer = 'platform-' + sha256(str(journal.resolve()).encode()).hexdigest()[:16]
        while consume(dsn, journal, consumer=consumer):
            pass
        rows = effective_changes(journal)
        if not rows:
            raise ValueError('empty PostgreSQL journal: seed the operational source first')
        for row in rows:
            row.setdefault('deleted', False)
        mode = 'postgresql_transactional_outbox'
    else:
        rows = []
        for depot in DEPOTS:
            for effective, revision, capacity, radius in [('2026-01-01', 1, 80, 1000), ('2026-01-04', 2, 120, 1800)]:
                effective_utc=datetime.fromisoformat(effective).replace(tzinfo=ZoneInfo('Europe/Brussels')).astimezone(timezone.utc).isoformat()
                rows.append(dict(entity_id=depot['entity_id'], effective_at=effective_utc,
                                 revision=revision, capacity=capacity, radius_m=radius, deleted=False,
                                 observed_at='2026-01-06T00:00:00+00:00'))
        mode = 'synthetic_versioned_change_fixture'
    return store.write('reference_changes', rows, dict(mode=mode))


def depot_history(store):
    return store.write('depot_history', scd2(store.read('reference_changes')),
                       dict(model='SCD Type 2', interval='[effective_at, valid_to)'))


def service_coverage(store):
    rows, history = [], store.read('depot_history')
    for event in store.read('accepted_events'):
        if event['status'] != 'created':
            continue
        matches = [p for p in history if p['entity_id'] == event['depot_id']
                   and p['effective_at'] <= event['event_time']
                   and (p['valid_to'] is None or event['event_time'] < p['valid_to'])]
        if len(matches) != 1:
            raise ValueError('shipment must match exactly one effective depot policy')
        policy = matches[0]
        depot = next(d for d in DEPOTS if d['entity_id'] == event['depot_id'])
        distance = distance_meters((event['longitude'], event['latitude']), (depot['longitude'], depot['latitude']))
        rows.append(dict(shipment_id=event['shipment_id'], depot_id=event['depot_id'],
                         distance_m=distance, covered=not policy['deleted'] and distance <= policy['radius_m'],
                         policy_key=policy['surrogate_key'], source_date=store.partition))
    return store.write('service_coverage', rows, dict(distance='straight_line_meters_EPSG3812'))


def capacity_plan(store):
    """Match workload to the policy effective at each actual shipment creation."""
    history = {r['surrogate_key']: r for r in store.read('depot_history')}
    groups = {}
    for row in store.read('service_coverage'):
        policy = history[row['policy_key']]
        key = (row['depot_id'], row['policy_key'])
        group = groups.setdefault(key, dict(depot_id=row['depot_id'], policy_key=row['policy_key'],
                                           capacity=policy['capacity'], shipments=0, outside_coverage=0))
        group['shipments'] += 1
        group['outside_coverage'] += not row['covered']
    rows = [dict(g, utilization=g['shipments'] / g['capacity'],
                 excess_shipments=max(0, g['shipments'] - g['capacity']), source_date=store.partition)
            for g in groups.values()]
    return store.write('capacity_plan', rows, dict(purpose='identify_overloaded_depots'))


def prepare_warehouse(store):
    """Transactional raw snapshots and persistent pending IDs for incremental dbt rebuilds."""
    target = store.root / 'warehouse.duckdb'
    con = duckdb.connect(str(target))
    incoming = store.read('accepted_events')
    try:
        con.execute('BEGIN')
        con.execute('CREATE TABLE IF NOT EXISTS source_changed_shipments(shipment_id VARCHAR PRIMARY KEY)')
        exists = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='raw_events'").fetchone()[0]
        previous = {} if not exists else {r[0]: r[1] for r in con.execute('SELECT event_id, payload_hash FROM raw_events').fetchall()}
        staged = [dict(r, payload_hash=sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()) for r in incoming]
        changed = {r['shipment_id'] for r in staged if previous.get(r['event_id']) != r['payload_hash']}
        con.register('incoming', pa.Table.from_pylist(staged))
        if not exists:
            con.execute('CREATE TABLE raw_events AS SELECT * FROM incoming')
        else:
            con.execute('DELETE FROM raw_events WHERE source_date=?', [store.partition])
            con.execute('INSERT INTO raw_events BY NAME SELECT * FROM incoming')
        for identity in changed:
            con.execute('INSERT INTO source_changed_shipments VALUES (?) ON CONFLICT DO NOTHING', [identity])
        for name in ['service_coverage', 'capacity_plan', 'depot_history']:
            con.register('incoming_product', pa.Table.from_pylist(store.read(name)))
            con.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT * FROM incoming_product')
            con.unregister('incoming_product')
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise
    finally:
        con.close()
    return store.json('warehouse_input', dict(path=str(target), changed_shipments=len(changed), partition=store.partition))
