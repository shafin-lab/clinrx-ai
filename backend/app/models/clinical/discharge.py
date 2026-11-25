"""Source-recorded discharge and transfer plans, decisions and handovers."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .common import Reference
from .endocrine import EndocrineTimes
from .laboratory import LaboratorySourceIdentity, RawText
from .recorded_v2 import RecordedFactV2


class DischargeRecord(RecordedFactV2):
    kind: Literal['discharge_record'] = 'discharge_record'
    transition_id: RawText
    transition: Literal['icu_to_ward', 'home_discharge']
    category: Literal['course', 'reconciliation', 'care', 'pending', 'handover']
    destination: RawText
    state: Literal['planned', 'pending', 'accepted', 'confirmed', 'completed', 'cancelled', 'unknown']
    owner: RawText | None = None
    due: RawText | None = None
    medication_reference: Reference | None = None
    medication_decision: Literal['continue', 'stop', 'completed', 'review_required'] | None = None
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
        if any(not text.strip() for text in (self.transition_id, self.destination, self.title, self.narrative)):
            raise ValueError('record the original title and source narrative')
        if self.revision != self.source_identity.source_version:
            raise ValueError('revision must preserve the exact source version')
        if self.report_status == 'withdrawn' and self.record_status != 'withdrawn':
            raise ValueError('withdrawn report requires withdrawn record')
        if self.report_status == 'corrected' and self.supersedes is None:
            raise ValueError('corrected reports require an exact predecessor')
        if (self.medication_reference is None) != (self.medication_decision is None):
            raise ValueError('medication decisions require an exact source reference')
        if self.medication_reference is not None:
            if self.category != 'reconciliation' or self.medication_reference.kind not in (
                'medication_order', 'medication_administration', 'antimicrobial_order',
                'antimicrobial_administration', 'antimicrobial_non_delivery',
            ):
                raise ValueError('medication reconciliation must reference an original medication source')
        return self
