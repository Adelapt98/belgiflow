"""Reproducible planning data product using the same comparison engine as the app."""
import json
import os
from pathlib import Path
from .engine import CoverageEngine, EXAMPLE
from .server import csv_report


def planning_product(store):
    path = os.getenv('BELGIFLOW_PLANNING_CONFIG')
    request = json.loads(Path(path).read_text(encoding='utf-8')) if path else EXAMPLE
    result = CoverageEngine.from_store(store).compare(request)
    store.json('network_plan', result)
    store.path('network_plan', 'csv').write_bytes(csv_report(result))
    return dict(plan_id=result['plan_id'], baseline_km2=result['baseline']['metrics']['covered_area_km2'],
                proposed_km2=result['proposed']['metrics']['covered_area_km2'],
                new_km2=result['changes']['added_area_km2'],
                additional_sampled_buildings=result['changes']['additional_buildings'])
