from pathlib import Path
for directory in ["data", "docs/assets/brands", "src/belgiflow/planner/web/vendor"]:
    Path(directory).mkdir(parents=True, exist_ok=True)
import zipfile,requests,io,json,hashlib
root=Path('docs/assets/brands')
with zipfile.ZipFile('data/dbt-brand-assets.zip') as z:
    (root/'dbt.png').write_bytes(z.read('dbt Logos/dbt-logo.png'))
url='https://d1.awsstatic.com/onedam/marketing-channels/website/public/shared/architecture-icon-release/Icon-package_07312026.5846e92413caa21490223536cc97f1269e44fa92.zip'
cache=Path('data/aws-icons.zip')
if not cache.exists():
    r=requests.get(url,timeout=180);r.raise_for_status();cache.write_bytes(r.content)
with zipfile.ZipFile(cache) as z:
    for service in ['Amazon-Simple-Storage-Service','Amazon-Redshift','AWS-Glue','Amazon-Elastic-Container-Service','Amazon-CloudWatch']:
        matches=[n for n in z.namelist() if n.endswith('/Arch_'+service+'_64.svg')]
        if len(matches)!=1: raise ValueError((service,matches))
        (root/(service+'.svg')).write_bytes(z.read(matches[0]))
url='https://spark.apache.org/images/spark-logo-trademark.png'
r=requests.get(url,timeout=30);r.raise_for_status();(root/'spark.png').write_bytes(r.content)
print('Official brand assets:',[p.name for p in root.iterdir()])
