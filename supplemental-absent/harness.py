"""Disposable loopback evidence harness, never part of application source."""
import asyncio,json,secrets,hashlib,time,sqlite3
from pathlib import Path
from contextlib import AsyncExitStack
from dataclasses import replace
from app.main import create_app
from app.api.config import APIConfig
from app.demo.circulatory import bootstrap,facts,TARGET,SIMULATION_AT,manifest,PROV
from app.models.clinical.common import LineageEdge
from app.persistence.database import create_database
from app.persistence.repository import transaction

ROOT=Path(__file__).resolve().parent
CONTROL=ROOT/'control.json'
apps={};stack=AsyncExitStack();serial=0;faulted=set();corrected=set()
def event(value):
 with (ROOT/'events.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),**value},default=str)+'\n')
def seed(engine):
 bootstrap(engine)
 p=facts()[0];support=facts()[11]
 data=p.model_dump();data.update(revision='2',supersedes=p.reference,correction_reason='Isolated synthetic cuff calibration fixture')
 ref={**p.reference.model_dump(),'version':'2'}
 data['acquisition'].update(method='automated_cuff',zeroing='not_applicable',zeroing_provenance=None,zeroing_application=None)
 data['acquisition']['calibration_application']['acquisition']=ref
 data['acquisition']['calibration_provenance']={**PROV.model_dump(),'upstream':(LineageEdge(target=support.reference,relationship='derived_from'),)}
 with transaction(engine) as repo:repo.append_revision(type(p).model_validate(data),target=TARGET)
def correction(engine,name):
 original=facts()[11]
 if name=='pressure':
  with transaction(engine) as repo:
   # Reconstruct this test fixture's exact pressure revision 2 via recorded history.
   from app.persistence.history import FactIdentity
   from app.persistence.bounded_history import HistoryBudget
   hist=repo.list_bounded_history(identity=FactIdentity(kind='circulatory_pressure',id='m7-P'),target=TARGET,cutoff=repo.capture_cutoff(),budget=HistoryBudget(max_rows=8))
   original=hist.records[-1].fact
 data=original.model_dump();data.update(revision=str(int(original.revision)+1),supersedes=original.reference,correction_reason='Isolated synthetic '+name+' correction')
 if name=='provenance':data['provenance']={**data['provenance'],'actor':'Isolated corrected source'}
 if name=='withdrawn':data['record_status']='withdrawn'
 if name=='pressure':data['acquisition']['calibration_application']['acquisition']={**original.reference.model_dump(),'version':data['revision']}
 revised=type(original).model_validate(data)
 with transaction(engine) as repo:repo.append_revision(revised,target=TARGET)
 event({'event':'correction','scenario':name,'consumed':original.reference.model_dump(),'terminal':revised.reference.model_dump()})
async def get_app(name,closed):
 if name not in apps:
  engine=create_database(ROOT/(name+'.sqlite3'));seed(engine)
  cfg=APIConfig(database_path=ROOT/(name+'.sqlite3'),environment='test',api_port=8765,
   allowed_dev_origins=('http://127.0.0.1:5178',),envelope_signing_key=secrets.token_hex(32),
   clock_mode='historical_simulation',simulation_at=SIMULATION_AT,circulatory_execution_enabled=True)
  app=create_app(cfg,engine=engine);await stack.enter_async_context(app.router.lifespan_context(app))
  apps[name]=(app,engine)
  event({'event':'scenario_created','scenario':name,'database':str(ROOT/(name+'.sqlite3')),'manifest':manifest()})
 app,engine=apps[name]
 app.state.dependencies=replace(app.state.dependencies,config=app.state.dependencies.config.model_copy(update={'circulatory_execution_enabled':not closed}))
 return app,engine
def rows_snapshot(engine, stem):
 with engine.connect() as conn:
  tables=('repository_identity','fact_revision','circulatory_execution')
  result={}
  for table in tables:
   rows=conn.exec_driver_sql('SELECT * FROM '+table+' ORDER BY 1')
   result[table]={'columns':list(rows.keys()),'rows':[list(row) for row in rows.fetchall()]}
 (ROOT/(stem+'.json')).write_text(json.dumps({'captured_at':time.time(),'tables':result},indent=2))

async def application(scope,receive,send):
 global serial
 if scope['type']=='lifespan':
  while True:
   message=await receive()
   if message['type']=='lifespan.startup':await send({'type':'lifespan.startup.complete'})
   else:
    await stack.aclose()
    for _,engine in apps.values():engine.dispose()
    await send({'type':'lifespan.shutdown.complete'});return
 if scope['type']!='http':return
 settings=json.loads(CONTROL.read_text());name=settings['scenario'];mode=settings.get('fault','none')
 app,engine=await get_app(name,settings.get('closed',False))
 serial+=1;number=serial;stem=f'{number:03}-{name}';chunks=[]
 while True:
  message=await receive();chunks.append(message)
  if not message.get('more_body',False):break
 request=b''.join(m.get('body',b'') for m in chunks)
 messages=[]
 async def replay():return chunks.pop(0) if chunks else await receive()
 async def capture(message):messages.append(message)
 rows_snapshot(engine,stem+'-before-rows')
 execution=scope['method']=='POST' and scope['path'].endswith('/circulatory-reviews')
 applyfault=execution and mode!='none' and name not in faulted
 if execution and name in ('same_value','provenance','withdrawn','pressure') and name not in corrected:
  correction(engine,name);corrected.add(name)
 if applyfault and mode=='absent':
  # Simulate a request lost before API dispatch. No execution service is called.
  messages=[{'type':'http.response.start','status':502,'headers':[(b'content-type',b'application/json')]},{'type':'http.response.body','body':b'{}'}]
 else:await app(scope,replay,capture)
 rows_snapshot(engine,stem+'-after-rows')
 body=b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body')
 start=next(m for m in messages if m['type']=='http.response.start')
 (ROOT/(stem+'-request.bin')).write_bytes(request)
 (ROOT/(stem+'-response.bin')).write_bytes(body)
 event({'event':'http','number':number,'scenario':name,'method':scope['method'],'path':scope['path'],'query':scope.get('query_string',b'').decode(),
  'origin':dict(scope.get('headers',[])).get(b'origin',b'').decode(),'status':start['status'],'request':stem+'-request.bin','response':stem+'-response.bin',
  'response_sha256':hashlib.sha256(body).hexdigest(),'closed':settings.get('closed',False),'fault':mode if applyfault else None})
 if applyfault:
  faulted.add(name)
  if mode=='timeout':
   # A real commit has completed; delay delivery beyond the real client's 30s deadline.
   await asyncio.sleep(35)
  elif mode=='malformed':
   value=json.loads(body);value['record']['final_recheck']['inference']['reference']['id']='foreign'
   body=json.dumps(value,separators=(',',':')).encode()
  elif mode=='post_commit_error':
   start={**start,'status':500};body=b'{"code":"internal_error"}'
  if mode in ('malformed','post_commit_error'):
   start={**start,'headers':[(k,v) for k,v in start['headers'] if k.lower()!=b'content-length']+[(b'content-length',str(len(body)).encode())]}
   messages=[start,{'type':'http.response.body','body':body}]
   (ROOT/(stem+'-delivered.bin')).write_bytes(body)
 for message in messages:await send(message)
