"""Thin scoped transport adapters. No clinical predicates or storage queries."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response
from app.api.dependencies import (ApplicationDependencies, get_config, get_engine, get_access_context,
    get_synthetic_identity, get_workflow_clock, get_state_context_codec, get_execution_command_codec)
from app.api.middleware import no_store
from app.api.schemas.temporal_review import (TemporalReviewPreparationRequest, PreparedTemporalReviewResponse,
    TemporalReviewRequest, TemporalExecutionResponse, ReconciliationRequest, ReconciliationResponse)
from app.services.patient_state_product_service import PatientStateProductService

PREFIX = '/api/v1/patients/{patient_id}/encounters/{encounter_id}'
router = APIRouter(prefix=PREFIX, dependencies=[Depends(no_store)])


def product_service(config=Depends(get_config), engine=Depends(get_engine), access=Depends(get_access_context),
                    identity=Depends(get_synthetic_identity), clock=Depends(get_workflow_clock),
                    state_context=Depends(get_state_context_codec), execution_command=Depends(get_execution_command_codec)):
    return PatientStateProductService(ApplicationDependencies(config, engine, access, identity, clock, state_context, execution_command))


def clinical_metadata(response, service):
    response.headers['X-ClinRx-Mode'] = ('historical-synthetic-simulation'
        if service.dependencies.config.clock_mode == 'historical_simulation' else 'synthetic-only-real-clock')


@router.post('/temporal-review-preparations', response_model=PreparedTemporalReviewResponse)
def prepare(patient_id: str, encounter_id: str, body: TemporalReviewPreparationRequest,
            request: Request, response: Response, service=Depends(product_service)):
    clinical_metadata(response, service)
    # Deliberately do not set execution_id for preparation uncertainty: the
    # execution reconciliation protocol cannot recover an unacknowledged inference.
    request.state.completion_stage = 'inference_preparation'
    return service.prepare(patient_id, encounter_id, body)


@router.post('/temporal-reviews', response_model=TemporalExecutionResponse)
def execute(patient_id: str, encounter_id: str, body: TemporalReviewRequest,
            request: Request, response: Response, service=Depends(product_service)):
    command = service.command(patient_id, encounter_id, body.command)
    request.state.execution_id = command.execution_id
    clinical_metadata(response, service)
    return service.execute(command)


@router.get('/temporal-executions/{execution_id}', response_model=TemporalExecutionResponse)
def find(patient_id: str, encounter_id: str, execution_id: UUID, request: Request, response: Response,
         service=Depends(product_service)):
    request.state.execution_id = execution_id
    clinical_metadata(response, service)
    return service.find(patient_id, encounter_id, execution_id)


@router.post('/temporal-executions/{execution_id}/reconcile', response_model=ReconciliationResponse)
def reconcile(patient_id: str, encounter_id: str, execution_id: UUID, body: ReconciliationRequest,
              request: Request, response: Response, service=Depends(product_service)):
    command = service.command(patient_id, encounter_id, body.command, execution_id)
    request.state.execution_id = command.execution_id
    clinical_metadata(response, service)
    return service.reconcile(command)
