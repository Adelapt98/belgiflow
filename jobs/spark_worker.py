"""Restricted local queue worker. No Docker socket or arbitrary command execution."""
import json
import os
from pathlib import Path
import subprocess
import time

DATA=Path('/data').resolve()
QUEUE=DATA/os.getenv('BELGIFLOW_SPARK_QUEUE','platform/spark_queue')
QUEUE.mkdir(parents=True,exist_ok=True)


def confined(value):
    path=(DATA/value).resolve()
    try:
        path.relative_to(DATA)
    except ValueError:
        raise ValueError('Spark path escaped the shared data directory')
    return path


# A stopped container cannot retain a live Spark child. Requeue its interrupted claims.
for stale in QUEUE.glob('*.request.running'):
    stale.rename(stale.with_suffix('.json'))

while True:
    for request in sorted(QUEUE.glob('*.request.json')):
        claimed=request.with_suffix('.running')
        try:
            request.rename(claimed)
        except FileNotFoundError:
            continue
        identity=request.name[:-len('.request.json')]
        result_path=QUEUE/(identity+'.result.json')
        try:
            message=json.loads(claimed.read_text())
            if message['id']!=identity or not (0<message['expected_shipments']<=10000000):
                raise ValueError('invalid worker request')
            if (QUEUE/(identity+'.cancel')).exists():
                raise ValueError('request cancelled before execution')
            log=QUEUE/(identity+'.log')
            command=['/opt/spark/bin/spark-submit','--master','local[2]',
                     '--conf','spark.sql.shuffle.partitions=4','/jobs/glue_compact.py',
                     '--INPUT_PATH',str(confined(message['input'])),
                     '--OUTPUT_PATH',str(confined(message['output'])),
                     '--EXPECTED_SHIPMENTS',str(message['expected_shipments'])]
            with log.open('w') as handle:
                process=subprocess.run(command,stdout=handle,stderr=subprocess.STDOUT,timeout=240)
            if process.returncode:
                raise RuntimeError('spark-submit failed: '+log.read_text()[-2500:])
            reports=[line.split('BELGIFLOW_RESULT=',1)[1] for line in log.read_text().splitlines() if 'BELGIFLOW_RESULT=' in line]
            result=dict(status='succeeded',backend='local_spark_worker',**json.loads(reports[-1]))
        except Exception as error:
            result=dict(status='failed',error=str(error))
        temporary=result_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result))
        temporary.replace(result_path)
        claimed.unlink(missing_ok=True)
    time.sleep(.5)
