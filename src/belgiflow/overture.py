"""Release discovery with bounded, allowlisted map extraction."""
import json
import re
from pathlib import Path
import requests
import duckdb

CATALOG = 'https://stac.overturemaps.org/catalog.json'
TYPES = {'building': 'buildings', 'segment': 'transportation', 'connector': 'transportation', 'division_area': 'divisions'}


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
    pending = output.with_suffix('.pending.parquet')
    source = f's3://overturemaps-us-west-2/release/{release}/theme={TYPES[feature]}/type={feature}/*'
    con = duckdb.connect()
    try:
        con.execute('INSTALL httpfs')
        con.execute('LOAD httpfs')
        con.execute("SET s3_region='us-west-2'")
        con.execute("SET memory_limit='1GB'")
        con.execute('SET threads=2')
        query = '''SELECT id, geometry, bbox FROM read_parquet(?)
          WHERE bbox.xmin <= ? AND bbox.xmax >= ? AND bbox.ymin <= ? AND bbox.ymax >= ?'''
        table = con.execute(query, [source, east, west, north, south]).fetch_arrow_table()
        import pyarrow.parquet as pq
        pq.write_table(table, pending)
        pending.replace(output)
        manifest = dict(release=release, feature=feature, bbox=list(bbox), rows=table.num_rows,
                        bytes=output.stat().st_size, exact_country_filter=False)
        output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        return manifest
    finally:
        con.close()
