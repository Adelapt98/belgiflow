"""Deterministic, CRS-aware service-network comparison using public geography."""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from pyproj import Transformer
from shapely import from_wkb, transform
from shapely.geometry import Point, box, mapping, shape, GeometryCollection
from shapely.ops import unary_union


EXAMPLE = {
    'study_area': [4.29, 50.79, 4.45, 50.91],
    'baseline': {'name': 'Current network', 'hubs': [
        {'id': 'west', 'name': 'West Brussels', 'longitude': 4.335, 'latitude': 50.852, 'radius_m': 1400}]},
    'proposed': {'name': 'Add an eastern service hub', 'hubs': [
        {'id': 'west', 'name': 'West Brussels', 'longitude': 4.335, 'latitude': 50.852, 'radius_m': 1400},
        {'id': 'east', 'name': 'East Brussels', 'longitude': 4.365, 'latitude': 50.844, 'radius_m': 1600}]}}


def number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be a finite number between {low} and {high}')
    return float(value)


def text(value, label):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 or any(ord(c) < 32 for c in value):
        raise ValueError(f'{label} must contain 1 to 80 printable characters')
    return value.strip()


class CoverageEngine:
    def __init__(self, country, features, provenance):
        if country.is_empty or not country.is_valid:
            raise ValueError('reference boundary is empty or invalid')
        self.country = country
        self.provenance = dict(provenance)
        self.project = Transformer.from_crs(4326, 3812, always_xy=True).transform
        self.unproject = Transformer.from_crs(3812, 4326, always_xy=True).transform
        self.country_m = self.to_meters(country)
        self.features = features
        self.buildings = [(r['feature_id'], self.to_meters(from_wkb(r['geometry'])).representative_point())
                          for r in features if r['kind'] == 'building']
        identity = {'boundary': country.wkb_hex, 'features': sorted((r['kind'], r['feature_id'], r['geometry'].hex()) for r in features),
                    'provenance': provenance}
        self.source_id = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    @classmethod
    def from_store(cls, store):
        reference = store.read_json('geographic_reference')
        return cls(shape(reference['geometry']), store.read('map_features'), reference['provenance'])

    def to_meters(self, geometry):
        return transform(geometry, self.project, interleaved=False)

    def to_geojson(self, geometry):
        return mapping(transform(geometry, self.unproject, interleaved=False))

    def validate(self, request):
        if not isinstance(request, dict):
            raise ValueError('comparison must be a JSON object')
        bounds = request.get('study_area')
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError('study_area must be [west, south, east, north]')
        west, south, east, north = [number(v, lo, hi, 'study area coordinate') for v, lo, hi in
                                  zip(bounds, [2.4, 49.4, 2.4, 49.4], [6.5, 51.6, 6.5, 51.6])]
        if east <= west or north <= south:
            raise ValueError('study area must have positive width and height')
        result = {'study_area': [west, south, east, north]}
        for key in ['baseline', 'proposed']:
            scenario = request.get(key)
            if not isinstance(scenario, dict):
                raise ValueError(f'{key} scenario is required')
            hubs = scenario.get('hubs')
            if not isinstance(hubs, list) or len(hubs) > 20:
                raise ValueError('each scenario supports at most 20 hubs')
            accepted = []
            for hub in hubs:
                if not isinstance(hub, dict):
                    raise ValueError('hub must be an object')
                identity = text(hub.get('id'), 'hub ID')
                if not all(c.isascii() and (c.isalnum() or c in '-_') for c in identity):
                    raise ValueError('hub IDs may contain letters, numbers, hyphens and underscores')
                row = dict(id=identity, name=text(hub.get('name'), 'hub name'),
                           longitude=number(hub.get('longitude'), 2.4, 6.5, 'longitude'),
                           latitude=number(hub.get('latitude'), 49.4, 51.6, 'latitude'),
                           radius_m=number(hub.get('radius_m'), 100, 50000, 'radius'))
                if not self.country.covers(Point(row['longitude'], row['latitude'])):
                    raise ValueError(f"{row['name']} must be inside the reference boundary")
                accepted.append(row)
            if len({r['id'] for r in accepted}) != len(accepted):
                raise ValueError('hub IDs must be unique within each scenario')
            result[key] = dict(name=text(scenario.get('name'), 'scenario name'), hubs=accepted)
        return result

    def _scenario(self, scenario, study, buildings):
        circles, hubs = [], []
        for hub in scenario['hubs']:
            point = self.to_meters(Point(hub['longitude'], hub['latitude']))
            area = point.buffer(hub['radius_m'], quad_segs=64).intersection(study)
            circles.append(area)
            hubs.append((hub, point, area))
        coverage = unary_union(circles) if circles else GeometryCollection()
        pairs = [a.intersection(b) for i, a in enumerate(circles) for b in circles[i + 1:]]
        overlap = unary_union(pairs) if pairs else GeometryCollection()
        assignments, unassigned = [], []
        for identity, point in buildings:
            candidates = [(point.distance(center), hub['id']) for hub, center, area in hubs if area.covers(point)]
            if candidates:
                distance, hub_id = min(candidates)
                assignments.append(dict(building_id=identity, hub_id=hub_id, straight_line_m=round(distance, 2)))
            else:
                unassigned.append(identity)
        metrics = dict(hubs=len(hubs), study_area_km2=round(study.area / 1e6, 4),
                       covered_area_km2=round(coverage.area / 1e6, 4),
                       uncovered_area_km2=round(study.difference(coverage).area / 1e6, 4),
                       overlap_area_km2=round(overlap.area / 1e6, 4),
                       coverage_percent=round(100 * coverage.area / study.area, 2),
                       sampled_buildings=len(buildings), covered_buildings=len(assignments),
                       uncovered_buildings=len(unassigned))
        return dict(name=scenario['name'], hubs=scenario['hubs'], metrics=metrics,
                    coverage=self.to_geojson(coverage), overlap=self.to_geojson(overlap),
                    uncovered=self.to_geojson(study.difference(coverage)), assignments=assignments,
                    unassigned_building_ids=unassigned,
                    per_hub=[dict(**hub, assigned_buildings=sum(a['hub_id'] == hub['id'] for a in assignments)) for hub, _, _ in hubs]), coverage

    def compare(self, request):
        request = self.validate(request)
        study = self.to_meters(box(*request['study_area'])).intersection(self.country_m)
        if study.is_empty or study.area < 10000:
            raise ValueError('select at least 0.01 square kilometers inside the reference boundary')
        buildings = [(identity, point) for identity, point in self.buildings if study.covers(point)]
        baseline, first = self._scenario(request['baseline'], study, buildings)
        proposed, second = self._scenario(request['proposed'], study, buildings)
        gained, lost = second.difference(first), first.difference(second)
        identity = sha256(json.dumps(dict(request=request, source=self.source_id), sort_keys=True).encode()).hexdigest()
        return dict(plan_id=identity, request=request, source_id=self.source_id, provenance=self.provenance,
                    study_area=self.to_geojson(study), baseline=baseline, proposed=proposed,
                    changes=dict(added_area_km2=round(gained.area / 1e6, 4),
                                 lost_area_km2=round(lost.area / 1e6, 4),
                                 net_area_km2=round((second.area - first.area) / 1e6, 4),
                                 additional_buildings=proposed['metrics']['covered_buildings'] - baseline['metrics']['covered_buildings'],
                                 newly_covered=self.to_geojson(gained), no_longer_covered=self.to_geojson(lost)),
                    assumptions=['Straight-line radius coverage in EPSG:3812, not driving time or routing.',
                                 'Buildings are the supplied sample, not households, customers, or demand.',
                                 'A building location is represented by an interior point of its footprint.'])

    def bootstrap(self):
        features = [dict(type='Feature', properties=dict(id=r['feature_id'], kind=r['kind']),
                         geometry=mapping(from_wkb(r['geometry']))) for r in self.features if r['kind'] != 'connector']
        return dict(example=deepcopy(EXAMPLE), provenance=self.provenance, source_id=self.source_id,
                    country=mapping(self.country.simplify(.001)),
                    features=dict(type='FeatureCollection', features=features),
                    total_buildings=len(self.buildings),
                    building_sample_extent=mapping(unary_union([from_wkb(r['geometry']) for r in self.features if r['kind']=='building']).envelope))
