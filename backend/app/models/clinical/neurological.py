"""Original recorded neurological examinations, imaging and medication status."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .common import DomainModel, Reference
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time


class NeurologicalTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class RecordedNeurologicalExam(DomainModel):
    eye: Annotated[int, Field(strict=True, ge=1, le=4)] | Literal['untestable'] | None = None
    verbal: Annotated[int, Field(strict=True, ge=1, le=5)] | Literal['untestable'] | None = None
    motor: Annotated[int, Field(strict=True, ge=1, le=6)] | Literal['untestable'] | None = None
    verbal_reason: RawText | None = None
    rass: Annotated[int, Field(strict=True, ge=-5, le=4)] | None = None
    pupils: RawText | None = None


class RecordedNeurologicalMedication(DomainModel):
    name: RawText
    status: Literal['running', 'paused', 'held', 'stopped', 'resumed', 'unknown']

    @model_validator(mode='after')
    def medication_is_named(self):
        if not self.name.strip():
            raise ValueError('record the source medication name')
        return self


class NeurologicalRecord(RecordedFactV2):
    kind: Literal['neurological_record'] = 'neurological_record'
    category: Literal['exam', 'imaging', 'medication_status']
    title: RawText
    narrative: Annotated[str, Field(min_length=1, max_length=16384)]
    source_identity: LaboratorySourceIdentity
    times: NeurologicalTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'
    change_state: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    linked_sources: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()
    exam: RecordedNeurologicalExam | None = None
    medication: RecordedNeurologicalMedication | None = None

    @property
    def semantic_time(self):
        for point in (self.times.available, self.times.reported, self.times.occurred):
            if point.anchor is not None:
                return point
        return self.times.available

    @model_validator(mode='after')
    def source_integrity(self):
        if not self.title.strip() or not self.narrative.strip():
            raise ValueError('record the source title and finding or report content')
        if (self.category == 'exam') != (self.exam is not None):
            raise ValueError('exam details are required only for an examination record')
        if (self.category == 'medication_status') != (self.medication is not None):
            raise ValueError('medication details are required only for a medication status record')
        if self.revision != self.source_identity.source_version:
            raise ValueError('revision must preserve source version')
        if len(set(self.linked_sources)) != len(self.linked_sources) or self.reference in self.linked_sources:
            raise ValueError('links must be unique external exact references')
        if self.report_status == 'withdrawn' and self.record_status != 'withdrawn':
            raise ValueError('withdrawn report requires withdrawn record')
        if self.change_state == 'corrected' and self.report_status != 'corrected':
            raise ValueError('corrected revision requires corrected report status')
        if self.change_state != 'original' and self.supersedes is None:
            raise ValueError('a changed source requires its exact predecessor')
        return self


class NeurologicalImport(DomainModel):
    repository: UUID
    record: NeurologicalRecord
