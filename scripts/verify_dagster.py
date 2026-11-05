from pathlib import Path
import os
temp = Path('.tmp').resolve()
temp.mkdir(exist_ok=True)
os.environ['TEMP']=str(temp)
os.environ['TMP']=str(temp)
import tempfile
tempfile.tempdir=str(temp)
from dagster import materialize
from belgiflow.definitions import operational_marts,dbt_marts,dashboard
assert materialize([operational_marts,dbt_marts,dashboard]).success
from belgiflow.dashboard import render
print(render())
