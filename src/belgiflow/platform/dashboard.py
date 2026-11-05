"""Reviewable business outcomes and pipeline catalog, with no external frontend dependency."""
from datetime import datetime,timezone
import html
from .catalog import PIPELINES


def render(store):
    quality=store.read_json('quality_report')
    if quality['status']!='passed':
        raise ValueError('cannot publish a failed partition')
    sla=[r for r in store.read('delivery_sla') if r['source_date']==store.partition]
    capacity=store.read('capacity_plan')
    coverage=store.read('service_coverage')
    accessible=store.read('building_accessibility')
    source=store.read_json('geographic_reference')['provenance']
    def cells(values):
        return ''.join('<td>'+html.escape(str(v))+'</td>' for v in values)
    pipeline_rows=''.join('<tr>'+cells([name,purpose,concepts])+'</tr>' for name,purpose,concepts in PIPELINES)
    depot_rows=''.join('<tr>'+cells([r['depot_id'],r['shipments'],r['delivered'],r['cancelled'],r['on_time']])+'</tr>' for r in sla)
    cap_rows=''.join('<tr>'+cells([r['depot_id'],r['capacity'],r['shipments'],round(r['utilization'],2),r['excess_shipments']])+'</tr>' for r in capacity)
    document=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>BelgiFlow operational data products</title><style>body{{font:16px system-ui;background:#eef3f1;color:#153c30;max-width:1250px;margin:30px auto;padding:20px}}section,header{{background:white;padding:25px;border-radius:14px;margin-bottom:20px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}.metrics{{display:flex;gap:25px;flex-wrap:wrap}}.metric{{font-size:22px}}small{{color:#50665d}}</style>
    <header><h1>BelgiFlow</h1><p>Supporting delivery coverage and depot operations review</p>
    <strong>Synthetic operations. No real customers, drivers, or shipments.</strong>
    <p>Partition: {store.partition} | Geography: {html.escape(source['mode'])} | Release: {html.escape(source['release'])}</p></header>
    <section class="metrics"><span class="metric">{quality['shipments']} shipments</span><span class="metric">{sum(not r['covered'] for r in coverage)} outside service radius</span><span class="metric">{sum(r['excess_shipments'] for r in capacity)} above depot capacity</span><span class="metric">{len(accessible)} building footprints analyzed</span></section>
    <section><h2>Delivery SLA</h2><table><tr><th>Depot</th><th>Shipments</th><th>Delivered</th><th>Cancelled</th><th>On time</th></tr>{depot_rows}</table></section>
    <section><h2>Capacity planning</h2><table><tr><th>Depot</th><th>Capacity</th><th>Shipments</th><th>Utilization</th><th>Excess shipments</th></tr>{cap_rows}</table></section>
    <section><h2>{len(PIPELINES)} independently launchable pipelines</h2><p>Open <a href="http://localhost:3000">Dagster</a> to inspect assets, select a date partition, launch a job, and review its logs.</p><table><tr><th>Job</th><th>Purpose</th><th>Concepts</th></tr>{pipeline_rows}</table></section>
    <section><h2>Interpretation</h2><p>Coverage is a historical straight-line radius check. Accessibility measures distance to sampled roads, not road routing or legal building access. Map changes use an explicitly synthetic scenario unless a previous snapshot is supplied.</p><small>Map attribution: © OpenStreetMap contributors, Overture Maps Foundation, when public map mode is selected. Quality passed at {html.escape(quality['checked_at'])}. A past publication does not establish current system health.</small></section></html>'''
    target=store.path('dashboard','html')
    target.write_text(document,encoding='utf-8')
    (store.root/'index.html').write_text(document,encoding='utf-8')
    return str(target)
