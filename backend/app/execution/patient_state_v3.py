"""Explicit M7 admission and bounded recorded state, separate from governance."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, field_validator, model_validator
from app.models.clinical.common import ContextTarget, Reference, Text
from app.models.clinical.recorded_v2 import Contract, Digest, instant, ref_key
from app.models.clinical.hemodynamics import CirculatoryRecord, LactateResult
from app.persistence.metadata import RepositoryCutoff, IngestionMetadata
from app.persistence.canonical import canonical_payload


class PatientStateScopeV3(Contract):
    contract_version: Literal['3'] = '3'
    patient_id: Text
    encounter_id: Text
    review_start: AwareDatetime
    review_end: AwareDatetime
    repository_cutoff: RepositoryCutoff

    @field_validator('repository_cutoff', mode='before')
    @classmethod
    def metadata(cls, value):
        return value.model_dump() if isinstance(value, RepositoryCutoff) else value

    @property
    def target(self):
        return ContextTarget(patient_id=self.patient_id, encounter_id=self.encounter_id)

    @model_validator(mode='after')
    def ordered(self):
        if instant(self.review_start) > instant(self.review_end):
            raise ValueError('reversed review window')
        return self


def clinical_time(fact):
    # The specimen collection axis is never replaced by reporting/availability.
    return fact.collected if isinstance(fact, LactateResult) else fact.occurred


class RetainedStateItemV3(Contract):
    fact: CirculatoryRecord
    expected_digest: Digest
    ingestion: IngestionMetadata
    inclusion: Literal['in_window', 'contextual', 'unplaced']
    contextual_for: Annotated[tuple[Reference, ...], Field(max_length=64)] = ()
    disclosures: Annotated[tuple[Text, ...], Field(min_length=1, max_length=32)]

    @field_validator('ingestion', mode='before')
    @classmethod
    def metadata(cls, value):
        value = value.model_dump() if isinstance(value, IngestionMetadata) else value
        if isinstance(value, dict) and type(value.get('payload_version',1)) is not int:
            raise ValueError('payload version must be an exact integer')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if self.expected_digest != self.fact.canonical_digest:
            raise ValueError('retained digest differs')
        if (self.inclusion == 'contextual') != bool(self.contextual_for):
            raise ValueError('contextual inclusion requires exact children')
        if len(set(self.contextual_for)) != len(self.contextual_for):
            raise ValueError('duplicate contextual identity')
        if self.inclusion == 'in_window' and clinical_time(self.fact).recorded.anchor is None:
            raise ValueError('unplaced evidence cannot assert window placement')
        return self

    @property
    def reference(self):
        return self.fact.reference

    @property
    def ordering_key(self):
        anchor = clinical_time(self.fact).recorded.anchor
        return (anchor is None, instant(anchor) if anchor else 0, *ref_key(self.reference))


class StateIssueV3(Contract):
    reference: Reference
    reason: Literal['outside_profile', 'withdrawn_terminal', 'outside_window',
        'temporal_uncertainty', 'unplaced', 'contextual', 'unresolved_association',
        'historical_association', 'missing_association', 'uncertain_quality']


class CoverageV3(Contract):
    source_completeness: Literal['unknown'] = 'unknown'
    continuity: Literal['not_established'] = 'not_established'
    candidate_rows: Annotated[int, Field(strict=True, ge=0)]
    terminal_count: Annotated[int, Field(strict=True, ge=0)]
    retained_count: Annotated[int, Field(strict=True, ge=0)]
    limitations: tuple[Text, ...] = ('Only declared recorded M7 evidence; absence and continuous physiology are not established.',)


class PatientStateSnapshotV3(Contract):
    contract_version: Literal['3'] = '3'
    scope: PatientStateScopeV3
    profile_id: Literal['RecordedCirculatoryEvidence'] = 'RecordedCirculatoryEvidence'
    profile_version: Literal['1'] = '1'
    items: Annotated[tuple[RetainedStateItemV3, ...], Field(max_length=512)] = ()
    issues: Annotated[tuple[StateIssueV3, ...], Field(max_length=1024)] = ()
    coverage: CoverageV3

    @field_validator('items')
    @classmethod
    def order_items(cls, items):
        return tuple(sorted(items, key=lambda i: i.ordering_key))

    @field_validator('issues')
    @classmethod
    def order_issues(cls, issues):
        return tuple(sorted(set(issues), key=lambda i: (*ref_key(i.reference), i.reason)))

    @model_validator(mode='after')
    def coherent(self):
        refs, stable = set(), set()
        cutoff = self.scope.repository_cutoff
        for item in self.items:
            ref = item.reference
            if ref in refs or (ref.kind, ref.id) in stable:
                raise ValueError('duplicate stable state identity')
            refs.add(ref)
            stable.add((ref.kind, ref.id))
            if item.fact.binding.target != self.scope.target:
                raise ValueError('retained evidence scope mismatch')
            if item.ingestion.repository_id != cutoff.repository_id or item.ingestion.ingestion_sequence > cutoff.fact_watermark:
                raise ValueError('retained evidence outside repository prefix')
            if item.inclusion == 'in_window':
                t = clinical_time(item.fact).recorded
                lo, hi = t.lower or t.value, t.upper or t.value
                if instant(lo) > instant(self.scope.review_end) or instant(hi) < instant(self.scope.review_start):
                    raise ValueError('in-window evidence outside review interval')
        if any(not set(i.contextual_for) <= refs for i in self.items):
            raise ValueError('contextual child missing')
        c = self.coverage
        if not c.candidate_rows >= c.terminal_count >= c.retained_count == len(self.items):
            raise ValueError('state coverage counts inconsistent')
        canonical_payload(self)
        return self
