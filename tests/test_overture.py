import pytest
from belgiflow.overture import overlaps,download


def test_overlap_retains_long_boundary_crossing_features():
    assert overlaps((0,0,10,10),(4,4,5,5))
    assert not overlaps((0,0,1,1),(4,4,5,5))


def test_source_rejects_global_or_injected_requests(tmp_path):
    with pytest.raises(ValueError,match='source selection'):
        download("invalid';",'building',(4,50,5,51),tmp_path/'x.parquet')
    with pytest.raises(ValueError,match='envelope'):
        download('2026-10-21.0','building',(-180,-90,180,90),tmp_path/'x.parquet')
