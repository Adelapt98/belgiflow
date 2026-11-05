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
    args = parser.parse_args()
    if not 1 <= args.shipments <= 1000000:
        parser.error('shipments must be between 1 and 1000000')
    events, rejected = normalize(generate(args.shipments))
    if rejected:
        raise RuntimeError('quality gate failed')
    result = dict(source='synthetic', events=len(events), marts=marts(events))
    print(json.dumps(dict(generation=publish(args.output, result), **result), indent=2))


if __name__ == '__main__':
    main()
