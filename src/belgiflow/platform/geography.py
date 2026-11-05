"""Public-map reference products and explicit synthetic offline fixtures."""
import json
from pathlib import Path
from shapely import from_wkb, to_wkb
from shapely.geometry import Point, LineString, box, shape, mapping
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer
import pyarrow.parquet as pq
from ..spatial import within_country
from ..snapshots import compare


def geographic_reference(store, mode='cached', legacy_root='data'):
    if mode not in {'fixtures', 'cached', 'live'}:
        raise ValueError('unknown map source mode')
    legacy = Path(legacy_root)
    if mode == 'live':
        from ..overture import discover, boundary, download
        release = discover()
        boundary(release, legacy / 'reference' / 'belgium.geojson')
        for kind in ['building', 'segment', 'connector']:
            download(release, kind, (4.35, 50.84, 4.351, 50.841), legacy / 'raw' / 'smoke' / f'{kind}.parquet')
    if mode == 'fixtures':
        country = box(4.33, 50.82, 4.39, 50.88)
        source = dict(mode='synthetic_geometry_fixture', release='fixture-v1', official_boundary=False)
    else:
        feature = json.loads((legacy / 'reference' / 'belgium.geojson').read_text(encoding='utf-8'))
        country = shape(feature['geometry'])
        source = dict(mode='Overture', release=feature['properties']['release'], official_boundary=True)
    return store.json('geographic_reference', dict(geometry=mapping(country), provenance=source))


def map_features(store, mode='cached', legacy_root='data'):
    reference = store.read_json('geographic_reference')
    country = shape(reference['geometry'])
    if mode == 'fixtures':
        features = {
            'building': [(f'fixture-building-{i}', box(4.345+i*.001, 50.845, 4.3455+i*.001, 50.8455)) for i in range(20)],
            'segment': [('fixture-road-1', LineString([(4.34,50.843),(4.38,50.843)])),
                        ('fixture-road-2', LineString([(4.35,50.83),(4.35,50.87)]))],
            'connector': [('fixture-junction-1', Point(4.35,50.843))]}
    else:
        features = {}
        for kind in ['building', 'segment', 'connector']:
            candidates = [Path(legacy_root)/'raw/smoke'/f'{kind}.parquet']
            if kind == 'building':
                candidates.append(Path(legacy_root)/'raw/smoke/buildings.parquet')
            source = next((p for p in candidates if p.exists()), None)
            if source is None:
                raise ValueError(f'cached {kind} missing: run map ingestion or select fixtures explicitly')
            manifest = json.loads(source.with_suffix('.manifest.json').read_text(encoding='utf-8'))
            if manifest['release'] != reference['provenance']['release']:
                raise ValueError('map themes must use the same release as the boundary')
            features[kind] = [(r['id'],from_wkb(r['geometry'])) for r in pq.ParquetFile(source).read().to_pylist()]
    rows = []
    for kind, items in features.items():
        accepted, rejected = within_country(items, country)
        if rejected:
            raise ValueError('invalid map geometry')
        rows.extend(dict(feature_id=identity, kind=kind, geometry=to_wkb(geometry),
                         release=reference['provenance']['release']) for identity,geometry in accepted)
    return store.write('map_features', rows, reference['provenance'])


def building_accessibility(store):
    features = store.read('map_features')
    projection = Transformer.from_crs('EPSG:4326','EPSG:3812',always_xy=True).transform
    roads = [transform(projection,from_wkb(r['geometry'])) for r in features if r['kind']=='segment']
    if not roads:
        raise ValueError('road sample is empty')
    tree = STRtree(roads)
    rows = []
    for row in features:
        if row['kind'] != 'building':
            continue
        center = transform(projection,from_wkb(row['geometry'])).centroid
        nearest = roads[int(tree.nearest(center))]
        distance = center.distance(nearest)
        rows.append(dict(building_id=row['feature_id'], nearest_sampled_road_m=distance,
                         over_100m_from_sampled_road=distance>100, source_date=store.partition))
    return store.write('building_accessibility', rows,
                       dict(caveat='distance to sampled roads, not access entitlement, routing, or complete national coverage'))


def map_change_audit(store, previous=None):
    current = [(r['kind']+':'+r['feature_id'],from_wkb(r['geometry'])) for r in store.read('map_features')]
    if previous:
        before = [(r['kind']+':'+r['feature_id'],from_wkb(r['geometry'])) for r in previous]
        mode = 'supplied_previous_snapshot'
    else:
        # A controlled revision scenario teaches additions, deletions and modifications.
        # It never pretends these are actual historical Overture edits.
        before = current[1:] + [('fixture-removed-feature',Point(4.35,50.85))]
        if len(before)>1:
            before[0] = (before[0][0],Point(4.36,50.86))
        mode = 'synthetic_change_scenario_over_current_reference'
    result = compare(before,current)
    return store.json('map_change_audit',dict(**result,provenance=mode,
                                            counts={k:len(v) for k,v in result.items()}))
