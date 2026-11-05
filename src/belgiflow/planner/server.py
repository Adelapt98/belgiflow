"""Local-only service-network planner API and self-hosted interface."""
import argparse
import csv
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import mimetypes
from urllib.parse import urlparse, parse_qs
from .engine import CoverageEngine

WEB = Path(__file__).parent / 'web'


def csv_report(result):
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['scenario', 'hubs', 'covered_area_km2', 'uncovered_area_km2', 'overlap_area_km2', 'covered_sample_buildings'])
    for key in ['baseline', 'proposed']:
        scenario = result[key]
        name = scenario['name']
        if name.lstrip().startswith(('=', '+', '-', '@')):
            name = "'" + name
        metrics = scenario['metrics']
        writer.writerow([name, metrics['hubs'], metrics['covered_area_km2'], metrics['uncovered_area_km2'],
                         metrics['overlap_area_km2'], metrics['covered_buildings']])
    writer.writerow([])
    writer.writerow(['Source', result['provenance']['mode'], result['provenance']['release']])
    writer.writerow(['Method', 'Straight-line service radius, not travel time. Building sample is not demand.'])
    return buffer.getvalue().encode('utf-8-sig')


class PlannerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, engine, output, products_root=None):
        self.products_root = Path(products_root) if products_root else Path(output).parent.parent / "platform"
        self.engine = engine
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        super().__init__(address, PlannerHandler)


class PlannerHandler(BaseHTTPRequestHandler):
    def trusted_host(self):
        try:
            return urlparse('http://' + self.headers.get('Host', '')).hostname in {'localhost', '127.0.0.1', '::1'}
        except ValueError:
            return False

    def send(self, status, content, content_type='application/json; charset=utf-8', filename=None):
        if isinstance(content, (dict, list)):
            content = json.dumps(content, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self.trusted_host():
            return self.send(403, {'error': 'this workspace accepts localhost requests only'})
        parsed = urlparse(self.path)
        if parsed.path == '/api/bootstrap':
            return self.send(200, self.server.engine.bootstrap())
        if parsed.path in {'/api/operations', '/api/operations/export'}:
            from .products import operational_report
            try:
                report = operational_report(self.server.products_root, parse_qs(parsed.query).get('date', [None])[0])
                return self.send(200, report, filename='belgiflow-operations.json' if parsed.path.endswith('/export') else None)
            except (ValueError, OSError, KeyError) as error:
                return self.send(400, {'error': str(error)})
        if parsed.path == '/api/export':
            params = parse_qs(parsed.query)
            identity = params.get('plan', [''])[0]
            if not re.fullmatch('[0-9a-f]{64}', identity):
                return self.send(400, {'error': 'invalid comparison ID'})
            path = self.server.output / (identity + '.json')
            if not path.exists():
                return self.send(404, {'error': 'comparison not found'})
            result = json.loads(path.read_text(encoding='utf-8'))
            if params.get('format', ['json'])[0] == 'csv':
                return self.send(200, csv_report(result), 'text/csv; charset=utf-8', 'belgiflow-comparison.csv')
            return self.send(200, result, filename='belgiflow-comparison.json')
        relative = 'index.html' if parsed.path == '/' else parsed.path.lstrip('/')
        target = (WEB / relative).resolve()
        if not target.is_relative_to(WEB.resolve()) or not target.is_file():
            return self.send(404, {'error': 'not found'})
        return self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')

    def do_POST(self):
        if not self.trusted_host():
            return self.send(403, {'error': 'this workspace accepts localhost requests only'})
        if self.path != '/api/compare':
            return self.send(404, {'error': 'not found'})
        origin = self.headers.get('Origin')
        if origin:
            try:
                parsed = urlparse(origin)
                allowed = parsed.scheme in {'http', 'https'} and parsed.hostname in {'127.0.0.1', 'localhost'} and parsed.port == self.server.server_port
            except ValueError:
                allowed = False
            if not allowed:
                return self.send(403, {'error': 'cross-origin requests are not allowed'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 256000:
                raise ValueError('request must contain at most 256 KB of JSON')
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('application/json is required')
            request = json.loads(self.rfile.read(length))
            result = self.server.engine.compare(request)
            target = self.server.output / (result['plan_id'] + '.json')
            # Unique temporary names keep independent browser requests from colliding.
            import uuid
            temporary = target.with_suffix('.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(result, sort_keys=True, allow_nan=False), encoding='utf-8')
            temporary.replace(target)
            self.send(200, result)
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            self.send(400, {'error': str(error)})


def load_engine(root='data', mode='cached'):
    from ..platform.store import Store
    from ..platform import geography
    store = Store(Path(root) / 'planner' / 'reference', '2026-01-03')
    geography.geographic_reference(store, mode=mode, legacy_root=root)
    geography.map_features(store, mode=mode, legacy_root=root)
    return CoverageEngine.from_store(store)


def main():
    parser = argparse.ArgumentParser(description='BelgiFlow service-network planning workspace')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--data', default='data')
    parser.add_argument('--source-mode', choices=['fixtures', 'cached', 'live'], default='fixtures')
    args = parser.parse_args()
    server = PlannerServer((args.host, args.port), load_engine(args.data, args.source_mode), Path(args.data) / 'planner' / 'comparisons')
    print(f'BelgiFlow planner: http://localhost:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
