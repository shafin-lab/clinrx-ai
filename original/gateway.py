"""Local validation capture wrapper. Responses are delivered unchanged."""
import hashlib,json,secrets,time
from pathlib import Path
from app.demo.renal_fluid_gateway import SyntheticRenalFluidGateway
ROOT=Path(__file__).resolve().parent
app=SyntheticRenalFluidGateway(ROOT/'synthetic.sqlite3',ROOT/'frontend',secrets.token_hex(32),'http://127.0.0.1:5197')
serial=0
def sanitized(value):
 if isinstance(value,dict):return {k:('[REDACTED]' if k in ('state_context','command') else sanitized(v)) for k,v in value.items()}
 if isinstance(value,list):return [sanitized(v) for v in value]
 return value
async def application(scope,receive,send):
 global serial
 if scope['type']!='http':return await app(scope,receive,send)
 serial+=1;number=serial;response=[];request=[];status=None
 async def wrapped_receive():
  m=await receive()
  if m['type']=='http.request':request.append(m.get('body',b''))
  return m
 async def wrapped_send(m):
  nonlocal status
  if m['type']=='http.response.start':status=m['status']
  if m['type']=='http.response.body':response.append(m.get('body',b''))
  await send(m)
 try:await app(scope,wrapped_receive,wrapped_send)
 finally:
  event={'at':time.time(),'number':number,'method':scope['method'],'path':scope['path'],'status':status}
  if scope['path'].startswith('/api/') or scope['path']=='/health':
   for side,chunks in [('request',request),('response',response)]:
    raw=b''.join(chunks)
    if raw:
     try:
      name=f'{number:03}-{side}-redacted.json';(ROOT/'evidence'/name).write_text(json.dumps(sanitized(json.loads(raw)),indent=2)+'\n');event[side]=name
     except (ValueError,UnicodeDecodeError):event[side]='non-json response not captured'
  with (ROOT/'evidence/events.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
