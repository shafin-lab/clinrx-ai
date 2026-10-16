"""Portable data-only publication verification; no app imports or network calls."""
from pathlib import Path
import json,hashlib,runpy
p=Path(__file__).resolve().parent
canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for name,h in json.loads((p/'SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==h,name
source=json.loads((p/'source-sha256.json').read_text());tested=json.loads((p/'validation/tested-source-sha256.json').read_text());assert source==tested
for name,h in source.items():assert hashlib.sha256((p/'source'/name).read_bytes()).hexdigest()==h,name
states=json.loads((p/'source/frontend/tests/fixtures/authoredCaseHpiCollision.json').read_text())
for order,state in states.items():
 assert state['execution_enabled'] is False
 assert hashlib.sha256(canonical(state['assembly'])).hexdigest()==state['assembly_digest']
 scope=state['assembly_request']['scope'];assert state['assembly']['request']==state['assembly_request'];assert state['assembly']['snapshot']['scope']==scope
 items=state['assembly']['snapshot']['items'];assert len(items)==42
 hpi=[i for i in items if i['fact']['kind']=='circulatory_device_prediction'];assert len(hpi)==1 and hpi[0]['fact']['concept']=='hpi' and hpi[0]['fact']['id']=='m7-ABG-PH'
 assert (items[0] if order=='first' else items[-1])==hpi[0]
 oxygen=next(i for i in items if i['fact']['kind']=='circulatory_oxygen' and i['fact']['id']=='m7-ABG-PH');assert oxygen['fact']['result']['quantity']['value']=='7.31'
 for i in items:
  assert hashlib.sha256(canonical(i['fact'])).hexdigest()==i['expected_digest']
  assert i['ingestion']['repository_id']==scope['repository_cutoff']['repository_id']
  assert i['ingestion']['ingestion_sequence']<=scope['repository_cutoff']['fact_watermark']
runpy.run_path(str(p/'verify_binary_mirrors.py'),run_name='__main__')
print(json.dumps({'source_files':len(source),'decoded_hpi_fixture_states':len(states),'fact_digest_checks':84,'result':'PASS','scope':'Implementation data-only verification; not independent acceptance'},indent=2))
