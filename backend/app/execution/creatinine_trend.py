"""Synthetic serum-creatinine selection/comparison only; no clinical interpretation."""
from collections import Counter
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from app.models.clinical.common import ContextTarget, DomainModel, Quantity, Reference
from app.models.clinical.facts import ClinicalObservation
from app.persistence.metadata import RepositoryCutoff
from app.persistence.repository import PatientRepository


def _instant(value):
    """Exact integer instants, including DST folds and UTC year-boundary overflow."""
    offset = value.utcoffset()
    if offset is None:
        raise ValueError('aware time required')
    wall = (((value.toordinal() * 24 + value.hour) * 60 + value.minute) * 60
            + value.second) * 1_000_000 + value.microsecond
    return wall - ((offset.days * 86400 + offset.seconds) * 1_000_000 + offset.microseconds)


class CreatinineTrendSelectionPolicy(DomainModel):
    """Fixed v1 eligibility profile; scope and repository cutoff are selector inputs."""
    id: Literal['CreatinineTrendSelectionPolicy'] = 'CreatinineTrendSelectionPolicy'
    version: Literal['1'] = '1'
    concept_id: Literal['synthetic-serum-creatinine'] = 'synthetic-serum-creatinine'
    unit: Literal['mg/dL'] = 'mg/dL'
    window_start: AwareDatetime
    window_end: AwareDatetime
    available_at: AwareDatetime

    @model_validator(mode='after')
    def ordered_window(self):
        if not _instant(self.window_start) < _instant(self.window_end) <= _instant(self.available_at):
            raise ValueError('require start < end <= source availability bound')
        return self


InputIssueCode = Literal[
    'invalid_or_missing_sample_time', 'unresolved_conflict', 'unverified_input',
    'unacceptable_provenance', 'invalid_value', 'unsupported_unit',
    'invalid_result_timing', 'source_unavailable_at_bound',
]
CardinalityIssueCode = Literal[
    'insufficient_eligible_inputs', 'ambiguous_eligible_inputs', 'invalid_measurement_order',
]
BenignExclusionCode = Literal['unrelated_fact', 'unrelated_concept', 'outside_sample_window']
_BENIGN = ('unrelated_fact', 'unrelated_concept', 'outside_sample_window')
_GLOBAL = ('insufficient_eligible_inputs', 'ambiguous_eligible_inputs', 'invalid_measurement_order')


class CreatinineTrendSelectionIssue(DomainModel):
    code: InputIssueCode | CardinalityIssueCode | Literal['duplicate_sample_measurement']
    reference: Reference | None = None

    @model_validator(mode='after')
    def reference_scope(self):
        if (self.code in _GLOBAL) != (self.reference is None):
            raise ValueError('input issues require a reference; cardinality issues do not')
        if self.reference is not None and self.reference.kind != 'observation':
            raise ValueError('input issue must identify an observation')
        return self


class CreatinineTrendExclusion(DomainModel):
    reference: Reference
    reason: InputIssueCode | BenignExclusionCode


def _sample_window_reason(fact, policy):
    time = fact.time
    if time.event is None or time.precision != 'instant' or time.uncertainty is not None:
        return 'invalid_or_missing_sample_time'
    if not _instant(policy.window_start) <= _instant(time.event) < _instant(policy.window_end):
        return 'outside_sample_window'
    return None


def _sample_key(fact):
    return fact.provenance.source.namespace, fact.provenance.source.identifier


def _ineligibility(fact, policy):
    reason = _sample_window_reason(fact, policy)
    if reason:
        return reason
    if fact.conflict != 'none_known':
        return 'unresolved_conflict'
    if (fact.verification not in ('verified', 'clinician_confirmed')
            or fact.binding.verification.status != 'verified'):
        return 'unverified_input'
    provenance = fact.provenance
    source = provenance.source
    if (fact.origin not in ('observed', 'reported') or provenance.lineage != 'complete'
            or provenance.upstream or provenance.limitations
            or source.namespace != 'clinrx.synthetic.serum-creatinine' or source.version != '1'
            or source.channel not in ('measurement', 'external_record')
            or any(item != 'synthetic uncertainty' for item in fact.uncertainty)):
        return 'unacceptable_provenance'
    value = fact.value
    if (value.status != 'known' or not isinstance(value.value, Quantity)
            or not value.value.value.is_finite() or value.value.value <= 0):
        return 'invalid_value'
    unit = value.value.unit
    if (unit.raw != policy.unit or unit.system != 'UCUM' or unit.code != policy.unit
            or unit.status not in ('assessed', 'normalized')):
        return 'unsupported_unit'
    time = fact.time
    times = (time.event, time.recorded, time.retrieved, time.processed)
    if (any(t is None for t in times)
            or any(_instant(a) > _instant(b) for a, b in zip(times, times[1:]))
            or _instant(provenance.recorded_at) != _instant(time.recorded)):
        return 'invalid_result_timing'
    availability = (*times[1:], provenance.recorded_at, fact.binding.verification.assessed_at)
    if any(_instant(t) > _instant(policy.available_at) for t in availability):
        return 'source_unavailable_at_bound'
    return None


class CreatinineTrendSelectionResult(DomainModel):
    policy: CreatinineTrendSelectionPolicy
    target: ContextTarget
    cutoff: RepositoryCutoff
    selected: tuple[ClinicalObservation, ...] = ()
    exclusions: tuple[CreatinineTrendExclusion, ...] = ()
    issues: tuple[CreatinineTrendSelectionIssue, ...] = ()

    @field_validator('cutoff', mode='before')
    @classmethod
    def revalidate_cutoff(cls, value):
        # Storage metadata predates DomainModel's instance revalidation convention.
        return RepositoryCutoff.model_validate(
            value.model_dump(warnings=False) if isinstance(value, RepositoryCutoff) else value)

    @property
    def successful(self) -> bool:
        return not self.issues

    @model_validator(mode='after')
    def selection_integrity(self):
        if self.target.encounter_id is None:
            raise ValueError('creatinine selection requires one encounter')
        excluded = [item.reference for item in self.exclusions]
        if len(set(excluded)) != len(excluded):
            raise ValueError('duplicate excluded reference')
        for item in self.exclusions:
            if item.reason not in _BENIGN and not any(
                    issue.reference == item.reference and issue.code == item.reason for issue in self.issues):
                raise ValueError('blocking exclusion requires its input issue')
        if self.issues:
            if self.selected:
                raise ValueError('unsuccessful selection cannot provide a usable pair')
            return self
        if len(self.selected) != 2:
            raise ValueError('successful selection requires exactly two observations')
        earlier, later = self.selected
        if (earlier.id == later.id or _sample_key(earlier) == _sample_key(later)
                or any(f.binding.target != self.target or f.concept_id != self.policy.concept_id
                       or _ineligibility(f, self.policy) for f in self.selected)
                or any(f.id == ref.id and ref.kind == 'observation'
                       for f in self.selected for ref in excluded)):
            raise ValueError('selected observations must be distinct eligible samples in scope')
        if _instant(earlier.time.event) >= _instant(later.time.event):
            raise ValueError('selected samples require increasing instants')
        return self


def select_creatinine_observations(repository: PatientRepository, *, target: ContextTarget,
                                   cutoff: RepositoryCutoff,
                                   policy: CreatinineTrendSelectionPolicy) -> CreatinineTrendSelectionResult:
    """Read terminal visible revisions first; no filters, writes or older fallback."""
    policy = CreatinineTrendSelectionPolicy.model_validate(policy)
    target = ContextTarget.model_validate(target)
    history = repository.list_latest_known(target=target, cutoff=cutoff)
    # Duplicate sample identity is checked independently of other eligibility failures.
    relevant = [stored.fact for stored in history.records
                if isinstance(stored.fact, ClinicalObservation)
                and stored.fact.concept_id == policy.concept_id
                and _sample_window_reason(stored.fact, policy) is None]
    samples = Counter(_sample_key(fact) for fact in relevant)
    duplicate_refs = {fact.reference for fact in relevant if samples[_sample_key(fact)] > 1}
    eligible, exclusions, issues = [], [], []
    for stored in history.records:
        fact = stored.fact
        if not isinstance(fact, ClinicalObservation):
            reason = 'unrelated_fact'
        elif fact.concept_id != policy.concept_id:
            reason = 'unrelated_concept'
        else:
            reason = _ineligibility(fact, policy)
        if reason:
            exclusions.append(CreatinineTrendExclusion(reference=fact.reference, reason=reason))
            if reason not in _BENIGN:
                issues.append(CreatinineTrendSelectionIssue(code=reason, reference=fact.reference))
        else:
            eligible.append(fact)
        if fact.reference in duplicate_refs:
            issues.append(CreatinineTrendSelectionIssue(
                code='duplicate_sample_measurement', reference=fact.reference))
    if len(eligible) < 2:
        issues.append(CreatinineTrendSelectionIssue(code='insufficient_eligible_inputs'))
    elif len(eligible) > 2:
        issues.append(CreatinineTrendSelectionIssue(code='ambiguous_eligible_inputs'))
    elif _instant(eligible[0].time.event) == _instant(eligible[1].time.event):
        issues.append(CreatinineTrendSelectionIssue(code='invalid_measurement_order'))
    selected = () if issues else tuple(sorted(eligible, key=lambda fact: _instant(fact.time.event)))
    return CreatinineTrendSelectionResult(policy=policy, target=history.target, cutoff=history.cutoff,
        selected=selected, exclusions=tuple(exclusions), issues=tuple(issues))


class RecordedCreatinineComparison(DomainModel):
    earlier_reference: Reference
    later_reference: Reference
    earlier_value: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    later_value: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    unit: Literal['mg/dL'] = 'mg/dL'
    earlier_sample_time: AwareDatetime
    later_sample_time: AwareDatetime
    direction: Literal['increase', 'unchanged', 'decrease']

    @model_validator(mode='after')
    def comparison_integrity(self):
        if (self.earlier_reference.kind != 'observation' or self.later_reference.kind != 'observation'
                or self.earlier_reference.id == self.later_reference.id
                or _instant(self.earlier_sample_time) >= _instant(self.later_sample_time)):
            raise ValueError('comparison requires distinct observations in increasing sample order')
        expected = ('increase' if self.later_value > self.earlier_value else
                    'decrease' if self.later_value < self.earlier_value else 'unchanged')
        if self.direction != expected:
            raise ValueError('direction disagrees with retained values')
        return self


def compare_recorded_creatinine(selection: CreatinineTrendSelectionResult
                               ) -> RecordedCreatinineComparison | CreatinineTrendSelectionIssue:
    """Pure exact comparison; supplied contracts establish consistency, not authenticity."""
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    if selection.issues:
        return selection.issues[0]
    earlier, later = selection.selected
    a, b = earlier.value.value.value, later.value.value.value
    return RecordedCreatinineComparison(
        earlier_reference=earlier.reference, later_reference=later.reference,
        earlier_value=a, later_value=b, unit=selection.policy.unit,
        earlier_sample_time=earlier.time.event, later_sample_time=later.time.event,
        direction='increase' if b > a else 'decrease' if b < a else 'unchanged',
    )
