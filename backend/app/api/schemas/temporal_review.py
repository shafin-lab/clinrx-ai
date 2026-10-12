"""Future product transport only; no inference or decision producers."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, model_validator
from app.api.schemas.common import DTO, AwareTimestamp, CutoffView, Digest, Envelope, ExactReference, Text
from app.api.schemas.patient_state import LaboratoryView, MedicationView


class SelectionPin(DTO):
    reference: ExactReference
    expected_digest: Digest


class TemporalReviewPreparationRequest(DTO):
    execution_id: UUID
    state_context: Envelope = Field(repr=False)
    earlier_laboratory: SelectionPin
    later_laboratory: SelectionPin
    medication: SelectionPin


class PreparedTemporalReviewResponse(DTO):
    status: Literal['prepared'] = 'prepared'
    execution_id: UUID
    inference_reference: ExactReference
    command: Envelope = Field(repr=False)


class TemporalReviewRequest(DTO):
    command: Envelope = Field(repr=False)


class ReconciliationRequest(DTO):
    command: Envelope = Field(repr=False)


class InferenceView(DTO):
    reference: ExactReference
    method: ExactReference
    statement: Text | None = None
    applicability: Text
    uncertainty: tuple[Text, ...]
    limitations: tuple[Text, ...]
    inputs: tuple[ExactReference, ExactReference, ExactReference]


class DirectDependencyView(DTO):
    target: ExactReference
    relationship: Literal['derived_from'] = 'derived_from'


class ProvenanceView(DTO):
    inference: InferenceView
    earlier_laboratory: LaboratoryView
    later_laboratory: LaboratoryView
    medication: MedicationView
    terminal_references: tuple[ExactReference, ExactReference, ExactReference]
    inference_terminal_reference: ExactReference
    direct_dependencies: tuple[DirectDependencyView, DirectDependencyView, DirectDependencyView]
    input_cutoff: CutoffView
    inference_cutoff: CutoffView
    final_cutoff: CutoffView
    final_recheck: Literal['unchanged', 'materially_changed', 'unavailable']
    recheck_reasons: tuple[Text, ...]


class GovernanceView(DTO):
    outcome: Literal['released', 'withheld']
    decision_reference: ExactReference
    decided_at: AwareTimestamp
    assessed_at: AwareTimestamp | None = None
    reasons: tuple[Text, ...]
    safety_status: Text
    fidelity_status: Text
    freshness_status: Text
    authority_status: Text
    limitations: tuple[Text, ...]


class ContextView(DTO):
    reference: ExactReference
    completeness: Literal['partial'] = 'partial'
    evidence_references: tuple[ExactReference, ExactReference, ExactReference, ExactReference]
    limitations: tuple[Text, ...]


class TemporalExecutionResponse(DTO):
    transport_version: Literal['1'] = '1'
    execution_id: UUID
    status: Literal['completed'] = 'completed'
    finalized_at: AwareTimestamp
    ingested_at: AwareTimestamp
    context: ContextView
    governance: GovernanceView
    provenance: ProvenanceView


class ReconciliationResponse(DTO):
    status: Literal['committed_match', 'absent']
    execution: TemporalExecutionResponse | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.status == 'committed_match') != (self.execution is not None):
            raise ValueError('reconciliation status differs from execution presence')
        return self


class CompletionUnknownResponse(DTO):
    status: Literal['completion_unknown'] = 'completion_unknown'
    execution_id: UUID
    next_action: Literal['reconcile'] = 'reconcile'
    automatic_retry: Literal[False] = False
    correlation_id: UUID
