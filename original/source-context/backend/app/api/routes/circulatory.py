"""Thin M7 adapters; all clinical behavior stays in the approved backend."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request,Response
from app.api.dependencies import (ApplicationDependencies,SyntheticIdentity,get_config,get_engine,get_access_context,get_workflow_clock)
from app.api.circulatory_commands import CirculatoryStateCodec,CirculatoryCommandCodec
from app.api.middleware import no_store
from app.api.routes.temporal_reviews import PREFIX,clinical_metadata
from app.api.routes.patient_state import StateQuery
from app.api.schemas.temporal_review import TemporalReviewRequest,ReconciliationRequest
from app.api.schemas.circulatory import (CirculatoryStateResponse,CirculatoryPreparationRequest,CirculatoryPreparedResponse,CirculatoryExecutionResponse,CirculatoryReconciliationResponse)
from app.execution.patient_state_v3_execution import GRANT_ACTOR,GRANT_TARGET
from app.services.circulatory_product_service import CirculatoryProductService

router=APIRouter(prefix=PREFIX,dependencies=[Depends(no_store)])

def service(config=Depends(get_config),engine=Depends(get_engine),access=Depends(get_access_context),clock=Depends(get_workflow_clock)):
    return CirculatoryProductService(ApplicationDependencies(config,engine,access,
        SyntheticIdentity(actor=GRANT_ACTOR,target=GRANT_TARGET),clock,
        CirculatoryStateCodec(config.envelope_signing_key),CirculatoryCommandCodec(config.envelope_signing_key)))

@router.get('/patient-state-v3',response_model=CirculatoryStateResponse)
def state(patient_id:str,encounter_id:str,query:Annotated[StateQuery,Query()],response:Response,app=Depends(service)):
    clinical_metadata(response,app)
    return app.state(patient_id,encounter_id,query.review_start,query.review_end)

@router.post('/circulatory-review-preparations',response_model=CirculatoryPreparedResponse)
def prepare(patient_id:str,encounter_id:str,body:CirculatoryPreparationRequest,request:Request,response:Response,app=Depends(service)):
    request.state.completion_stage='inference_preparation'
    clinical_metadata(response,app)
    return app.prepare(patient_id,encounter_id,body)

@router.post('/circulatory-reviews',response_model=CirculatoryExecutionResponse)
def execute(patient_id:str,encounter_id:str,body:TemporalReviewRequest,request:Request,response:Response,app=Depends(service)):
    command=app.command(patient_id,encounter_id,body.command)
    request.state.execution_id=command.execution_id
    clinical_metadata(response,app)
    return app.execute(command)

@router.get('/circulatory-reviews/{execution_id}',response_model=CirculatoryExecutionResponse)
def find(patient_id:str,encounter_id:str,execution_id:UUID,request:Request,response:Response,app=Depends(service)):
    request.state.execution_id=execution_id
    clinical_metadata(response,app)
    return app.find(patient_id,encounter_id,execution_id)

@router.post('/circulatory-review-reconciliations',response_model=CirculatoryReconciliationResponse)
def reconcile(patient_id:str,encounter_id:str,body:ReconciliationRequest,request:Request,response:Response,app=Depends(service)):
    command=app.command(patient_id,encounter_id,body.command)
    request.state.execution_id=command.execution_id
    clinical_metadata(response,app)
    return app.reconcile(command)

from app.api.schemas.circulatory import CirculatoryHistoryRequest,CirculatoryHistoryResponse

@router.post('/circulatory-evidence-history',response_model=CirculatoryHistoryResponse)
def history(patient_id:str,encounter_id:str,body:CirculatoryHistoryRequest,response:Response,app=Depends(service)):
    clinical_metadata(response,app)
    return app.history(patient_id,encounter_id,body)
