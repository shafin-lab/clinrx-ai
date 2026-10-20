from pathlib import Path
import urllib.request,urllib.error,json,uuid,sqlite3,hashlib
r=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6');out=r/'rf2-f123-validation';origin='http://127.0.0.1:5201';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-rf2';events=[]
def redact(v):
 if isinstance(v,dict):return {k:'REDACTED_CONTEXT' if k=='state_context' else redact(x) for k,x in v.items()}
 if isinstance(v,list):return [redact(x) for x in v]
 return v
def call(path,b=None):
 raw=json.dumps(b,separators=(',',':')).encode() if b is not None else None
 req=urllib.request.Request(origin+path,data=raw,headers={'Origin':origin,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=30) as response:status=response.status;value=json.loads(response.read())
 except urllib.error.HTTPError as e:status=e.code;value=json.loads(e.read())
 events.append({'path':path,'request':b,'status':status,'response':redact(value)});return status,value
status,health=call('/health');assert status==200 and health['execution_enabled'] is False
status,cat=call(prefix);assert status==200 and cat['cutoff']['fact_watermark']==182 and cat['execution_enabled'] is False
item=next(x for x in cat['combined']['circulatory']['assembly']['snapshot']['items'] if x['fact']['id']=='fs-WEIGHT');f=item['fact'];p={'repository':cat['repository'],'reference':{'kind':f['kind'],'id':f['id'],'version':f['revision']},'digest':item['expected_digest'],'ingestion':item['ingestion']['ingestion_sequence'],'cutoff':182}
assert call(prefix+'/history',{'repository':str(uuid.uuid4()),'pins':[p]})[0]==409
assert call(prefix+'/history',{'repository':cat['repository'],'pins':[{**p,'repository':str(uuid.uuid4())}]})[0]==409
assert call(prefix+'/history',{'repository':cat['repository'],'pins':[p]})[0]==200
for name in ('013-request.json','019-request.json'):
 b=json.loads((r/'rf2-milestone-validation/api-journey'/name).read_text());status,v=call(prefix+'/lookup',b);assert status==200 and v['evidence']['fact']['id']==b['id'] and json.loads(v['request_canonical'])==b
# Validate a new draft retaining the original urine/weight selections: read-only, no append.
b=json.loads((r/'rf2-milestone-validation/api-journey/013-request.json').read_text());b.update(id=str(uuid.uuid4()),revision=str(uuid.uuid4()))
status,v=call(prefix+'/validate',b);assert status==200 and len(v['source_review'])==3
assert any(x['selected']!=x['terminal'] for x in v['source_review'])
b['source_review']=v['source_review'];assert call(prefix+'/validate',b)[0]==409
for x in b['source_review']:x['retain_historical']=True
status,v=call(prefix+'/validate',b);assert status==200 and v['source_review']==b['source_review']
b['source_review'][0]['terminal_digest']='a'*64
status,v=call(prefix+'/validate',b);assert status==409 and v['code']=='rf2_source_review_changed'
with sqlite3.connect(f'file:{r/"rf2-milestone-validation/runtime/synthetic.sqlite3"}?mode=ro',uri=True) as db,sqlite3.connect(out/'runtime-after.sqlite3') as backup:
 assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('pragma foreign_key_check').fetchall();db.backup(backup)
 after={t:db.execute('select * from "'+t+'" order by rowid').fetchall() for t, in db.execute("select name from sqlite_master where type='table' order by name")}
assert json.loads(json.dumps(after))==json.loads((out/'runtime-before-rows.json').read_text())
(out/'runtime-after-rows.json').write_text(json.dumps(after,indent=2)+'\n');(out/'runtime-events-redacted.json').write_text(json.dumps(events,indent=2)+'\n')
result={'status':'PASS','application':'757b163f0f56f1343a32455fc0c4427460dfdd71','http_events':len(events),'all_12_tables_unchanged':True,'fact_revisions':len(after['fact_revision']),'retained_receipts':len(after['circulatory_execution']),'execution_enabled':False,'historical_source_review_explicit':True,'old_exact_note_requests_preserved':2,'limitations':'Actual read/validation HTTP only; no new note save, no browser or browser-storage inspection'}
(out/'RUNTIME-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
