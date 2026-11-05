"""One PySpark transformation used unchanged by the local worker and AWS Glue."""
import argparse
import json
from pyspark.sql import SparkSession,functions as F
from pyspark.sql.window import Window


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--INPUT_PATH',required=True)
    parser.add_argument('--OUTPUT_PATH',required=True)
    parser.add_argument('--EXPECTED_SHIPMENTS',type=int,required=True)
    args,_=parser.parse_known_args()  # Glue adds JOB_NAME and runtime arguments.
    spark=SparkSession.builder.appName('BelgiFlow-compaction').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        source=spark.read.parquet(args.INPUT_PATH)
        required={'event_id','shipment_id','revision','depot_id','status','event_time','source_date'}
        if not required.issubset(source.columns):
            raise ValueError('input batch violates the event schema contract')
        # Equal revisions must agree. Do not choose arbitrary winners in a distributed window.
        fingerprints=source.withColumn('_payload',F.sha2(F.to_json(F.struct(*[F.col(c) for c in sorted(source.columns)])),256))
        conflicts=fingerprints.groupBy('event_id','revision').agg(F.countDistinct('_payload').alias('versions')).filter('versions > 1')
        if conflicts.limit(1).count():
            raise ValueError('conflicting event revisions')
        window=Window.partitionBy('event_id').orderBy(F.col('revision').desc())
        clean=source.withColumn('_rank',F.row_number().over(window)).filter('_rank=1').drop('_rank').cache()
        shipments=clean.select('shipment_id').distinct().count()
        if shipments!=args.EXPECTED_SHIPMENTS:
            raise ValueError('Spark shipment count does not reconcile')
        events=clean.count()
        clean.repartition('depot_id').write.mode('overwrite').partitionBy('depot_id').parquet(args.OUTPUT_PATH+'/events')
        clean.groupBy('depot_id','status').count().write.mode('overwrite').parquet(args.OUTPUT_PATH+'/status_counts')
        report=dict(shipments=shipments,events=events,spark_version=spark.version,synthetic_operations=True)
        spark.createDataFrame([(json.dumps(report),)],['value']).coalesce(1).write.mode('overwrite').text(args.OUTPUT_PATH+'/verification')
        print('BELGIFLOW_RESULT='+json.dumps(report),flush=True)
    finally:
        spark.stop()


if __name__=='__main__':
    main()
