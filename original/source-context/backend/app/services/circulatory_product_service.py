"""Additive HTTP application composition; M7 policy/kernel own clinical semantics."""
from uuid import uuid4
from app.services.patient_state_product_service import PatientStateProductService
from app.api.schemas.circulatory import (CirculatoryStateContext, CirculatoryStateResponse,
    CirculatoryPreparedResponse, CirculatoryReconciliationResponse)
from app.api.circulatory_projections import execution
from app.execution.patient_state_v3 import PatientStateScopeV3
from app.execution.patient_state_v3_assembly import AssemblyRequestV3, assemble_patient_state_v3
from app.execution.patient_state_v3_inference import (CirculatoryTimingRequest, POLICY_VERSION,
    CirculatoryInferenceError, build_circulatory_timing_inference)
from app.execution.patient_state_v3_execution import CirculatoryExecutionRequest, digest
from app.execution.patient_state_v3_workflow import execute_circulatory_review, reconcile_circulatory_execution
from app.persistence.circulatory_executions import find_circulatory_execution
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from app.persistence.errors import RecordNotFound, StorageIntegrityError, UnsupportedOperation

class CirculatoryProductService(PatientStateProductService):
    # Reuse scope, bounded-response, window and command verification infrastructure.
    def state(self,patient_id,encounter_id,start,end):
        target=self.scope(patient_id,encounter_id)
        self.window(start,end)
        with transaction(self.dependencies.engine) as repo:
            repo.load_patient(patient_id)
            repo.load_encounter(patient_id=patient_id,encounter_id=encounter_id)
            cutoff=repo.capture_cutoff()
        scope=PatientStateScopeV3(patient_id=target.patient_id,encounter_id=target.encounter_id,
            review_start=start,review_end=end,repository_cutoff=cutoff)
        ar=AssemblyRequestV3(scope=scope,profile_id='RecordedCirculatoryEvidence',profile_version='1')
        assembly=assemble_patient_state_v3(self.dependencies.engine,request=ar)
        context=self.dependencies.state_context.issue(CirculatoryStateContext(assembly_request=ar,assembly_digest=assembly.canonical_digest))
        return self.bounded(CirculatoryStateResponse(assembly_request=ar,assembly_digest=assembly.canonical_digest,assembly=assembly,state_context=context,execution_enabled=self.dependencies.config.circulatory_execution_enabled))

    def prepare(self,patient_id,encounter_id,body):
        d=self.dependencies
        context=d.state_context.verify(body.state_context)
        scope=context.assembly_request.scope
        self.require_scope(scope.target,patient_id,encounter_id)
        self.window(scope.review_start,scope.review_end)
        assembly=assemble_patient_state_v3(d.engine,request=context.assembly_request)
        if assembly.canonical_digest!=context.assembly_digest:
            raise StorageIntegrityError('historical assembly differs from signed state')
        self.require_enabled()
        pins={field:getattr(body,field).model_dump() for field in ('pressure','lactate','vasopressor')}
        ir=CirculatoryTimingRequest(eligibility_policy=POLICY_VERSION,scope=scope,
            expected_assembly_digest=context.assembly_digest,inference_id=str(uuid4()),executed_at=d.clock(),
            supporting=tuple(p.model_dump() for p in sorted(body.supporting,key=lambda p:(p.reference.kind,p.reference.id,p.reference.version))),**pins)
        try: inference=build_circulatory_timing_inference(assembly=assembly,request=ir)
        except CirculatoryInferenceError as error:
            if error.code in ('invalid_assembly','assembly_digest_mismatch','scope_mismatch'):
                raise StorageIntegrityError('historical assembly integrity failure') from None
            raise UnsupportedOperation('selected evidence is unsuitable') from None
        target=type(d.identity.target).model_validate({**d.identity.target.model_dump(),'context':scope.target})
        with execution_transaction(d.engine) as tx:
            tx.repository.append_fact(inference,target=scope.target)
            cutoff=tx.repository.capture_cutoff()
            command=CirculatoryExecutionRequest(execution_id=body.execution_id,target=target,actor=d.identity.actor,
                inference_request=ir,assembly_request=context.assembly_request,inference_cutoff=cutoff,
                expected_inference_digest=digest(inference),requested_at=d.clock())
            response=self.bounded(CirculatoryPreparedResponse(execution_id=command.execution_id,inference=inference,
                command=d.execution_command.issue(command)))
        return response

    def require_enabled(self):
        if not self.dependencies.config.circulatory_execution_enabled:
            raise UnsupportedOperation('M7 connected execution awaits independent review')

    def execute(self,request):
        # Recovery is available even while connected new execution is gated.
        if not self.dependencies.config.circulatory_execution_enabled:
            stored=find_circulatory_execution(self.dependencies.engine,request.execution_id,target=request.target.context)
            if stored is None:self.require_enabled()
            from app.execution.patient_state_v3_execution import require_circulatory_request_match
            require_circulatory_request_match(stored.record,request)
            return self.bounded(execution(stored))
        return self.bounded(execution(execute_circulatory_review(self.dependencies.engine,request,clock=self.dependencies.clock)))

    def find(self,patient_id,encounter_id,execution_id):
        stored=find_circulatory_execution(self.dependencies.engine,execution_id,target=self.scope(patient_id,encounter_id))
        if stored is None: raise RecordNotFound('resource not found')
        return self.bounded(execution(stored))

    def reconcile(self,request):
        result=reconcile_circulatory_execution(self.dependencies.engine,request)
        return self.bounded(CirculatoryReconciliationResponse(status=result.status,execution=execution(result.stored) if result.stored else None))

    def history(self,patient_id,encounter_id,body):
        from app.api.schemas.circulatory import CirculatoryHistoryResponse, CirculatoryHistoricalFact
        from app.models.clinical.hemodynamics import CirculatoryFact, M7_FACTS
        from app.persistence.history import FactIdentity
        from app.persistence.bounded_history import HistoryBudget
        context=self.dependencies.state_context.verify(body.state_context)
        self.require_scope(context.assembly_request.scope.target,patient_id,encounter_id)
        if body.reference.kind not in M7_FACTS:raise RecordNotFound('resource not found')
        with transaction(self.dependencies.engine) as repo:
            history=repo.list_bounded_history(identity=FactIdentity(kind=body.reference.kind,id=body.reference.id),
                target=context.assembly_request.scope.target,cutoff=context.assembly_request.scope.repository_cutoff,
                budget=HistoryBudget(max_rows=512))
        if not any(s.fact.reference.model_dump()==body.reference.model_dump() for s in history.records):
            raise RecordNotFound('resource not found')
        return self.bounded(CirculatoryHistoryResponse(context=context,reference=body.reference,
            revisions=tuple(CirculatoryHistoricalFact(fact=s.fact,ingestion=s.ingestion) for s in history.records)))
