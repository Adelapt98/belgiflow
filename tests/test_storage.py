import pytest
from belgiflow.storage import publish, read_current


def test_publication_is_repeatable_and_detects_corruption(tmp_path):
    digest = publish(tmp_path, {'rows': [1, 2]})
    assert publish(tmp_path, {'rows': [1, 2]}) == digest
    assert read_current(tmp_path) == {'rows': [1, 2]}
    (tmp_path / f'{digest}.json').write_text('broken')
    with pytest.raises(ValueError, match='checksum'):
        read_current(tmp_path)
