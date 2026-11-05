from shapely.geometry import box
from belgiflow.snapshots import compare


def test_snapshot_changes_are_not_cdc():
    result=compare([('a',box(0,0,1,1)),('b',box(0,0,1,1))],
                   [('a',box(0,0,2,2)),('c',box(0,0,1,1))])
    assert result==dict(added=['c'],removed=['b'],changed=['a'])
