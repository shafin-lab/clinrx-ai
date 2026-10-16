import json,sqlite3,hashlib,urllib.request,urllib.parse
from pathlib import Path
OUT=Path(__file__).resolve().parent
DB=OUT.parent/'abg-echo-local-run/synthetic.sqlite3'
P='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
BASE='http://127.0.0.1:8766'
def rows():
 with sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True) as db:
  names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  return {n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in names}
def get(path):
 with urllib.request.urlopen(BASE+path) as r:
  assert r.status==200
  return json.load(r)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
before=rows()
manifest=json.loads((DB.parent/'manifest.json').read_text())
state=get(P+'/patient-state-v3?'+urllib.parse.urlencode({k:manifest[k] for k in ('review_start','review_end')}))
assert state['execution_enabled'] is False
items=state['assembly']['snapshot']['items']
assert len(items)==41 and len({i['fact']['kind'] for i in items})==14
assert all(i['fact']['id']!='m7-HPI' for i in items)
with sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True) as db:
 stored={(k,i,v):json.loads(payload) for k,i,v,payload in db.execute('SELECT kind,fact_id,revision,payload FROM fact_revision')}
for i in items:
 f=i['fact'];assert f==stored[(f['kind'],f['id'],f['revision'])]
 assert i['ingestion']['repository_id']==state['assembly']['request']['scope']['repository_cutoff']['repository_id']
 assert i['ingestion']['ingestion_sequence']<=state['assembly']['request']['scope']['repository_cutoff']['fact_watermark']
for label,expected in [('released_example','released'),('withheld_example','withheld')]:
 r=get(P+'/circulatory-reviews/'+manifest[label])
 assert r['execution_id']==manifest[label] and r['record']['decision']['outcome']==expected
 (OUT/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n')
after=rows();assert before==after
assert len(after['circulatory_execution'])==2
state['state_context']='redacted.ephemeral-read-context'
(OUT/'live-state.json').write_text(json.dumps(state,indent=2)+'\n')
report={'execution_enabled':False,'records':len(items),'populated_families':14,'supported_families':15,
 'hpi_absent':True,'state_facts_match_persisted_payloads':len(items),'unchanged_tables_during_api_reads':len(before),
 'retained_receipts':len(after['circulatory_execution']),'rows_sha256_before':digest(before),'rows_sha256_after':digest(after)}
(OUT/'live-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
