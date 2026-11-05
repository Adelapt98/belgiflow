"""Dagster assets for batch processing and opt-in public map refresh."""
import os
from pathlib import Path
from dagster import asset, Definitions, define_asset_job, AssetSelection, ScheduleDefinition
from .pipeline import run
from .overture import discover, boundary, download, clip_file


@asset
def belgium_boundary():
    release=discover()
    boundary(release)
    return release


@asset
def belgian_buildings(belgium_boundary):
    import json
    from shapely.geometry import shape
    release=belgium_boundary
    country=shape(json.loads(Path('data/reference/belgium.geojson').read_text())['geometry'])
    download(release,'building',(4.35,50.84,4.351,50.841),'data/raw/smoke/buildings.parquet')
    return clip_file('data/raw/smoke/buildings.parquet',country,'data/silver/buildings.parquet')


@asset
def operational_marts():
    return run(shipments=int(os.getenv('BELGIFLOW_SHIPMENTS','1000')),dsn=os.getenv('BELGIFLOW_DSN'))


@asset
def dbt_marts(operational_marts):
    from dbt.cli.main import dbtRunner
    result=dbtRunner().invoke(['build','--project-dir','dbt','--profiles-dir','dbt'])
    if not result.success:
        raise RuntimeError('dbt publication checks failed')
    return 'data/warehouse.duckdb'


@asset
def dashboard(dbt_marts):
    import duckdb
    from .storage import read_current,publish
    from .dashboard import render
    report=read_current('data/dashboard')
    con=duckdb.connect(dbt_marts)
    try:
        cursor=con.execute('SELECT * FROM mart_depots ORDER BY depot_id')
        names=[c[0] for c in cursor.description]
        report['marts']=[dict(zip(names,row)) for row in cursor.fetchall()]
    finally:
        con.close()
    report['mart_engine']='dbt-duckdb'
    publish('data/dashboard',report)
    return str(render())


offline=define_asset_job('offline_operations',selection=AssetSelection.assets(operational_marts,dbt_marts,dashboard))
defs=Definitions(assets=[belgium_boundary,belgian_buildings,operational_marts,dbt_marts,dashboard],jobs=[offline],
                 schedules=[ScheduleDefinition(job=offline,cron_schedule='0 6 * * *',execution_timezone='Europe/Brussels')])
