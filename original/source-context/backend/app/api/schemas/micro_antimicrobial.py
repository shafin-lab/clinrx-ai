"""Strict capability DTOs; reuse typed recorded facts without numeric coercion."""
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from app.api.schemas.common import DTO, Envelope, Digest, AwareTimestamp, ExactReference
from app.api.schemas.temporal_review import SelectionPin, GovernanceView
from app.execution.patient_state_v2 import RetainedStateItemV2
from app.execution.patient_state_v2_assembly import AssemblyRequestV2, PatientStateAssemblyResultV2
from app.execution.patient_state_v2_execution import MicroAntimicrobialFinalRecheck
from app.models.clinical.facts import ClinicalInference
from app.persistence.metadata import RepositoryCutoff

class MicroStateContext(DTO):
    transport_version: Literal['1'] = '1'
    assembly_request: AssemblyRequestV2
    assembly_digest: Digest

class MicroStateResponse(DTO):
    transport_version: Literal['1'] = '1'
    assembly: PatientStateAssemblyResultV2
    state_context: Envelope = Field(repr=False)

class MicroPreparationRequest(DTO):
    execution_id: UUID
    state_context: Envelope = Field(repr=False)
    specimen_ref: SelectionPin
    isolate_ref: SelectionPin
    susceptibility_ref: SelectionPin
    administration_ref: SelectionPin

class MicroPreparedResponse(DTO):
    status: Literal['prepared'] = 'prepared'
    execution_id: UUID
    inference: ClinicalInference
    command: Envelope = Field(repr=False)

class MicroProvenance(DTO):
    inference: ClinicalInference
    consumed: tuple[RetainedStateItemV2,RetainedStateItemV2,RetainedStateItemV2,RetainedStateItemV2]
    original_cutoff: RepositoryCutoff
    inference_cutoff: RepositoryCutoff
    final_recheck: MicroAntimicrobialFinalRecheck
    specimen_binding_matches: bool
    isolate_binding_matches: bool
    antimicrobial_identity_matches: bool
    governance_policy: ExactReference
    witness_statuses: tuple[Literal['current','superseded'], Literal['current','superseded'], Literal['current','superseded'], Literal['current','superseded']]
    recheck_reasons: tuple[str,...]

class MicroExecutionResponse(DTO):
    transport_version: Literal['1'] = '1'
    execution_id: UUID
    status: Literal['completed'] = 'completed'
    statement: str | None
    finalized_at: AwareTimestamp
    ingested_at: AwareTimestamp
    governance: GovernanceView
    provenance: MicroProvenance

class MicroReconciliationResponse(DTO):
    status: Literal['committed_match','absent']
    execution: MicroExecutionResponse | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.status=='committed_match') != (self.execution is not None):
            raise ValueError('inconsistent reconciliation result')
        return self
