"""Quality-gated incremental warehouse builds and extraction of business marts."""
import os
from pathlib import Path
import subprocess
import sys
import duckdb


def build_marts(store, target='local'):
    executable = str(Path(sys.executable).with_name('dbt.exe' if os.name=='nt' else 'dbt'))
    environment = dict(os.environ, BELGIFLOW_WAREHOUSE=str((store.root/'warehouse.duckdb').resolve()),
                       DBT_SEND_ANONYMOUS_USAGE_STATS='false')
    project = Path(os.environ.get('BELGIFLOW_DBT_PROJECT','warehouse_dbt')).resolve()
    result = subprocess.run([executable,'build','--project-dir',str(project),'--profiles-dir',str(project),'--target',target],
                            env=environment,capture_output=True,text=True,timeout=300)
    store.path('dbt_run','log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:
        raise RuntimeError('dbt build failed: '+result.stdout[-3000:]+result.stderr[-1000:])
    if target=='local':
        con=duckdb.connect(str(store.root/'warehouse.duckdb'))
        try:
            cursor=con.execute('SELECT * FROM mart_delivery_sla ORDER BY source_date,depot_id')
            names=[c[0] for c in cursor.description]
            rows=[dict(zip(names,row)) for row in cursor.fetchall()]
            # Only acknowledge the pending source keys after all models and tests pass.
            con.execute('DELETE FROM source_changed_shipments')
        finally:
            con.close()
        return store.write('delivery_sla',rows,dict(engine='dbt-duckdb',incremental='affected shipment IDs'))
    return store.json('redshift_dbt_run',dict(target='redshift',status='completed'))
