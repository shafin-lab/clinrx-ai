"""Portable data-only checks. Uses Python standard library; imports no application code."""
from pathlib import Path
from datetime import datetime
import json,hashlib,sqlite3,runpy
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
manifest=json.loads((p/'PUBLISHED-SHA256SUMS.json').read_text())
for name,digest in manifest.items():assert sha((p/name).read_bytes())==digest,name
original=json.loads((p/'original/SHA256SUMS.json').read_text())
for name,digest in original.items():assert sha((p/'original'/name).read_bytes())==digest,name
identity=json.loads((p/'source-identity.json').read_text())
for name,digest in identity['files_sha256'].items():assert sha((p/'original/source'/name).read_bytes())==digest,name
runpy.run_path(str(p/'original/verify_capture.py'),run_name='__main__')

def rows(path):
 with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  return {n:[list(r) for r in db.execute('SELECT * FROM "'+n+'" ORDER BY rowid')] for n in names}
current=rows(p/'original/synthetic.sqlite3');baseline=rows(p/'original-baseline-database.sqlite3')
assert current==json.loads((p/'original/raw-row-arrays.json').read_text())
assert baseline==json.loads((p/'original-baseline-rows.json').read_text())
assert sha(json.dumps(current,sort_keys=True,separators=(',',':')).encode())=='273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc'
assert sha(json.dumps(baseline,sort_keys=True,separators=(',',':')).encode())=='91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c'
readable=json.loads((p/'original/readable-tables.json').read_text())
assert {n:d['rows'] for n,d in readable.items()}==current
stored={(r[1],r[2],r[3]):r for r in current['fact_revision']}
for r in baseline['fact_revision']:assert stored[(r[1],r[2],r[3])][7]==r[7]
state=json.loads((p/'original/live-state-redacted.json').read_text());scope=state['assembly_request']['scope'];cutoff=scope['repository_cutoff']
assert state['assembly']['request']==state['assembly_request']
assert state['assembly']['snapshot']['scope']==scope
assert sha(canonical(state['assembly']))==state['assembly_digest']
assert current['repository_identity'][0][1]==cutoff['repository_id']
index=json.loads((p/'api-items-index.json').read_text());items=state['assembly']['snapshot']['items'];by_id={(i['fact']['kind'],i['fact']['id'],i['fact']['revision']):i for i in items}
for item in items:
 f=item['fact'];meta=item['ingestion'];row=stored[(f['kind'],f['id'],f['revision'])]
 assert f['binding']['target']=={'patient_id':scope['patient_id'],'encounter_id':scope['encounter_id'],'longitudinal_context_id':None}
 assert (row[4],row[5])==(scope['patient_id'],scope['encounter_id'])
 assert meta['repository_id']==cutoff['repository_id']
 assert meta['ingestion_sequence']==row[0]<=cutoff['fact_watermark']
 assert datetime.fromisoformat(meta['ingested_at'])==datetime.fromisoformat(row[8]) and meta['payload_version']==row[6]
 assert datetime.fromisoformat(meta['ingested_at'])<=datetime.fromisoformat(cutoff['captured_at'])
for entry in index:assert json.loads((p/entry['path']).read_text())==by_id[(entry['kind'],entry['id'],entry['revision'])]
assert len(index)==len(items)==156
for name in ('released','withheld'):
 response=json.loads((p/('original/'+name+'_example-response.json')).read_text());r=next(r for r in current['circulatory_execution'] if r[0]==response['execution_id'])
 assert sha(r[5].encode())==r[3] and json.loads(r[5])==response['record']
 assert response['record']['decision']['outcome']==name
print(json.dumps({'publication_hashes':len(manifest),'original_hashes':len(original),'source_files':len(identity['files_sha256']),'api_and_ingestion_correspondences':len(items),'baseline_fact_payloads_preserved':len(baseline['fact_revision']),'all_tables':len(current),'retained_receipts':len(current['circulatory_execution']),'result':'PASS','scope':'Data-only implementation verification; not independent clinical or live browser acceptance'},indent=2))
