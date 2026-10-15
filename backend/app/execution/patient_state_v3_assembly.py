"""Bounded cutoff reconstruction of M7 recorded evidence; no inferred physiology."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from app.models.clinical.recorded_v2 import Contract, instant, ref_key
from app.models.clinical.hemodynamics import (CirculatoryFact, DynamicAssessment,
    Measurement, VasoactiveEvent, InfusionEvent)
from app.persistence.bounded_history import HistoryBudget, HistoryAccounting, AggregateHistoryBudget
from app.persistence.canonical import canonical_payload
from app.persistence.errors import QueryLimitExceeded, StorageIntegrityError, PersistenceInputError
from app.persistence.repository import transaction
from .patient_state_v3 import (PatientStateScopeV3, PatientStateSnapshotV3, RetainedStateItemV3,
    CoverageV3, StateIssueV3, clinical_time)


class AssemblyLimitsV3(Contract):
    history: HistoryBudget = Field(default_factory=HistoryBudget)
    max_items: Annotated[int, Field(strict=True, ge=1, le=512)] = 512
    max_relationships: Annotated[int, Field(strict=True, ge=1, le=2048)] = 2048
    max_contextual: Annotated[int, Field(strict=True, ge=1, le=256)] = 256
    max_groups: Annotated[int, Field(strict=True, ge=1, le=256)] = 256
    max_signals: Annotated[int, Field(strict=True, ge=1, le=64)] = 64
    max_depth: Annotated[int, Field(strict=True, ge=0, le=8)] = 8
    max_fanout: Annotated[int, Field(strict=True, ge=1, le=64)] = 64
    max_steps: Annotated[int, Field(strict=True, ge=1, le=8192)] = 8192
    max_issues: Annotated[int, Field(strict=True, ge=1, le=1024)] = 1024
    max_result_bytes: Annotated[int, Field(strict=True, ge=1, le=16777216)] = 16777216


class AssemblyRequestV3(Contract):
    scope: PatientStateScopeV3
    profile_id: Literal['RecordedCirculatoryEvidence'] = 'RecordedCirculatoryEvidence'
    profile_version: Literal['1'] = '1'
    limits: AssemblyLimitsV3 = Field(default_factory=AssemblyLimitsV3)


class PatientStateAssemblyResultV3(Contract):
    request: AssemblyRequestV3
    snapshot: PatientStateSnapshotV3

    @model_validator(mode='after')
    def coherent(self):
        if canonical_payload(self.request.scope) != canonical_payload(self.snapshot.scope):
            raise ValueError('assembly scope differs from request')
        _limit(len(self.snapshot.items)>self.request.limits.max_items)
        _limit(len(self.snapshot.issues)>self.request.limits.max_issues)
        _limit(len(canonical_payload(self).encode())>self.request.limits.max_result_bytes)
        return self

    @property
    def input_references(self):
        return tuple(i.reference for i in self.snapshot.items)


def related_references(fact):
    refs = [b.exact for b in fact.associations if b.exact is not None]
    if isinstance(fact, DynamicAssessment):
        refs.extend((*fact.baseline, *fact.intervention, *fact.subsequent))
    if isinstance(fact, Measurement):
        refs.extend(fact.calculation_inputs)
    if isinstance(fact, VasoactiveEvent) and isinstance(fact.action, InfusionEvent):
        if fact.action.delivery.dosing_weight:
            refs.append(fact.action.delivery.dosing_weight)
    return tuple(dict.fromkeys(refs))


def _limit(condition):
    if condition:
        raise QueryLimitExceeded('circulatory state resource limit exceeded')


def _assemble(repository, request, *, history_budget=None, family_budget=None, accounting=None):
    request = AssemblyRequestV3.model_validate(request)
    scope, limits = request.scope, request.limits
    budget = limits.history
    if history_budget is not None:
        operational = HistoryBudget.model_validate(history_budget)
        budget = HistoryBudget(max_rows=min(budget.max_rows, operational.max_rows),
            max_payload_bytes=min(budget.max_payload_bytes, operational.max_payload_bytes))
    history = repository.list_bounded_history(target=scope.target, cutoff=scope.repository_cutoff,
        budget=budget, family_budget=family_budget,
        accounting=HistoryAccounting(AggregateHistoryBudget()) if accounting is None else accounting)
    exact, terminal = {}, {}
    for stored in history.records:
        ref = stored.fact.reference
        if ref in exact:
            raise StorageIntegrityError('duplicate exact history identity')
        exact[ref] = stored
        terminal[(ref.kind, ref.id)] = stored
    selected, contextual, issues = {}, {}, set()

    def issue(ref, reason):
        issues.add(StateIssueV3(reference=ref, reason=reason))
        _limit(len(issues) > limits.max_issues)

    for key in sorted(terminal):
        stored = terminal[key]
        f = stored.fact
        if not isinstance(f, CirculatoryFact):
            issue(f.reference, 'outside_profile')
            continue
        if f.record_status in ('withdrawn', 'invalid'):
            issue(f.reference, 'withdrawn_terminal')
        t = clinical_time(f)
        lo, hi = t.recorded.lower or t.recorded.value, t.recorded.upper or t.recorded.value
        if lo is None:
            selected[f.reference] = (stored, 'unplaced')
            issue(f.reference, 'unplaced')
        elif instant(lo) <= instant(scope.review_end) and instant(hi) >= instant(scope.review_start):
            selected[f.reference] = (stored, 'in_window')
        else:
            issue(f.reference, 'outside_window')
        if not t.trustworthy:
            issue(f.reference, 'temporal_uncertainty')
        if isinstance(f, Measurement) and f.acquisition.quality.status != 'acceptable':
            issue(f.reference, 'uncertain_quality')
        _limit(len(selected) > limits.max_items)

    steps = relationships = 0
    def parents(ref, depth, path):
        nonlocal steps, relationships
        f = selected[ref][0].fact
        if any(b.status != 'resolved' for b in f.associations):
            issue(ref, 'unresolved_association')
        refs = related_references(f)
        _limit(len(refs) > limits.max_fanout)
        relationships += len(refs)
        _limit(relationships > limits.max_relationships)
        repository.check_visible_binding_scopes(refs, target=scope.target, cutoff=scope.repository_cutoff)
        for parent in sorted(refs, key=ref_key):
            steps += 1
            _limit(steps > limits.max_steps)
            if parent in path:
                raise StorageIntegrityError('circular circulatory associations')
            candidate = exact.get(parent)
            if candidate is None:
                issue(ref, 'missing_association')
                continue
            if not isinstance(candidate.fact, CirculatoryFact):
                issue(ref, 'outside_profile')
                continue
            if terminal[(parent.kind, parent.id)].fact.reference != parent:
                issue(ref, 'historical_association')
                continue
            _limit(depth + 1 > limits.max_depth)
            if parent not in selected:
                selected[parent] = (candidate, 'contextual')
                issue(parent, 'contextual')
                issues.discard(StateIssueV3(reference=parent, reason='outside_window'))
            if selected[parent][1] == 'contextual':
                contextual.setdefault(parent, set()).add(ref)
                _limit(len(contextual) > limits.max_contextual or len(contextual[parent]) > 64)
            _limit(len(selected) > limits.max_items)
            parents(parent, depth+1, path | {parent})

    for ref in sorted(tuple(selected), key=ref_key):
        parents(ref, 0, {ref})
    items, groups = [], set()
    for ref in sorted(selected, key=ref_key):
        stored, inclusion = selected[ref]
        acquisition = getattr(stored.fact, 'acquisition', None)
        if acquisition and acquisition.episode:
            groups.add(acquisition.episode)
        items.append(RetainedStateItemV3(fact=stored.fact, expected_digest=stored.fact.canonical_digest,
            ingestion=stored.ingestion, inclusion=inclusion,
            contextual_for=tuple(sorted(contextual.get(ref, ()), key=ref_key)),
            disclosures=('Recorded evidence only; source availability, continuity and completeness require separate assessment.',)))
    _limit(len(groups) > limits.max_groups)
    _limit(sum(i.fact.kind == 'circulatory_signal' for i in items) > limits.max_signals)
    snapshot = PatientStateSnapshotV3(scope=scope, items=tuple(items), issues=tuple(issues),
        coverage=CoverageV3(candidate_rows=len(history.records), terminal_count=len(terminal), retained_count=len(items)))
    result = PatientStateAssemblyResultV3(request=request, snapshot=snapshot)
    _limit(len(canonical_payload(result).encode()) > limits.max_result_bytes)
    return result


def assemble_patient_state_v3(engine, *, request, history_budget=None, family_budget=None, accounting=None):
    from sqlalchemy import Engine
    from pydantic import ValidationError
    if not isinstance(engine, Engine):
        raise PersistenceInputError('circulatory assembly requires an Engine')
    try:
        request = AssemblyRequestV3.model_validate(request)
    except (ValidationError, ValueError, TypeError):
        raise PersistenceInputError('invalid circulatory assembly request') from None
    try:
        with transaction(engine) as repository:
            return _assemble(repository, request, history_budget=history_budget,
                family_budget=family_budget, accounting=accounting)
    except ValidationError:
        raise StorageIntegrityError('visible stored evidence contradicts circulatory assembly') from None
