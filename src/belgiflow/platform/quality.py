"""Cross-product reconciliation and observable partition health."""
from datetime import datetime, timezone
import math


def assess(store):
    events = store.read('accepted_events')
    coverage = store.read('service_coverage')
    capacity = store.read('capacity_plan')
    history = store.read('depot_history')
    sla = [r for r in store.read('delivery_sla') if r['source_date'] == store.partition]
    errors = []
    created = {r['shipment_id']: r for r in events if r['status'] == 'created'}
    if len({r['event_id'] for r in events}) != len(events):
        errors.append('duplicate event identity')
    if len(created) != len({r['shipment_id'] for r in events}):
        errors.append('shipment lifecycle missing a creation event')
    for row in events:
        if not all(math.isfinite(row[k]) for k in ['longitude','latitude']):
            errors.append('non-finite coordinate')
        first = created.get(row['shipment_id'])
        if first and (row['depot_id'] != first['depot_id'] or row['event_time'] < first['event_time']):
            errors.append('inconsistent depot or event preceding creation')
    if len(coverage) != len(created) or len({r['shipment_id'] for r in coverage}) != len(created):
        errors.append('coverage does not reconcile with shipment cohort')
    if sum(r['shipments'] for r in capacity) != len(created):
        errors.append('capacity workload double counts or loses shipments')
    if sum(r['shipments'] for r in sla) != len(created):
        errors.append('SLA mart does not reconcile with accepted source')
    for entity in {r['entity_id'] for r in history}:
        versions = sorted([r for r in history if r['entity_id']==entity],key=lambda r:r['effective_at'])
        if sum(r['is_current'] for r in versions) != 1:
            errors.append('history needs exactly one current version')
        if any(a['valid_to'] != b['effective_at'] for a,b in zip(versions,versions[1:])):
            errors.append('history intervals overlap or leave an unintended gap')
    report = dict(status='failed' if errors else 'passed', errors=sorted(set(errors)), partition=store.partition,
                  checked_at=datetime.now(timezone.utc).isoformat(), events=len(events),shipments=len(created),
                  coverage_rows=len(coverage),sla_shipments=sum(r['shipments'] for r in sla),
                  synthetic_operations=True)
    store.json('quality_report',report)
    if errors:
        raise ValueError('quality gate failed: '+', '.join(sorted(set(errors))))
    return report


def observability(store, now=None):
    now=now or datetime.now(timezone.utc)
    datasets=['accepted_events','reference_changes','depot_history','service_coverage',
              'capacity_plan','map_features','building_accessibility','delivery_sla']
    rows=[]
    for dataset in datasets:
        manifest=store.read_json(dataset+'_manifest')
        age=(now-datetime.fromisoformat(manifest['observed_at'])).total_seconds()
        rows.append(dict(dataset=dataset,rows=manifest['rows'],bytes=store.path(dataset).stat().st_size,
                         artifact_age_seconds=max(0,age),stale=age>86400,
                         checksum_verified=len(store.read(dataset))==manifest['rows']))
    return store.write('observability',rows,dict(freshness='artifact publication age, not historical event age'))
