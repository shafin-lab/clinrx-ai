"""Capture synthetic loopback API and read-only database correspondence. No keys."""
from pathlib import Path
import sqlite3,json,hashlib,urllib.request,urllib.parse
p=Path(__file__).resolve().parent
root=p.parent
live=root/'hemodynamics-complete-final-local-run'
manifest=json.loads((live/'manifest.json').read_text())
query=urllib.parse.urlencode({k:manifest[k] for k in ('review_start','review_end')})
base='http://127.0.0.1:8766/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
with urllib.request.urlopen(base+'/patient-state-v3?'+query) as r:state=json.load(r)
assert state['execution_enabled'] is False
state['state_context']='[REDACTED signed read context]'
(p/'live-state-redacted.json').write_text(json.dumps(state,indent=2)+'\n')

def tables(path):
 with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  rows={};readable={}
  for name in names:
   cols=[r[1] for r in db.execute('PRAGMA table_info("'+name+'")')]
   raw=[list(r) for r in db.execute('SELECT * FROM "'+name+'" ORDER BY rowid')]
   rows[name]=raw;readable[name]={'columns':cols,'rows':raw}
 return rows,readable
rows,readable=tables(live/'synthetic.sqlite3')
old,_=tables(root/'abg-echo-local-run/synthetic.sqlite3')
digest=lambda obj:hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert digest(old)=='91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c'
assert len(rows['fact_revision'])==162 and len(rows['circulatory_execution'])==2
stored={(r[1],r[2],r[3]):r for r in rows['fact_revision']}
items=state['assembly']['snapshot']['items'];assert len(items)==156
for item in items:
 f=item['fact'];r=stored[(f['kind'],f['id'],f['revision'])]
 assert json.loads(r[7])==f and hashlib.sha256(r[7].encode()).hexdigest()==item['expected_digest']
matched=0
for r in old['fact_revision']:
 assert r[7]==stored[(r[1],r[2],r[3])][7];matched+=1
for suffix in ('15','30','45','60'):
 f=next(i['fact'] for i in items if i['fact']['id']=='fs-CI-'+suffix)
 assert f['production']=='source_calculated'
for key in ('released_example','withheld_example'):
 with urllib.request.urlopen(base+'/circulatory-reviews/'+manifest[key]) as r:body=r.read()
 with urllib.request.urlopen(base+'/circulatory-reviews/'+manifest[key]) as r:assert r.read()==body
 (p/(key+'-response.json')).write_bytes(body)
with sqlite3.connect('file:'+str(live/'synthetic.sqlite3')+'?mode=ro',uri=True) as db,sqlite3.connect(p/'synthetic.sqlite3') as dest:db.backup(dest)
(p/'raw-row-arrays.json').write_text(json.dumps(rows,indent=2)+'\n')
(p/'readable-tables.json').write_text(json.dumps(readable,indent=2)+'\n')
result={'execution_enabled':False,'api_records':len(items),'tables':len(rows),'fact_revisions':len(rows['fact_revision']),'retained_receipts':2,'integrity':'ok','api_facts_and_digests_matched':len(items),'old_database_row_sha256_unchanged':digest(old),'all_original_fact_payloads_matched':matched,'new_database_row_sha256':digest(rows),'matching_retained_lookups_repeat_byte_identically':True,'boundary':'Implementation-produced local synthetic verification; no independent or clinical acceptance inferred.'}
(p/'live-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
