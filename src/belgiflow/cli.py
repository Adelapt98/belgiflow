import argparse
import json
from pathlib import Path
from .events import generate, normalize
from .analytics import marts
from .storage import publish


def main():
    parser = argparse.ArgumentParser(description='BelgiFlow synthetic batch demo')
    parser.add_argument('--shipments', type=int, default=1000)
    parser.add_argument('--output', type=Path, default=Path('data/published'))
    parser.add_argument('--full-demo', action='store_true', help='run Parquet, historical coverage, warehouse and dashboard')
    parser.add_argument('--refresh-map', choices=['demo','belgium'])
    parser.add_argument('--release', help='pin Overture release, otherwise resolve once')
    args = parser.parse_args()
    if not 1 <= args.shipments <= 1000000:
        parser.error('shipments must be between 1 and 1000000')
    if args.refresh_map:
        from .overture import discover,boundary,download,clip_file
        release=args.release or discover()
        country=boundary(release)
        bbox=(4.35,50.84,4.351,50.841) if args.refresh_map=='demo' else (2.5,49.45,6.45,51.55)
        for feature in ['building','segment','connector']:
            source=f'data/raw/{release}/{args.refresh_map}/{feature}.parquet'
            print(json.dumps(download(release,feature,bbox,source)))
            clip_file(source,country,f'data/silver/{args.refresh_map}/{feature}.parquet')
    if args.full_demo:
        from .pipeline import run
        from .dashboard import render
        result=run(shipments=args.shipments)
        print(json.dumps(dict(events=result['events'],coverage=result['coverage'],dashboard=str(render())),indent=2))
        import os
        if os.getenv('BELGIFLOW_BUCKET'):
            from .cloud import upload
            upload('data/dashboard',os.environ['BELGIFLOW_BUCKET'])
        return
    events, rejected = normalize(generate(args.shipments))
    if rejected:
        raise RuntimeError('quality gate failed')
    result = dict(source='synthetic', events=len(events), marts=marts(events))
    print(json.dumps(dict(generation=publish(args.output, result), **result), indent=2))


if __name__ == '__main__':
    main()
