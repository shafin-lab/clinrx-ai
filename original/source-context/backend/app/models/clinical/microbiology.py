"""M6.1 independently addressable recorded microbiology assertions. No inference."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .common import Text
from .antimicrobials import AntimicrobialIdentity
from .recorded_v2 import (Contract, NonnegativeQuantity, PositiveQuantity, RawText,
    RecordedConcept, RecordedFactV2, RecordedTime, ReportState, SourceCode, missing_time)


class Specimen(RecordedFactV2):
    kind: Literal['microbiology_specimen'] = 'microbiology_specimen'
    accession: SourceCode
    specimen_type: RecordedConcept
    site: RecordedConcept | None = None
    collected: RecordedTime = Field(default_factory=missing_time)
    received: RecordedTime = Field(default_factory=missing_time)
    collector: RawText | None = None
    recorded_adequacy: RecordedConcept | None = None

    @property
    def semantic_time(self):
        return self.collected

    @model_validator(mode='after')
    def roles(self):
        self.require_roles((), ())
        return self


class ReportedMicrobiology(RecordedFactV2):
    report: ReportState

    @property
    def semantic_time(self):
        return self.report.available if self.report.available.anchor is not None else self.report.reported

    @model_validator(mode='after')
    def revision_report(self):
        if type(self) is ReportedMicrobiology:
            raise ValueError('construct a concrete microbiology result')
        if self.report.change in ('amended', 'corrected') and self.supersedes is None:
            raise ValueError('amendment/correction requires exact predecessor and reason')
        if self.supersedes is not None and self.report.change == 'original':
            raise ValueError('successor requires non-original change disposition')
        return self


class ExaminationFinding(Contract):
    category: Literal['gram_reaction', 'morphology', 'cellular', 'organism_seen', 'other']
    finding: RecordedConcept
    presence: Literal['present', 'absent', 'indeterminate', 'not_reported']
    semiquantitation: RecordedConcept | None = None


class DirectExamination(ReportedMicrobiology):
    kind: Literal['microbiology_direct_examination'] = 'microbiology_direct_examination'
    examination_type: Literal['gram_stain', 'microscopy', 'other']
    other_type: RecordedConcept | None = None
    findings: Annotated[tuple[ExaminationFinding, ...], Field(min_length=1, max_length=32)]
    method: RecordedConcept | None = None
    examined: RecordedTime = Field(default_factory=missing_time)
    source_note: RawText | None = None

    @model_validator(mode='after')
    def roles(self):
        self.require_roles(('specimen',), ('specimen',))
        if (self.examination_type == 'other') != (self.other_type is not None):
            raise ValueError('other examination requires explicit type')
        return self


class CultureFinding(ReportedMicrobiology):
    kind: Literal['microbiology_culture'] = 'microbiology_culture'
    growth: Literal['growth', 'no_growth', 'indeterminate']
    quantity: NonnegativeQuantity | None = None
    semiquantitation: RecordedConcept | None = None
    recorded_interpretation: RecordedConcept | None = None

    @model_validator(mode='after')
    def roles(self):
        self.require_roles(('specimen',), ('specimen', 'bottle'))
        if self.growth == 'no_growth' and (self.quantity is not None or self.semiquantitation is not None):
            raise ValueError('no-growth assertion cannot carry a growth magnitude')
        return self


class IsolateIdentification(ReportedMicrobiology):
    kind: Literal['microbiology_isolate'] = 'microbiology_isolate'
    isolate_identifier: SourceCode
    organism: RecordedConcept
    identification_state: Literal['provisional', 'final', 'unresolved']
    method: RecordedConcept | None = None
    identified: RecordedTime = Field(default_factory=missing_time)
    quantity: NonnegativeQuantity | None = None
    semiquantitation: RecordedConcept | None = None

    @model_validator(mode='after')
    def roles(self):
        self.require_roles(('specimen',), ('specimen', 'bottle'))
        return self


class MinimumInhibitoryConcentration(Contract):
    comparator: Literal['<', '<=', '=', '>=', '>']
    quantity: NonnegativeQuantity


class SusceptibilityInterpretation(Contract):
    raw: RawText
    coding: SourceCode | None = None
    category: Literal['susceptible', 'intermediate', 'resistant', 'other', 'unknown']
    meaning_limitation: Text | None = None

    @model_validator(mode='after')
    def interpretation_context(self):
        if self.coding is None and self.meaning_limitation is None:
            raise ValueError('uncoded interpretation requires limitation')
        return self


class BreakpointContext(Contract):
    authority: Text
    version: Text | None = None
    source_reference: RawText | None = None


class SusceptibilityResult(ReportedMicrobiology):
    kind: Literal['microbiology_susceptibility'] = 'microbiology_susceptibility'
    test_identifier: SourceCode
    antimicrobial: AntimicrobialIdentity
    mic: MinimumInhibitoryConcentration | None = None
    zone_diameter: NonnegativeQuantity | None = None
    interpretation: SusceptibilityInterpretation | None = None
    result_status: Literal['reported', 'indeterminate', 'not_performed']
    method: RecordedConcept | None = None
    breakpoint: BreakpointContext | None = None

    @model_validator(mode='after')
    def result_shape(self):
        self.require_roles(('isolate',), ('isolate',))
        values = (self.mic, self.zone_diameter, self.interpretation)
        if self.result_status == 'reported' and all(v is None for v in values):
            raise ValueError('reported susceptibility requires a recorded result')
        if self.result_status == 'not_performed' and any(v is not None for v in values):
            raise ValueError('not-performed test cannot carry results')
        return self


class ResistanceFinding(ReportedMicrobiology):
    kind: Literal['microbiology_resistance'] = 'microbiology_resistance'
    category: Literal['phenotype', 'genotype', 'mechanism', 'esbl', 'carbapenemase', 'inducible_resistance', 'resistance_gene']
    target: RecordedConcept
    method: RecordedConcept | None = None
    result: Literal['positive', 'negative', 'indeterminate', 'not_performed']

    @model_validator(mode='after')
    def roles(self):
        self.require_roles((), ('specimen', 'isolate'))
        if len(self.domain_bindings) != 1:
            raise ValueError('resistance requires one explicit specimen or isolate binding')
        return self


class MolecularResult(ReportedMicrobiology):
    """One target assertion per stable fact; panel membership is source identity only."""
    kind: Literal['microbiology_molecular'] = 'microbiology_molecular'
    test_identifier: SourceCode
    panel_identifier: SourceCode | None = None
    target: RecordedConcept
    result: Literal['positive', 'negative', 'indeterminate', 'not_performed']
    method: RecordedConcept | None = None

    @model_validator(mode='after')
    def roles(self):
        self.require_roles(('specimen',), ('specimen',))
        return self


class BloodCultureSet(RecordedFactV2):
    kind: Literal['blood_culture_set'] = 'blood_culture_set'
    set_identifier: SourceCode
    collected: RecordedTime = Field(default_factory=missing_time)

    @property
    def semantic_time(self):
        return self.collected

    @model_validator(mode='after')
    def roles(self):
        self.require_roles((), ())
        return self


class BloodCultureBottle(RecordedFactV2):
    kind: Literal['blood_culture_bottle'] = 'blood_culture_bottle'
    bottle_identifier: SourceCode
    bottle_type: RecordedConcept
    bottle_role: Literal['aerobic', 'anaerobic', 'pediatric', 'other', 'unknown']
    positive_at: RecordedTime = Field(default_factory=missing_time)
    reported_time_to_positivity: PositiveQuantity | None = None

    @property
    def semantic_time(self):
        return self.positive_at

    @model_validator(mode='after')
    def roles(self):
        self.require_roles(('collection_set', 'specimen'), ('collection_set', 'specimen'))
        return self
