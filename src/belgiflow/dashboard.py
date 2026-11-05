"""Offline HTML dashboard generated from published marts."""
import html
import json
from pathlib import Path
from .storage import read_current


def render(root='data'):
    root=Path(root)
    report=read_current(root/'dashboard')
    boundary=report.get('map_boundary')
    from shapely.geometry import shape
    polygons=[]
    if boundary:
        geometry=shape(boundary['geometry']).simplify(.003)
        polygons=list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]
    def position(x,y):
        return ((x-2.5)/4*700, (51.6-y)/2.2*500)
    paths=[]
    for polygon in polygons:
        coords=[position(x,y) for x,y in polygon.exterior.coords]
        paths.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in coords)+'" fill="#d8e8e4" stroke="#527c70"/>')
    for depot in report['depots']:
        x,y=position(depot['longitude'],depot['latitude'])
        paths.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#d35b37"><title>{html.escape(depot["entity_id"])}</title></circle>')
    rows=''.join('<tr data-depot="'+html.escape(r['depot_id'])+'">'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ['depot_id','shipments','delivered','on_time'])+'</tr>' for r in report['marts'])
    options=''.join(f'<option>{html.escape(d["entity_id"])}</option>' for d in report['depots'])
    document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>BelgiFlow operations</title><style>body{font:16px system-ui;background:#f3f6f4;color:#16382e;margin:30px auto;max-width:1100px;padding:20px}header,section{background:white;border-radius:12px;padding:24px;margin-bottom:18px}h1{margin:0}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}svg{width:100%;max-height:440px}small{color:#52675f}</style>
    <header><h1>BelgiFlow</h1><p>Belgium logistics data platform</p><strong>Synthetic operational data. No real shipments or customers.</strong></header>
    <div class="grid"><section><h2>Belgian reference map</h2><svg viewBox="0 0 700 500">MAP</svg><small>Map source: Overture Maps. © OpenStreetMap contributors. Fictional depots shown. Map display uses longitude and latitude, not metric distances.</small></section>
    <section><h2>Published batch</h2><p>EVENTS normalized events</p><p>OUTSIDE shipments outside their historical service radius</p><p>Generated: GENERATED</p><p>Critical checks passed before publication. An old publication does not establish current pipeline health.</p></section></div>
    <section><h2>Depot performance</h2><label>Depot <select id="filter"><option value="">All depots</option>OPTIONS</select></label><table><thead><tr><th>Depot</th><th>Shipments</th><th>Delivered</th><th>On time</th></tr></thead><tbody>ROWS</tbody></table></section>
    <script>document.getElementById('filter').addEventListener('change',function(){document.querySelectorAll('tbody tr').forEach(row=>row.hidden=this.value!==''&&row.dataset.depot!==this.value)})</script></html>'''
    for key,value in {'MAP':''.join(paths),'EVENTS':str(report['events']),'OUTSIDE':str(report['coverage']['outside']),
                      'GENERATED':html.escape(report['generated_at']),'OPTIONS':options,'ROWS':rows}.items():
        document=document.replace(key,value)
    target=root/'dashboard/index.html'
    target.write_text(document,encoding='utf-8')
    return target
