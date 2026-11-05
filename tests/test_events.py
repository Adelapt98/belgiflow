from belgiflow.events import generate, normalize


def test_replay_and_order():
    rows = generate(20)
    result, rejected = normalize(rows)
    assert len(result) == 60
    assert not rejected
    assert normalize(list(reversed(rows)))[0] == result
    assert normalize(result + result)[0] == result


def test_late_correction_and_quarantine():
    row = generate(1)[0]
    correction = dict(row, revision=2, status='cancelled')
    result, rejected = normalize([correction, row, dict(row, status='bad')])
    assert result == [correction]
    assert len(rejected) == 1
