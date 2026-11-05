"""Read verified, date-partitioned operational products for the user workspace."""
from pathlib import Path
from ..platform.store import Store, day


def operational_report(root, partition=None):
    root = Path(root)
    available = sorted(p.name for p in (root / 'partitions').glob('*')
                       if p.is_dir() and (p / 'quality_report.json').exists())
    if not available:
        return dict(available=[], status='not_built', message='No operational report has been built yet.')
    selected = day(partition) if partition else available[-1]
    if selected not in available:
        raise ValueError('No published report for this date')
    store = Store(root, selected)
    quality = store.read_json('quality_report')
    if quality.get('status') != 'passed':
        return dict(available=available, partition=selected, status='failed', message='Quality checks failed. Results are withheld.')
    capacity = store.read('capacity_plan')
    sla = [r for r in store.read('delivery_sla') if r['source_date'] == selected]
    coverage = store.read('service_coverage')
    accessible = store.read('building_accessibility')
    health = store.read('observability')
    delivered = sum(r['delivered'] for r in sla)
    on_time = sum(r['on_time'] for r in sla)
    exceptions = sorted((r for r in coverage if not r['covered']), key=lambda r: -r['distance_m'])
    return dict(status='ready', available=available, partition=selected, synthetic_operations=True,
                checked_at=quality['checked_at'], geography=store.read_json('geographic_reference')['provenance'],
                metrics=dict(shipments=quality['shipments'], events=quality['events'],
                             outside_coverage=len(exceptions), excess_shipments=sum(r['excess_shipments'] for r in capacity),
                             delivered=delivered, on_time=on_time, on_time_pct=100*on_time/delivered if delivered else None,
                             buildings=len(accessible)), capacity=capacity, sla=sla,
                exceptions=exceptions[:20], exception_limit=20, health=health,
                accessibility=dict(over_100m=sum(r['over_100m_from_sampled_road'] for r in accessible),
                                   method='Distance to sampled roads, not route access or travel time'))
