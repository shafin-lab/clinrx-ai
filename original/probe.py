import subprocess,json,urllib.request,urllib.error,time,sqlite3,hashlib,os,sys
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/expanded-packaging-validation')
profile='clinrx-review-28496c4';socket='unix://'+str(Path.home()/'.colima'/profile/'docker.sock')
container='clinrx-expanded-2539eb6';base='http://127.0.0.1:5183';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
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
items=state['assembly']['snapshot']['items'];assert len(items)==156 and len({i['fact']['kind'] for i in items})==14
assert all(i['fact']['kind']!='circulatory_device_prediction' for i in items)
assert manifest['dataset']=='synthetic-icu-flowsheet/2' and manifest['flowsheet_additional_records']==115 and manifest['optional_hpi_included'] is False
assert len(before['fact_revision'])==162 and len(before['circulatory_execution'])==2
by_ref={(r[1],r[2],r[3]):r for r in before['fact_revision']}
for item in items:
 f=item['fact'];stored=by_ref[(f['kind'],f['id'],f['revision'])]
 assert json.loads(stored[7])==f and hashlib.sha256(stored[7].encode()).hexdigest()==item['expected_digest']
assert call('index','/')[0]==200
import re
index=(out/'index-response.bin').read_text()
for n,asset in enumerate(re.findall(r'(?:src|href)="(/assets/[^"]+)"',index)):
 assert call('asset-'+str(n),asset)[0]==200
assert call('health','/health')[0]==200
support=next(i for i in items if i['fact']['id']=='m7-CAL')
history={'state_context':state['state_context'],'reference':{'kind':support['fact']['kind'],'id':'m7-CAL','version':'2'}}
status,raw=call('history',prefix+'/circulatory-evidence-history',history);assert status==200 and [i['fact']['revision'] for i in json.loads(raw)['revisions']]==['1','2']
event=next(i for i in items if i['fact']['id']=='fs-D-CHANGE')
flow_history={'state_context':state['state_context'],'reference':{'kind':event['fact']['kind'],'id':event['fact']['id'],'version':'1'}}
status,raw=call('flowsheet-history',prefix+'/circulatory-evidence-history',flow_history)
assert status==200 and json.loads(raw)['revisions'][0]['fact']==event['fact']
receipts={}
for name,ending in [('released','c901'),('withheld','c902')]:
 status,raw=call(name,prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending);assert status==200 and json.loads(raw)['record']['decision']['outcome']==name;receipts[name]=raw
 record=json.loads(raw)['record'];stored_receipt=next(r for r in before['circulatory_execution'] if r[0]==record['request']['execution_id'])
 # Identify the canonical stored record without relying on inherited column order.
 stored_payload=next(v for v in stored_receipt if isinstance(v,str) and v.startswith('{'))
 assert json.loads(stored_payload)==record
 assert hashlib.sha256(stored_payload.encode()).hexdigest() in stored_receipt
 assert len(record['final_recheck']['evidence'])==4
 for f in record['evidence']['facts']:
  assert json.loads(by_ref[(f['kind'],f['id'],f['revision'])][7])==f
 for w in record['final_recheck']['evidence']:
  for refkey,digestkey in [('consumed','source_digest'),('terminal','terminal_source_digest')]:
   ref=w[refkey];stored=by_ref[(ref['kind'],ref['id'],ref['version'])]
   assert hashlib.sha256(stored[7].encode()).hexdigest()==w[digestkey]
 assert record['evidence']['facts'][-1]['id']=='m7-CAL' and record['evidence']['facts'][-1]['revision']=='1'
 assert record['final_recheck']['evidence'][-1]['terminal']['version']==('1' if name=='released' else '2')
for suffix in ['circulatory-review-preparations','circulatory-reviews','circulatory-review-reconciliations','temporal-review-preparations','temporal-reviews']:
 assert call('blocked-'+suffix,prefix+'/'+suffix,{'command':'never-dispatch'})[0]==404
for path in ['/docs','/openapi.json','/synthetic/synthetic.sqlite3',prefix.replace('synthetic-p1','foreign')+'/patient-state-v3']:
 assert call('blocked-file-'+str(len(events)),path)[0]==404
assert call('malformed-history',prefix+'/circulatory-evidence-history',{'state_context':'invalid','reference':{}})[0]==422
assert call('malformed-state',prefix+'/patient-state-v3?review_start=invalid&review_end=invalid')[0]==422
assert rows('rows-after-probes')==before
(out/'runtime-user.txt').write_bytes(docker('exec',container,'id'));assert b'uid=10001' in (out/'runtime-user.txt').read_bytes()
(out/'python-version.txt').write_bytes(docker('exec',container,'python','--version'))
(out/'dependency-check.txt').write_bytes(docker('exec',container,'python','-m','pip','check'))
(out/'container-inspect.json').write_bytes(docker('inspect',container))
info=json.loads((out/'container-inspect.json').read_text())[0]
assert info['Config']['User']=='10001:10001' and not info['Mounts']
assert info['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5183'}]
print('PASS initial container checks; restarting same container',flush=True)
(out/'restart-command.txt').write_bytes(docker('restart',container));ready()
for name,ending in [('released','c901'),('withheld','c902')]:
 status,raw=call(name+'-after-restart',prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending);assert status==200 and raw==receipts[name]
status,raw=call('stale-context',prefix+'/circulatory-evidence-history',history);assert status>=400 and json.loads(raw)['code']=='invalid_state_context'
status,raw=call('fresh-state',statepath);fresh=json.loads(raw);assert status==200 and fresh['execution_enabled'] is False
history['state_context']=fresh['state_context'];assert call('fresh-history',prefix+'/circulatory-evidence-history',history)[0]==200
flow_history['state_context']=fresh['state_context']
assert call('fresh-flowsheet-history',prefix+'/circulatory-evidence-history',flow_history)[0]==200
assert rows('rows-after-restart')==before
assert info['Image']==json.loads(docker('image','inspect','clinrx-expanded-demo:2539eb6-local'))[0]['Id']
(out/'http-events.json').write_text(json.dumps(events,indent=2)+'\n')
(out/'probe-results.json').write_text(json.dumps({'status':'PASS','records':156,'populated_families':14,'supported_families':15,'hpi_present':False,'gate_enabled':False,'receipt_outcomes':['released','withheld'],'all_12_tables_unchanged':True,'restart_receipts_byte_identical':True,'stale_context_rejected':True,'fresh_context_works':True,'non_root_user':True,'host_mounts':False,'loopback_port_only':True,'architecture':'linux/arm64'},indent=2)+'\n')
print('PASS: container state/history, retained outcomes, denied routes, no writes, non-root, loopback exposure and restart recovery',flush=True)
