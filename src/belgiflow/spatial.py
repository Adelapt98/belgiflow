"""Explicit country filtering and metric distances."""
from shapely.geometry import Point
from shapely import transform
from pyproj import Transformer
from functools import lru_cache


def within_country(features, country):
    if country.is_empty or not country.is_valid:
        raise ValueError('invalid country geometry')
    seen, accepted, rejected = {}, [], []
    for identity, geometry in features:
        if identity in seen:
            if not seen[identity].equals(geometry):
                raise ValueError('conflicting geometry for feature identifier')
            continue
        seen[identity]=geometry
        if geometry.is_empty or not geometry.is_valid:
            rejected.append(identity)
        elif country.intersects(geometry):
            accepted.append((identity, geometry.intersection(country)))
    return accepted, rejected


def distance_meters(first, second):
    projection = _projection().transform
    return transform(Point(first), projection, interleaved=False).distance(transform(Point(second), projection, interleaved=False))


@lru_cache(maxsize=1)
def _projection():
    return Transformer.from_crs('EPSG:4326', 'EPSG:3812', always_xy=True)
