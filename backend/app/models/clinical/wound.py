"""Original wound assessments and care events for the shared patient timeline."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from .common import DomainModel, Reference
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time


WoundDimension = Annotated[str, StringConstraints(max_length=64, pattern=r'^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$')]


class WoundTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class WoundRecord(RecordedFactV2):
    kind: Literal['wound_record'] = 'wound_record'
    category: Literal['assessment', 'dressing', 'pressure_care']
    title: RawText
    narrative: Annotated[str, Field(min_length=1, max_length=16384)]
    source_identity: LaboratorySourceIdentity
    times: WoundTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'
    change_state: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    linked_sources: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()
    wound_id: RawText | None = None
    site: RawText | None = None
    stage: RawText | None = None
    length_cm: WoundDimension | None = None
    width_cm: WoundDimension | None = None
    dressing: RawText | None = None
    action: RawText | None = None

    @property
    def semantic_time(self):
        for point in (self.times.available, self.times.reported, self.times.occurred):
            if point.anchor is not None:
                return point
        return self.times.available

    @model_validator(mode='after')
    def source_integrity(self):
        if not self.title.strip() or not self.narrative.strip():
            raise ValueError('record the original title and source narrative')
        if self.wound_id is not None and not self.wound_id.strip():
            raise ValueError('wound identifier must not be blank')
        if self.category != 'pressure_care' and self.wound_id is None:
            raise ValueError('a wound assessment or dressing record requires a wound identifier')
        if self.revision != self.source_identity.source_version:
            raise ValueError('revision must preserve the exact source version')
        if len(set(self.linked_sources)) != len(self.linked_sources) or self.reference in self.linked_sources:
            raise ValueError('links must be unique external exact references')
        if self.report_status == 'withdrawn' and self.record_status != 'withdrawn':
            raise ValueError('withdrawn report requires withdrawn record')
        if self.change_state == 'corrected' and self.report_status != 'corrected':
            raise ValueError('corrected revision requires corrected report status')
        if self.change_state != 'original' and self.supersedes is None:
            raise ValueError('a changed source requires its exact predecessor')
        return self


class WoundImport(DomainModel):
    repository: UUID
    record: WoundRecord
