"""Validate real boto3 request shapes offline, without AWS credentials or network calls."""
import pytest
from botocore.stub import Stubber,ANY
import boto3
import io
from pathlib import Path

from belgiflow.platform.cloud import publish_lake,replicate,register_catalog
from test_platform import product,clone


class S3Recorder:
    def __init__(self,fail=False):
        self.calls=[]
        self.objects={}
        self.fail=fail

    def upload_file(self,path,bucket,key):
        if self.fail:
            raise RuntimeError('simulated upload failure')
        self.calls.append(('upload',key))
        self.objects[key]=Path(path).read_bytes()

    def put_object(self,**request):
        self.calls.append(('put',request['Key']))
        self.objects[request['Key']]=request['Body']

    def get_object(self,**request):
        return {'Body':io.BytesIO(self.objects[request['Key']])}


def test_s3_failure_does_not_advance_success_pointer(clone):
    client=S3Recorder(fail=True)
    with pytest.raises(RuntimeError):
        publish_lake(clone,'example-bucket',s3=client)
    assert not any(key.endswith('CURRENT.json') for _,key in client.calls)


def test_s3_and_redshift_request_shapes_and_transactional_batch(clone):
    recorder=S3Recorder()
    manifest=publish_lake(clone,'example-bucket',s3=recorder)
    assert recorder.calls[-1][1].endswith('CURRENT.json')
    client=boto3.client('redshift-data',region_name='eu-west-1',aws_access_key_id='testing',aws_secret_access_key='testing')
    identifier='12345678-1234-1234-1234-123456789012'
    with Stubber(client) as stub:
        stub.add_response('batch_execute_statement',{'Id':identifier},
                          dict(WorkgroupName='belgiflow',Database='belgiflow',Sqls=ANY,ClientToken=manifest['generation']))
        stub.add_response('describe_statement',{'Id':identifier,'Status':'FINISHED'},dict(Id=identifier))
        report=replicate(clone,bucket='example-bucket',workgroup='belgiflow',
                         role_arn='arn:aws:iam::123456789012:role/belgiflow-copy',client=client)
        assert report['backend']=='redshift_serverless'
        stub.assert_no_pending_responses()


def test_glue_catalog_registration_uses_exact_immutable_partition(clone):
    manifest=publish_lake(clone,'example-bucket',s3=S3Recorder())
    client=boto3.client('glue',region_name='eu-west-1',aws_access_key_id='testing',aws_secret_access_key='testing')
    with Stubber(client) as stub:
        stub.add_response('get_table',{'Table':{'Name':'raw_events','StorageDescriptor':{'Columns':[],'Location':'s3://example-bucket/'}}},
                          {'DatabaseName':'belgiflow','Name':'raw_events'})
        stub.add_response('batch_create_partition',{},
                          dict(DatabaseName='belgiflow',TableName='raw_events',PartitionInputList=ANY))
        report=register_catalog(clone,'belgiflow','example-bucket',client)
        assert report['generation']==manifest['generation']
        stub.assert_no_pending_responses()


def test_private_cloud_geography_bundle_preserves_source_provenance(clone,tmp_path,monkeypatch):
    from belgiflow.platform.store import Store
    from belgiflow.platform.geography import geographic_reference,map_features
    client=S3Recorder()
    manifest=publish_lake(clone,'example-bucket',s3=client)
    monkeypatch.setenv('BELGIFLOW_MAP_BUNDLE',manifest['map_bundle_uri'])
    monkeypatch.setattr(boto3,'client',lambda name:client)
    remote=Store(tmp_path/'remote','2026-01-03')
    reference=geographic_reference(remote,'s3')
    assert reference['provenance']['mode']=='synthetic_geometry_fixture'
    assert map_features(remote,'s3')['rows']==clone.read_json('map_features_manifest')['rows']


def test_glue_dispatch_uses_the_shared_compaction_contract(clone,monkeypatch):
    from belgiflow.platform.spark import compact
    client=boto3.client('glue',region_name='eu-west-1',aws_access_key_id='testing',aws_secret_access_key='testing')
    storage=S3Recorder()
    monkeypatch.setattr(boto3,'client',lambda name:storage)
    with Stubber(client) as stub:
        stub.add_response('start_job_run',{'JobRunId':'jr_example'},dict(JobName='compaction',Arguments=ANY))
        stub.add_response('get_job_run',{'JobRun':{'Id':'jr_example','JobRunState':'SUCCEEDED'}},
                          dict(JobName='compaction',RunId='jr_example'))
        result=compact(clone,backend='glue',glue_job='compaction',bucket='example-bucket',client=client)
        assert result['status']=='SUCCEEDED'
        assert storage.calls[0][1].endswith('.parquet')
        stub.assert_no_pending_responses()
