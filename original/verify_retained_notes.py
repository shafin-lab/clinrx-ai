from pathlib import Path
from tempfile import TemporaryDirectory
import json,shutil
from fastapi.testclient import TestClient
from app.demo.renal_fluid_entry_gateway import SyntheticRF2Gateway,RF2
from tests.test_synthetic_hosting import rows
from tests.test_renal_fluid_entry import ORIGIN
root=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6')
with TemporaryDirectory() as t:
 p=Path(t);db=p/'copy.sqlite3';shutil.copyfile(root/'rf2-milestone-validation/api-journey/after.sqlite3',db);front=p/'frontend';(front/'assets').mkdir(parents=True);(front/'index.html').write_text('synthetic');before=rows(db)
 with TestClient(SyntheticRF2Gateway(db,front,'ab'*32,ORIGIN),base_url=ORIGIN,client=('127.0.0.1',1),headers={'Origin':ORIGIN}) as c:
  for name in ('013-request.json','019-request.json'):
   b=json.loads((root/'rf2-milestone-validation/api-journey'/name).read_text());assert 'source_review' not in b
   for action in ('lookup','save'):
    r=c.post(RF2+'/'+action,json=b);assert r.status_code==200,r.text;v=r.json();assert json.loads(v['request_canonical'])==b;assert v['evidence']['fact']['id']==b['id'];assert v['evidence']['metadata'].get('source_review') is None
  assert rows(db)==before
  assert c.get('/health').json()['execution_enabled'] is False
 print(json.dumps({'status':'PASS','actual_pre_fix_notes':2,'exact_original_lookup_and_retry_checks':4,'original_request_canonical_correspondence':True,'all_12_tables_unchanged':True,'original_fact_revisions':len(before['fact_revision']),'retained_receipts':len(before['circulatory_execution']),'attribution':'Corrected consumer against copies of original captured SQLite and raw requests; runtime and published evidence unchanged'},indent=2))
