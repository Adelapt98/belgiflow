"""Release discovery with bounded, allowlisted map extraction."""
import json
import re
from pathlib import Path
import requests
import duckdb
import hashlib
import threading
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CATALOG = 'https://stac.overturemaps.org/catalog.json'
TYPES = {'building': 'buildings', 'segment': 'transportation', 'connector': 'transportation', 'division_area': 'divisions'}


def get_json(url):
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=.5, status_forcelist=[429, 500, 502, 503])))
    response = session.get(url, timeout=(10, 60))
    response.raise_for_status()
    return response.json()


def overlaps(first, second):
    return first[0] <= second[2] and first[2] >= second[0] and first[1] <= second[3] and first[3] >= second[1]


def source_files(release, feature, bbox):
    """Inspect STAC item extents, never guess that collection bbox order maps to files."""
    url = f'https://stac.overturemaps.org/{release}/{TYPES[feature]}/{feature}/collection.json'
    collection = get_json(url)
    cache = Path('data/cache/stac') / release / feature
    cache.mkdir(parents=True, exist_ok=True)

    def item(link):
        path = cache / (Path(link['href']).stem + '.json')
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        result = get_json(urljoin(url, link['href']))
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result), encoding='utf-8')
        temporary.replace(path)
        return result

    with ThreadPoolExecutor(max_workers=8) as pool:
        items = pool.map(item, [link for link in collection['links'] if link['rel'] == 'item'])
        selected = [i['assets']['aws']['href'] for i in items if overlaps(i['bbox'], bbox)]
    if not selected:
        raise ValueError('no source files intersect requested extent')
    return selected


def boundary(release, output='data/reference/belgium.geojson'):
    from shapely import from_wkb
    from shapely.geometry import mapping
    files = source_files(release, 'division_area', (2.5,49.45,6.45,51.55))
    con = duckdb.connect()
    extensions = Path('data/cache/duckdb_extensions').resolve()
    extensions.mkdir(parents=True, exist_ok=True)
    try:
        con.execute('SET extension_directory=?', [str(extensions)])
        con.execute('INSTALL httpfs')
        con.execute('LOAD httpfs')
        rows = con.execute("SELECT id,geometry FROM read_parquet(?) WHERE country='BE' AND subtype='country' AND is_land AND NOT is_territorial", [files]).fetchall()
        if len(rows) != 1:
            raise ValueError('expected one Belgian land boundary')
        geometry = from_wkb(rows[0][1])
        if not geometry.is_valid or not geometry.covers(__import__('shapely').Point(4.35,50.85)):
            raise ValueError('invalid Belgian boundary')
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(dict(type='Feature',geometry=mapping(geometry),
                                        properties=dict(id=rows[0][0],release=release,source='Overture'))), encoding='utf-8')
        return geometry
    finally:
        con.close()


def clip_file(source, country, output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from shapely import from_wkb, to_wkb
    from .spatial import within_country
    table = pq.read_table(source)
    features = [(r['id'], from_wkb(r['geometry'])) for r in table.to_pylist()]
    accepted, rejected = within_country(features, country)
    if rejected:
        raise ValueError(f'{len(rejected)} invalid source geometries')
    result = pa.table({'id':pa.array([r[0] for r in accepted], type=pa.string()),
                       'geometry':pa.array([to_wkb(r[1]) for r in accepted], type=pa.binary())})
    metadata = dict(result.schema.metadata or {})
    metadata[b'geo'] = json.dumps({'version':'1.1.0','primary_column':'geometry',
        'columns':{'geometry':{'encoding':'WKB','geometry_types':sorted({r[1].geom_type for r in accepted})}}}).encode()
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.pending.parquet')
    pq.write_table(result.replace_schema_metadata(metadata), temporary)
    temporary.replace(target)
    return len(accepted)


def discover():
    response = requests.get(CATALOG, timeout=60)
    response.raise_for_status()
    catalog = response.json()
    release = catalog.get('latest')
    if not isinstance(release, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.\d+', release):
        raise ValueError('unrecognized catalog release structure')
    return release


def download(release, feature, bbox, output):
    if feature not in TYPES or not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.\d+', release):
        raise ValueError('invalid source selection')
    west, south, east, north = map(float, bbox)
    if not (2.5 <= west < east <= 6.45 and 49.45 <= south < north <= 51.55):
        raise ValueError('download must stay within Belgium acquisition envelope')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path=output.with_suffix('.manifest.json')
    if output.exists() and manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if (manifest.get('release'),manifest.get('feature'),manifest.get('bbox')) == (release,feature,list(bbox)):
            if manifest.get('sha256')==_checksum(output):
                return manifest
    pending = output.with_suffix('.pending.parquet')
    source = source_files(release, feature, bbox)
    con = duckdb.connect()
    try:
        extensions = Path('data/cache/duckdb_extensions').resolve()
        extensions.mkdir(parents=True, exist_ok=True)
        con.execute('SET extension_directory = ?', [str(extensions)])
        con.execute('INSTALL httpfs')
        con.execute('LOAD httpfs')
        con.execute("SET s3_region='us-west-2'")
        con.execute("SET memory_limit='1GB'")
        con.execute('SET threads=2')
        con.execute('SET http_timeout=60')
        con.execute('SET enable_progress_bar=false')
        query = '''SELECT id, geometry, bbox FROM read_parquet(?)
          WHERE bbox.xmin <= ? AND bbox.xmax >= ? AND bbox.ymin <= ? AND bbox.ymax >= ?'''
        import pyarrow.parquet as pq
        timer=threading.Timer(300,con.interrupt)
        timer.start()
        try:
            reader=con.execute(query, [source, east, west, north, south]).to_arrow_reader(65536)
            rows=0
            with pq.ParquetWriter(pending,reader.schema) as writer:
                for batch in reader:
                    writer.write_batch(batch)
                    rows+=batch.num_rows
        finally:
            timer.cancel()
        pending.replace(output)
        manifest = dict(release=release, feature=feature, bbox=list(bbox), rows=rows,
                        bytes=output.stat().st_size,sha256=_checksum(output), exact_country_filter=False,
                        extracted_at=datetime.now(timezone.utc).isoformat(),source_files=len(source),
                        schema_fingerprint=hashlib.sha256(str(reader.schema).encode()).hexdigest())
        temporary_manifest=manifest_path.with_suffix('.tmp')
        temporary_manifest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        temporary_manifest.replace(manifest_path)
        return manifest
    finally:
        con.close()


def _checksum(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()
