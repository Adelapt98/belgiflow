from copy import deepcopy
import csv
import http.client
import io
import json
import math
import threading
import pytest
from shapely import to_wkb
from shapely.geometry import Point, box
from belgiflow.planner.engine import CoverageEngine, EXAMPLE
from belgiflow.planner.server import PlannerServer, csv_report


@pytest.fixture
def engine():
    features = [dict(feature_id='west-building', kind='building', geometry=to_wkb(Point(4.335, 50.852))),
                dict(feature_id='east-building', kind='building', geometry=to_wkb(Point(4.365, 50.844)))]
    return CoverageEngine(box(4.30, 50.80, 4.40, 50.90), features,
                          dict(mode='synthetic_geometry_fixture', release='test-v1', official_boundary=False))


def test_added_hub_expands_coverage_without_double_counting(engine):
    result = engine.compare(EXAMPLE)
    assert result['baseline']['metrics']['covered_buildings'] == 1
    assert result['proposed']['metrics']['covered_buildings'] == 2
    assert result['changes']['additional_buildings'] == 1
    assert result['changes']['added_area_km2'] > 0
    assert result['changes']['lost_area_km2'] == 0
    assert len(result['plan_id']) == 64
    assert engine.compare(deepcopy(EXAMPLE))['plan_id'] == result['plan_id']


def test_same_network_has_no_gain_or_loss(engine):
    request = deepcopy(EXAMPLE)
    request['proposed'] = deepcopy(request['baseline'])
    result = engine.compare(request)
    assert result['changes']['added_area_km2'] == 0
    assert result['changes']['lost_area_km2'] == 0
    assert result['changes']['additional_buildings'] == 0


def test_three_identical_service_circles_count_overlap_once(engine):
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'] = [dict(request['baseline']['hubs'][0], id=str(i), radius_m=1000) for i in range(3)]
    metrics = engine.compare(request)['proposed']['metrics']
    assert metrics['covered_area_km2'] == pytest.approx(math.pi, rel=.001)
    assert metrics['overlap_area_km2'] == metrics['covered_area_km2']
    assert metrics['covered_buildings'] == 1


def test_removal_and_empty_networks_are_supported(engine):
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'] = []
    result = engine.compare(request)
    assert result['proposed']['metrics']['coverage_percent'] == 0
    assert result['changes']['lost_area_km2'] > 0
    assert result['changes']['added_area_km2'] == 0


def test_boundary_clipping_and_study_area_limits(engine):
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'][0]['radius_m'] = 50000
    result = engine.compare(request)
    metrics = result['proposed']['metrics']
    assert metrics['covered_area_km2'] == metrics['study_area_km2']
    assert metrics['coverage_percent'] == 100


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, True, 0, 50001, '1000'])
def test_invalid_radii_rejected(engine, bad):
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'][0]['radius_m'] = bad
    with pytest.raises(ValueError):
        engine.compare(request)


def test_outside_hubs_and_duplicate_ids_are_rejected(engine):
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'][0]['longitude'] = 3
    with pytest.raises(ValueError, match='boundary'):
        engine.compare(request)
    request = deepcopy(EXAMPLE)
    request['proposed']['hubs'][1]['id'] = 'west'
    with pytest.raises(ValueError, match='unique'):
        engine.compare(request)


def test_csv_neutralizes_formula_names(engine):
    request = deepcopy(EXAMPLE)
    request['baseline']['name'] = '=SUM(1,2)'
    rows = list(csv.reader(io.StringIO(csv_report(engine.compare(request)).decode('utf-8-sig'))))
    assert rows[1][0].startswith("'=")


def test_http_compare_export_and_local_origin_validation(engine, tmp_path):
    server = PlannerServer(('127.0.0.1', 0), engine, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    try:
        client.request('POST', '/api/compare', json.dumps(EXAMPLE), {'Content-Type': 'application/json'})
        response = client.getresponse()
        assert response.status == 200
        result = json.loads(response.read())
        client.request('GET', '/api/export?format=csv&plan=' + result['plan_id'])
        response = client.getresponse()
        assert response.status == 200 and b'covered_area_km2' in response.read()
        client.request('POST', '/api/compare', json.dumps(EXAMPLE),
                       {'Content-Type': 'application/json', 'Origin': 'https://untrusted.example'})
        response = client.getresponse()
        assert response.status == 403
        response.read()
        client.request('GET', '/api/bootstrap', headers={'Host': 'untrusted.example'})
        response = client.getresponse()
        assert response.status == 403
        response.read()
        client.request('GET', '/../../LICENSE')
        response = client.getresponse()
        assert response.status == 404
        response.read()
    finally:
        client.close()
        server.shutdown()
        server.server_close()
