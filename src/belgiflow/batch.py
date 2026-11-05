"""Durable batch ledger. Publication is separate and can always be rebuilt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .events import normalize
from .analytics import marts
from .storage import publish


class Ledger:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS batches (digest TEXT PRIMARY KEY, observed_at TEXT, rows INTEGER);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, revision INTEGER, payload TEXT);
        CREATE TABLE IF NOT EXISTS quarantine (batch TEXT, position INTEGER, reason TEXT, payload TEXT,
          PRIMARY KEY(batch, position));
        ''')

    def close(self):
        self.db.close()

    def ingest(self, rows):
        encoded = json.dumps(rows, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        if self.db.execute('SELECT 1 FROM batches WHERE digest=?', (digest,)).fetchone():
            return digest
        valid, rejected = normalize(rows)
        with self.db:
            for row in valid:
                payload = json.dumps(row, sort_keys=True, allow_nan=False)
                prior = self.db.execute('SELECT revision,payload FROM events WHERE id=?', (row['event_id'],)).fetchone()
                if prior and prior[0] == row['revision'] and prior[1] != payload:
                    raise ValueError('conflicting revision across batches')
                self.db.execute('''INSERT INTO events VALUES (?,?,?) ON CONFLICT(id) DO UPDATE
                  SET revision=excluded.revision,payload=excluded.payload WHERE excluded.revision > events.revision''',
                                (row['event_id'], row['revision'], payload))
            for position, row in enumerate(rejected):
                self.db.execute('INSERT INTO quarantine VALUES (?,?,?,?)',
                                (digest, position, row['reason'], json.dumps(row['record'], sort_keys=True)))
            self.db.execute('INSERT INTO batches VALUES (?,?,?)',
                            (digest, datetime.now(timezone.utc).isoformat(), len(rows)))
        return digest

    def events(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM events ORDER BY id')]

    def publish(self, output):
        events = self.events()
        rejected = self.db.execute('SELECT count(*) FROM quarantine').fetchone()[0]
        if rejected:
            raise ValueError(f'quality gate: {rejected} quarantined records require resolution')
        if not events:
            raise ValueError('no accepted events')
        return publish(output, {'source': 'synthetic', 'events': len(events), 'marts': marts(events)})
