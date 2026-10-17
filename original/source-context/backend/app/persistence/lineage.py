"""Read-only resolution of declared lineage inside a validated repository prefix."""
from collections import deque
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import func, select

from app.models.clinical.common import ContextTarget, LineageEdge, Reference, validate_origin
from .entities import FactRow
from .errors import (PersistenceInputError, QueryLimitExceeded, RecordNotFound,
                     ScopeMismatch, StorageIntegrityError)
from .history import QueryContract, _instant_key
from .mapping import SUPPORTED_FACTS, StoredFact
from .metadata import RepositoryCutoff


class LineageLimits(QueryContract):
    """Finite work budgets, including the scoped history scan and closure storage."""
    max_records: Annotated[int, Field(strict=True, gt=0, le=10000)] = 10000
    max_nodes: Annotated[int, Field(strict=True, gt=0, le=1000)] = 1000
    max_assertions: Annotated[int, Field(strict=True, gt=0, le=10000)] = 10000
    max_width: Annotated[int, Field(strict=True, gt=0, le=1000)] = 1000
    max_depth: Annotated[int, Field(strict=True, ge=0, le=1000)] = 100
    max_ancestry_entries: Annotated[int, Field(strict=True, gt=0, le=100000)] = 100000


@dataclass(frozen=True)
class ResolvedNode:
    stored: StoredFact
    roles: tuple[Literal['evidence', 'confirmation_validation', 'association'], ...]


@dataclass(frozen=True)
class LineageAssertion:
    owner: Reference
    ordinal: int
    edge: LineageEdge

    @property
    def identity(self):
        return (self.owner, self.ordinal)


@dataclass(frozen=True)
class Dependency:
    """Evidence flows source -> owner; basis ordinal is present for confirmation."""
    owner: Reference
    ordinal: int
    basis_ordinal: int | None
    source: Reference


@dataclass(frozen=True)
class Association:
    owner: Reference
    field: Literal['upstream', 'order']
    ordinal: int
    target: Reference


@dataclass(frozen=True)
class UnresolvedReference:
    owner: Reference
    reference: Reference
    role: Literal['dependency', 'confirmation_target', 'association']
    ordinal: int
    basis_ordinal: int | None
    reason: Literal['not_resolvable_in_scope_at_cutoff', 'unsupported_reference_kind']


@dataclass(frozen=True)
class ProvenanceDisclosure:
    reference: Reference
    lineage: Literal['complete', 'incomplete', 'unknown']
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ConfirmationAssessment:
    owner: Reference
    ordinal: int
    relationship: Literal['unknown']
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class LineageResult:
    reference: Reference
    target: ContextTarget
    cutoff: RepositoryCutoff
    nodes: tuple[ResolvedNode, ...]
    assertions: tuple[LineageAssertion, ...]
    dependencies: tuple[Dependency, ...]
    associations: tuple[Association, ...]
    unresolved: tuple[UnresolvedReference, ...]
    provenance: tuple[ProvenanceDisclosure, ...]
    confirmations: tuple[ConfirmationAssessment, ...]
    coverage: Literal['complete_for_declared_visible_graph', 'partial']
    # Includes unresolved leaves; never includes revision-history edges.
    ancestry: tuple[tuple[Reference, frozenset[Reference]], ...]

    def support_relationship(self, left, right) -> Literal['dependent', 'unknown']:
        """Compare analyzed closures only; disjoint IDs never prove independence."""
        try:
            left, right = Reference.model_validate(left), Reference.model_validate(right)
        except ValueError:
            raise PersistenceInputError('invalid lineage comparison reference') from None
        closures = dict(self.ancestry)
        if left not in closures or right not in closures:
            raise PersistenceInputError('lineage comparison requires analyzed references')
        return 'dependent' if _shared(closures[left], closures[right]) else 'unknown'


def _key(ref):
    return ref.kind, ref.id, ref.version


def _shared(left, right):
    # Stable-family overlap is conservative dependence, NOT revision traversal.
    return bool(left & right or {(r.kind, r.id) for r in left} &
                {(r.kind, r.id) for r in right})


def _limit(condition):
    if condition:
        raise QueryLimitExceeded('lineage query resource limit exceeded')


def resolve(repository, reference, *, target, cutoff, limits, history_budget=None, family_budget=None, accounting=None):
    """Called inside the repository's checked transaction boundary."""
    reference = Reference.model_validate(reference)
    limits = LineageLimits.model_validate(limits)
    cutoff = RepositoryCutoff.model_validate(
        cutoff.model_dump(warnings=False) if isinstance(cutoff, RepositoryCutoff) else cutoff)
    if str(cutoff.repository_id) != repository._repository_id:
        raise ScopeMismatch('cutoff belongs to a different repository')
    maximum = repository._session.scalar(select(func.max(FactRow.ingestion_sequence))) or 0
    if cutoff.fact_watermark > maximum:
        raise PersistenceInputError('cutoff exceeds visible repository state')
    target = repository._target(target)
    # Bound the history scan before decoding any payload. No future/out-of-scope
    # lookup is used to classify references. History rechecks envelopes/chains.
    count = repository._session.scalar(select(func.count()).select_from(FactRow).where(
        FactRow.patient_id == target.patient_id, FactRow.encounter_id == target.encounter_id,
        FactRow.ingestion_sequence <= cutoff.fact_watermark))
    _limit(count > limits.max_records)
    from .bounded_history import HistoryBudget, _bounded_retrieve
    budget = HistoryBudget.model_validate(history_budget) if history_budget is not None else None
    # Preserve the legacy max_records ceiling, including values above 4096.
    history = _bounded_retrieve(repository, target=target, cutoff=cutoff,
        max_rows=limits.max_records if budget is None else min(limits.max_records, budget.max_rows),
        max_payload_bytes=16777216 if budget is None else budget.max_payload_bytes,
        family_budget=family_budget, accounting=accounting)
    visible = {item.fact.reference: item for item in history.records}
    if reference not in visible:
        raise RecordNotFound('lineage root not resolvable in scope at cutoff')

    roles, active, pending = {reference: {'evidence'}}, {reference}, deque([reference])
    assertions, dependencies, associations, unresolved = [], [], [], []
    adjacency = {}
    units = 0

    def endpoint(owner, ref, role, ordinal, basis=None):
        nonlocal units
        units += 1
        _limit(units > limits.max_assertions)
        if ref not in visible:
            reason = ('unsupported_reference_kind' if ref.kind not in SUPPORTED_FACTS
                      else 'not_resolvable_in_scope_at_cutoff')
            unresolved.append(UnresolvedReference(owner, ref, role, ordinal, basis, reason))
            return
        roles.setdefault(ref, set())
        if role == 'association':
            roles[ref].add('association')
        _limit(len(roles) > limits.max_nodes)
        if role != 'association' and ref not in active:
            active.add(ref)
            pending.append(ref)

    while pending:
        owner = pending.popleft()
        fact = visible[owner].fact
        upstream = fact.provenance.upstream
        width = sum(max(1, len(edge.basis)) for edge in upstream)
        if getattr(fact, 'order', None) is not None:
            width += 1
        _limit(width > limits.max_width)
        adjacency[owner] = fact.provenance.dependencies
        for ordinal, edge in enumerate(upstream):
            assertions.append(LineageAssertion(owner, ordinal, edge))
            if edge.relationship == 'fulfills_order':
                associations.append(Association(owner, 'upstream', ordinal, edge.target))
                endpoint(owner, edge.target, 'association', ordinal)
            else:
                for index, parent in enumerate(edge.dependencies):
                    basis = index if edge.relationship == 'independent_confirmation' else None
                    dependencies.append(Dependency(owner, ordinal, basis, parent))
                    endpoint(owner, parent, 'dependency', ordinal, basis)
                if edge.relationship == 'independent_confirmation':
                    endpoint(owner, edge.target, 'confirmation_target', ordinal)
        # The administration's order field is an association even without an edge.
        order = getattr(fact, 'order', None)
        if order is not None:
            associations.append(Association(owner, 'order', 0, order))
            endpoint(owner, order, 'association', 0)

    # Iterative leaf-first topological reduction detects all dependency cycles,
    # including self-links; confirmation validation links are NOT evidence edges.
    remaining = {ref: sum(parent in active for parent in parents)
                 for ref, parents in adjacency.items()}
    children = {ref: [] for ref in active}
    for child, parents in adjacency.items():
        for parent in parents:
            if parent in active:
                children[parent].append(child)
    ready = deque(ref for ref in adjacency if remaining[ref] == 0)
    closures, depths, entries = {}, {}, 0
    while ready:
        ref = ready.popleft()
        closure, depth = {ref}, 0
        for parent in adjacency[ref]:
            closure.update(closures.get(parent, (parent,)))
            depth = max(depth, 1 + depths.get(parent, 0))
            _limit(entries + len(closure) > limits.max_ancestry_entries)
        _limit(depth > limits.max_depth)
        entries += len(closure)
        _limit(entries > limits.max_ancestry_entries)
        closures[ref], depths[ref] = frozenset(closure), depth
        for child in children[ref]:
            remaining[child] -= 1
            if remaining[child] == 0:
                ready.append(child)
    if len(closures) != len(active):
        raise StorageIntegrityError('circular retained dependency lineage')

    # Roles may overlap, but a validation target is never an evidence parent
    # merely because it was visited. Propagate roles over dependency edges only.
    for assertion in assertions:
        if assertion.edge.relationship == 'independent_confirmation':
            for ref in closures.get(assertion.edge.target, ()):
                if ref in roles:
                    roles[ref].add('confirmation_validation')
    for ref in closures[reference]:
        if ref in roles:
            roles[ref].add('evidence')
    origins = {ref: visible[ref].fact.origin for ref in active}
    confirmations = []
    for owner in adjacency:
        fact = visible[owner].fact
        try:
            validate_origin(fact.origin, fact.provenance, origins)
        except ValueError:
            raise StorageIntegrityError('retained lineage does not preserve origin') from None
        if fact.origin in ('observed', 'reported') and any(
                origins.get(ref, {'inference': 'inferred', 'derived_value': 'derived'}.get(ref.kind))
                in ('derived', 'inferred') for ref in closures[owner] - {owner}):
            raise StorageIntegrityError('retained transitive lineage does not preserve origin')
        for ordinal, edge in enumerate(fact.provenance.upstream):
            if edge.relationship != 'independent_confirmation':
                continue
            target_closure = closures.get(edge.target, frozenset((edge.target,)))
            involved = set(target_closure)
            for basis in edge.basis:
                basis_closure = closures.get(basis, frozenset((basis,)))
                if _shared(basis_closure, target_closure):
                    raise StorageIntegrityError('retained confirmation has dependent evidence')
                involved.update(basis_closure)
                if basis in visible and _instant_key(visible[basis].fact.provenance.recorded_at) > _instant_key(fact.provenance.recorded_at):
                    raise StorageIntegrityError('retained confirmation basis occurs after confirmation')
            if edge.target in visible and _instant_key(fact.provenance.recorded_at) <= _instant_key(visible[edge.target].fact.provenance.recorded_at):
                raise StorageIntegrityError('retained confirmation does not follow target')
            limitations = ['independence_not_established']
            if any(ref not in visible for ref in involved):
                limitations.append('unresolved_confirmation_ancestry')
            if any(visible[ref].fact.provenance.lineage != 'complete' or
                   visible[ref].fact.provenance.limitations for ref in involved if ref in visible):
                limitations.append('limited_declared_provenance')
            confirmations.append(ConfirmationAssessment(owner, ordinal, 'unknown', tuple(limitations)))

    sequence = lambda ref: visible[ref].ingestion.ingestion_sequence
    ordered = sorted(roles, key=sequence)
    assertions.sort(key=lambda item: (sequence(item.owner), item.ordinal))
    dependencies.sort(key=lambda item: (sequence(item.owner), item.ordinal,
                                        -1 if item.basis_ordinal is None else item.basis_ordinal))
    associations.sort(key=lambda item: (sequence(item.owner), item.field, item.ordinal))
    unresolved.sort(key=lambda item: (_key(item.reference), item.role, _key(item.owner),
                                      item.ordinal, -1 if item.basis_ordinal is None else item.basis_ordinal))
    confirmations.sort(key=lambda item: (sequence(item.owner), item.ordinal))
    return LineageResult(reference, history.target, history.cutoff,
        tuple(ResolvedNode(visible[ref], tuple(sorted(roles[ref]))) for ref in ordered),
        tuple(assertions), tuple(dependencies), tuple(associations), tuple(unresolved),
        tuple(ProvenanceDisclosure(ref, visible[ref].fact.provenance.lineage,
                                   visible[ref].fact.provenance.limitations) for ref in ordered),
        tuple(confirmations), 'partial' if unresolved else 'complete_for_declared_visible_graph',
        tuple((ref, closures[ref]) for ref in sorted(closures, key=sequence)))
