"""Deterministic synthetic event source and correction-aware normalization."""
from datetime import datetime, timedelta, timezone
import random


def generate(count=1000, seed=42):
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        created = start + timedelta(minutes=i)
        for status, hours in [('created', 0), ('dispatched', 2), ('delivered', rng.randint(6, 40))]:
            rows.append(dict(event_id=f'{i}:{status}', shipment_id=f'SYN-{i}', status=status,
                             event_time=(created + timedelta(hours=hours)).isoformat(),
                             revision=1, depot_id=f'DEPOT-{i % 3}',
                             longitude=4.34 + rng.random() * .04,
                             latitude=50.83 + rng.random() * .03))
    rows.extend(dict(r) for r in rows[:10])
    rng.shuffle(rows)
    return rows


def normalize(rows):
    accepted, rejected = {}, []
    for row in rows:
        try:
            if row['status'] not in {'created', 'dispatched', 'delivered', 'cancelled'}:
                raise ValueError('unknown status')
            timestamp = datetime.fromisoformat(row['event_time'])
            if timestamp.tzinfo is None:
                raise ValueError('timestamp must have timezone')
            if not row['shipment_id'].startswith('SYN-'):
                raise ValueError('synthetic identifier required')
            if not (2.5 <= row['longitude'] <= 6.45 and 49.45 <= row['latitude'] <= 51.55):
                raise ValueError('outside acquisition envelope')
            key = row['event_id']
            prior = accepted.get(key)
            if prior and row['revision'] == prior['revision'] and row != prior:
                raise ValueError('conflicting equal revisions')
            if prior is None or row['revision'] > prior['revision']:
                accepted[key] = dict(row)
        except (KeyError, ValueError, TypeError) as error:
            rejected.append({'record': row, 'reason': str(error)})
    return sorted(accepted.values(), key=lambda r: (r['event_time'], r['event_id'])), rejected
