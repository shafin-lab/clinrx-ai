"""Original nutrition and insulin non-delivery observations for the shared timeline."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .common import DomainModel, Reference
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time


class EndocrineTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class RecordedNutrition(DomainModel):
    status: Literal['running', 'paused', 'resumed', 'stopped', 'unknown']
    route: RawText | None = None


class RecordedInsulinNonDelivery(DomainModel):
    name: RawText
    status: Literal['held', 'missed', 'not_given']
    reason: RawText | None = None

    @model_validator(mode='after')
    def require_name(self):
        if not self.name.strip():
            raise ValueError('record the source insulin name')
        return self


class EndocrineRecord(RecordedFactV2):
    kind: Literal['endocrine_record'] = 'endocrine_record'
    category: Literal['nutrition', 'insulin_non_delivery']
    title: RawText
    narrative: Annotated[str, Field(min_length=1, max_length=16384)]
    source_identity: LaboratorySourceIdentity
    times: EndocrineTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'
    change_state: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    linked_sources: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()
    nutrition: RecordedNutrition | None = None
    insulin: RecordedInsulinNonDelivery | None = None

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
        if (self.category == 'nutrition') != (self.nutrition is not None):
            raise ValueError('nutrition details are required only for a nutrition record')
        if (self.category == 'insulin_non_delivery') != (self.insulin is not None):
            raise ValueError('insulin details are required only for a non-delivery record')
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


class EndocrineImport(DomainModel):
    repository: UUID
    record: EndocrineRecord
