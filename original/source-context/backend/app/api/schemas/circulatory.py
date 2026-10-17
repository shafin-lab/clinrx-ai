"""M7-only typed transport, complete retained receipt, no clinical projection loss."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator
from app.api.schemas.common import DTO, Envelope, Digest, AwareTimestamp, ExactReference
from app.api.schemas.temporal_review import SelectionPin
from app.execution.patient_state_v3_assembly import AssemblyRequestV3, PatientStateAssemblyResultV3
from app.execution.patient_state_v3_execution import CirculatoryExecutionRecord
from app.models.clinical.hemodynamics import CirculatoryRecord
from app.models.clinical.facts import ClinicalInference
from app.persistence.metadata import IngestionMetadata

class CirculatoryStateContext(DTO):
    transport_version: Literal['m7-c/1'] = 'm7-c/1'
    assembly_request: AssemblyRequestV3
    assembly_digest: Digest

class CirculatoryStateResponse(CirculatoryStateContext):
    assembly: PatientStateAssemblyResultV3
    state_context: Envelope = Field(repr=False)
    execution_enabled: bool = Field(strict=True)

class CirculatoryPreparationRequest(DTO):
    execution_id: UUID
    state_context: Envelope = Field(repr=False)
    pressure: SelectionPin
    lactate: SelectionPin
    vasopressor: SelectionPin
    supporting: Annotated[tuple[SelectionPin,...],Field(max_length=32)] = ()

class CirculatoryPreparedResponse(DTO):
    transport_version: Literal['m7-c/1'] = 'm7-c/1'
    status: Literal['prepared'] = 'prepared'
    execution_id: UUID
    inference: ClinicalInference
    command: Envelope = Field(repr=False)

class CirculatoryExecutionResponse(DTO):
    transport_version: Literal['m7-c/1'] = 'm7-c/1'
    execution_id: UUID
    record: CirculatoryExecutionRecord
    ingested_at: AwareTimestamp
    statement: str | None

    @model_validator(mode='after')
    def coherent(self):
        content=self.record.decision.released_content
        if self.execution_id!=self.record.request.execution_id or self.statement!=(content.content if content else None):
            raise ValueError('receipt projection mismatch')
        return self

class CirculatoryReconciliationResponse(DTO):
    status: Literal['committed_match','absent']
    execution: CirculatoryExecutionResponse | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.status=='committed_match')!=(self.execution is not None):raise ValueError('inconsistent reconciliation')
        return self

class CirculatoryHistoryRequest(DTO):
    state_context: Envelope = Field(repr=False)
    reference: ExactReference

class CirculatoryHistoricalFact(DTO):
    fact: CirculatoryRecord
    ingestion: IngestionMetadata

class CirculatoryHistoryResponse(DTO):
    transport_version: Literal['m7-c/1'] = 'm7-c/1'
    context: CirculatoryStateContext
    reference: ExactReference
    revisions: Annotated[tuple[CirculatoryHistoricalFact,...],Field(max_length=512)]
