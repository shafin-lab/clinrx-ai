"""Bounded original respiratory evidence; calculations never rewrite source values."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, model_validator
from .common import DomainModel, Reference, Text
from .laboratory import LaboratoryResult, LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time

RespiratoryCategory = Literal['bedside','support','blood_gas','mechanics','imaging','procedure','treatment','liberation','lung_function','sleep','extracorporeal','assessment']


class RespiratoryTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    collected: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class RespiratoryContext(DomainModel):
    sample_type: Literal['arterial','peripheral_venous','central_venous','mixed_venous','capillary','noninvasive','unknown'] = 'unknown'
    specimen_id: RawText | None = None
    collection_site: RawText | None = None
    oxygen_device: RawText | None = None
    ventilator_mode: RawText | None = None
    airway_id: RawText | None = None
    position: RawText | None = None
    population: Literal['adult','child','neonate','unknown'] = 'unknown'
    settings_confirmed_at_sample: StrictBool | None = None
    passive: StrictBool | None = None
    occlusion_confirmed: StrictBool | None = None
    reference_equation: RawText | None = None


class RespiratoryMeasurement(DomainModel):
    concept: Text
    label: RawText
    result: LaboratoryResult
    role: Literal['measured','set','reported','calculated_by_source','unknown'] = 'unknown'
    quality: Literal['usable','suspect','unknown'] = 'unknown'
    method: RawText | None = None


class RespiratoryRecord(RecordedFactV2):
    kind: Literal['respiratory_record'] = 'respiratory_record'
    category: RespiratoryCategory
    source_identity: LaboratorySourceIdentity
    title: RawText
    times: RespiratoryTimes
    context: RespiratoryContext
    measurements: Annotated[tuple[RespiratoryMeasurement, ...], Field(max_length=128)] = ()
    narrative: Annotated[str, Field(max_length=65536)] | None = None
    report_status: Literal['pending','preliminary','interim','final','corrected','withdrawn','cancelled','unknown']
    change_state: Literal['original','amended','corrected','superseded'] = 'original'
    record_status: Literal['recorded','withdrawn','invalid','unknown'] = 'recorded'
    linked_sources: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()

    @property
    def semantic_time(self):
        for point in (self.times.available, self.times.reported, self.times.collected, self.times.occurred):
            if point.anchor is not None:return point
        return self.times.available

    @model_validator(mode='after')
    def respiratory_integrity(self):
        if self.revision != self.source_identity.source_version:
            raise ValueError('record revision must preserve exact source version')
        concepts=[item.concept for item in self.measurements]
        if len(set(concepts)) != len(concepts):raise ValueError('measurement concepts must be unique')
        if len(set(self.linked_sources)) != len(self.linked_sources) or self.reference in self.linked_sources:
            raise ValueError('linked sources must be unique exact external references')
        if self.report_status=='withdrawn' and self.record_status!='withdrawn':
            raise ValueError('withdrawn report requires withdrawn record status')
        if self.change_state=='corrected' and self.report_status!='corrected':
            raise ValueError('corrected revision requires corrected source status')
        if self.change_state!='original' and self.supersedes is None:
            raise ValueError('changed source revision requires explicit predecessor')
        return self


class RespiratoryImport(DomainModel):
    repository: UUID
    record: RespiratoryRecord
