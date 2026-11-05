"""Immutable lake publication and local/Redshift serving-table replication."""
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import time
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

# Column order is explicit because Redshift COPY from Parquet matches by order.
TABLES = {
    'raw_events': ('accepted_events', ['event_id','shipment_id','status','event_time','revision','depot_id','longitude','latitude','source_date','ingested_at'], ['event_id']),
    'depot_history': ('depot_history', ['entity_id','effective_at','revision','capacity','radius_m','deleted','observed_at','valid_to','is_current','surrogate_key'], ['surrogate_key']),
    'service_coverage': ('service_coverage', ['shipment_id','depot_id','distance_m','covered','policy_key','source_date'], ['shipment_id']),
    'capacity_plan': ('capacity_plan', ['depot_id','source_date','policy_key','capacity','shipments','outside_coverage','utilization','excess_shipments'], ['source_date','depot_id','policy_key']),
    'daily_delivery_sla': ('delivery_sla', ['source_date','depot_id','shipments','delivered','cancelled','on_time','average_delivery_minutes'], ['source_date','depot_id']),
    'source_changed_shipments': ('accepted_events', ['shipment_id'], ['shipment_id']),
}
INTEGERS = {'revision','capacity','radius_m','shipments','outside_coverage','excess_shipments','delivered','cancelled','on_time'}
DOUBLES = {'longitude','latitude','distance_m','utilization','average_delivery_minutes'}
BOOLEANS = {'deleted','is_current','covered'}


def arrow_type(column):
    return pa.int64() if column in INTEGERS else pa.float64() if column in DOUBLES else pa.bool_() if column in BOOLEANS else pa.string()


def sql_type(column):
    return 'BIGINT' if column in INTEGERS else 'DOUBLE PRECISION' if column in DOUBLES else 'BOOLEAN' if column in BOOLEANS else 'VARCHAR(256)'


def export_tables(store):
    directory = store.directory/'exports'
    directory.mkdir(exist_ok=True)
    result = {}
    for table,(dataset,columns,keys) in TABLES.items():
        rows = store.read(dataset)
        unique = {}
        for row in rows:
            unique[tuple(row[k] for k in keys)] = {c:row.get(c) for c in columns}
        schema = pa.schema([(c,arrow_type(c)) for c in columns])
        target = directory/(table+'.parquet')
        pq.write_table(pa.Table.from_pylist(list(unique.values()),schema=schema),target)
        result[table] = dict(path=str(target),bytes=target.stat().st_size,
                             sha256=sha256(target.read_bytes()).hexdigest(),rows=len(unique))
    return result


def publish_lake(store, bucket=None, s3=None):
    if store.read_json('quality_report')['status'] != 'passed':
        raise ValueError('quality gate must pass before publishing')
    exports = export_tables(store)
    identity=dict(tables={k:v['sha256'] for k,v in exports.items()},geography={
        name:sha256(store.path(name,suffix).read_bytes()).hexdigest()
        for name,suffix in [('geographic_reference','json'),('map_features','parquet')]})
    generation = sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    prefix = f'belgiflow/products/date={store.partition}/generation={generation}'
    if bucket and not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket):
        raise ValueError('invalid bucket name')
    if bucket and s3 is None:
        import boto3
        s3 = boto3.client('s3')
    local_root = store.root/'lake'
    manifest = dict(generation=generation,partition=store.partition,backend='s3' if bucket else 'local_filesystem',tables={})
    for table,item in exports.items():
        key=f'{prefix}/{table}/part-00000.parquet'
        if bucket:
            s3.upload_file(item['path'],bucket,key)
        else:
            target=local_root/key
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(item['path'],target)
        copy_manifest={'entries':[dict(url=f's3://{bucket}/{key}' if bucket else str(local_root/key),
                                       mandatory=True,meta=dict(content_length=item['bytes']))]}
        manifest_key=f'{prefix}/{table}.manifest.json'
        content=json.dumps(copy_manifest,sort_keys=True).encode()
        if bucket:
            s3.put_object(Bucket=bucket,Key=manifest_key,Body=content,ContentType='application/json')
        else:
            (local_root/manifest_key).write_bytes(content)
        manifest['tables'][table]=dict(**item,key=key,manifest_key=manifest_key)
    # Include a pinned geographic bundle so private cloud tasks need no public-map internet access.
    geography={}
    for name,suffix in [('geographic_reference','json'),('map_features','parquet')]:
        path=store.path(name,suffix)
        geo_key=f'{prefix}/geography/{name}.{suffix}'
        payload=path.read_bytes()
        if bucket:
            s3.put_object(Bucket=bucket,Key=geo_key,Body=payload)
        else:
            destination=local_root/geo_key
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(payload)
        geography[name]=dict(key=geo_key,sha256=sha256(payload).hexdigest())
    bundle_key=f'{prefix}/map_bundle.json'
    bundle_payload=json.dumps(dict(objects=geography),sort_keys=True).encode()
    if bucket:
        s3.put_object(Bucket=bucket,Key=bundle_key,Body=bundle_payload,ContentType='application/json')
    else:
        (local_root/bundle_key).write_bytes(bundle_payload)
    manifest['map_bundle_uri']=f's3://{bucket}/{bundle_key}' if bucket else str(local_root/bundle_key)
    completion=json.dumps(manifest,sort_keys=True).encode()
    pointer=f'belgiflow/products/date={store.partition}/CURRENT.json'
    if bucket:
        s3.put_object(Bucket=bucket,Key=f'{prefix}/_SUCCESS',Body=completion)
        s3.put_object(Bucket=bucket,Key=pointer,Body=completion,ContentType='application/json')
    else:
        (local_root/prefix/'_SUCCESS').write_bytes(completion)
        target=local_root/pointer
        temporary=target.with_suffix('.tmp')
        temporary.write_bytes(completion)
        temporary.replace(target)
    return store.json('lake_publication',manifest)


def register_catalog(store,database=None,bucket=None,client=None):
    manifest=store.read_json('lake_publication')
    schema=[dict(Name=c,Type='bigint' if c in INTEGERS else 'double' if c in DOUBLES else 'boolean' if c in BOOLEANS else 'string')
            for c in TABLES['raw_events'][1]]
    if bucket:
        if not database:
            raise ValueError('Glue database name required')
        if client is None:
            import boto3
            client=boto3.client('glue')
        descriptor=client.get_table(DatabaseName=database,Name='raw_events')['Table']['StorageDescriptor']
        allowed={'Columns','Location','InputFormat','OutputFormat','Compressed','NumberOfBuckets','SerdeInfo','BucketColumns','SortColumns','Parameters','SkewedInfo','StoredAsSubDirectories'}
        descriptor={k:v for k,v in descriptor.items() if k in allowed}
        descriptor['Location']=f"s3://{bucket}/"+manifest['tables']['raw_events']['key'].rsplit('/',1)[0]+'/'
        result=client.batch_create_partition(DatabaseName=database,TableName='raw_events',PartitionInputList=[
            dict(Values=[store.partition,manifest['generation']],StorageDescriptor=descriptor)])
        errors=[e for e in result.get('Errors',[]) if e.get('ErrorDetail',{}).get('ErrorCode')!='AlreadyExistsException']
        if errors:
            raise RuntimeError('Glue catalog partition registration failed')
        backend='aws_glue_catalog'
    else:
        backend='local_schema_registry'
    return store.json('catalog_registration',dict(backend=backend,partition=store.partition,
                                                 generation=manifest['generation'],columns=schema))


def redshift_sql(manifest,bucket,role_arn):
    if not re.fullmatch(r'arn:aws(?:-[a-z]+)?:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]+',role_arn):
        raise ValueError('invalid Redshift COPY role')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket):
        raise ValueError('invalid bucket')
    statements=['CREATE SCHEMA IF NOT EXISTS analytics']
    for table,(_,columns,keys) in TABLES.items():
        definition=','.join(f'{c} {sql_type(c)}' for c in columns)
        manifest_key=manifest['tables'][table]['manifest_key']
        if not re.fullmatch(r'belgiflow/products/date=\d{4}-\d{2}-\d{2}/generation=[a-f0-9]{64}/[a-z_]+\.manifest.json',manifest_key):
            raise ValueError('untrusted COPY manifest key')
        statements.extend([
            f'CREATE TABLE IF NOT EXISTS analytics.{table} ({definition})',
            f'CREATE TEMP TABLE stage_{table} (LIKE analytics.{table})',
            f"COPY stage_{table} FROM 's3://{bucket}/{manifest_key}' IAM_ROLE '{role_arn}' FORMAT AS PARQUET MANIFEST",
            f'DELETE FROM analytics.{table} USING stage_{table} WHERE '+ ' AND '.join(f'analytics.{table}.{k}=stage_{table}.{k}' for k in keys),
            f'INSERT INTO analytics.{table} SELECT * FROM stage_{table}'])
    return statements


def replicate(store,bucket=None,workgroup=None,database='belgiflow',role_arn=None,client=None,timeout=300):
    manifest=store.read_json('lake_publication')
    if bucket:
        if manifest['backend']!='s3':
            raise ValueError('Redshift requires a completed S3 publication')
        if client is None:
            import boto3
            client=boto3.client('redshift-data')
        statements=redshift_sql(manifest,bucket,role_arn)
        request=dict(WorkgroupName=workgroup,Database=database,Sqls=statements,
                     ClientToken=manifest['generation'])
        identity=client.batch_execute_statement(**request)['Id']
        deadline=time.monotonic()+timeout
        while True:
            status=client.describe_statement(Id=identity)
            if status['Status']=='FINISHED':
                break
            if status['Status'] in {'FAILED','ABORTED'}:
                raise RuntimeError('Redshift load failed: '+status.get('Error','no details'))
            if time.monotonic()>=deadline:
                client.cancel_statement(Id=identity)
                raise TimeoutError('Redshift load deadline exceeded')
            time.sleep(1)
        report=dict(backend='redshift_serverless',statement_id=identity,tables=list(TABLES),generation=manifest['generation'])
    else:
        con=duckdb.connect(str(store.root/'serving.duckdb'))
        try:
            con.execute('BEGIN')
            con.execute('CREATE SCHEMA IF NOT EXISTS analytics')
            for table,(_,columns,keys) in TABLES.items():
                path=store.root/'lake'/manifest['tables'][table]['key']
                if sha256(path.read_bytes()).hexdigest()!=manifest['tables'][table]['sha256']:
                    raise ValueError('immutable lake object checksum mismatch')
                incoming=pq.ParquetFile(path).read()
                con.register('incoming',incoming)
                con.execute(f'CREATE TABLE IF NOT EXISTS analytics.{table} AS SELECT * FROM incoming WHERE false')
                con.execute(f'DELETE FROM analytics.{table} USING incoming WHERE '+
                            ' AND '.join(f'analytics.{table}.{k}=incoming.{k}' for k in keys))
                con.execute(f'INSERT INTO analytics.{table} SELECT * FROM incoming')
                con.unregister('incoming')
            con.execute('COMMIT')
            counts={table:con.execute(f'SELECT count(*) FROM analytics.{table}').fetchone()[0] for table in TABLES}
        except Exception:
            con.execute('ROLLBACK')
            raise
        finally:
            con.close()
        report=dict(backend='local_duckdb_serving',tables=counts,generation=manifest['generation'])
    return store.json('warehouse_replication',report)
