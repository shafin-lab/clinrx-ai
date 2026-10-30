"""Typed, source-preserving laboratory reports for the synthetic shared feed."""
from hashlib import sha256
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from .common import DomainModel, Text
from .recorded_v2 import RecordedFactV2, RecordedTime, SourceCode

RawText = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
DecimalText = Annotated[str, StringConstraints(pattern=r'^[+-]?(?:0|[1-9]\d*)(?:\.\d+)?$')]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]

SUPPORTED_LAB_MAPPINGS = frozenset({
    'hemoglobin', 'hematocrit', 'platelets', 'pt', 'inr', 'aptt', 'thrombin_time',
    'fibrinogen', 'total_calcium', 'ionised_calcium', 'd_dimer', 'anti_xa',
    'creatinine', 'urea', 'bun', 'sodium', 'potassium', 'urine_appearance', 'urine_colour',
    'urine_specific_gravity', 'urine_ph', 'urine_protein', 'urine_glucose',
    'urine_ketones', 'urine_blood', 'urine_leukocyte_esterase', 'urine_nitrite',
    'urine_bilirubin', 'urine_urobilinogen', 'urine_rbc', 'urine_wbc',
    'urine_epithelial_cells', 'urine_casts', 'urine_crystals', 'urine_bacteria',
})


class LaboratorySourceIdentity(DomainModel):
    issuer_namespace: Text
    source_report_id: RawText
    source_version: RawText
    accession_id: RawText | None = None


class LaboratorySpecimen(DomainModel):
    source_specimen_id: RawText | None = None
    specimen_type: SourceCode | None = None
    collection_site: SourceCode | None = None
    collection_context: Text | None = None


class LaboratoryTimes(DomainModel):
    collected: RecordedTime = Field(default_factory=lambda: RecordedTime(status='not_recorded'))
    received: RecordedTime = Field(default_factory=lambda: RecordedTime(status='not_recorded'))
    measured: RecordedTime = Field(default_factory=lambda: RecordedTime(status='not_recorded'))
    reported: RecordedTime = Field(default_factory=lambda: RecordedTime(status='not_recorded'))
    available: RecordedTime = Field(default_factory=lambda: RecordedTime(status='not_recorded'))


class LaboratoryNumericResult(DomainModel):
    kind: Literal['numeric'] = 'numeric'
    raw_value: DecimalText
    comparator: Literal['<', '<=', '=', '>=', '>']
    unit: SourceCode | None = None


class LaboratoryQualitativeResult(DomainModel):
    kind: Literal['qualitative'] = 'qualitative'
    raw_value: RawText
    coding: SourceCode | None = None


class LaboratoryNarrativeResult(DomainModel):
    kind: Literal['narrative'] = 'narrative'
    raw_value: RawText


class LaboratoryUnavailableResult(DomainModel):
    kind: Literal['unavailable'] = 'unavailable'
    status: Literal['pending', 'not_performed', 'unavailable', 'cancelled']
    reason: RawText


LaboratoryResult = Annotated[
    LaboratoryNumericResult | LaboratoryQualitativeResult | LaboratoryNarrativeResult | LaboratoryUnavailableResult,
    Field(discriminator='kind'),
]


class LaboratoryReferenceInterval(DomainModel):
    raw_text: RawText | None = None
    lower: DecimalText | None = None
    lower_inclusive: bool | None = None
    upper: DecimalText | None = None
    upper_inclusive: bool | None = None
    unit: SourceCode | None = None
    applicability: Text | None = None

    @model_validator(mode='after')
    def interval_shape(self):
        if (self.lower is None) != (self.lower_inclusive is None) or (self.upper is None) != (self.upper_inclusive is None):
            raise ValueError('numeric reference boundaries require explicit inclusivity')
        if self.lower is not None and self.upper is not None and Decimal(self.lower) > Decimal(self.upper):
            raise ValueError('reference interval boundaries must be ordered')
        return self


class LaboratoryComponent(DomainModel):
    source_component_id: RawText
    test_code: SourceCode
    mapping_status: Literal['mapped', 'unsupported', 'ambiguous']
    mapped_concept: Text | None = None
    mapping_version: Text | None = None
    assay: SourceCode | None = None
    result: LaboratoryResult
    reference_interval: LaboratoryReferenceInterval | None = None
    source_flags: Annotated[tuple[SourceCode, ...], Field(max_length=16)] = ()
    source_interference_flags: Annotated[tuple[SourceCode, ...], Field(max_length=16)] = ()
    source_critical_flag: Literal['flagged', 'not_flagged', 'unknown'] = 'unknown'

    @field_validator('source_flags', 'source_interference_flags')
    @classmethod
    def unique_flags(cls, values):
        if len(set(values)) != len(values):
            raise ValueError('duplicate source flag')
        return values

    @model_validator(mode='after')
    def mapping_is_explicit(self):
        if self.mapping_status == 'mapped':
            if self.mapped_concept not in SUPPORTED_LAB_MAPPINGS or not self.mapping_version:
                raise ValueError('mapped laboratory result requires an explicitly supported concept and mapping version')
        elif self.mapped_concept is not None or self.mapping_version is not None:
            raise ValueError('unsupported or ambiguous mapping cannot supply a canonical concept')
        return self


class LaboratoryReport(RecordedFactV2):
    """One exact issued report revision; original source identity survives corrections."""
    kind: Literal['laboratory_report'] = 'laboratory_report'
    source_identity: LaboratorySourceIdentity
    source_panel: SourceCode | None = None
    specimen: LaboratorySpecimen
    times: LaboratoryTimes
    report_status: Literal['pending', 'preliminary', 'interim', 'final', 'corrected', 'withdrawn', 'cancelled', 'unknown']
    change_state: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    record_status: Literal['recorded', 'withdrawn', 'invalid', 'unknown'] = 'recorded'
    components: Annotated[tuple[LaboratoryComponent, ...], Field(min_length=1, max_length=128)]
    original_report: Annotated[str, Field(max_length=65536)] | None = None
    original_report_digest: Digest | None = None

    @property
    def semantic_time(self):
        """Prefer source result-availability time, then reported, measured, or collected."""
        for point in (self.times.available, self.times.reported, self.times.measured,
                      self.times.collected):
            if point.anchor is not None:
                return point
        return self.times.available

    @model_validator(mode='after')
    def report_integrity(self):
        if self.source_identity.source_version != self.revision:
            raise ValueError('report revision must preserve its exact source version')
        identities = [component.source_component_id for component in self.components]
        if len(set(identities)) != len(identities):
            raise ValueError('source component identities must be unique within a report')
        if (self.original_report is None) != (self.original_report_digest is None):
            raise ValueError('retained report bytes and digest must be supplied together')
        if self.original_report is not None and sha256(self.original_report.encode('utf-8')).hexdigest() != self.original_report_digest:
            raise ValueError('original report digest differs from retained bytes')
        if self.report_status == 'withdrawn' and self.record_status != 'withdrawn':
            raise ValueError('withdrawn report must retain withdrawn record status')
        if self.change_state == 'corrected' and self.report_status != 'corrected':
            raise ValueError('corrected source revision must retain corrected report status')
        if self.change_state in ('amended', 'corrected', 'superseded') and self.supersedes is None:
            raise ValueError('changed report revision requires an explicit predecessor')
        return self
