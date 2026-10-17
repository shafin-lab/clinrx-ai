"""Additive HTTP application composition; M6.3/M6.4 own clinical semantics."""
from uuid import uuid4
from app.services.patient_state_product_service import PatientStateProductService
from app.api.schemas.micro_antimicrobial import (MicroStateContext, MicroStateResponse,
    MicroPreparedResponse, MicroReconciliationResponse)
from app.api.micro_projections import execution
from app.execution.patient_state_v2 import PatientStateScopeV2
from app.execution.patient_state_v2_assembly import AssemblyRequestV2, assemble_patient_state_v2
from app.execution.patient_state_v2_inference import (MicroAntimicrobialTimingRequest,
    MicroAntimicrobialInferenceError, build_micro_antimicrobial_timing_inference)
from app.execution.patient_state_v2_execution import MicroAntimicrobialExecutionRequest, digest
from app.execution.patient_state_v2_workflow import execute_micro_antimicrobial_review, reconcile_micro_antimicrobial_execution
from app.persistence.micro_antimicrobial_executions import find_micro_antimicrobial_execution
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from app.persistence.errors import RecordNotFound, StorageIntegrityError, UnsupportedOperation

class MicroAntimicrobialProductService(PatientStateProductService):
    # Reuse scope, bounded-response, window and command verification infrastructure.
    def state(self,patient_id,encounter_id,start,end):
        target=self.scope(patient_id,encounter_id)
        self.window(start,end)
        with transaction(self.dependencies.engine) as repo:
            repo.load_patient(patient_id)
            repo.load_encounter(patient_id=patient_id,encounter_id=encounter_id)
            cutoff=repo.capture_cutoff()
        scope=PatientStateScopeV2(patient_id=target.patient_id,encounter_id=target.encounter_id,
            review_start=start,review_end=end,repository_cutoff=cutoff)
        ar=AssemblyRequestV2(scope=scope,profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2')
        assembly=assemble_patient_state_v2(self.dependencies.engine,request=ar)
        context=self.dependencies.state_context.issue(MicroStateContext(assembly_request=ar,assembly_digest=assembly.canonical_digest))
        return self.bounded(MicroStateResponse(assembly=assembly,state_context=context))

    def prepare(self,patient_id,encounter_id,body):
        d=self.dependencies
        context=d.state_context.verify(body.state_context)
        scope=context.assembly_request.scope
        self.require_scope(scope.target,patient_id,encounter_id)
        self.window(scope.review_start,scope.review_end)
        assembly=assemble_patient_state_v2(d.engine,request=context.assembly_request)
        if assembly.canonical_digest!=context.assembly_digest:
            raise StorageIntegrityError('historical assembly differs from signed state')
        pins={field:{**getattr(body,field).model_dump(),'role':role} for field,role in
            (('specimen_ref','S'),('isolate_ref','I'),('susceptibility_ref','U'),('administration_ref','D'))}
        ir=MicroAntimicrobialTimingRequest(scope=scope,expected_assembly_digest=context.assembly_digest,
            inference_id=str(uuid4()),executed_at=d.clock(),**pins)
        try: inference=build_micro_antimicrobial_timing_inference(assembly=assembly,request=ir)
        except MicroAntimicrobialInferenceError as error:
            if error.code in ('invalid_assembly','assembly_digest_mismatch','scope_mismatch'):
                raise StorageIntegrityError('historical assembly integrity failure') from None
            raise UnsupportedOperation('selected evidence is unsuitable') from None
        target=type(d.identity.target).model_validate({**d.identity.target.model_dump(),'context':scope.target})
        with execution_transaction(d.engine) as tx:
            tx.repository.append_fact(inference,target=scope.target)
            cutoff=tx.repository.capture_cutoff()
            command=MicroAntimicrobialExecutionRequest(execution_id=body.execution_id,target=target,actor=d.identity.actor,
                inference_request=ir,assembly_request=context.assembly_request,inference_cutoff=cutoff,
                expected_inference_digest=digest(inference),requested_at=d.clock())
            response=self.bounded(MicroPreparedResponse(execution_id=command.execution_id,inference=inference,
                command=d.execution_command.issue(command)))
        return response

    def execute(self,request):
        return self.bounded(execution(execute_micro_antimicrobial_review(self.dependencies.engine,request,clock=self.dependencies.clock)))

    def find(self,patient_id,encounter_id,execution_id):
        stored=find_micro_antimicrobial_execution(self.dependencies.engine,execution_id,target=self.scope(patient_id,encounter_id))
        if stored is None: raise RecordNotFound('resource not found')
        return self.bounded(execution(stored))

    def reconcile(self,request):
        result=reconcile_micro_antimicrobial_execution(self.dependencies.engine,request)
        return self.bounded(MicroReconciliationResponse(status=result.status,execution=execution(result.stored) if result.stored else None))
