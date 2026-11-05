"""Inspect and execute the same partitioned jobs displayed in Dagster."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def main():
    parser=argparse.ArgumentParser(description='BelgiFlow Belgian logistics learning platform')
    parser.add_argument('command',choices=['list','run'])
    parser.add_argument('--pipeline',default='13_operations_dashboard')
    parser.add_argument('--date',default='2026-01-03')
    parser.add_argument('--root',default='data/platform')
    parser.add_argument('--source-mode',choices=['fixtures','cached','live'],default='fixtures')
    parser.add_argument('--shipments',type=int,default=300)
    args=parser.parse_args()
    from .catalog import PIPELINES
    if args.command=='list':
        print(json.dumps([dict(job=name,purpose=purpose,concepts=concepts) for name,purpose,concepts in PIPELINES],indent=2))
        return
    temp=Path('.tmp').resolve()
    temp.mkdir(exist_ok=True)
    tempfile.tempdir=str(temp)
    from ..definitions import defs,Platform
    job=defs.resolve_job_def(args.pipeline)
    result=job.execute_in_process(partition_key=args.date,
                                 resources={'platform':Platform(root=args.root,source_mode=args.source_mode,shipments=args.shipments)})
    if not result.success:
        raise SystemExit(1)


if __name__=='__main__':
    main()
