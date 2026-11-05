"""One-command offline product demo, built from the actual operational workflow."""
import argparse
from pathlib import Path
import subprocess
import sys
from .server import PlannerServer, load_engine


def main():
    parser = argparse.ArgumentParser(description='Build and open a complete local BelgiFlow demonstration')
    parser.add_argument('--data', default='data')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    root = Path(args.data).resolve()
    subprocess.run([sys.executable, '-m', 'belgiflow.platform.cli', 'run', '--pipeline',
                    '13_operations_dashboard', '--date', '2026-01-03', '--source-mode', 'fixtures',
                    '--root', str(root / 'platform')], check=True)
    server = PlannerServer(('127.0.0.1', args.port), load_engine(root, 'fixtures'),
                           root / 'planner' / 'comparisons', products_root=root / 'platform')
    print(f'Complete synthetic demo ready: http://localhost:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
