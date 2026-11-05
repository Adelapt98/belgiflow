"""Executed large-batch reference workload, independent of live downloads."""
import argparse
import json
import time
from pathlib import Path
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window

parser = argparse.ArgumentParser()
parser.add_argument('--shipments', type=int, default=100000)
parser.add_argument('--output', default='/tmp/belgiflow-spark')
parser.add_argument('--input', help='optional normalized Parquet event batch')
args = parser.parse_args()
if not 1 <= args.shipments <= 10000000:
    parser.error('shipments must be between 1 and 10000000')
spark = SparkSession.builder.appName('BelgiFlow-event-batch').master('local[2]').config('spark.sql.shuffle.partitions', '4').getOrCreate()
spark.sparkContext.setLogLevel('WARN')
started = time.monotonic()
try:
    if args.input:
        events=spark.read.parquet(args.input)
    else:
        shipments = spark.range(args.shipments).select(
            F.concat(F.lit('SYN-'), F.col('id')).alias('shipment_id'),
            (F.col('id') % 3).alias('depot_id'), F.col('id'))
        events = shipments.crossJoin(spark.createDataFrame([('created',0),('dispatched',2),('delivered',24)], ['status','offset_hours']))
        events = events.withColumn('event_id', F.concat_ws(':','shipment_id','status')).withColumn('revision', F.lit(1))
    duplicated = events.unionByName(events.limit(30))
    window = Window.partitionBy('event_id').orderBy(F.col('revision').desc())
    clean = duplicated.withColumn('row',F.row_number().over(window)).filter('row=1').drop('row')
    clean.write.mode('overwrite').partitionBy('depot_id').parquet(args.output + '/events')
    result = clean.groupBy('depot_id').agg(F.countDistinct('shipment_id').alias('shipments'),F.count('*').alias('events')).orderBy('depot_id').collect()
    assert sum(row['shipments'] for row in result) == args.shipments
    assert sum(row['events'] for row in result) == args.shipments * 3
    report = dict(shipments=args.shipments, events=args.shipments*3, seconds=round(time.monotonic()-started,2),
                  engine=spark.version, synthetic=True, depots=[row.asDict() for row in result])
    print('BELGIFLOW_RESULT=' + json.dumps(report), flush=True)
    Path(args.output).mkdir(parents=True,exist_ok=True)
    Path(args.output,'verification.json').write_text(json.dumps(report,indent=2))
finally:
    spark.stop()
