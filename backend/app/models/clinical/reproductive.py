"""Original recorded obstetrics, gynecology and reproductive-care evidence."""
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .common import DomainModel, Reference
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time


class ReproductiveTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class RecordedPregnancyStatus(DomainModel):
    phase: Literal['antepartum', 'in_labour', 'postpartum', 'not_pregnant', 'pregnancy_loss', 'unknown']
    gestational_weeks: Annotated[int, Field(strict=True, ge=0)] | None = None
    gestational_days: Annotated[int, Field(strict=True, ge=0, le=6)] | None = None
    estimated_due_date: date | None = None
    fetus_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    dating_basis: RawText | None = None


class ReproductiveRecord(RecordedFactV2):
    kind: Literal['reproductive_record'] = 'reproductive_record'
    category: Literal[
        'pregnancy_status', 'maternal_assessment', 'fetal_assessment', 'labour_delivery',
        'postpartum', 'gynecology', 'reproductive_care', 'imaging', 'procedure',
    ]
    title: RawText
    narrative: Annotated[str, Field(min_length=1, max_length=16384)]
    source_identity: LaboratorySourceIdentity
    times: ReproductiveTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'
    change_state: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    linked_sources: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()
    pregnancy: RecordedPregnancyStatus | None = None

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
        if (self.category == 'pregnancy_status') != (self.pregnancy is not None):
            raise ValueError('a pregnancy status record requires an explicit pregnancy phase')
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


class ReproductiveImport(DomainModel):
    repository: UUID
    record: ReproductiveRecord
