"""Rebuild effective-time history from durable, replayable changes."""
from hashlib import sha256
from datetime import datetime,timezone


def scd2(changes):
    versions = {}
    for change in changes:
        change=dict(change)
        effective=datetime.fromisoformat(change['effective_at'])
        if effective.tzinfo is None:
            raise ValueError('effective timestamp must have a timezone')
        change['effective_at']=effective.astimezone(timezone.utc).isoformat()
        key = (change['entity_id'], change['effective_at'])
        previous = versions.get(key)
        if previous is None or change['revision'] > previous['revision']:
            versions[key] = change
        elif change['revision'] == previous['revision'] and change != previous:
            raise ValueError('ambiguous history revision')
    result = []
    entities = sorted({key[0] for key in versions})
    for entity in entities:
        ordered = sorted((v for (e, _), v in versions.items() if e == entity), key=lambda v: v['effective_at'])
        for i, row in enumerate(ordered):
            end = ordered[i + 1]['effective_at'] if i + 1 < len(ordered) else None
            result.append(dict(row, valid_to=end, is_current=end is None,
                               surrogate_key=sha256(f"{entity}|{row['effective_at']}".encode()).hexdigest()))
    return result
