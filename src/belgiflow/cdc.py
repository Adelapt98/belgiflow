"""At-least-once transactional outbox with idempotent local journal."""
import json
from pathlib import Path
import sqlite3


def initialize(dsn):
    import psycopg
    with psycopg.connect(dsn) as con:
        con.execute((Path(__file__).resolve().parents[2] / 'sql/operational.sql').read_text())


def consume(dsn, journal, consumer='belgiflow', limit=1000, fail_before_ack=False):
    import psycopg
    journal = Path(journal)
    journal.parent.mkdir(parents=True, exist_ok=True)
    local = sqlite3.connect(journal)
    local.execute('CREATE TABLE IF NOT EXISTS changes (change_id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
    try:
        with psycopg.connect(dsn) as source:
            rows = source.execute('''SELECT o.change_id,o.entity_id,o.operation,o.payload,o.observed_at
              FROM outbox o WHERE NOT EXISTS
              (SELECT 1 FROM delivery_ack a WHERE a.consumer=%s AND a.change_id=o.change_id)
              ORDER BY o.change_id LIMIT %s''', (consumer, limit)).fetchall()
            with local:
                for change_id, entity, operation, payload, observed in rows:
                    record = dict(change_id=change_id, entity_id=entity, operation=operation,
                                  payload=payload, observed_at=observed.isoformat())
                    local.execute('INSERT OR IGNORE INTO changes VALUES (?,?)', (change_id, json.dumps(record, sort_keys=True)))
            if fail_before_ack:
                raise RuntimeError('simulated interruption before acknowledgement')
            for row in rows:
                source.execute('INSERT INTO delivery_ack VALUES (%s,%s) ON CONFLICT DO NOTHING', (consumer, row[0]))
            return len(rows)
    finally:
        local.close()


def changes(journal):
    with sqlite3.connect(journal) as con:
        return [json.loads(row[0]) for row in con.execute('SELECT payload FROM changes ORDER BY change_id')]


def seed_demo(dsn):
    import psycopg
    from .pipeline import policies
    initialize(dsn)
    with psycopg.connect(dsn) as con:
        for policy in policies():
            prior=con.execute('SELECT revision FROM depot WHERE entity_id=%s',(policy['entity_id'],)).fetchone()
            revision=1 if policy['effective_at'].startswith('2026-01-01') else 2
            if prior and prior[0]>=revision:
                continue
            con.execute('''INSERT INTO depot(entity_id,capacity,effective_at,revision,radius_m)
              VALUES (%s,%s,%s,%s,%s) ON CONFLICT(entity_id) DO UPDATE SET
              capacity=excluded.capacity,effective_at=excluded.effective_at,
              revision=excluded.revision,radius_m=excluded.radius_m''',
                        (policy['entity_id'],policy['capacity'],policy['effective_at'],revision,policy['radius_m']))


def effective_changes(journal):
    from datetime import datetime,timezone
    records=[]
    for row in changes(journal):
        payload=row['payload']
        effective=row['observed_at'] if row['operation']=='DELETE' else payload['effective_at']
        effective=datetime.fromisoformat(effective).astimezone(timezone.utc).isoformat()
        records.append(dict(entity_id=row['entity_id'],effective_at=effective,revision=row['change_id'],
                            capacity=payload['capacity'],radius_m=payload.get('radius_m',1000),
                            deleted=row['operation']=='DELETE',observed_at=row['observed_at']))
    return records
