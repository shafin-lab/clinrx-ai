"""Bounded transport contracts for explicitly authored synthetic M10 records."""
from typing import Annotated
from uuid import UUID
from pydantic import Field, StrictStr, TypeAdapter, model_validator
from app.api.schemas.common import DTO, AwareTimestamp, Digest, ExactReference
from app.models.clinical.transfusion import M10_FACTS, Short, Stamp

class M10Draft(DTO):
    repository: UUID
    command_id: UUID
    id: UUID
    revision: UUID
    kind: Short
    patient_id: Short
    encounter_id: Short
    source_record: Short
    source_issuer: Short
    actor: Short
    recorded_at: Stamp
    available_at: Stamp | None = None
    data: dict
    predecessor: ExactReference | None = None
    predecessor_digest: Digest | None = None
    correction_reason: Short | None = None
    @model_validator(mode='after')
    def coherent(self):
        from app.persistence.canonical import canonical_payload
        TypeAdapter(AwareTimestamp).validate_python(self.recorded_at)
        if self.available_at is not None:TypeAdapter(AwareTimestamp).validate_python(self.available_at)
        if self.kind not in M10_FACTS:raise ValueError('unsupported M10 kind')
        if len(canonical_payload(self).encode())>250000:raise ValueError('M10 command exceeds capacity')
        if not all(x.strip() for x in (self.source_record,self.source_issuer,self.actor)):raise ValueError('nonblank source identity required')
        # Validate data before transaction and reject unknown members instead of dropping them.
        M10_FACTS[self.kind].model_fields['data'].annotation.model_validate(self.data)
        if len({self.predecessor is None,self.predecessor_digest is None,self.correction_reason is None})!=1:raise ValueError('correction needs predecessor, digest and reason')
        if self.predecessor and (self.predecessor.kind!=self.kind or self.predecessor.id!=str(self.id) or self.predecessor.version==str(self.revision)):raise ValueError('correction must retain source owner identity')
        return self

class M10History(DTO):
    repository: UUID
    reference: ExactReference
    cutoff: Annotated[int,Field(strict=True,ge=0)]
    review_end: AwareTimestamp
    offset: Annotated[int,Field(strict=True,ge=0)] = 0
    limit: Annotated[int,Field(strict=True,gt=0,le=128)] = 50

class M10Attachment(DTO):
    repository: UUID
    digest: Digest
    media_type: str
    data_base64: Annotated[StrictStr,Field(max_length=2800000)]

class M10Evaluation(DTO):
    repository: UUID
    patient_id: Short
    encounter_id: Short
    cutoff: Annotated[int,Field(strict=True,ge=0)]
    review_end: AwareTimestamp
    device_profile_id: Short
    protocol_profile_id: Short
    mode: str = 'synthetic_reference'
    context: dict
    observations: Annotated[list[dict],Field(max_length=256)] = []
    laboratory: Annotated[list[dict],Field(max_length=128)] = []
    selected_observation_ids: Annotated[list[Short],Field(max_length=256)] = []
