from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from belgiflow.events import generate,normalize


@pytest.mark.parametrize('value',[None,[],{},dict(event_id='a',revision=-1)])
def test_bad_records_are_quarantined(value):
    accepted,rejected=normalize([value])
    assert not accepted and len(rejected)==1


def test_conflicting_revision_never_publishes_arbitrary_winner():
    row=generate(1)[0]
    other=dict(row,status='cancelled')
    assert normalize([row,other])[0]==normalize([other,row])[0]==[]


def test_brussels_dst_conversion():
    zone=ZoneInfo('Europe/Brussels')
    before=datetime.fromisoformat('2026-03-29T00:30:00+00:00').astimezone(zone)
    after=datetime.fromisoformat('2026-03-29T01:30:00+00:00').astimezone(zone)
    assert (before.hour,after.hour)==(1,3)
