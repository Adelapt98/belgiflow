from pathlib import Path
for directory in ["data", "docs/assets/brands", "src/belgiflow/planner/web/vendor"]:
    Path(directory).mkdir(parents=True, exist_ok=True)
import io,tarfile,zipfile,re,requests
root=Path('.')
url='https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz'
r=requests.get(url,timeout=60);r.raise_for_status()
with tarfile.open(fileobj=io.BytesIO(r.content),mode='r:gz') as archive:
    for name in ['dist/leaflet.js','dist/leaflet.css','dist/leaflet.js.map','LICENSE']:
        data=archive.extractfile('package/'+name).read()
        (root/'src/belgiflow/planner/web/vendor'/Path(name).name).write_bytes(data)
    for member in archive.getmembers():
        if member.name.startswith('package/dist/images/') and member.isfile():
            target=root/'src/belgiflow/planner/web/vendor/images'/Path(member.name).name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
r=requests.get('https://dagster.io/company-pages/brand/dagster-logo.svg',timeout=30);r.raise_for_status()
(root/'docs/assets/brands/dagster.svg').write_bytes(r.content)
r=requests.get('https://cdn.sanity.io/files/wl0ndo6t/main/0ea2ccef348a2014d2a38fa63bf7c23fb898a448.zip',timeout=60);r.raise_for_status()
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    names=[n for n in z.namelist() if n.lower().endswith('.svg') and '__MACOSX' not in n]
    print('dbt assets:',names[:30])
    Path('data/dbt-brand-assets.zip').write_bytes(r.content)
page=requests.get('https://aws.amazon.com/architecture/icons/',timeout=30).text
print('AWS zip links:',re.findall(r'https[^\s\"<>]+\.zip[^\s\"<>]*',page)[:10])
