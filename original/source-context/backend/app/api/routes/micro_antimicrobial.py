"""Thin S/I/U/D adapters; all clinical behavior stays in M6.3/M6.4."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request,Response
from app.api.dependencies import (ApplicationDependencies,SyntheticIdentity,get_config,get_engine,get_access_context,get_workflow_clock)
from app.api.micro_commands import MicroStateCodec,MicroCommandCodec
from app.api.middleware import no_store
from app.api.routes.temporal_reviews import PREFIX,clinical_metadata
from app.api.routes.patient_state import StateQuery
from app.api.schemas.temporal_review import TemporalReviewRequest,ReconciliationRequest
from app.api.schemas.micro_antimicrobial import (MicroStateResponse,MicroPreparationRequest,MicroPreparedResponse,MicroExecutionResponse,MicroReconciliationResponse)
from app.execution.patient_state_v2_execution import GRANT_ACTOR,GRANT_TARGET
from app.services.micro_antimicrobial_product_service import MicroAntimicrobialProductService

router=APIRouter(prefix=PREFIX,dependencies=[Depends(no_store)])

def service(config=Depends(get_config),engine=Depends(get_engine),access=Depends(get_access_context),clock=Depends(get_workflow_clock)):
    return MicroAntimicrobialProductService(ApplicationDependencies(config,engine,access,
        SyntheticIdentity(actor=GRANT_ACTOR,target=GRANT_TARGET),clock,
        MicroStateCodec(config.envelope_signing_key),MicroCommandCodec(config.envelope_signing_key)))

@router.get('/patient-state-v2',response_model=MicroStateResponse)
def state(patient_id:str,encounter_id:str,query:Annotated[StateQuery,Query()],response:Response,app=Depends(service)):
    clinical_metadata(response,app)
    return app.state(patient_id,encounter_id,query.review_start,query.review_end)

@router.post('/micro-antimicrobial-review-preparations',response_model=MicroPreparedResponse)
def prepare(patient_id:str,encounter_id:str,body:MicroPreparationRequest,request:Request,response:Response,app=Depends(service)):
    request.state.completion_stage='inference_preparation'
    clinical_metadata(response,app)
    return app.prepare(patient_id,encounter_id,body)

@router.post('/micro-antimicrobial-reviews',response_model=MicroExecutionResponse)
def execute(patient_id:str,encounter_id:str,body:TemporalReviewRequest,request:Request,response:Response,app=Depends(service)):
    command=app.command(patient_id,encounter_id,body.command)
    request.state.execution_id=command.execution_id
    clinical_metadata(response,app)
    return app.execute(command)

@router.get('/micro-antimicrobial-reviews/{execution_id}',response_model=MicroExecutionResponse)
def find(patient_id:str,encounter_id:str,execution_id:UUID,request:Request,response:Response,app=Depends(service)):
    request.state.execution_id=execution_id
    clinical_metadata(response,app)
    return app.find(patient_id,encounter_id,execution_id)

@router.post('/micro-antimicrobial-review-reconciliations',response_model=MicroReconciliationResponse)
def reconcile(patient_id:str,encounter_id:str,body:ReconciliationRequest,request:Request,response:Response,app=Depends(service)):
    command=app.command(patient_id,encounter_id,body.command)
    request.state.execution_id=command.execution_id
    clinical_metadata(response,app)
    return app.reconcile(command)
