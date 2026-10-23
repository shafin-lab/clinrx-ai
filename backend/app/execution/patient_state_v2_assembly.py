"""Bounded recorded microbiology/antimicrobial state; no clinical reasoning."""
from typing import Annotated, Literal
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import Engine
from app.models.clinical.common import Reference
from app.models.clinical.recorded_v2 import Contract, RecordedFactV2, instant, ref_key
from app.execution.patient_state_v2 import (PatientStateScopeV2, PatientStateSnapshotV2,
    RetainedStateItemV2, MicrobiologyView, AntimicrobialView, SpecimenGroup,
    IsolateGroup, MolecularPanelGroup, CoverageV2, MappingIssueV2)
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.errors import (PersistenceError, PersistenceInputError, QueryLimitExceeded,
    StorageIntegrityError, TransactionAborted)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction


class AssemblyLimits(Contract):
    history: HistoryBudget = Field(default_factory=HistoryBudget)
    max_items: Annotated[int, Field(strict=True, ge=1, le=512)] = 512
    max_specimens: Annotated[int, Field(strict=True, ge=1, le=128)] = 128
    max_isolates: Annotated[int, Field(strict=True, ge=1, le=256)] = 256
    max_children: Annotated[int, Field(strict=True, ge=1, le=64)] = 64
    max_molecular_targets: Annotated[int, Field(strict=True, ge=1, le=64)] = 64
    max_bindings: Annotated[int, Field(strict=True, ge=1, le=1024)] = 1024
    max_depth: Annotated[int, Field(strict=True, ge=0, le=8)] = 8
    max_fanout: Annotated[int, Field(strict=True, ge=1, le=16)] = 16
    max_traversal_steps: Annotated[int, Field(strict=True, ge=1, le=8192)] = 8192
    max_issues: Annotated[int, Field(strict=True, ge=1, le=512)] = 512
    max_result_bytes: Annotated[int, Field(strict=True, ge=1, le=16777216)] = 16777216


class AssemblyRequestV2(Contract):
    scope: PatientStateScopeV2
    profile_id: Literal['SyntheticMicrobiologyAntimicrobialState']
    profile_version: Literal['2']
    limits: AssemblyLimits = Field(default_factory=AssemblyLimits)


class AssemblyIssueV2(Contract):
    reference: Reference
    reason: Literal['unsupported_source_structure', 'withdrawn_terminal', 'outside_review_window',
        'temporal_incompleteness', 'contextual_parent', 'unresolved_parent', 'ambiguous_binding',
        'historical_target_not_retained', 'withdrawn_binding_target', 'unsupported_antimicrobial_mapping',
        'preliminary_report', 'incomplete_susceptibility', 'unknown_isolate_identity']


class BindingOutcomeV2(Contract):
    owner: Reference
    role: Literal['specimen', 'isolate', 'collection_set', 'bottle', 'order']
    declared: Reference | None = None
    status: Literal['resolved', 'unresolved', 'ambiguous']
    disposition: Literal['retained_exact', 'historical_exact_not_retained',
        'unavailable_in_prefix', 'declared_unresolved', 'declared_ambiguous', 'outside_profile',
        'withdrawn_target_not_retained']
    candidates: Annotated[tuple[Reference, ...], Field(max_length=16)] = ()


class PatientStateAssemblyResultV2(Contract):
    request: AssemblyRequestV2
    snapshot: PatientStateSnapshotV2
    candidate_rows: Annotated[int, Field(strict=True, ge=0, le=4096)]
    terminal_count: Annotated[int, Field(strict=True, ge=0, le=4096)]
    bindings: Annotated[tuple[BindingOutcomeV2, ...], Field(max_length=1024)] = ()
    issues: Annotated[tuple[AssemblyIssueV2, ...], Field(max_length=512)] = ()

    @model_validator(mode='after')
    def coherent(self):
        if canonical_payload(self.request.scope) != canonical_payload(self.snapshot.scope):
            raise ValueError('assembly scope differs from request')
        if self.candidate_rows < self.terminal_count or self.terminal_count < len(self.snapshot.items):
            raise ValueError('assembly counts inconsistent')
        if any(item.ingestion is None for item in self.snapshot.items):
            raise ValueError('assembly requires durable ingestion metadata')
        if self.bindings != tuple(sorted(self.bindings, key=lambda b: (*ref_key(b.owner), b.role))):
            raise ValueError('binding outcomes must be ordered')
        if self.issues != tuple(sorted(set(self.issues), key=lambda i: (*ref_key(i.reference), i.reason))):
            raise ValueError('assembly issues must be unique and ordered')
        return self


def _limit(condition):
    if condition:
        raise QueryLimitExceeded('patient state v2 assembly budget exceeded')


def _domain(fact):
    if fact.kind.startswith('antimicrobial_'):
        return 'antimicrobial'
    if fact.kind.startswith('microbiology_') or fact.kind in ('blood_culture_set', 'blood_culture_bottle'):
        return 'microbiology'
    return 'other'


def _withdrawn(fact):
    return getattr(getattr(fact, 'report', None), 'status', None) == 'withdrawn'


def _placement(fact, scope):
    time = fact.semantic_time
    if time.anchor is None:
        return 'unplaced'
    lo = time.lower if time.lower is not None else time.value
    hi = time.upper if time.upper is not None else time.value
    return 'in_window' if instant(lo) <= instant(scope.review_end) and instant(hi) >= instant(scope.review_start) else None


def _assemble(repository, request, *, history_budget=None, family_budget=None, accounting=None):
    scope, limits = request.scope, request.limits
    budget = limits.history
    if history_budget is not None:
        operational = HistoryBudget.model_validate(history_budget)
        budget = HistoryBudget(max_rows=min(budget.max_rows, operational.max_rows),
            max_payload_bytes=min(budget.max_payload_bytes, operational.max_payload_bytes))
    history = repository.list_bounded_history(target=scope.target,
        cutoff=scope.repository_cutoff, budget=budget, family_budget=family_budget,
        accounting=HistoryAccounting(AggregateHistoryBudget()) if accounting is None else accounting)
    exact, terminal = {}, {}
    for stored in history.records:
        ref = stored.fact.reference
        if ref in exact:
            raise StorageIntegrityError('duplicate exact historical identity')
        exact[ref] = stored
        terminal[(ref.kind, ref.id)] = stored
    selected, contextual, issues = {}, {}, set()

    def issue(ref, reason):
        issues.add(AssemblyIssueV2(reference=ref, reason=reason))
        _limit(len(issues) > limits.max_issues)

    def include(stored, placement):
        selected[stored.fact.reference] = (stored, placement)
        _limit(len(selected) > limits.max_items)

    for key in sorted(terminal):
        stored = terminal[key]
        fact = stored.fact
        if not isinstance(fact, RecordedFactV2):
            issue(fact.reference, 'unsupported_source_structure')
        elif _domain(fact) == 'other':
            # M6 assembles only facts owned by microbiology and antimicrobial
            # contracts. Shared laboratory reports are served through M8/RF2.
            continue
        elif _withdrawn(fact):
            issue(fact.reference, 'withdrawn_terminal')
        else:
            placement = _placement(fact, scope)
            if placement:
                include(stored, placement)
            else:
                issue(fact.reference, 'outside_review_window')

    # The profile follows exact declared parents only. Historical predecessors
    # are reported as such, not substituted for the terminal state of a family.
    steps = 0
    def parents(ref, depth, path):
        nonlocal steps
        fact = selected[ref][0].fact
        _limit(len(fact.domain_bindings) > limits.max_fanout)
        for binding in sorted(fact.domain_bindings, key=lambda b: b.role):
            steps += 1
            _limit(steps > limits.max_traversal_steps)
            parent = binding.exact
            if parent is None or parent not in exact:
                continue
            candidate = exact[parent]
            if not isinstance(candidate.fact, RecordedFactV2) or _withdrawn(candidate.fact):
                continue
            if terminal[(parent.kind, parent.id)].fact.reference != parent:
                continue
            if parent in path:
                raise StorageIntegrityError('circular exact domain bindings')
            _limit(depth + 1 > limits.max_depth)
            if parent not in selected:
                include(candidate, 'contextual_parent')
                issue(parent, 'contextual_parent')
                issues.discard(AssemblyIssueV2(reference=parent, reason='outside_review_window'))
            if selected[parent][1] == 'contextual_parent':
                contextual.setdefault(parent, set()).add(ref)
                _limit(len(contextual[parent]) > limits.max_children)
            parents(parent, depth + 1, path | {parent})
    for ref in sorted(tuple(selected), key=ref_key):
        parents(ref, 0, {ref})

    declared = tuple(b.exact for stored, _ in selected.values()
                     for b in stored.fact.domain_bindings if b.exact is not None)
    _limit(len(declared) > limits.max_bindings)
    repository.check_visible_binding_scopes(declared, target=scope.target, cutoff=scope.repository_cutoff)
    outcomes, snapshot_issues = [], set()
    for ref in sorted(selected, key=ref_key):
        fact = selected[ref][0].fact
        time = fact.semantic_time
        if time.precision != 'instant':
            issue(ref, 'temporal_incompleteness')
        if fact.kind == 'microbiology_specimen' and fact.collected.anchor is None:
            snapshot_issues.add(MappingIssueV2(reference=ref, reason='missing_collection_time'))
        if fact.kind == 'antimicrobial_administration' and fact.administered.anchor is None:
            snapshot_issues.add(MappingIssueV2(reference=ref, reason='missing_administration_time'))
        drug = getattr(fact, 'antimicrobial', None)
        if drug and drug.mapping_status != 'mapped':
            issue(ref, 'unsupported_antimicrobial_mapping')
            snapshot_issues.add(MappingIssueV2(reference=ref, reason='unsupported_antimicrobial_identity'))
        report = getattr(fact, 'report', None)
        if report and report.status in ('preliminary', 'interim'):
            issue(ref, 'preliminary_report')
        if fact.kind == 'microbiology_isolate' and fact.identification_state == 'unresolved':
            issue(ref, 'unknown_isolate_identity')
        if fact.kind == 'microbiology_susceptibility' and fact.result_status != 'reported':
            issue(ref, 'incomplete_susceptibility')
        for binding in sorted(fact.domain_bindings, key=lambda b: b.role):
            status = binding.status
            if status != 'resolved':
                disposition = 'declared_' + status
                issue(ref, 'ambiguous_binding' if status == 'ambiguous' else 'unresolved_parent')
            elif binding.exact in selected:
                disposition = 'retained_exact'
            elif binding.exact in exact:
                target_fact = exact[binding.exact].fact
                if _withdrawn(target_fact):
                    disposition = 'withdrawn_target_not_retained'
                    issue(ref, 'withdrawn_binding_target')
                else:
                    disposition = 'historical_exact_not_retained' if isinstance(target_fact, RecordedFactV2) else 'outside_profile'
                    issue(ref, 'historical_target_not_retained')
            else:
                status, disposition = 'unresolved', 'unavailable_in_prefix'
                issue(ref, 'unresolved_parent')
            if binding.exact and binding.exact not in selected:
                snapshot_issues.add(MappingIssueV2(reference=ref, reason='binding_target_unavailable'))
            outcomes.append(BindingOutcomeV2(owner=ref, role=binding.role, declared=binding.exact,
                status=status, disposition=disposition, candidates=binding.candidates))
            _limit(len(outcomes) > limits.max_bindings)
    _limit(len(snapshot_issues) + len(issues) > limits.max_issues)
    refs_by_kind = {}
    for ref in selected:
        refs_by_kind.setdefault(ref.kind, []).append(ref)
    def refs(kind):
        return tuple(sorted(refs_by_kind.get(kind, ()), key=ref_key))
    def children(parent, role, kind):
        found = tuple(o.owner for o in outcomes if o.role == role and o.declared == parent
                      and o.disposition == 'retained_exact' and o.owner.kind == kind)
        _limit(len(found) > limits.max_children)
        return found
    specimens = refs('microbiology_specimen')
    isolates = refs('microbiology_isolate')
    _limit(len(specimens) > limits.max_specimens or len(isolates) > limits.max_isolates)
    _limit(len(refs('microbiology_molecular')) > limits.max_molecular_targets)
    panels = {}
    for ref in refs('microbiology_molecular'):
        panel = selected[ref][0].fact.panel_identifier
        if panel:
            key = (panel.namespace, panel.code, panel.version)
            if key in panels and canonical_payload(panels[key][0]) != canonical_payload(panel):
                raise StorageIntegrityError('contradictory molecular panel source identity')
            panels.setdefault(key, (panel, []))[1].append(ref)
    items = []
    for ref, (stored, placement) in selected.items():
        disclosures = ('Source completeness and clinical availability are not established by repository visibility.',)
        if placement == 'unplaced':
            disclosures += ('Clinical temporal placement is unresolved.',)
        if placement == 'contextual_parent':
            disclosures += ('Exact contextual parent outside the review window.',)
        items.append(RetainedStateItemV2(fact=stored.fact, expected_digest=stored.fact.canonical_digest,
            ingestion=stored.ingestion, inclusion=placement,
            contextual_for=tuple(contextual.get(ref, ())), disclosures=disclosures))
    coverage = []
    for domain in ('microbiology', 'antimicrobial'):
        count = sum(isinstance(v.fact, RecordedFactV2) and _domain(v.fact) == domain for v in terminal.values())
        retained = sum(_domain(v[0].fact) == domain for v in selected.values())
        coverage.append(CoverageV2(domain=domain, mapping_support='partial', retrieval='completed',
            candidate_count=count, retained_count=retained,
            limitations=('Only explicitly typed persisted M6 facts are mapped; source completeness is unknown.',)))
    try:
        snapshot = PatientStateSnapshotV2(scope=scope, items=tuple(items), coverage=tuple(coverage),
            issues=tuple(snapshot_issues), disclosures=('Recorded state only; no inference or clinical absence claim.',),
            microbiology=MicrobiologyView(references=tuple(r for r in selected if _domain(selected[r][0].fact) == 'microbiology'),
                specimens=tuple(SpecimenGroup(specimen=r, examinations=children(r,'specimen','microbiology_direct_examination'),
                    cultures=children(r,'specimen','microbiology_culture'), isolates=children(r,'specimen','microbiology_isolate'),
                    molecular_results=children(r,'specimen','microbiology_molecular')) for r in specimens),
                isolates=tuple(IsolateGroup(isolate=r, susceptibilities=children(r,'isolate','microbiology_susceptibility'),
                    resistance_findings=children(r,'isolate','microbiology_resistance')) for r in isolates),
                panels=tuple(MolecularPanelGroup(panel=p, targets=tuple(targets)) for p, targets in panels.values())),
            antimicrobial=AntimicrobialView(orders=refs('antimicrobial_order'),
                administrations=refs('antimicrobial_administration'), non_delivery=refs('antimicrobial_non_delivery')))
    except ValidationError:
        raise StorageIntegrityError('persisted facts contradict patient state v2 contracts') from None
    result = PatientStateAssemblyResultV2(request=request, snapshot=snapshot,
        candidate_rows=len(history.records), terminal_count=len(terminal), bindings=tuple(outcomes),
        issues=tuple(sorted(issues, key=lambda i: (*ref_key(i.reference), i.reason))))
    _limit(len(canonical_payload(result).encode('utf-8')) > limits.max_result_bytes)
    return result


def assemble_patient_state_v2(engine: Engine, *, request: AssemblyRequestV2, history_budget=None, family_budget=None, accounting=None) -> PatientStateAssemblyResultV2:
    """One existing transaction, no writes, clock sampling or execution."""
    if not isinstance(engine, Engine):
        raise PersistenceInputError('patient state v2 assembly requires an Engine')
    try:
        request = AssemblyRequestV2.model_validate(request)
    except (ValidationError, ValueError, TypeError):
        raise PersistenceInputError('invalid patient state v2 assembly request') from None
    try:
        with transaction(engine) as repository:
            result = _assemble(repository, request, history_budget=history_budget,
                family_budget=family_budget, accounting=accounting)
        return result
    except PersistenceError as error:
        raise error from None
    except Exception:
        raise TransactionAborted('patient state v2 assembly failed') from None
