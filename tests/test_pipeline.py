from belgiflow.pipeline import run
from belgiflow.dashboard import render


def test_end_to_end_replay(tmp_path):
    first=run(tmp_path,30)
    second=run(tmp_path,30)
    assert first['marts']==second['marts']
    assert first['coverage']==second['coverage']
    assert first['events']==90
    page=render(tmp_path).read_text(encoding='utf-8')
    assert 'Synthetic operational data' in page
    assert 'DEPOT-0' in page
