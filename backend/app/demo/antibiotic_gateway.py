"""Explicit loopback antibiotic chart candidate. Not attached to production API."""
import os,secrets
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter,Depends,Query
from starlette.responses import JSONResponse
from app.api.routes.circulatory import service as circulatory_service
from app.api.routes.patient_state import StateQuery
from app.api.schemas.antibiotic_chart import AntibioticDraft,AntibioticHistoryRequest
from app.demo.renal_fluid_entry_gateway import SyntheticRF2Gateway
from app.demo.hosting import PREFIX
from app.services.antibiotic_chart_service import AntibioticChartService
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction

ABX=PREFIX+'/synthetic-antibiotics';router=APIRouter()
def service(base=Depends(circulatory_service)):return AntibioticChartService(base.dependencies)
@router.get(ABX)
def catalog(query:Annotated[StateQuery,Query()],app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.catalog(repo,query.review_start,query.review_end)
@router.post(ABX+'/validate')
def validate(body:AntibioticDraft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.action(repo,body,'validate')
@router.post(ABX+'/lookup')
def lookup(body:AntibioticDraft,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.action(repo,body,'lookup')
@router.post(ABX+'/save')
def save(body:AntibioticDraft,app=Depends(service)):
    with execution_transaction(app.dependencies.engine) as tx:return app.action(tx.repository,body,'save')
@router.post(ABX+'/history')
def history(body:AntibioticHistoryRequest,app=Depends(service)):
    with transaction(app.dependencies.engine) as repo:return app.history(repo,body)
class SyntheticAntibioticGateway(SyntheticRF2Gateway):
    def __init__(self,database,frontend,signing_key,origin):
        super().__init__(database,frontend,signing_key,origin);self.core.include_router(router)
    async def __call__(self,scope,receive,send):
        if scope['type']=='http' and (scope['path']==ABX or scope['path'].startswith(ABX+'/')):
            headers=dict(scope.get('headers',()));path=scope['path'];method=scope['method']
            read=method=='GET' and path==ABX
            write=method=='POST' and path in {ABX+'/'+a for a in ('validate','lookup','save','history')}
            allowed=scope.get('client') and scope['client'][0] in ('127.0.0.1','::1') and headers.get(b'host',b'').decode()==self.host and headers.get(b'sec-fetch-site',b'none') in (b'none',b'same-origin') and (read or write and headers.get(b'origin',b'').decode()==self.origin and headers.get(b'content-type',b'').split(b';')[0]==b'application/json')
            if not allowed:return await JSONResponse({'code':'local_antibiotic_denied'},status_code=403)(scope,receive,send)
            async def no_store(message):
                if message['type']=='http.response.start':message={**message,'headers':[*message.get('headers',()),(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]}
                await send(message)
            return await self.core(scope,receive,no_store)
        return await super().__call__(scope,receive,send)
def from_environment():return SyntheticAntibioticGateway(Path(os.environ['CLINRX_ABX_DATABASE']),Path(os.environ['CLINRX_ABX_FRONTEND']),secrets.token_hex(32),os.environ['CLINRX_ABX_ORIGIN'])
