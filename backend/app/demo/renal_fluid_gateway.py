"""Separate loopback RF1 entry point; production and Docker defaults unchanged."""
import os
import secrets
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from starlette.responses import JSONResponse
from app.api.routes.circulatory import service as circulatory_service
from app.api.routes.patient_state import StateQuery
from app.api.schemas.renal_fluid import RenalFluidResponse, RenalHistoryRequest, RenalHistoryResponse
from app.demo.authoring import SyntheticAuthoringGateway
from app.demo.hosting import PREFIX
from app.services.renal_fluid_product_service import RenalFluidProductService

STATE = PREFIX + '/synthetic-renal-fluid'
HISTORY = STATE + '/history'
router = APIRouter()

def service(app=Depends(circulatory_service)):
    return RenalFluidProductService(app.dependencies)

@router.get(STATE, response_model=RenalFluidResponse)
def state(query: Annotated[StateQuery, Query()], response: Response, app=Depends(service)):
    response.headers['Cache-Control'] = 'no-store'
    return app.state('synthetic-p1', 'synthetic-e1', query.review_start, query.review_end)

@router.post(HISTORY, response_model=RenalHistoryResponse)
def history(body: RenalHistoryRequest, response: Response, app=Depends(service)):
    response.headers['Cache-Control'] = 'no-store'
    return app.history('synthetic-p1', 'synthetic-e1', body)

class SyntheticRenalFluidGateway(SyntheticAuthoringGateway):
    def __init__(self, database, frontend, signing_key, origin):
        super().__init__(database, frontend, signing_key, origin)
        self.core.include_router(router)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] in (STATE, HISTORY):
            headers = dict(scope.get('headers', ()))
            local = scope.get('client') and scope['client'][0] in ('127.0.0.1', '::1')
            allowed = ((scope['path'] == STATE and scope['method'] == 'GET') or
                (scope['path'] == HISTORY and scope['method'] == 'POST'
                and headers.get(b'origin', b'').decode() == self.origin
                and headers.get(b'content-type', b'').split(b';')[0] == b'application/json'))
            if not local or headers.get(b'host', b'').decode() != self.host or not allowed or headers.get(b'sec-fetch-site', b'same-origin') not in (b'same-origin', b'none'):
                return await JSONResponse({'code': 'local_read_denied'}, status_code=403, headers={'Cache-Control': 'no-store'})(scope, receive, send)
            return await self.core(scope, receive, send)
        return await super().__call__(scope, receive, send)

def from_environment():
    return SyntheticRenalFluidGateway(Path(os.environ['CLINRX_RF1_DATABASE']),
        Path(os.environ['CLINRX_RF1_FRONTEND']), secrets.token_hex(32), os.environ['CLINRX_RF1_ORIGIN'])
