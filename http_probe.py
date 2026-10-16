import json,sqlite3,urllib.request,urllib.error,hashlib
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-hosting-validation');dbpath=out/'hosted-synthetic.sqlite3'
with sqlite3.connect(dbpath) as db:
 tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
 rows={name:db.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall() for name, in tables}
 (out/'rows-before-browser.json').write_text(json.dumps(rows,indent=2)+'\n')
 with sqlite3.connect(out/'fixture-snapshot.sqlite3') as copy:db.backup(copy)
base='http://127.0.0.1:5181';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1';events=[]
def call(name,path,body=None):
 raw=None if body is None else json.dumps(body,separators=(',',':')).encode()
 if raw is not None:(out/(name+'-request.json')).write_bytes(raw)
 request=urllib.request.Request(base+path,data=raw,headers={} if raw is None else {'Content-Type':'application/json'})
 try:response=urllib.request.urlopen(request)
 except urllib.error.HTTPError as error:response=error
 result=response.read();(out/(name+'-response.json')).write_bytes(result)
 events.append({'name':name,'method':request.get_method(),'url':base+path,'status':response.status,'headers':dict(response.headers),'response_sha256':hashlib.sha256(result).hexdigest()})
 return response.status,json.loads(result)
manifest=json.loads((out/'fixture-manifest.json').read_text())
from urllib.parse import urlencode
status,state=call('state',prefix+'/patient-state-v3?'+urlencode({k:manifest[k] for k in ('review_start','review_end')}));assert status==200 and state['execution_enabled'] is False
assert len(state['assembly']['snapshot']['items'])==26
item=next(i for i in state['assembly']['snapshot']['items'] if i['fact']['id']=='m7-CAL')
assert call('history',prefix+'/circulatory-evidence-history',{'state_context':state['state_context'],'reference':{'kind':item['fact']['kind'],'id':'m7-CAL','version':'2'}})[0]==200
for ending,outcome in [('c901','released'),('c902','withheld')]:
 code,receipt=call(outcome,prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending);assert code==200 and receipt['record']['decision']['outcome']==outcome
for suffix in ['circulatory-review-preparations','circulatory-reviews','circulatory-review-reconciliations']:
 assert call('blocked-'+suffix,prefix+'/'+suffix,{'command':'blocked-local-probe'})[0]==404
(out/'http-exchanges.json').write_text(json.dumps(events,indent=2)+'\n')
print('PASS: real HTTP state, bounded history, two receipts and three blocked execution routes')
