from pathlib import Path
import pytest
from belgiflow.planner.products import operational_report
from belgiflow.platform.store import Store


def build(root):
    s=Store(root,'2026-01-03')
    s.json('quality_report',dict(status='passed',checked_at='2026-01-03T00:00:00Z',shipments=2,events=6))
    s.json('geographic_reference',dict(provenance=dict(mode='fixtures',release='test')))
    s.write('capacity_plan',[dict(depot_id='A',capacity=1,shipments=2,excess_shipments=1,utilization=2,outside_coverage=1)])
    s.write('delivery_sla',[dict(source_date='2026-01-03',depot_id='A',delivered=1,on_time=1,cancelled=1)])
    s.write('service_coverage',[dict(shipment_id='synthetic-1',depot_id='A',covered=False,distance_m=200)])
    s.write('building_accessibility',[dict(over_100m_from_sampled_road=True)])
    s.write('observability',[dict(dataset='accepted_events',rows=6,checksum_verified=True,stale=False)])
    return s


def test_missing_report_does_not_invent_results(tmp_path):
    assert operational_report(tmp_path)['status']=='not_built'


def test_report_uses_deliveries_as_denominator_and_checksums(tmp_path):
    s=build(tmp_path)
    r=operational_report(tmp_path)
    assert r['metrics']['on_time_pct']==100
    assert r['metrics']['excess_shipments']==1
    assert r['metrics']['outside_coverage']==1
    assert r['synthetic_operations'] is True
    s.path('capacity_plan').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        operational_report(tmp_path)


def test_failed_quality_withholds_metrics(tmp_path):
    s=build(tmp_path)
    s.json('quality_report',dict(status='failed'))
    r=operational_report(tmp_path)
    assert r['status']=='failed'
    assert 'metrics' not in r


def test_partition_path_is_validated(tmp_path):
    build(tmp_path)
    with pytest.raises(ValueError): operational_report(tmp_path,'../../secrets')
    with pytest.raises(ValueError): operational_report(tmp_path,'2026-01-04')
