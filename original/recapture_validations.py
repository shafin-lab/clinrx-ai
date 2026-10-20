from pathlib import Path
import urllib.request,urllib.error,json,hashlib,uuid,datetime
root=Path.cwd().parent;out=root/'rf2-f2-compatibility-validation'/'immutable-validation-recaptures';out.mkdir(exist_ok=True)
u='http://127.0.0.1:5201';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-rf2'
def get(path):
 return json.load(urllib.request.urlopen(urllib.request.Request(u+path,headers={'Origin':u}),timeout=30))
assert get('/health')['execution_enabled'] is False
cat=get(prefix)
# Use the original captured note command, retaining its actual historical pins.
b=json.loads((root/'rf2-milestone-validation/api-journey/013-request.json').read_text());b.update(id=str(uuid.uuid4()),revision=str(uuid.uuid4()))
events=[]
def capture(number,body):
 raw=json.dumps(body,separators=(',',':'),ensure_ascii=False).encode()
 request_path=out/f'{number:02}-request.json';request_path.write_bytes(raw)
 req=urllib.request.Request(u+prefix+'/validate',data=raw,headers={'Origin':u,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:status=r.status;response=r.read()
 except urllib.error.HTTPError as r:status=r.code;response=r.read()
 (out/f'{number:02}-response.json').write_bytes(response)
 value=json.loads(response)
 # Freeze the dispatched JSON value; no event retains a reference to mutable body.
 events.append({'number':number,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'POST','path':prefix+'/validate','status':status,'request_file':request_path.name,'request_sha256':hashlib.sha256(raw).hexdigest(),'response_file':f'{number:02}-response.json','response_sha256':hashlib.sha256(response).hexdigest(),'request':json.loads(raw)})
 return status,value
status,result=capture(1,b);assert status==200
b['source_review']=result['source_review'];assert any(r['selected']!=r['terminal'] for r in b['source_review'])
assert capture(2,b)[0]==409
for row in b['source_review']:row['retain_historical']=True
assert capture(3,b)[0]==200
b['source_review'][0]['terminal_digest']='a'*64
assert capture(4,b)[0]==409
assert 'source_review' not in events[0]['request']
assert not any(r['retain_historical'] for r in events[1]['request']['source_review'])
assert all(r['retain_historical'] for r in events[2]['request']['source_review'])
assert events[2]['request']['source_review'][0]['terminal_digest']!='a'*64
(out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
(out/'ATTRIBUTION.md').write_text('Fresh immutable validation-only recaptures on the running 757b163 local server. Four POST /validate operations; no save, no browser exercise. Original corrupted mutable-request transcript is preserved and not relabelled. Raw dispatched request bytes and raw response bytes are saved individually before any later mutation. Historical source pins remain at their original cutoff; current checks occurred later.\n')
print(json.dumps({'statuses':[e['status'] for e in events],'requests_frozen':True,'execution_enabled':False}))
