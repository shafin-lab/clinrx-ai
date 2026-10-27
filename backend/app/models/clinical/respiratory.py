"""Bounded original respiratory evidence; calculations never rewrite source values."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, model_validator, model_serializer
from .common import DomainModel, Reference, Text
from .laboratory import LaboratoryResult, LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2, RecordedTime, missing_time, instant

RespiratoryCategory = Literal['bedside','support','blood_gas','mechanics','imaging','procedure','treatment','liberation','lung_function','sleep','extracorporeal','assessment']


class RespiratoryTimes(DomainModel):
    occurred: RecordedTime = Field(default_factory=missing_time)
    collected: RecordedTime = Field(default_factory=missing_time)
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)


class RespiratorySupportEpisode(DomainModel):
    type: Literal['room_air','nasal_cannula','simple_mask','venturi_mask','reservoir_mask','hfnc','niv','invasive','other','unknown']
    until: RecordedTime | None = None


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
    support_episode: RespiratorySupportEpisode | None = None

    @model_serializer(mode='wrap')
    def preserve_legacy_serialization(self, handler):
        data = handler(self)
        if 'support_episode' not in self.model_fields_set:
            data.pop('support_episode', None)
        return data


class RespiratoryAcquisition(DomainModel):
    breath_channel: Literal['total','spontaneous','mandatory','unknown']
    acquisition_id: Annotated[str, Field(min_length=1, max_length=500)]


class RespiratoryMeasurement(DomainModel):
    concept: Text
    label: RawText
    result: LaboratoryResult
    role: Literal['measured','set','reported','calculated_by_source','unknown'] = 'unknown'
    quality: Literal['usable','suspect','unknown'] = 'unknown'
    method: RawText | None = None
    acquisition: RespiratoryAcquisition | None = None

    @model_serializer(mode='wrap')
    def preserve_legacy_serialization(self, handler):
        data = handler(self)
        if 'acquisition' not in self.model_fields_set:
            data.pop('acquisition', None)
        return data


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
        episode = self.context.support_episode
        if episode is not None:
            start = self.times.occurred
            if self.category != 'support' or start.status != 'known' or start.precision != 'instant' or start.value is None:
                raise ValueError('a support episode requires a support record and exact start time')
            end = episode.until
            if end is not None and (end.status != 'known' or end.precision != 'instant' or end.value is None or instant(end.value) <= instant(start.value)):
                raise ValueError('support episode end must be an exact instant after its start')
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
