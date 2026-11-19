"""Source-recorded infection prevention precautions."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .endocrine import EndocrineTimes
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2


class PrecautionRecord(RecordedFactV2):
    kind: Literal['precaution_record'] = 'precaution_record'
    status: Literal['in_place', 'discontinued']
    precaution: RawText
    title: RawText
    narrative: Annotated[str, Field(min_length=1, max_length=16384)]
    source_identity: LaboratorySourceIdentity
    times: EndocrineTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'

    @property
    def semantic_time(self):
        for point in (self.times.available, self.times.reported, self.times.occurred):
            if point.anchor is not None:
                return point
        return self.times.available

    @model_validator(mode='after')
    def source_integrity(self):
        if not self.precaution.strip() or not self.title.strip() or not self.narrative.strip():
            raise ValueError('record the original title and source narrative')
        if self.revision != self.source_identity.source_version:
            raise ValueError('revision must preserve the exact source version')
        if self.report_status == 'withdrawn' and self.record_status != 'withdrawn':
            raise ValueError('withdrawn report requires withdrawn record')
        if self.report_status == 'corrected' and self.supersedes is None:
            raise ValueError('corrected reports require an exact predecessor')
        return self
