"""Transport primitives preserve source representations; no clinical policy."""
from datetime import datetime, timezone
import re
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, StrictStr, model_validator

MAX_ENVELOPE_BYTES = 65536
Text = Annotated[StrictStr, Field(min_length=1, max_length=4096)]
Identifier = Annotated[StrictStr, Field(min_length=1, max_length=256)]
Digest = Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
Envelope = Annotated[StrictStr, Field(min_length=1, max_length=MAX_ENVELOPE_BYTES, pattern=r'^[A-Za-z0-9_.=-]+$')]
DecimalString = Annotated[StrictStr, Field(max_length=128, pattern=r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$')]


def _timestamp(value):
    if isinstance(value, str) and re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is None:
        raise ValueError("explicit aware ISO timestamp with at most microsecond precision required")
    if not isinstance(value, (str, datetime)):
        raise ValueError("aware timestamp representation required")
    return value


AwareTimestamp = Annotated[AwareDatetime, BeforeValidator(_timestamp)]


class DTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', revalidate_instances='always')

    @model_validator(mode="after")
    def representable(self):
        from app.persistence.mapping import canonical_payload
        canonical_payload(self)
        return self


class ExactReference(DTO):
    kind: Identifier
    id: Identifier
    version: Identifier


class CutoffView(DTO):
    repository_id: UUID
    fact_watermark: Annotated[int, Field(strict=True, ge=0)]
    captured_at: AwareTimestamp


class ScopeView(DTO):
    patient_id: Identifier
    encounter_id: Identifier
    review_start: AwareTimestamp
    review_end: AwareTimestamp
    repository_cutoff: CutoffView

    @model_validator(mode='after')
    def ordered(self):
        if self.review_start.astimezone(timezone.utc) > self.review_end.astimezone(timezone.utc):
            raise ValueError('reversed review window')
        return self


class SourceView(DTO):
    namespace: Identifier
    identifier: Identifier
    version: Identifier | None = None
    channel: Identifier


class TimesView(DTO):
    event: AwareTimestamp | None = None
    effective_start: AwareTimestamp | None = None
    effective_end: AwareTimestamp | None = None
    recorded: AwareTimestamp | None = None
    retrieved: AwareTimestamp | None = None
    processed: AwareTimestamp | None = None
    precision: Identifier
    uncertainty: Text | None = None


class QuantityView(DTO):
    value: DecimalString
    unit_raw: Text
    unit_code: Text | None = None
    unit_system: Text | None = None
    unit_status: Identifier
