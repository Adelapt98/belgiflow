import pytest
from belgiflow.batch import Ledger
from belgiflow.events import generate
from belgiflow.storage import read_current


def test_restart_replay_correction_and_publication(tmp_path):
    path = tmp_path / 'ledger.sqlite'
    ledger = Ledger(path)
    rows = generate(4)
    ledger.ingest(rows)
    ledger.close()
    ledger = Ledger(path)
    ledger.ingest(rows)
    assert len(ledger.events()) == 12
    row = ledger.events()[0]
    ledger.ingest([dict(row, revision=2, status='cancelled')])
    first = ledger.publish(tmp_path / 'published')
    assert ledger.publish(tmp_path / 'published') == first
    assert read_current(tmp_path / 'published')['events'] == 12
    ledger.close()


def test_conflict_rolls_back_entire_batch(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite')
    row = generate(1)[0]
    ledger.ingest([row])
    with pytest.raises(ValueError, match='conflicting'):
        ledger.ingest([dict(row, event_id='new'), dict(row, status='cancelled')])
    assert len(ledger.events()) == 1
    ledger.close()


def test_quarantine_blocks_new_publication(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite')
    ledger.ingest([dict(generate(1)[0], status='invalid')])
    with pytest.raises(ValueError, match='quality gate'):
        ledger.publish(tmp_path / 'published')
    assert not (tmp_path / 'published' / 'CURRENT').exists()
    ledger.close()
