"""RF1 local read transport. Original legacy observations, never invented M7 facts."""
from hashlib import sha256
from typing import Annotated, Literal
from pydantic import Field, model_validator
from app.api.schemas.common import DTO, Digest, Envelope, ExactReference
from app.api.schemas.circulatory import CirculatoryStateResponse
from app.execution.patient_state_v3 import PatientStateScopeV3
from app.models.clinical.facts import ClinicalObservation
from app.persistence.canonical import canonical_payload
from app.persistence.metadata import IngestionMetadata

CONCEPT = 'synthetic-serum-creatinine'

def digest(model):
    return sha256(canonical_payload(model).encode()).hexdigest()

class RenalObservation(DTO):
    fact: ClinicalObservation
    expected_digest: Digest
    canonical_fact: str
    ingestion: IngestionMetadata
    inclusion: Literal['in_window', 'outside_window', 'unplaced']

    @model_validator(mode='after')
    def coherent(self):
        if self.fact.concept_id != CONCEPT or self.canonical_fact != canonical_payload(self.fact) or self.expected_digest != digest(self.fact):
            raise ValueError('observation correspondence failure')
        return self

class RenalFluidContext(DTO):
    transport_version: Literal['SyntheticRenalFluidReview/v1'] = 'SyntheticRenalFluidReview/v1'
    scope: PatientStateScopeV3
    circulatory_digest: Digest
    observations_digest: Digest

class RenalObservations(DTO):
    scope: PatientStateScopeV3
    observations: Annotated[tuple[RenalObservation, ...], Field(max_length=128)]

    @model_validator(mode='after')
    def coherent(self):
        seen = set()
        for item in self.observations:
            identity = (item.fact.kind, item.fact.id)
            if identity in seen:
                raise ValueError('duplicate observation family')
            seen.add(identity)
            if item.fact.binding.target != self.scope.target or item.ingestion.repository_id != self.scope.repository_cutoff.repository_id or item.ingestion.ingestion_sequence > self.scope.repository_cutoff.fact_watermark:
                raise ValueError('observation scope or cutoff mismatch')
        return self

class RenalFluidResponse(DTO):
    context: RenalFluidContext
    state_context: Envelope = Field(repr=False)
    circulatory: CirculatoryStateResponse
    laboratory: RenalObservations
    canonical_assembly: str
    canonical_laboratory: str
    execution_enabled: Literal[False] = False

    @model_validator(mode='after')
    def coherent(self):
        if self.circulatory.execution_enabled or self.context.scope != self.circulatory.assembly.request.scope or self.context.scope != self.laboratory.scope:
            raise ValueError('combined scope or gate mismatch')
        if self.context.circulatory_digest != self.circulatory.assembly.canonical_digest or self.context.observations_digest != digest(self.laboratory):
            raise ValueError('combined digest mismatch')
        if self.circulatory.assembly_digest != self.context.circulatory_digest or self.canonical_assembly != canonical_payload(self.circulatory.assembly) or self.canonical_laboratory != canonical_payload(self.laboratory):
            raise ValueError('combined content mismatch')
        return self

class RenalHistoryRequest(DTO):
    state_context: Envelope = Field(repr=False)
    reference: ExactReference

class RenalHistoryResponse(DTO):
    context: RenalFluidContext
    reference: ExactReference
    revisions: Annotated[tuple[RenalObservation, ...], Field(min_length=1, max_length=128)]

    @model_validator(mode='after')
    def coherent(self):
        seen = set()
        last = 0
        for item in self.revisions:
            f, meta, scope = item.fact, item.ingestion, self.context.scope
            if (f.kind, f.id) != (self.reference.kind, self.reference.id) or f.reference in seen or f.binding.target != scope.target or meta.repository_id != scope.repository_cutoff.repository_id or not last < meta.ingestion_sequence <= scope.repository_cutoff.fact_watermark:
                raise ValueError('history correspondence failure')
            seen.add(f.reference)
            last = meta.ingestion_sequence
        if not any(i.fact.reference.model_dump() == self.reference.model_dump() for i in self.revisions):
            raise ValueError('selected revision missing')
        return self
