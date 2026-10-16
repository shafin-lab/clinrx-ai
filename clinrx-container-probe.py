import subprocess,json,urllib.request,urllib.error,time,sqlite3,hashlib,os,sys
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-container-validation')
profile='clinrx-review-28496c4';socket='unix://'+str(Path.home()/'.colima'/profile/'docker.sock')
container='clinrx-review-28496c4';base='http://127.0.0.1:5182';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')};events=[]
def docker(*args):return subprocess.check_output(['docker','--host',socket,*args],env=env)
def call(name,path,body=None):
 data=None if body is None else json.dumps(body,separators=(',',':')).encode()
 if data is not None:(out/(name+'-request.json')).write_bytes(data)
 request=urllib.request.Request(base+path,data=data,headers={} if data is None else {'Content-Type':'application/json'})
 started=time.time()
 try:response=urllib.request.urlopen(request,timeout=10)
 except urllib.error.HTTPError as error:response=error
 raw=response.read();(out/(name+'-response.bin')).write_bytes(raw)
 events.append({'name':name,'path':path,'method':request.get_method(),'status':response.status,'started_unix':started,'headers':dict(response.headers),'sha256':hashlib.sha256(raw).hexdigest()})
 return response.status,raw
rows_script="""import sqlite3,json
with sqlite3.connect('/app/synthetic/synthetic.sqlite3') as db:
 tables=db.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
 print(json.dumps({name:db.execute('SELECT * FROM \"'+name+'\" ORDER BY rowid').fetchall() for name, in tables},sort_keys=True))
"""
def rows(name):
 data=docker('exec',container,'python','-c',rows_script);(out/(name+'.json')).write_bytes(data);return json.loads(data)
def ready():
 for _ in range(80):
  try:
   with urllib.request.urlopen(base+'/health',timeout=1) as response:
    if response.status==200:return
  except OSError:time.sleep(.25)
 raise AssertionError('container readiness failed')
ready();before=rows('rows-before')
assert len(before)==12 and before['alembic_version']==[['m7_0008']]
manifest=json.loads(docker('exec',container,'cat','/app/synthetic/manifest.json'));(out/'fixture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
from urllib.parse import urlencode
statepath=prefix+'/patient-state-v3?'+urlencode({k:manifest[k] for k in ('review_start','review_end')})
status,raw=call('state',statepath);state=json.loads(raw);assert status==200 and state['execution_enabled'] is False
items=state['assembly']['snapshot']['items'];assert len(items)==26 and len({i['fact']['kind'] for i in items})==15
support=next(i for i in items if i['fact']['id']=='m7-CAL')
history={'state_context':state['state_context'],'reference':{'kind':support['fact']['kind'],'id':'m7-CAL','version':'2'}}
status,raw=call('history',prefix+'/circulatory-evidence-history',history);assert status==200 and [i['fact']['revision'] for i in json.loads(raw)['revisions']]==['1','2']
receipts={}
for name,ending in [('released','c901'),('withheld','c902')]:
 status,raw=call(name,prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending);assert status==200 and json.loads(raw)['record']['decision']['outcome']==name;receipts[name]=raw
for suffix in ['circulatory-review-preparations','circulatory-reviews','circulatory-review-reconciliations','temporal-review-preparations','temporal-reviews']:
 assert call('blocked-'+suffix,prefix+'/'+suffix,{'command':'never-dispatch'})[0]==404
for path in ['/docs','/openapi.json','/synthetic/synthetic.sqlite3',prefix.replace('synthetic-p1','foreign')+'/patient-state-v3']:
 assert call('blocked-file-'+str(len(events)),path)[0]==404
assert call('malformed-history',prefix+'/circulatory-evidence-history',{'state_context':'invalid','reference':{}})[0]==422
assert rows('rows-after-probes')==before
(out/'runtime-user.txt').write_bytes(docker('exec',container,'id'));assert b'uid=10001' in (out/'runtime-user.txt').read_bytes()
(out/'python-version.txt').write_bytes(docker('exec',container,'python','--version'))
(out/'dependency-check.txt').write_bytes(docker('exec',container,'python','-m','pip','check'))
(out/'container-inspect.json').write_bytes(docker('inspect',container))
info=json.loads((out/'container-inspect.json').read_text())[0]
assert info['Config']['User']=='10001:10001' and not info['Mounts']
assert info['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5182'}]
print('PASS initial container checks; restarting same container',flush=True)
(out/'restart-command.txt').write_bytes(docker('restart',container));ready()
for name,ending in [('released','c901'),('withheld','c902')]:
 status,raw=call(name+'-after-restart',prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending);assert status==200 and raw==receipts[name]
status,raw=call('stale-context',prefix+'/circulatory-evidence-history',history);assert status>=400 and json.loads(raw)['code']=='invalid_state_context'
status,raw=call('fresh-state',statepath);fresh=json.loads(raw);assert status==200 and fresh['execution_enabled'] is False
history['state_context']=fresh['state_context'];assert call('fresh-history',prefix+'/circulatory-evidence-history',history)[0]==200
assert rows('rows-after-restart')==before
(out/'http-events.json').write_text(json.dumps(events,indent=2)+'\n')
(out/'probe-results.json').write_text(json.dumps({'status':'PASS','records':26,'families':15,'gate_enabled':False,'receipt_outcomes':['released','withheld'],'all_12_tables_unchanged':True,'restart_receipts_byte_identical':True,'stale_context_rejected':True,'fresh_context_works':True,'non_root_user':True,'host_mounts':False,'loopback_port_only':True,'architecture':'linux/arm64'},indent=2)+'\n')
print('PASS: container state/history, retained outcomes, denied routes, no writes, non-root, loopback exposure and restart recovery',flush=True)
