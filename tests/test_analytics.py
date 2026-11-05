from belgiflow.analytics import marts
from belgiflow.events import generate, normalize


def test_mart_reconciles_at_shipment_grain():
    events, _ = normalize(generate(100))
    result = marts(events)
    assert sum(row['shipments'] for row in result) == 100
    assert all(0 <= row['on_time'] <= row['delivered'] <= row['shipments'] for row in result)
