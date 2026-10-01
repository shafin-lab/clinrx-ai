"""Synthetic weight execution contracts only: no storage, transactions or release.

Evidence is supplied by trusted readers. Digests bind retained representations;
they do not authenticate reads. A valid envelope does not establish a DB commit.
"""
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, field_validator, model_validator

from app.execution.weight_trend import (
    RecordedWeightComparison, WeightTrendExclusion, WeightTrendSelectionIssue,
    WeightTrendSelectionPolicy, WeightTrendSelectionResult, _instant,
    compare_recorded_weights,
)
from app.models.clinical.common import ContextTarget, DomainModel, LineageEdge, Reference, Text
from app.models.clinical.facts import ClinicalInference
from app.models.clinical.governance import Digest, OutputTarget, ReleaseDecision
from app.persistence.errors import StorageIntegrityError
from app.persistence.lineage import LineageResult, UnresolvedReference
from app.persistence.mapping import canonical_payload, validate_fact
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff

FINAL_RECHECK_POLICY = Reference(kind='final_recheck_policy', id='WeightTrendFinalRecheckPolicy', version='1')
FINAL_RECHECK_IMPLEMENTATION = Reference(kind='software', id='WeightTrendFinalRecheck', version='1')
EXECUTION_IMPLEMENTATION = Reference(kind='software', id='WeightTrendExecutionContract', version='1')
_BENIGN = {'unrelated_fact', 'unrelated_concept', 'outside_comparison_window'}
_GLOBAL_ISSUES = {'insufficient_eligible_inputs', 'ambiguous_eligible_inputs', 'invalid_measurement_order'}


def _retained_digest(model):
    return sha256(canonical_payload(model).encode('utf-8')).hexdigest()


def _storage_fields(value):
    # Existing storage metadata does not revalidate model_copy/construct instances.
    return value.model_dump(warnings=False) if isinstance(value, (RepositoryCutoff, IngestionMetadata)) else value


def _key(ref):
    return ref.kind, ref.id, ref.version


def _pair(refs):
    return len(refs) == 2 and all(r.kind == 'observation' for r in refs) and refs[0].id != refs[1].id


class WeightTrendSelectionManifest(DomainModel):
    """Compact Phase 1 result; policy content pins parameters as well as version."""
    target: ContextTarget
    policy: WeightTrendSelectionPolicy
    cutoff: RepositoryCutoff
    selected: tuple[Reference, ...] = ()
    selected_payload_digests: tuple[Digest, ...] = ()
    exclusions: tuple[WeightTrendExclusion, ...] = ()
    issues: tuple[WeightTrendSelectionIssue, ...] = ()

    _cutoff_fields = field_validator('cutoff', mode='before')(_storage_fields)

    @property
    def successful(self):
        return not self.issues

    @model_validator(mode='after')
    def coherent(self):
        if self.target.encounter_id is None:
            raise ValueError('weight execution requires an encounter')
        if self.issues:
            if self.selected or self.selected_payload_digests:
                raise ValueError('unsuccessful selection cannot supply a pair')
        elif not _pair(self.selected) or len(self.selected_payload_digests) != 2:
            raise ValueError('successful selection requires two distinct exact observations and digests')
        excluded = tuple(e.reference for e in self.exclusions)
        if (len({(r.kind, r.id) for r in excluded}) != len(excluded)
                or len(set(self.issues)) != len(self.issues)):
            raise ValueError('duplicate selection disclosures')
        if {(r.kind, r.id) for r in self.selected} & {(r.kind, r.id) for r in excluded}:
            raise ValueError('selected and excluded stable measurements overlap')
        if sum(issue.code in _GLOBAL_ISSUES for issue in self.issues) > 1:
            raise ValueError('selection cannot have contradictory cardinality/order issues')
        blocking = {(e.reference, e.reason) for e in self.exclusions if e.reason not in _BENIGN}
        disclosed = set()
        for issue in self.issues:
            if issue.code in _GLOBAL_ISSUES:
                if issue.reference is not None:
                    raise ValueError('cardinality/order issue must describe the selection')
            elif issue.reference is None or issue.reference.kind != 'observation':
                raise ValueError('input issue requires an exact observation')
            else:
                disclosed.add((issue.reference, issue.code))
        if blocking != disclosed:
            raise ValueError('blocking exclusions and input issues disagree')
        return self


def weight_trend_selection_manifest(selection: WeightTrendSelectionResult) -> WeightTrendSelectionManifest:
    selection = WeightTrendSelectionResult.model_validate(selection)
    return WeightTrendSelectionManifest(target=selection.target, policy=selection.policy, cutoff=selection.cutoff,
        selected=tuple(f.reference for f in selection.selected),
        selected_payload_digests=tuple(_retained_digest(f) for f in selection.selected),
        exclusions=selection.exclusions, issues=selection.issues)


class WeightTrendInferenceTerminalCheck(DomainModel):
    """Supplied lookup at the final cutoff. None means unavailable, never current."""
    target: ContextTarget
    cutoff: RepositoryCutoff
    consumed: Reference
    terminal: Reference | None

    _cutoff_fields = field_validator('cutoff', mode='before')(_storage_fields)

    @model_validator(mode='after')
    def coherent(self):
        if self.target.encounter_id is None or self.consumed.kind != 'inference':
            raise ValueError('terminal check requires an encounter and inference')
        if self.terminal and (self.terminal.kind, self.terminal.id) != (self.consumed.kind, self.consumed.id):
            raise ValueError('terminal check must name the consumed inference family')
        return self

    @property
    def status(self):
        return 'unavailable' if self.terminal is None else 'current' if self.terminal == self.consumed else 'superseded'


class WeightTrendFinalRecheck(DomainModel):
    policy: Reference = FINAL_RECHECK_POLICY
    implementation: Reference = FINAL_RECHECK_IMPLEMENTATION
    original_selected: tuple[Reference, ...]
    original_payload_digests: tuple[Digest, ...]
    final: WeightTrendSelectionManifest
    inference_terminal: WeightTrendInferenceTerminalCheck

    @model_validator(mode='after')
    def coherent(self):
        if self.policy != FINAL_RECHECK_POLICY or self.implementation != FINAL_RECHECK_IMPLEMENTATION:
            raise ValueError('unsupported final recheck version')
        if not _pair(self.original_selected) or len(self.original_payload_digests) != 2:
            raise ValueError('recheck requires an original successful pair')
        if (self.inference_terminal.target != self.final.target or
                canonical_payload(self.inference_terminal.cutoff) != canonical_payload(self.final.cutoff)):
            raise ValueError('terminal check and final selection must share scope and cutoff')
        originals = dict(zip(self.original_selected, self.original_payload_digests))
        if any(ref in originals and originals[ref] != digest
               for ref, digest in zip(self.final.selected, self.final.selected_payload_digests)):
            raise ValueError('contradictory retained representation for an exact reference')
        return self

    @property
    def reasons(self):
        reasons = []
        if not self.final.successful:
            reasons.append('final_selection_failed')
        elif self.final.selected != self.original_selected:
            reasons.append('selected_exact_references_changed')
        if self.inference_terminal.status != 'current':
            reasons.append('inference_' + self.inference_terminal.status)
        return tuple(reasons)

    @property
    def outcome(self):
        if any(r != 'inference_unavailable' for r in self.reasons):
            return 'materially_changed'
        return 'unavailable' if self.reasons else 'unchanged'


def assess_weight_trend_final_recheck(*, original: WeightTrendSelectionResult,
                                     final: WeightTrendSelectionResult,
                                     inference_terminal: WeightTrendInferenceTerminalCheck) -> WeightTrendFinalRecheck:
    """Pure comparison of supplied results; never query latest or create a decision."""
    original = WeightTrendSelectionResult.model_validate(original)
    final = WeightTrendSelectionResult.model_validate(final)
    inference_terminal = WeightTrendInferenceTerminalCheck.model_validate(inference_terminal)
    before, after = weight_trend_selection_manifest(original), weight_trend_selection_manifest(final)
    if not before.successful:
        raise ValueError('final recheck requires an original successful selection')
    if (before.target != after.target or canonical_payload(before.policy) != canonical_payload(after.policy)
            or before.cutoff.repository_id != after.cutoff.repository_id
            or after.cutoff.fact_watermark < before.cutoff.fact_watermark):
        raise ValueError('recheck must preserve scope and selection policy on a later repository prefix')
    retained = dict(zip(before.selected, before.selected_payload_digests))
    if any(ref in retained and retained[ref] != digest
           for ref, digest in zip(after.selected, after.selected_payload_digests)):
        raise StorageIntegrityError('contradictory retained weight evidence')
    return WeightTrendFinalRecheck(original_selected=before.selected,
        original_payload_digests=before.selected_payload_digests, final=after, inference_terminal=inference_terminal)


class WeightTrendLineageNodeWitness(DomainModel):
    reference: Reference
    ingestion: IngestionMetadata
    payload_digest: Digest
    roles: tuple[Literal['evidence'], ...]
    ancestry: tuple[Reference, ...]
    lineage: Literal['complete', 'incomplete', 'unknown']
    limitations: tuple[Text, ...]

    _ingestion_fields = field_validator('ingestion', mode='before')(_storage_fields)

    @field_validator('ancestry')
    @classmethod
    def ordered_ancestry(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('duplicate ancestry reference')
        return tuple(sorted(value, key=_key))

    @model_validator(mode='after')
    def coherent(self):
        if self.roles != ('evidence',) or self.reference not in self.ancestry:
            raise ValueError('weight lineage requires self-inclusive evidence ancestry')
        if self.lineage != 'complete' and not self.limitations:
            raise ValueError('limited lineage requires disclosures')
        return self


class WeightTrendLineageWitness(DomainModel):
    """V1 two-input declared graph; node bodies remain in immutable fact storage."""
    root: Reference
    target: ContextTarget
    cutoff: RepositoryCutoff
    declarations: tuple[LineageEdge, ...]
    nodes: tuple[WeightTrendLineageNodeWitness, ...]
    coverage: Literal['complete_for_declared_visible_graph', 'partial']
    unresolved: tuple[UnresolvedReference, ...] = ()

    _cutoff_fields = field_validator('cutoff', mode='before')(_storage_fields)

    @field_validator('unresolved')
    @classmethod
    def ordered_unresolved(cls, value):
        return tuple(sorted(value, key=lambda item: (item.ordinal, _key(item.reference))))

    @property
    def direct_dependencies(self):
        return tuple(edge.target for edge in self.declarations)

    @model_validator(mode='after')
    def coherent(self):
        if self.root.kind != 'inference' or self.target.encounter_id is None:
            raise ValueError('weight lineage requires a scoped inference')
        refs = self.direct_dependencies
        if not _pair(refs) or any(edge.relationship != 'derived_from' for edge in self.declarations):
            raise ValueError('weight lineage requires two declared observation inputs')
        nodes = {n.reference: n for n in self.nodes}
        sequences = [n.ingestion.ingestion_sequence for n in self.nodes]
        if len(nodes) != len(self.nodes) or len(set(sequences)) != len(sequences):
            raise ValueError('duplicate lineage node or ingestion position')
        if self.root not in nodes or set(nodes) - {self.root, *refs}:
            raise ValueError('weight lineage node membership mismatch')
        if sequences != sorted(sequences):
            raise ValueError('lineage nodes must preserve ingestion order')
        for node in self.nodes:
            if (node.ingestion.repository_id != self.cutoff.repository_id
                    or node.ingestion.ingestion_sequence > self.cutoff.fact_watermark):
                raise ValueError('lineage node outside retained prefix')
            expected = {self.root, *refs} if node.reference == self.root else {node.reference}
            if set(node.ancestry) != expected:
                raise ValueError('lineage ancestry mismatch')
        missing = tuple((i, r) for i, r in enumerate(refs) if r not in nodes)
        actual = []
        for item in self.unresolved:
            if (item.owner != self.root or item.role != 'dependency' or item.basis_ordinal is not None
                    or item.reason != 'not_resolvable_in_scope_at_cutoff'):
                raise ValueError('unexpected unresolved weight lineage disclosure')
            actual.append((item.ordinal, item.reference))
        if len(set(actual)) != len(actual) or set(actual) != set(missing):
            raise ValueError('unresolved disclosures disagree with missing nodes')
        if self.coverage != ('partial' if missing else 'complete_for_declared_visible_graph'):
            raise ValueError('lineage coverage disagrees with retained nodes')
        return self


def weight_trend_lineage_witness(lineage: LineageResult) -> WeightTrendLineageWitness:
    """Project actual supplied resolution; reject rather than discard extra structure."""
    if lineage.associations or lineage.confirmations:
        raise ValueError('unsupported weight lineage structure')
    ancestry = dict(lineage.ancestry)
    if len(ancestry) != len(lineage.ancestry):
        raise ValueError('duplicate lineage ancestry entry')
    facts = tuple(validate_fact(n.stored.fact) for n in lineage.nodes)
    if any(f.binding.target != lineage.target for f in facts):
        raise ValueError('lineage payload scope mismatch')
    roots = [f for f in facts if f.reference == lineage.reference]
    if len(roots) != 1 or not isinstance(roots[0], ClinicalInference):
        raise ValueError('weight lineage root unavailable')
    declarations = roots[0].provenance.upstream
    refs = tuple(e.target for e in declarations)
    if roots[0].inputs != refs or any(f.provenance.upstream for f in facts if f.reference != lineage.reference):
        raise ValueError('weight lineage payload dependencies mismatch')
    if tuple((a.owner, a.ordinal, a.edge) for a in lineage.assertions) != tuple(
            (lineage.reference, i, edge) for i, edge in enumerate(declarations)):
        raise ValueError('resolved declarations mismatch')
    if tuple((d.owner, d.ordinal, d.basis_ordinal, d.source) for d in lineage.dependencies) != tuple(
            (lineage.reference, i, None, ref) for i, ref in enumerate(refs)):
        raise ValueError('resolved dependencies mismatch')
    if set(ancestry) != {f.reference for f in facts} or tuple(
            (p.reference, p.lineage, p.limitations) for p in lineage.provenance) != tuple(
            (f.reference, f.provenance.lineage, f.provenance.limitations) for f in facts):
        raise ValueError('resolved ancestry or provenance disclosures mismatch')
    return WeightTrendLineageWitness(root=lineage.reference, target=lineage.target, cutoff=lineage.cutoff,
        declarations=declarations, coverage=lineage.coverage, unresolved=lineage.unresolved,
        nodes=tuple(WeightTrendLineageNodeWitness(reference=f.reference, ingestion=n.stored.ingestion,
            payload_digest=_retained_digest(f), roles=n.roles, ancestry=tuple(ancestry[f.reference]),
            lineage=f.provenance.lineage, limitations=f.provenance.limitations)
            for f, n in zip(facts, lineage.nodes)))


class WeightTrendExecutionIssue(DomainModel):
    """Only bounded codes/stages; no exception text, SQL, values or stack traces."""
    stage: Literal['final_recheck', 'governance', 'execution_persistence', 'transaction_commit', 'recovery']
    code: Literal['invalid_contract', 'integrity_failure', 'content_conflict', 'storage_failure',
                  'commit_outcome_unknown', 'internal_failure']


class WeightTrendExecutionRecord(DomainModel):
    """Future durable envelope, not evidence that persistence/commit happened."""
    execution_id: UUID
    execution_type: Literal['synthetic_weight_trend'] = 'synthetic_weight_trend'
    execution_version: Literal['1'] = '1'
    payload_version: Literal[1] = 1
    implementation: Reference = EXECUTION_IMPLEMENTATION
    target: OutputTarget
    actor: Text
    original: WeightTrendSelectionManifest
    comparison: RecordedWeightComparison
    inference: Reference
    lineage: WeightTrendLineageWitness | None = None
    final_recheck: WeightTrendFinalRecheck | None = None
    decision: ReleaseDecision | None = None
    issue: WeightTrendExecutionIssue | None = None
    started_at: AwareDatetime
    finalized_at: AwareDatetime

    @field_validator('payload_version', mode='before')
    @classmethod
    def supported_payload(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('unsupported execution payload version')
        return value

    @property
    def repository_id(self):
        return self.original.cutoff.repository_id

    @property
    def disposition(self):
        return 'failed_operationally' if self.issue else 'completed_' + self.decision.outcome

    @model_validator(mode='after')
    def coherent(self):
        if (self.decision is None) == (self.issue is None):
            raise ValueError('exactly one decision or operational issue is required')
        if self.implementation != EXECUTION_IMPLEMENTATION:
            raise ValueError('unsupported execution implementation')
        if _instant(self.finalized_at) < _instant(self.started_at):
            raise ValueError('finalization cannot precede execution start')
        if not self.original.successful or self.original.target != self.target.context or self.inference.kind != 'inference':
            raise ValueError('execution requires the original successful scoped evidence')
        refs = (self.comparison.earlier_reference, self.comparison.later_reference)
        if refs != self.original.selected:
            raise ValueError('comparison must preserve original selection order')
        policy = self.original.policy
        if any(not _instant(policy.window_start) <= _instant(t) < _instant(policy.window_end)
               for t in (self.comparison.earlier_event, self.comparison.later_event)):
            raise ValueError('comparison outside original selection window')
        if self.lineage:
            if (self.lineage.root != self.inference or self.lineage.target != self.target.context
                    or self.lineage.cutoff.repository_id != self.repository_id
                    or self.lineage.cutoff.fact_watermark <= self.original.cutoff.fact_watermark
                    or self.lineage.direct_dependencies != self.original.selected):
                raise ValueError('lineage differs from original execution evidence')
            original_digests = dict(zip(self.original.selected, self.original.selected_payload_digests))
            for node in self.lineage.nodes:
                if node.reference == self.inference:
                    if node.ingestion.ingestion_sequence <= self.original.cutoff.fact_watermark:
                        raise ValueError('inference must follow original input prefix')
                elif (node.ingestion.ingestion_sequence > self.original.cutoff.fact_watermark
                      or node.payload_digest != original_digests[node.reference]):
                    raise ValueError('lineage observation differs from original input prefix')
        if self.final_recheck:
            check, final = self.final_recheck, self.final_recheck.final
            if (check.original_selected != self.original.selected
                    or check.original_payload_digests != self.original.selected_payload_digests
                    or check.inference_terminal.consumed != self.inference or final.target != self.target.context
                    or canonical_payload(final.policy) != canonical_payload(policy)
                    or final.cutoff.repository_id != self.repository_id
                    or final.cutoff.fact_watermark < (self.lineage.cutoff.fact_watermark if self.lineage else self.original.cutoff.fact_watermark)):
                raise ValueError('final recheck differs from execution request')
        if self.decision:
            if self.lineage is None or self.final_recheck is None:
                raise ValueError('decision requires lineage and final recheck evidence')
            d, a = self.decision, self.decision.assessment
            if d.actor != self.actor or a.target != self.target or a.review.candidate.snapshot.binding.target != self.target.context:
                raise ValueError('decision actor or request differs from execution')
            if not _instant(self.started_at) <= _instant(a.assessed_at) <= _instant(d.at) <= _instant(self.finalized_at):
                raise ValueError('decision must occur within execution times')
            facts = a.review.candidate.snapshot.facts
            expected = (*self.original.selected, self.inference)
            present = tuple(f.reference for f in facts)
            if present != tuple(r for r in expected if r in present):
                raise ValueError('decision snapshot differs from consumed evidence')
            partial = present != expected or self.lineage.coverage == 'partial'
            if partial and (d.outcome != 'withheld' or a.state.freshness.adequate):
                raise ValueError('partial lineage or snapshot cannot support release')
            retained = dict(zip(self.original.selected, self.original.selected_payload_digests))
            retained.update((n.reference, n.payload_digest) for n in self.lineage.nodes)
            if any(retained[f.reference] != _retained_digest(f) for f in facts):
                raise ValueError('decision snapshot contradicts retained evidence')
            witness_nodes = {n.reference: n for n in self.lineage.nodes}
            for fact in facts:
                node = witness_nodes.get(fact.reference)
                if node is not None and (node.lineage, node.limitations) != (
                        fact.provenance.lineage, fact.provenance.limitations):
                    raise ValueError('lineage witness provenance contradicts retained evidence')
            observations = tuple(f for f in facts if f.reference != self.inference)
            if len(observations) == 2:
                original = WeightTrendSelectionResult(target=self.original.target, policy=policy,
                    cutoff=self.original.cutoff, selected=observations, exclusions=self.original.exclusions)
                if (canonical_payload(weight_trend_selection_manifest(original)) != canonical_payload(self.original)
                        or canonical_payload(compare_recorded_weights(original)) != canonical_payload(self.comparison)):
                    raise ValueError('decision snapshot contradicts original comparison')
            else:
                # Missing bodies are not fabricated to record an unavailable/withheld decision.
                for fact in observations:
                    prefix = 'earlier' if fact.reference == self.original.selected[0] else 'later'
                    encoded = fact.model_dump(mode='json')
                    comparison = self.comparison.model_dump(mode='json')
                    if (not isinstance(encoded['value']['value'], dict)
                            or encoded['value']['value'].get('value') != comparison[prefix + '_kg']
                            or encoded['time']['event'] != comparison[prefix + '_event']):
                        raise ValueError('partial snapshot contradicts original comparison')
            root = next((f for f in facts if f.reference == self.inference), None)
            if root is not None and (not isinstance(root, ClinicalInference)
                    or root.inputs != self.original.selected
                    or root.provenance.upstream != self.lineage.declarations):
                raise ValueError('decision inference contradicts declared lineage')
            if self.final_recheck.outcome != 'unchanged':
                if d.outcome != 'withheld' or a.state.freshness.adequate:
                    raise ValueError('changed or unavailable final context cannot support release')
                if self.final_recheck.outcome == 'materially_changed' and not a.state.freshness.material_change:
                    raise ValueError('decision must retain the established material change')
        return self
