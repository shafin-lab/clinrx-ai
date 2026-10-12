"""Synthetic product composition; clinical semantics remain in M2/M3/M4."""
from datetime import timedelta, timezone
from uuid import uuid4

from app.api.review_commands import StateContext
from app.api import projections
from app.api.schemas.temporal_review import PreparedTemporalReviewResponse, ReconciliationResponse
from app.execution.patient_state import PatientStateScope
from app.execution.patient_state_assembly import assemble_patient_state
from app.execution.patient_state_inference import PatientStateTemporalRelationRequest, build_patient_state_temporal_inference
from app.execution.patient_state_execution import PatientStateTemporalExecutionRequest, digest
from app.execution.patient_state_workflow import execute_patient_state_temporal_review, reconcile_patient_state_temporal_execution
from app.models.clinical.common import ContextTarget
from app.persistence.errors import PersistenceInputError, QueryLimitExceeded, RecordNotFound
from app.persistence.patient_state_executions import find_patient_state_temporal_execution
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction


class PatientStateProductService:
    def __init__(self, dependencies):
        self.dependencies = dependencies

    def scope(self, patient_id, encounter_id):
        self.dependencies.access.require_scope(patient_id, encounter_id)
        return ContextTarget(patient_id=patient_id, encounter_id=encounter_id)

    def require_scope(self, target, patient_id, encounter_id):
        if target != self.scope(patient_id, encounter_id):
            raise RecordNotFound('resource not found')

    def bounded(self, response):
        if len(response.model_dump_json().encode('utf-8')) > self.dependencies.config.max_response_bytes:
            raise QueryLimitExceeded('response limit exceeded')
        return response

    def window(self, start, end):
        length = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
        if length < timedelta(0):
            raise PersistenceInputError('invalid review window')
        if length > timedelta(seconds=self.dependencies.config.max_review_window_seconds):
            raise QueryLimitExceeded('review window limit exceeded')

    def state(self, patient_id, encounter_id, start, end):
        target = self.scope(patient_id, encounter_id)
        self.window(start, end)
        with transaction(self.dependencies.engine) as repository:
            repository.load_patient(patient_id)
            repository.load_encounter(patient_id=patient_id, encounter_id=encounter_id)
            cutoff = repository.capture_cutoff()
        scope = PatientStateScope(patient_id=target.patient_id, encounter_id=target.encounter_id,
            review_start=start, review_end=end, repository_cutoff=cutoff)
        assembly = assemble_patient_state(self.dependencies.engine, scope=scope)
        envelope = self.dependencies.state_context.issue(StateContext(scope=scope))
        return self.bounded(projections.state(assembly, envelope))

    def prepare(self, patient_id, encounter_id, body):
        dependencies = self.dependencies
        context = dependencies.state_context.verify(body.state_context)
        self.require_scope(context.scope.target, patient_id, encounter_id)
        self.window(context.scope.review_start, context.scope.review_end)
        assembly = assemble_patient_state(dependencies.engine, scope=context.scope)
        inference_request = PatientStateTemporalRelationRequest(scope=context.scope,
            earlier_laboratory=body.earlier_laboratory.model_dump(),
            later_laboratory=body.later_laboratory.model_dump(), medication=body.medication.model_dump(),
            inference_id=str(uuid4()), revision='1', executed_at=dependencies.clock())
        inference = build_patient_state_temporal_inference(assembly=assembly, request=inference_request)
        identity = dependencies.identity
        target = type(identity.target).model_validate({**identity.target.model_dump(), 'context': context.scope.target})
        # Existing shared owner supplies the commit-uncertainty contract. Only its
        # fact repository is used; no execution or automatic retry occurs here.
        with execution_transaction(dependencies.engine) as tx:
            tx.repository.append_fact(inference, target=context.scope.target)
            cutoff = tx.repository.capture_cutoff()
            request = PatientStateTemporalExecutionRequest(execution_id=body.execution_id,
                target=target, actor=identity.actor, inference_request=inference_request,
                inference_cutoff=cutoff, expected_inference_digest=digest(inference),
                requested_at=dependencies.clock())
            response = self.bounded(PreparedTemporalReviewResponse(execution_id=request.execution_id,
                inference_reference=projections.reference(inference.reference),
                command=dependencies.execution_command.issue(request)))
        return response

    def command(self, patient_id, encounter_id, token, execution_id=None):
        request = self.dependencies.execution_command.verify(token)
        self.require_scope(request.target.context, patient_id, encounter_id)
        if execution_id is not None and request.execution_id != execution_id:
            raise PersistenceInputError('execution identity mismatch')
        return request

    def execute(self, request):
        stored = execute_patient_state_temporal_review(self.dependencies.engine, request, clock=self.dependencies.clock)
        return self.bounded(projections.execution(stored))

    def find(self, patient_id, encounter_id, execution_id):
        target = self.scope(patient_id, encounter_id)
        stored = find_patient_state_temporal_execution(self.dependencies.engine, execution_id, target=target)
        if stored is None:
            raise RecordNotFound('resource not found')
        return self.bounded(projections.execution(stored))

    def reconcile(self, request):
        result = reconcile_patient_state_temporal_execution(self.dependencies.engine, request)
        return self.bounded(ReconciliationResponse(status=result.status,
            execution=None if result.stored is None else projections.execution(result.stored)))
