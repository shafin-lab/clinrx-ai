"""Prototype value objects; validation is structural, not clinical approval."""
from collections.abc import Iterable
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Origin = Literal['observed', 'reported', 'derived', 'inferred']


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', revalidate_instances='always')


class Reference(DomainModel):
    """An exact internal record revision, never a pointer to mutable 'latest'."""
    kind: Text
    id: Text
    version: Text


def require_kind(reference: Reference, *kinds: str) -> None:
    if reference.kind not in kinds:
        raise ValueError(f'reference must identify one of {kinds}')


def ensure_consistent_revisions(records: Iterable[tuple[Reference, DomainModel]]) -> None:
    """Check only supplied content; cross-request uniqueness belongs to storage."""
    seen: dict[Reference, DomainModel] = {}
    for reference, record in records:
        if reference in seen and seen[reference] != record:
            raise ValueError(f'conflicting content for exact revision {reference}')
        seen[reference] = record


class Source(DomainModel):
    namespace: Text
    identifier: Text
    version: Text | None = None  # Explicitly unknown when unavailable.
    channel: Literal['measurement', 'external_record', 'clinician', 'patient', 'system']


class ClinicalTime(DomainModel):
    event: AwareDatetime | None = None
    recorded: AwareDatetime | None = None
    effective_start: AwareDatetime | None = None
    effective_end: AwareDatetime | None = None
    retrieved: AwareDatetime | None = None
    processed: AwareDatetime | None = None
    precision: Literal['instant', 'day', 'approximate', 'unknown']
    uncertainty: Text | None = None

    @model_validator(mode='after')
    def valid_interval(self):
        if self.effective_end and (not self.effective_start or self.effective_end < self.effective_start):
            raise ValueError('effective interval requires an ordered start and end')
        return self


class LineageEdge(DomainModel):
    target: Reference
    relationship: Literal[
        'copied_from', 'derived_from', 'calculated_from',
        'independent_confirmation', 'fulfills_order',
    ]
    # Confirmation records a separate assertion, not a promotion of the target.
    basis: tuple[Reference, ...] = ()
    rationale: Text | None = None

    @model_validator(mode='after')
    def relationship_semantics(self):
        if self.relationship == 'independent_confirmation':
            require_kind(self.target, 'inference', 'derived_value')
            if not self.basis or not self.rationale:
                raise ValueError('independent confirmation requires clinical basis and rationale')
            if self.target in self.basis or len(set(self.basis)) != len(self.basis):
                raise ValueError('confirmation basis cannot repeat or include its target')
            for reference in self.basis:
                require_kind(reference, 'observation')
        elif self.basis:
            raise ValueError('separate basis is only used for independent confirmation')
        if self.relationship == 'fulfills_order':
            require_kind(self.target, 'medication_order')
        return self

    @property
    def dependencies(self) -> tuple[Reference, ...]:
        if self.relationship == 'independent_confirmation':
            return self.basis
        if self.relationship == 'fulfills_order':
            return ()  # An intended order is not evidence of actual delivery.
        return (self.target,)


class Provenance(DomainModel):
    source: Source
    actor: Text
    recorded_at: AwareDatetime
    upstream: tuple[LineageEdge, ...] = ()
    lineage: Literal['complete', 'incomplete', 'unknown']
    limitations: tuple[Text, ...] = ()

    @property
    def dependencies(self) -> tuple[Reference, ...]:
        return tuple(dict.fromkeys(ref for edge in self.upstream for ref in edge.dependencies))

    @model_validator(mode='after')
    def disclose_limits(self):
        if self.lineage != 'complete' and not self.limitations:
            raise ValueError('incomplete or unknown lineage requires limitations')
        if len(set(self.upstream)) != len(self.upstream):
            raise ValueError('duplicate provenance edges')
        return self


class ContextTarget(DomainModel):
    patient_id: Text
    encounter_id: Text | None = None
    longitudinal_context_id: Text | None = None

    @model_validator(mode='after')
    def explicit_context(self):
        if (self.encounter_id is None) == (self.longitudinal_context_id is None):
            raise ValueError('select exactly one encounter or longitudinal context')
        return self


class IdentityVerification(DomainModel):
    status: Literal['verified', 'unresolved']
    method: Text
    verifier: Text
    assessed_at: AwareDatetime
    source: Source
    ambiguity: Text | None = None

    @model_validator(mode='after')
    def consistent_assertion(self):
        if self.status == 'verified' and self.ambiguity:
            raise ValueError('ambiguous binding cannot be verified')
        if self.status == 'unresolved' and not self.ambiguity:
            raise ValueError('unresolved binding requires a reason')
        return self


class Binding(DomainModel):
    target: ContextTarget
    verification: IdentityVerification


class Unit(DomainModel):
    """Source spelling and an explicit assessment, not a unit-conversion engine."""
    raw: Annotated[str, Field(min_length=1)] | None = None
    status: Literal['unresolved', 'assessed', 'normalized']
    system: Text | None = None
    code: Text | None = None
    limitation: Text | None = None

    @model_validator(mode='after')
    def explicit_meaning(self):
        if self.status == 'unresolved':
            if not self.limitation or self.system or self.code:
                raise ValueError('unresolved units need a limitation, not an asserted code')
        elif not self.system or not self.code:
            raise ValueError('assessed/normalized units require a system and code')
        return self


class Quantity(DomainModel):
    value: Annotated[Decimal, Field(allow_inf_nan=False)]
    unit: Unit


class ClinicalValue(DomainModel):
    status: Literal['known', 'unknown', 'missing', 'not_measured', 'not_applicable']
    value: Quantity | Text | StrictBool | None = None
    reason: Text | None = None

    @model_validator(mode='after')
    def missing_is_not_negative(self):
        if (self.status == 'known') != (self.value is not None):
            raise ValueError('only a known value may carry a result')
        if self.status != 'known' and not self.reason:
            raise ValueError('unavailable value requires a reason')
        return self


def validate_origin(origin: Origin, provenance: Provenance, origins: dict[Reference, Origin]) -> None:
    """Prevent declared dependencies from relabeling copied or inferred content."""
    for edge in provenance.upstream:
        target_origin = origins.get(edge.target)
        if target_origin is None:
            target_origin = {'inference': 'inferred', 'derived_value': 'derived'}.get(edge.target.kind)
        if edge.relationship == 'copied_from' and target_origin in ('derived', 'inferred'):
            if origin != target_origin:
                raise ValueError('copied information must retain its derived/inferred origin')
        if origin in ('observed', 'reported'):
            for ref in edge.dependencies:
                parent_origin = origins.get(ref)
                if parent_origin is None:
                    parent_origin = {'inference': 'inferred', 'derived_value': 'derived'}.get(ref.kind)
                if parent_origin in ('derived', 'inferred'):
                    raise ValueError('dependent derived/inferred content cannot become an observation or report')


class LineageNode(DomainModel):
    reference: Reference
    origin: Origin
    provenance: Provenance


class LineageGraph(DomainModel):
    """Bounded execution lineage. Neither an assertion nor disjoint IDs prove independence."""
    nodes: tuple[LineageNode, ...]

    def _ancestry(self, reference: Reference) -> set[Reference]:
        nodes = {node.reference: node for node in self.nodes}
        result, pending = set(), [reference]
        while pending:
            current = pending.pop()
            if current not in result:
                result.add(current)
                if current in nodes:
                    pending.extend(nodes[current].provenance.dependencies)
        return result

    @model_validator(mode='after')
    def coherent_lineage(self):
        ensure_consistent_revisions((node.reference, node) for node in self.nodes)
        nodes = {node.reference: node for node in self.nodes}
        done, visiting = set(), set()

        def visit(ref):
            if ref in visiting:
                raise ValueError('circular execution lineage')
            if ref in done or ref not in nodes:
                return
            visiting.add(ref)
            for parent in nodes[ref].provenance.dependencies:
                visit(parent)
            visiting.remove(ref)
            done.add(ref)

        for ref in nodes:
            visit(ref)
        origins = {ref: node.origin for ref, node in nodes.items()}
        for node in nodes.values():
            validate_origin(node.origin, node.provenance, origins)
            if node.origin in ('observed', 'reported'):
                for ancestor in self._ancestry(node.reference) - {node.reference}:
                    if origins.get(ancestor) in ('derived', 'inferred'):
                        raise ValueError('transitive lineage cannot erase inferred/derived origin')
            for edge in node.provenance.upstream:
                if edge.relationship == 'independent_confirmation':
                    for basis in edge.basis:
                        if self._ancestry(basis) & self._ancestry(edge.target):
                            raise ValueError('confirmation depends on the assertion it claims to confirm independently')
                    target = nodes.get(edge.target)
                    if target and node.provenance.recorded_at <= target.provenance.recorded_at:
                        raise ValueError('subsequent confirmation must follow the earlier assertion')
                    for basis in edge.basis:
                        if basis in nodes and nodes[basis].provenance.recorded_at > node.provenance.recorded_at:
                            raise ValueError('confirmation basis is not yet available')
        return self

    def support_relationship(self, left: Reference, right: Reference) -> Literal['dependent', 'unknown']:
        return 'dependent' if self._ancestry(left) & self._ancestry(right) else 'unknown'
