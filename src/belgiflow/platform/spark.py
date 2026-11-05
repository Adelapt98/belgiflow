"""Spark dispatch through a shared local worker queue or an actual Glue API call."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import uuid


def compact(store, backend='local', glue_job=None, bucket=None, client=None, timeout=300):
    if backend=='glue':
        if not glue_job or not bucket:
            raise ValueError('Glue job name and S3 bucket are required')
        if client is None:
            import boto3
            client=boto3.client('glue')
        import boto3
        # Upload a complete immutable input batch before starting remote processing.
        source=store.path('accepted_events')
        digest=store.read_json('accepted_events_manifest')['sha256']
        key=f'belgiflow/spark-input/date={store.partition}/{digest}.parquet'
        boto3.client('s3').upload_file(str(source),bucket,key)
        identity=client.start_job_run(JobName=glue_job,Arguments={
            '--INPUT_PATH':f's3://{bucket}/{key}',
            '--OUTPUT_PATH':f's3://{bucket}/belgiflow/spark-output/date={store.partition}/generation={digest}/',
            '--EXPECTED_SHIPMENTS':str(len({r['shipment_id'] for r in store.read('accepted_events')}))})['JobRunId']
        deadline=time.monotonic()+timeout
        while True:
            run=client.get_job_run(JobName=glue_job,RunId=identity)['JobRun']
            status=run['JobRunState']
            if status=='SUCCEEDED':
                break
            if status in {'FAILED','STOPPED','TIMEOUT','ERROR','EXPIRED'}:
                raise RuntimeError('Glue compaction failed: '+status)
            if time.monotonic()>deadline:
                client.batch_stop_job_run(JobName=glue_job,JobRunIds=[identity])
                raise TimeoutError('Glue job exceeded orchestration deadline')
            time.sleep(2)
        return store.json('spark_compaction',dict(backend='aws_glue',job_run_id=identity,status=status))
    queue=store.root/'spark_queue'
    queue.mkdir(parents=True,exist_ok=True)
    identity=uuid.uuid4().hex
    source=store.path('accepted_events').resolve()
    output=store.directory/'spark'
    # Paths relative to the mounted data directory remain valid on Windows and Linux.
    data_root=Path('data').resolve()
    try:
        input_relative=source.relative_to(data_root).as_posix()
        output_relative=output.resolve().relative_to(data_root).as_posix()
    except ValueError:
        raise ValueError('local Spark artifacts must live under the shared data directory')
    request=dict(id=identity,input=input_relative,output=output_relative,
                 expected_shipments=len({r['shipment_id'] for r in store.read('accepted_events')}))
    pending=queue/(identity+'.tmp')
    pending.write_text(json.dumps(request),encoding='utf-8')
    pending.replace(queue/(identity+'.request.json'))
    deadline=time.monotonic()+timeout
    response=queue/(identity+'.result.json')
    while not response.exists():
        if time.monotonic()>deadline:
            (queue/(identity+'.cancel')).touch()
            raise TimeoutError('Spark worker did not finish. Start the Compose spark-worker service.')
        time.sleep(.5)
    result=json.loads(response.read_text(encoding='utf-8'))
    if result['status']!='succeeded':
        raise RuntimeError('Spark worker failed: '+result.get('error','see worker log'))
    return store.json('spark_compaction',result)
