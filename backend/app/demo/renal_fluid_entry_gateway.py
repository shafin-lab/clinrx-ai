"""Explicit loopback RF2 entry point. No production/Docker configuration changes."""
import os,secrets
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from typing import Annotated
from app.api.routes.patient_state import StateQuery
from starlette.responses import JSONResponse
from app.api.routes.circulatory import service as circulatory_service
from app.api.schemas.renal_fluid_entry import RF2Draft, ResolveRequest
from app.demo.renal_fluid_gateway import SyntheticRenalFluidGateway
from app.demo.hosting import PREFIX
from app.services.renal_fluid_entry_service import RF2Service
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction

RF2=PREFIX+'/synthetic-rf2'
router=APIRouter()
def service(base=Depends(circulatory_service)):return RF2Service(base.dependencies)
@router.get(RF2)
def catalog(review_start:str='2026-10-08T08:00:00+00:00',review_end:str='2026-10-08T10:00:00+00:00',app=Depends(service)):
    from pydantic import TypeAdapter
    from app.api.schemas.common import AwareTimestamp
    start=TypeAdapter(AwareTimestamp).validate_python(review_start);end=TypeAdapter(AwareTimestamp).validate_python(review_end)
    with transaction(app.dependencies.engine) as repo:return app.catalog(repo,start,end)
@router.post(RF2+'/resolve')
def resolve(body:ResolveRequest,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.resolve(repo,body)
@router.post(RF2+'/history')
def history(body:ResolveRequest,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.history(repo,body)
@router.post(RF2+'/validate')
def validate(body:RF2Draft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.validate(repo,body)
@router.post(RF2+'/lookup')
def lookup(body:RF2Draft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.lookup(repo,body)
@router.post(RF2+'/save')
def save(body:RF2Draft,app=Depends(service)):
    with execution_transaction(app.dependencies.engine) as tx:return app.save(tx.repository,body)

class SyntheticRF2Gateway(SyntheticRenalFluidGateway):
    def __init__(self,database,frontend,signing_key,origin):
        super().__init__(database,frontend,signing_key,origin)
        self.core.include_router(router)
    async def __call__(self,scope,receive,send):
        if scope['type']=='http' and (scope['path']==RF2 or scope['path'].startswith(RF2+'/')):
            headers=dict(scope.get('headers',()))
            paths={RF2+'/history',RF2+'/resolve',RF2+'/validate',RF2+'/lookup',RF2+'/save'}
            allowed=(scope['path']==RF2 and scope['method']=='GET') or (scope['path'] in paths and scope['method']=='POST' and headers.get(b'origin',b'').decode()==self.origin and headers.get(b'content-type',b'').split(b';')[0]==b'application/json')
            if not scope.get('client') or scope['client'][0] not in ('127.0.0.1','::1') or headers.get(b'host',b'').decode()!=self.host or headers.get(b'sec-fetch-site',b'same-origin') not in (b'same-origin',b'none') or not allowed:
                return await JSONResponse({'code':'local_rf2_denied'},status_code=403)(scope,receive,send)
            if scope['method']=='POST':
                from app.services.renal_fluid_entry_service import exact_json
                chunks=[];size=0
                while True:
                    m=await receive()
                    if m['type']=='http.disconnect':return
                    chunk=m.get('body',b'');size+=len(chunk)
                    if size>65536:return await JSONResponse({'code':'request_too_large'},status_code=413)(scope,receive,send)
                    chunks.append(chunk)
                    if not m.get('more_body'):break
                raw=b''.join(chunks)
                try:exact_json(raw)
                except (ValueError,UnicodeDecodeError):return await JSONResponse({'code':'invalid_request'},status_code=422)(scope,receive,send)
                delivered=False
                upstream=receive
                async def replay_receive():
                    nonlocal delivered
                    if not delivered:delivered=True;return {'type':'http.request','body':raw,'more_body':False}
                    return await upstream()
                receive=replay_receive
            async def no_store(m):
                if m['type']=='http.response.start':m={**m,'headers':[*m.get('headers',()),(b'cache-control',b'no-store')]}
                await send(m)
            return await self.core(scope,receive,no_store)
        return await super().__call__(scope,receive,send)
def from_environment():
    return SyntheticRF2Gateway(Path(os.environ['CLINRX_RF2_DATABASE']),Path(os.environ['CLINRX_RF2_FRONTEND']),secrets.token_hex(32),os.environ['CLINRX_RF2_ORIGIN'])
