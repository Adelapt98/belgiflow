import sys
from types import SimpleNamespace
import pytest
from belgiflow.cloud import upload
from belgiflow.storage import publish


def test_s3_pointer_is_written_only_after_content(tmp_path,monkeypatch):
    digest=publish(tmp_path,{'source':'synthetic'})
    calls=[]
    client=SimpleNamespace(upload_file=lambda *a,**k:calls.append(('file',a[2])),
                           put_object=lambda **k:calls.append(('pointer',k['Key'])))
    monkeypatch.setitem(sys.modules,'boto3',SimpleNamespace(client=lambda _:client))
    assert upload(tmp_path,'test-bucket')==digest
    assert calls==[('file',f'belgiflow/dashboard/{digest}.json'),('pointer','belgiflow/dashboard/CURRENT')]


def test_failed_s3_content_upload_does_not_advance_pointer(tmp_path,monkeypatch):
    publish(tmp_path,{'source':'synthetic'})
    def fail(*args,**kwargs):
        raise RuntimeError('simulated upload failure')
    calls=[]
    client=SimpleNamespace(upload_file=fail,put_object=lambda **k:calls.append(k))
    monkeypatch.setitem(sys.modules,'boto3',SimpleNamespace(client=lambda _:client))
    with pytest.raises(RuntimeError):
        upload(tmp_path,'test-bucket')
    assert not calls
