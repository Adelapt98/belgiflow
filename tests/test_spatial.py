from shapely.geometry import box
from belgiflow.spatial import within_country, distance_meters


def test_crossing_features_retained_and_clipped():
    rows, bad = within_country([('a', box(-1, -1, 1, 1))] * 2, box(0, 0, 2, 2))
    assert len(rows) == 1 and rows[0][1].area == 1
    assert not bad


def test_distance_is_metric():
    assert 600 < distance_meters((4.35, 50.85), (4.36, 50.85)) < 800
