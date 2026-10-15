"""Synthetic weight selection, comparison and inference construction; no release."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from app.models.clinical.common import (
    ClinicalTime, ContextTarget, DomainModel, LineageEdge, Provenance, Quantity,
    Reference, Source, Text,
)
from app.models.clinical.facts import ClinicalInference, ClinicalObservation
from app.persistence.metadata import RepositoryCutoff
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.repository import PatientRepository


def _instant(value):
    """Integer instant comparison, including DST folds and datetime boundaries."""
    offset = value.utcoffset()
    if offset is None:
        raise ValueError('aware time required')
    wall = (((value.toordinal() * 24 + value.hour) * 60 + value.minute) * 60
            + value.second) * 1_000_000 + value.microsecond
    return wall - ((offset.days * 86400 + offset.seconds) * 1_000_000 + offset.microseconds)


class WeightTrendSelectionPolicy(DomainModel):
    id: Literal['WeightTrendSelectionPolicy'] = 'WeightTrendSelectionPolicy'
    version: Literal['1'] = '1'
    concept_id: Text
    window_start: AwareDatetime
    window_end: AwareDatetime
    # Source availability bound, never derived from an ingestion watermark.
    available_at: AwareDatetime

    @model_validator(mode='after')
    def ordered_window(self):
        if not _instant(self.window_start) < _instant(self.window_end) <= _instant(self.available_at):
            raise ValueError('require start < end <= source availability cutoff')
        return self


IssueCode = Literal[
    'insufficient_eligible_inputs', 'ambiguous_eligible_inputs', 'unsupported_unit',
    'invalid_value', 'invalid_or_missing_event_time', 'unresolved_conflict',
    'invalid_measurement_order', 'unverified_input', 'unacceptable_provenance',
    'source_unavailable_at_cutoff',
]


class WeightTrendSelectionIssue(DomainModel):
    code: IssueCode
    reference: Reference | None = None


class WeightTrendExclusion(DomainModel):
    reference: Reference
    reason: Literal[
        'unrelated_fact', 'unrelated_concept', 'outside_comparison_window',
        'unsupported_unit', 'invalid_value', 'invalid_or_missing_event_time',
        'unresolved_conflict', 'unverified_input', 'unacceptable_provenance',
        'source_unavailable_at_cutoff',
    ]


def _ineligibility(fact, policy):
    time = fact.time
    if time.event is None or time.precision != 'instant' or time.uncertainty is not None:
        return 'invalid_or_missing_event_time'
    if not _instant(policy.window_start) <= _instant(time.event) < _instant(policy.window_end):
        return 'outside_comparison_window'
    if fact.conflict != 'none_known':
        return 'unresolved_conflict'
    if (fact.binding.verification.status != 'verified'
            or fact.verification not in ('verified', 'clinician_confirmed')):
        return 'unverified_input'
    if (fact.origin not in ('observed', 'reported') or fact.provenance.lineage != 'complete'
            or fact.provenance.upstream or fact.provenance.limitations
            or fact.provenance.source.channel not in ('measurement', 'clinician', 'external_record')):
        return 'unacceptable_provenance'
    value = fact.value
    if value.status != 'known' or not isinstance(value.value, Quantity) or value.value.value <= 0:
        return 'invalid_value'
    unit = value.value.unit
    if (unit.status not in ('assessed', 'normalized') or unit.system != 'UCUM'
            or unit.code != 'kg' or unit.raw is None or unit.raw.strip() != 'kg'):
        return 'unsupported_unit'
    availability = (fact.binding.verification.assessed_at, fact.provenance.recorded_at,
                    time.recorded, time.retrieved, time.processed)
    if any(t is not None and _instant(t) > _instant(policy.available_at) for t in availability):
        return 'source_unavailable_at_cutoff'
    return None


class WeightTrendSelectionResult(DomainModel):
    policy: WeightTrendSelectionPolicy
    target: ContextTarget
    cutoff: RepositoryCutoff
    selected: tuple[ClinicalObservation, ...] = ()
    exclusions: tuple[WeightTrendExclusion, ...] = ()
    issues: tuple[WeightTrendSelectionIssue, ...] = ()

    @property
    def successful(self) -> bool:
        return not self.issues

    @model_validator(mode='after')
    def selection_integrity(self):
        if self.target.encounter_id is None:
            raise ValueError('weight selection requires one encounter')
        if self.issues:
            if self.selected:
                raise ValueError('unsuccessful selection cannot provide a usable pair')
            return self
        if len(self.selected) != 2:
            raise ValueError('successful selection requires exactly two observations')
        earlier, later = self.selected
        if (earlier.id == later.id or any(f.binding.target != self.target
                or f.concept_id != self.policy.concept_id or _ineligibility(f, self.policy)
                for f in self.selected)):
            raise ValueError('selected observations must be distinct eligible measurements in scope')
        if _instant(earlier.time.event) >= _instant(later.time.event):
            raise ValueError('selected measurements require increasing event instants')
        return self


def select_weight_observations(repository: PatientRepository, *, target: ContextTarget,
                               cutoff: RepositoryCutoff,
                               policy: WeightTrendSelectionPolicy, history_budget=None, family_budget=None, accounting=None) -> WeightTrendSelectionResult:
    """Read the explicit visible prefix; invalid relevant candidates block v1."""
    policy = WeightTrendSelectionPolicy.model_validate(policy)
    target = ContextTarget.model_validate(target)
    # No time/concept predicate is passed to persistence: terminal selection first.
    history = repository.list_bounded_history(target=target, cutoff=cutoff, latest=True,
        budget=HistoryBudget() if history_budget is None else history_budget, family_budget=family_budget,
        accounting=HistoryAccounting(AggregateHistoryBudget()) if accounting is None else accounting)
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
            exclusions.append(WeightTrendExclusion(reference=fact.reference, reason=reason))
            if reason not in ('unrelated_fact', 'unrelated_concept', 'outside_comparison_window'):
                issues.append(WeightTrendSelectionIssue(code=reason, reference=fact.reference))
        else:
            eligible.append(fact)
    if len(eligible) < 2:
        issues.append(WeightTrendSelectionIssue(code='insufficient_eligible_inputs'))
    elif len(eligible) > 2:
        issues.append(WeightTrendSelectionIssue(code='ambiguous_eligible_inputs'))
    elif _instant(eligible[0].time.event) == _instant(eligible[1].time.event):
        issues.append(WeightTrendSelectionIssue(code='invalid_measurement_order'))
    selected = () if issues else tuple(sorted(eligible, key=lambda f: _instant(f.time.event)))
    return WeightTrendSelectionResult(policy=policy, target=history.target, cutoff=history.cutoff,
                                     selected=selected, exclusions=tuple(exclusions), issues=tuple(issues))


class RecordedWeightComparison(DomainModel):
    earlier_reference: Reference
    later_reference: Reference
    earlier_kg: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    later_kg: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
    earlier_event: AwareDatetime
    later_event: AwareDatetime
    direction: Literal['decrease', 'unchanged', 'increase']

    @model_validator(mode='after')
    def comparison_integrity(self):
        if (self.earlier_reference.kind != 'observation' or self.later_reference.kind != 'observation'
                or self.earlier_reference.id == self.later_reference.id
                or _instant(self.earlier_event) >= _instant(self.later_event)):
            raise ValueError('comparison requires distinct observations in increasing event order')
        expected = ('decrease' if self.later_kg < self.earlier_kg else
                    'increase' if self.later_kg > self.earlier_kg else 'unchanged')
        if self.direction != expected:
            raise ValueError('direction disagrees with retained kilogram values')
        return self


def compare_recorded_weights(selection: WeightTrendSelectionResult
                             ) -> RecordedWeightComparison | WeightTrendSelectionIssue:
    """Preserve selected exact revisions; failed selection never becomes a result."""
    selection = WeightTrendSelectionResult.model_validate(selection)
    if selection.issues:
        return selection.issues[0]
    earlier, later = selection.selected
    a, b = earlier.value.value.value, later.value.value.value
    return RecordedWeightComparison(
        earlier_reference=earlier.reference, later_reference=later.reference,
        earlier_kg=a, later_kg=b, earlier_event=earlier.time.event, later_event=later.time.event,
        direction='decrease' if b < a else 'increase' if b > a else 'unchanged',
    )


RECORDED_WEIGHT_TREND_METHOD = Reference(kind='inference_method', id='RecordedWeightTrend', version='1')


def build_weight_trend_inference(*, selection: WeightTrendSelectionResult,
                                comparison: RecordedWeightComparison | WeightTrendSelectionIssue,
                                inference_id: str, executed_at: datetime, revision: str = '1'
                                ) -> ClinicalInference | WeightTrendSelectionIssue:
    """Build only from the supplied exact pair; callers persist through the repository.

    Validation is structural and synthetic, not source authentication or permission
    to release. This function performs no repository reads or writes.
    """
    selection = WeightTrendSelectionResult.model_validate(selection)
    if selection.issues:
        return selection.issues[0]
    comparison = RecordedWeightComparison.model_validate(comparison)
    expected = compare_recorded_weights(selection)
    # Compare retained representations too: equal instants/Decimal values must not
    # silently replace the selected offsets or source precision.
    if comparison.model_dump(mode='json') != expected.model_dump(mode='json'):
        raise ValueError('comparison does not match the exact selected observations')
    executed_at = TypeAdapter(AwareDatetime).validate_python(executed_at)
    if _instant(executed_at) < _instant(selection.policy.available_at):
        raise ValueError('inference execution precedes the source availability cutoff')
    earlier, later = selection.selected
    inputs = (earlier.reference, later.reference)
    if comparison.direction == 'unchanged':
        statement = (f'Recorded weight was unchanged at {comparison.earlier_kg} kg between the selected observations. '
                     'This comparison does not establish nutritional status. Synthetic evaluation only.')
    else:
        verb = 'decreased' if comparison.direction == 'decrease' else 'increased'
        statement = (f'Recorded weight {verb} from {comparison.earlier_kg} kg to {comparison.later_kg} kg '
                     'between the selected observations. This comparison does not establish cause or '
                     'nutritional diagnosis. Synthetic evaluation only.')
    return ClinicalInference(
        id=inference_id, revision=revision, binding=earlier.binding, origin='inferred',
        statement=statement, inputs=inputs, method=RECORDED_WEIGHT_TREND_METHOD,
        applicability='Synthetic recorded-weight comparison within the selected patient/encounter and event window only.',
        validation_limitations='Not clinically validated; no diagnosis, causal interpretation or treatment recommendation.',
        uncertainty=tuple(dict.fromkeys((
            'Recorded comparison does not establish cause or nutritional status.',
            'Synthetic evaluation only; input authenticity is not established.',
            *earlier.uncertainty, *later.uncertainty,
        ))),
        provenance=Provenance(
            source=Source(namespace='clinrx.synthetic', identifier=RECORDED_WEIGHT_TREND_METHOD.id,
                          version=RECORDED_WEIGHT_TREND_METHOD.version, channel='system'),
            actor='RecordedWeightTrend/v1', recorded_at=executed_at,
            upstream=tuple(LineageEdge(target=reference, relationship='derived_from') for reference in inputs),
            lineage='complete', limitations=('Synthetic evaluation only; no clinical validity or source-authenticity claim.',),
        ),
        time=ClinicalTime(event=executed_at, recorded=executed_at, processed=executed_at, precision='instant'),
        verification='unverified', conflict='unknown', temporal_status='unknown',
    )
