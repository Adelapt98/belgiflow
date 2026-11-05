from belgiflow.history import scd2


def test_late_effective_change_splits_history():
    def change(day, capacity):
        return dict(entity_id='DEPOT-0', effective_at=f'2026-01-{day:02}T00:00:00+00:00', revision=1, capacity=capacity)
    rows = scd2([change(1, 100), change(20, 200), change(10, 150)])
    assert [r['capacity'] for r in rows] == [100, 150, 200]
    assert rows[0]['valid_to'] == rows[1]['effective_at']
    assert sum(r['is_current'] for r in rows) == 1
    assert scd2([change(1, 100)] * 2) == scd2([change(1, 100)])
