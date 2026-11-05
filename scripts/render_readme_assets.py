"""Generate documentation figures from real planner results and the actual job catalog."""
from pathlib import Path
import base64
import html
import json
import textwrap
from shapely import from_wkb
from shapely.geometry import shape
from belgiflow.planner.server import load_engine
from belgiflow.planner.engine import EXAMPLE
from belgiflow.platform.catalog import PIPELINES

OUT=Path('docs/assets')
OUT.mkdir(parents=True,exist_ok=True)

def esc(value): return html.escape(str(value))
def rect(x,y,w,h,fill='#ffffff',stroke='#dfe6de',radius=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'
def text(x,y,value,size=16,color='#253b32',weight=400):
    return f'<text x="{x}" y="{y}" font-family="DejaVu Sans,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(value)}</text>'
def logo(name,x,y,w,h):
    p=OUT/'brands'/name
    mime='image/svg+xml' if p.suffix=='.svg' else 'image/png'
    data=base64.b64encode(p.read_bytes()).decode()
    return f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{data}"/>'
def svg(w,h,parts):
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'+''.join(parts)+'</svg>'
def arrow(x1,y1,x2,y2,color='#aab8ab'):
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>'

engine=load_engine(mode='cached')
result=engine.compare(EXAMPLE)
Path('data/readme-planning-result.json').write_text(json.dumps(result,indent=2))
parts=[rect(0,0,1440,850,'#f3f6f1','#f3f6f1',0),text(55,60,'BelgiFlow',29,weight=700),
       text(55,92,'SERVICE-NETWORK PLANNING / BELGIUM',11,'#718574',600),
       text(55,145,'See what a new hub changes.',34,weight=650),
       text(55,177,'Same study area. Same public reference. Two reproducible scenarios.',15,'#718574')]
a=result['baseline']['metrics'];b=result['proposed']['metrics'];delta=result['changes']
for i,(label,value,note) in enumerate([
    ('CURRENT COVERAGE',f"{a['covered_area_km2']:.2f} km²",'1 illustrative service hub'),
    ('PROPOSED COVERAGE',f"{b['covered_area_km2']:.2f} km²",'2 illustrative service hubs'),
    ('NEW SERVICE AREA',f"+{delta['added_area_km2']:.2f} km²",'Computed from polygon difference'),
    ('SAMPLED BUILDINGS',str(b['covered_buildings']),'Observed footprints, not demand')]):
    y=218+i*127
    parts += [rect(55,y,330,108),text(75,y+27,label,10,'#778878',600),text(75,y+64,value,30,weight=600),text(75,y+88,note,11,'#7a897d')]
parts += [rect(410,218,975,489,'#edf1e9'),text(435,247,'BRUSSELS STUDY AREA',11,'#70826d',600)]
coverage=engine.to_meters(shape(result['proposed']['coverage']))
minx,miny,maxx,maxy=coverage.bounds
margin=450
minx-=margin;miny-=margin;maxx+=margin;maxy+=margin
scale=min(900/(maxx-minx),400/(maxy-miny))
cx=(minx+maxx)/2;cy=(miny+maxy)/2

def pt(x,y): return (897+(x-cx)*scale,478-(y-cy)*scale)
def path(geometry):
    pieces=[]
    if geometry.is_empty: return ''
    if geometry.geom_type in ('MultiPolygon','GeometryCollection','MultiLineString'):
        return ''.join(path(g) for g in geometry.geoms)
    rings=[geometry.exterior]+list(geometry.interiors) if geometry.geom_type=='Polygon' else [geometry]
    for ring in rings:
        coords=[pt(x,y) for x,y in ring.coords]
        pieces.append('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in coords)+(' Z' if geometry.geom_type=='Polygon' else ''))
    return ' '.join(pieces)
for x in range(440,1380,45): parts.append(f'<path d="M{x},265 V680" stroke="#dfe6d9" stroke-width="1"/>')
for y in range(275,690,45): parts.append(f'<path d="M430,{y} H1370" stroke="#dfe6d9" stroke-width="1"/>')
for geometry,stroke,fill,opacity in [(result['baseline']['coverage'],'#5e86be','#789bc7',.25),
                                      (delta['newly_covered'],'#659267','#8eb582',.35),
                                      (result['proposed']['overlap'],'#bc954c','#d6b36d',.4)]:
    parts.append(f'<path d="{path(engine.to_meters(shape(geometry)))}" stroke="{stroke}" fill="{fill}" fill-opacity="{opacity}" stroke-width="2" fill-rule="evenodd"/>')
for row in engine.features:
    if row['kind'] not in ('segment','building'):continue
    geom=engine.to_meters(from_wkb(row['geometry']))
    parts.append(f'<path d="{path(geom)}" fill="'+('#49614a' if row['kind']=='building' else 'none')+'" stroke="#607c60" stroke-width="1"/>')
for hub,color in [(result['baseline']['hubs'][0],'#4e77b2'),(result['proposed']['hubs'][1],'#4b8256')]:
    from shapely.geometry import Point
    point=engine.to_meters(Point(hub['longitude'],hub['latitude']))
    x,y=pt(point.x,point.y)
    parts += [f'<circle cx="{x}" cy="{y}" r="8" fill="{color}" stroke="white" stroke-width="3"/>',
              rect(x-68,y-40,136,25,'#ffffff','#d7e1d3',5),text(x-55,y-23,hub['name'],11)]
parts += [text(438,733,'Radius coverage, not travel time. Building metrics refer only to the supplied sample.',12,'#74816f'),
          text(55,805,'Public vectors: © OpenStreetMap contributors, Overture Maps Foundation.',11,'#74816f'),
          text(55,825,'Reference '+result['provenance']['release']+' | Illustrative hub locations | Generated from actual comparison results.',10,'#859180')]
(OUT/'planning-report.svg').write_text(svg(1440,850,parts),encoding='utf-8')

# Pipeline cards are generated from the actual executable job catalog.
parts=[rect(0,0,1500,910,'#f5f7f3','#f5f7f3',0),logo('dagster.svg',55,35,170,47),
       text(55,125,f'{len(PIPELINES)} pipelines. One planning product.',32,weight=650),
       text(55,156,'Independently launchable date-partitioned jobs with shared data contracts.',15,'#758773')]
for i,(job,purpose,concepts) in enumerate(PIPELINES):
    x=55+(i%5)*282;y=195+(i//5)*213
    parts += [rect(x,y,263,191),rect(x+16,y+16,32,26,'#edf4e9','#edf4e9',5),text(x+23,y+34,job[:2],12,'#5d7e51',600)]
    lines=textwrap.wrap(purpose,width=23)
    for j,line in enumerate(lines): parts.append(text(x+16,y+76+j*21,line,15,weight=600))
    note=textwrap.wrap(concepts,width=31)[:3]
    for j,line in enumerate(note): parts.append(text(x+16,y+126+j*16,line,10,'#7d8b76'))
parts += [text(55,876,'Generated from belgiflow.platform.catalog. Local graph tested. Optional AWS execution is not yet deployed.',11,'#819079')]
(OUT/'pipeline-map.svg').write_text(svg(1500,910,parts),encoding='utf-8')

# Product path and the supporting infrastructure are explicitly separated.
parts=[rect(0,0,1500,1030,'#f5f7f3','#f5f7f3',0),
       '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#aab8ab"/></marker></defs>',
       text(55,65,'BelgiFlow architecture',31,weight=650),
       text(55,98,'Data acquisition, processing, storage and delivery.',15,'#778875'),
       rect(55,135,1390,230,'#eef4e9','#dae4d4'),text(78,167,'PLANNING PRODUCT',11,'#6d855d',600)]
for x,title,lines in [(90,'Public map reference',['Overture snapshots','Buildings + roads + boundary']),
                      (430,'Coverage engine',['Configurable service hubs','Metric geometry + scenario comparison']),
                      (890,'Planning workspace',['Interactive map and scenario editor','Coverage gains, overlap, CSV and JSON'])]:
    width=300 if x==90 else 390 if x==430 else 510
    parts += [rect(x,190,width,130),text(x+20,224,title,19,weight=650),text(x+20,253,lines[0],12,'#7d8a76'),text(x+20,277,lines[1],12,'#7d8a76')]
parts += [arrow(390,253,425,253),arrow(820,253,885,253),
          rect(55,395,1390,230,'#ffffff','#dfe6de'),text(78,427,'DATA ENGINEERING',11,'#6d855d',600),
          logo('dagster.svg',110,470,175,48),text(108,552,'15 jobs · 21 connected assets',13,'#70846d'),
          logo('dbt.png',450,468,120,48),logo('spark.png',600,468,135,48),
          text(450,552,'SQL models + distributed batches',13,'#70846d'),
          text(925,490,'Parquet · DuckDB · PostgreSQL',22,weight=600),text(925,525,'History, quality and operational data products',13,'#70846d'),
          arrow(310,497,420,497),arrow(760,497,890,497),
          rect(55,660,1390,270,'#f4f1f8','#e1d9e9'),text(78,692,'AWS INFRASTRUCTURE',11,'#8a739d',600)]
for x,file,title,note in [(110,'Amazon-Elastic-Container-Service.svg','ECS Fargate','On-demand task execution'),
                           (445,'Amazon-Simple-Storage-Service.svg','Amazon S3','Versioned product bundles'),
                           (780,'AWS-Glue.svg','AWS Glue','Spark + data catalog'),
                           (1115,'Amazon-Redshift.svg','Amazon Redshift','Serving tables + dbt')]:
    parts += [rect(x,720,275,165),logo(file,x+19,741,55,55),text(x+20,826,title,18,weight=600),text(x+20,852,note,12,'#83728e')]
parts += [text(55,980,'',11,'#84907d'),
          text(55,1002,'Infrastructure as code: Terraform   |   Application services: ECS   |   Data lake: S3   |   Processing: Glue   |   Analytics: Redshift',11,'#84907d')]
(OUT/'architecture.svg').write_text(svg(1500,1030,parts),encoding='utf-8')
print('Generated planning-report.svg, pipeline-map.svg, architecture.svg from source and actual results.')
