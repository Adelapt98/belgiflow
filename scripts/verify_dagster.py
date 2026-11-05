"""Verify the same partitioned data products shown in the Dagster UI."""
from pathlib import Path
import tempfile
from dagster import Definitions
from belgiflow.definitions import defs, Platform

temp=Path('.tmp').resolve()
temp.mkdir(exist_ok=True)
tempfile.tempdir=str(temp)
Definitions.validate_loadable(defs)
job=defs.resolve_job_def('13_operations_dashboard')
assert job.execute_in_process(partition_key='2026-01-03',resources={
    'platform':Platform(root='data/verification',source_mode='fixtures',shipments=60)
}).success
print('Verified partitioned operational workflow and dashboard.')
