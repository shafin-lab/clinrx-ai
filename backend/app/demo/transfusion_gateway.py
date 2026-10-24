"""Opt-in M10 synthetic gateway; all mutations restricted to this loopback surface."""
import os,secrets
from pathlib import Path
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter,Depends,Query,HTTPException
from pydantic import Field,model_validator
from starlette.responses import JSONResponse,Response
from app.api.routes.circulatory import service as circulatory_service
from app.api.routes.patient_state import StateQuery
from app.api.schemas.transfusion import M10Draft,M10History,M10Attachment,M10Evaluation
from app.api.schemas.common import AwareTimestamp
from app.demo.antibiotic_gateway import SyntheticAntibioticGateway
from app.demo.hosting import PREFIX
from app.services.transfusion_service import TransfusionService
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
M10=PREFIX+'/synthetic-m10'
router=APIRouter()
def service(base=Depends(circulatory_service)):return TransfusionService(base.dependencies)
class CatalogQuery(StateQuery):
    repository:UUID|None=None
    cutoff:Annotated[int,Field(ge=0)]|None=None
    @model_validator(mode='after')
    def paired_scope(self):
        if (self.repository is None)!=(self.cutoff is None):raise ValueError('repository and cutoff must be supplied together')
        return self
@router.get(M10)
def catalog(query:Annotated[CatalogQuery,Query()],app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:
        if query.repository is not None:app.require_repo(repo,query.repository)
        return app.catalog(repo,query.review_start,query.review_end,query.cutoff)
@router.post(M10+'/validate')
def validate(body:M10Draft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.action(repo,body,'validate')
@router.post(M10+'/lookup')
def lookup(body:M10Draft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.action(repo,body,'lookup')
@router.post(M10+'/save')
def save(body:M10Draft,app=Depends(service)):
    with execution_transaction(app.dependencies.engine) as tx:return app.action(tx.repository,body,'save')
@router.post(M10+'/history')
def history(body:M10History,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.history(repo,body)
@router.post(M10+'/attachments')
def attachment(body:M10Attachment,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.attachment(repo,body)
@router.get(M10+'/profiles')
def profiles():
    from app.services.m10_profiles import device_profiles,protocol_profiles
    return {'devices':device_profiles(),'protocols':protocol_profiles(),'execution_enabled':False}
@router.post(M10+'/evaluate')
def evaluate(body:M10Evaluation,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.evaluate(repo,body)
@router.get(M10+'/attachments/{digest_value}')
def read_attachment(digest_value:str,repository:UUID,cutoff:int,review_end:AwareTimestamp,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:media,data=app.read_attachment(repo,repository,digest_value,cutoff,review_end)
    return Response(data,media_type=media,headers={'Content-Disposition':'attachment; filename=original-source','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
class SyntheticM10Gateway(SyntheticAntibioticGateway):
    def __init__(self,database,frontend,signing_key,origin):
        super().__init__(database,frontend,signing_key,origin);self.core.include_router(router)
    async def __call__(self,scope,receive,send):
        if scope['type']=='http' and (scope['path']==M10 or scope['path'].startswith(M10+'/')):
            headers=dict(scope.get('headers',()));path=scope['path'];method=scope['method']
            read=method=='GET' and (path in (M10,M10+'/profiles') or path.startswith(M10+'/attachments/'))
            write=method=='POST' and path in {M10+'/'+a for a in ('validate','lookup','save','history','evaluate','attachments')}
            allowed=scope.get('client') and scope['client'][0] in ('127.0.0.1','::1') and headers.get(b'host',b'').decode()==self.host and headers.get(b'sec-fetch-site',b'none') in (b'none',b'same-origin') and (read or write and headers.get(b'origin',b'').decode()==self.origin and headers.get(b'content-type',b'').split(b';')[0]==b'application/json')
            if not allowed:return await JSONResponse({'code':'local_m10_denied'},status_code=403)(scope,receive,send)
            if method=='POST':
                from app.services.renal_fluid_entry_service import exact_json
                chunks=[];size=0
                while True:
                    msg=await receive()
                    if msg['type']=='http.disconnect':return
                    chunk=msg.get('body',b'');size+=len(chunk)
                    if size>262144:return await JSONResponse({'code':'request_too_large'},status_code=413)(scope,receive,send)
                    chunks.append(chunk)
                    if not msg.get('more_body'):break
                raw=b''.join(chunks)
                try:exact_json(raw)
                except (ValueError,UnicodeDecodeError):return await JSONResponse({'code':'invalid_request'},status_code=422)(scope,receive,send)
                delivered=False;upstream=receive
                async def replay_receive():
                    nonlocal delivered
                    if not delivered:delivered=True;return {'type':'http.request','body':raw,'more_body':False}
                    return await upstream()
                receive=replay_receive
            async def no_store(message):
                if message['type']=='http.response.start':message={**message,'headers':[*message.get('headers',()),(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]}
                await send(message)
            return await self.core(scope,receive,no_store)
        return await super().__call__(scope,receive,send)
def retained_signing_key(database):
    """Keep reviewed pending interpretations verifiable after a preview restart."""
    path=Path(database).with_suffix('.m10-signing.key')
    try:
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor,'w') as stream:stream.write(secrets.token_hex(32))
    value=path.read_text().strip()
    if len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise RuntimeError('Invalid retained M10 signing material')
    return value

def from_environment():
    database=Path(os.environ['CLINRX_M10_DATABASE'])
    return SyntheticM10Gateway(database,Path(os.environ['CLINRX_M10_FRONTEND']),retained_signing_key(database),os.environ['CLINRX_M10_ORIGIN'])
