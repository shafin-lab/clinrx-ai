"""Pure synthetic creatinine execution evidence; no persistence or workflow.

Supplied contracts establish consistency, not authentic reads, specimen identity,
transaction protection or completion. D4 must obtain and replay actual retained data.
"""
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictStr, field_validator, model_validator

from app.execution.creatinine_trend import (
    CreatinineTrendExclusion, CreatinineTrendSelectionIssue, CreatinineTrendSelectionPolicy,
    CreatinineTrendSelectionResult, RecordedCreatinineComparison, _instant,
    build_creatinine_trend_inference, compare_recorded_creatinine,
)
from app.models.clinical.common import ContextTarget, DomainModel, LineageEdge, Reference, Text
from app.models.clinical.facts import ClinicalInference
from app.models.clinical.governance import Digest, OutputTarget, ReleaseDecision
from app.persistence.errors import StorageIntegrityError
from app.persistence.lineage import LineageResult, UnresolvedReference
from app.persistence.mapping import canonical_payload, validate_fact
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff

FINAL_RECHECK_POLICY = Reference(kind='final_recheck_policy', id='CreatinineTrendFinalRecheckPolicy', version='1')
FINAL_RECHECK_IMPLEMENTATION = Reference(kind='software', id='CreatinineTrendFinalRecheck', version='1')
EXECUTION_IMPLEMENTATION = Reference(kind='software', id='CreatinineTrendExecutionContract', version='1')
WORKFLOW_ASSESSOR = 'SyntheticCreatinineProtectedExecution/v1'
FINAL_CONTEXT_ASSESSOR = 'SyntheticCreatinineFinalContext/v1'
_BENIGN = {'unrelated_fact', 'unrelated_concept', 'outside_sample_window'}
_GLOBAL = {'insufficient_eligible_inputs', 'ambiguous_eligible_inputs', 'invalid_measurement_order'}
PositiveValue = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


def _digest(model):
    return sha256(canonical_payload(model).encode('utf-8')).hexdigest()


def _storage_fields(value):
    if isinstance(value, (RepositoryCutoff, IngestionMetadata)):
        value = value.model_dump(warnings=False)
    if isinstance(value, dict) and 'payload_version' in value and type(value['payload_version']) is not int:
        raise ValueError('storage payload version must be an integer')
    return value


def _key(ref):
    return ref.kind, ref.id, ref.version


def _pair(refs):
    return len(refs) == 2 and all(r.kind == 'observation' for r in refs) and refs[0].id != refs[1].id


class CreatinineTrendSampleIdentity(DomainModel):
    """Exact retained source key, not authenticated specimen identity."""
    namespace: Literal['clinrx.synthetic.serum-creatinine']
    identifier: StrictStr

    @field_validator('identifier')
    @classmethod
    def retained_identifier(cls, value):
        if not value or value != value.strip():
            raise ValueError('sample identifier must already satisfy retained Source semantics')
        return value


class CreatinineTrendSelectionManifest(DomainModel):
    version: Literal['1'] = '1'
    target: ContextTarget
    policy: CreatinineTrendSelectionPolicy
    cutoff: RepositoryCutoff
    selected: tuple[Reference, ...] = ()
    selected_payload_digests: tuple[Digest, ...] = ()
    selected_samples: tuple[CreatinineTrendSampleIdentity, ...] = ()
    selected_values: tuple[PositiveValue, ...] = ()
    selected_sample_times: tuple[AwareDatetime, ...] = ()
    exclusions: tuple[CreatinineTrendExclusion, ...] = ()
    issues: tuple[CreatinineTrendSelectionIssue, ...] = ()

    _cutoff = field_validator('cutoff', mode='before')(_storage_fields)

    @property
    def successful(self):
        return not self.issues

    @property
    def comparison(self):
        if not self.successful:
            return None
        a, b = self.selected_values
        return RecordedCreatinineComparison(earlier_reference=self.selected[0], later_reference=self.selected[1],
            earlier_value=a, later_value=b, unit=self.policy.unit,
            earlier_sample_time=self.selected_sample_times[0], later_sample_time=self.selected_sample_times[1],
            direction='increase' if b > a else 'decrease' if b < a else 'unchanged')

    @model_validator(mode='after')
    def coherent(self):
        if self.target.encounter_id is None:
            raise ValueError('creatinine manifest requires an encounter')
        groups = (self.selected, self.selected_payload_digests, self.selected_samples,
                  self.selected_values, self.selected_sample_times)
        if self.issues:
            if any(groups):
                raise ValueError('failed selection cannot fabricate selected evidence')
        else:
            if not _pair(self.selected) or any(len(g) != 2 for g in groups):
                raise ValueError('successful manifest requires two aligned distinct observations')
            if self.selected_samples[0] == self.selected_samples[1]:
                raise ValueError('selected sample identities must differ')
            self.comparison  # Strict positive values and increasing actual sample instants.
            if any(not _instant(self.policy.window_start) <= _instant(t) < _instant(self.policy.window_end)
                   for t in self.selected_sample_times):
                raise ValueError('selected sample outside policy window')
        excluded = {(e.reference.kind, e.reference.id) for e in self.exclusions}
        if len(excluded) != len(self.exclusions) or excluded & {(r.kind, r.id) for r in self.selected}:
            raise ValueError('duplicate terminal family or selected/excluded overlap')
        if any(e.reason != 'unrelated_fact' and e.reference.kind != 'observation' for e in self.exclusions):
            raise ValueError('observation exclusion requires an observation')
        if len(set(self.issues)) != len(self.issues):
            raise ValueError('duplicate selection issue')
        globals_ = [i for i in self.issues if i.code in _GLOBAL]
        if len(globals_) > 1 or (globals_ and self.issues[-1] != globals_[0]):
            raise ValueError('one terminal cardinality/order issue is permitted')
        blocking = [(e.reference, e.reason) for e in self.exclusions if e.reason not in _BENIGN]
        actual = [(i.reference, i.code) for i in self.issues
                  if i.code not in _GLOBAL and i.code != 'duplicate_sample_measurement']
        if blocking != actual:
            raise ValueError('ordered blocking exclusions and eligibility issues disagree')
        duplicate_refs = [i.reference for i in self.issues if i.code == 'duplicate_sample_measurement']
        if duplicate_refs and len(duplicate_refs) < 2:
            raise ValueError('duplicate sample disclosure requires at least two observations')
        # Duplicate issues can exist without exclusions; keep each terminal's issues together.
        seen, last = set(), None
        by_family = {}
        for issue in self.issues:
            ref = issue.reference
            if ref is None:
                continue
            family = (ref.kind, ref.id)
            if family in by_family and by_family[family] != ref:
                raise ValueError('issues contain multiple revisions of a terminal family')
            by_family[family] = ref
            if ref != last:
                if ref in seen:
                    raise ValueError('terminal issue groups must remain contiguous')
                seen.add(ref)
            elif issue.code != 'duplicate_sample_measurement':
                raise ValueError('eligibility issue must precede duplicate-sample issue')
            last = ref
        for e in self.exclusions:
            if (e.reference.kind, e.reference.id) in by_family and by_family[(e.reference.kind, e.reference.id)] != e.reference:
                raise ValueError('issue and exclusion terminal revisions disagree')
            if e.reason in _BENIGN and e.reference in seen:
                raise ValueError('benign exclusion cannot have relevant sample issues')
        canonical_payload(self)
        return self


def creatinine_trend_selection_manifest(selection: CreatinineTrendSelectionResult) -> CreatinineTrendSelectionManifest:
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    return CreatinineTrendSelectionManifest(target=selection.target, policy=selection.policy, cutoff=selection.cutoff,
        selected=tuple(f.reference for f in selection.selected),
        selected_payload_digests=tuple(_digest(f) for f in selection.selected),
        selected_samples=tuple(CreatinineTrendSampleIdentity(namespace=f.provenance.source.namespace,
            identifier=f.provenance.source.identifier) for f in selection.selected),
        selected_values=tuple(f.value.value.value for f in selection.selected),
        selected_sample_times=tuple(f.time.event for f in selection.selected),
        exclusions=selection.exclusions, issues=selection.issues)


class CreatinineTrendLineageNodeWitness(DomainModel):
    reference: Reference
    ingestion: IngestionMetadata
    payload_digest: Digest
    roles: tuple[Literal['evidence'], ...]
    ancestry: tuple[Reference, ...]
    lineage: Literal['complete', 'incomplete', 'unknown']
    limitations: tuple[Text, ...]

    _metadata = field_validator('ingestion', mode='before')(_storage_fields)

    @field_validator('ancestry')
    @classmethod
    def ordered_set(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('duplicate ancestry reference')
        return tuple(sorted(value, key=_key))

    @model_validator(mode='after')
    def coherent(self):
        if self.roles != ('evidence',) or self.reference not in self.ancestry:
            raise ValueError('self-inclusive evidence ancestry required')
        if self.lineage != 'complete' and not self.limitations:
            raise ValueError('limited lineage requires disclosures')
        return self


class CreatinineTrendLineageWitness(DomainModel):
    version: Literal['1'] = '1'
    root: Reference
    target: ContextTarget
    cutoff: RepositoryCutoff
    declarations: tuple[LineageEdge, ...]
    nodes: tuple[CreatinineTrendLineageNodeWitness, ...]
    coverage: Literal['complete_for_declared_visible_graph', 'partial']
    unresolved: tuple[UnresolvedReference, ...] = ()

    _cutoff = field_validator('cutoff', mode='before')(_storage_fields)

    @property
    def direct_dependencies(self):
        return tuple(edge.target for edge in self.declarations)

    @model_validator(mode='after')
    def coherent(self):
        refs = self.direct_dependencies
        if self.root.kind != 'inference' or self.target.encounter_id is None or not _pair(refs):
            raise ValueError('scoped two-observation inference graph required')
        if any(e.relationship != 'derived_from' or e.basis or e.rationale is not None for e in self.declarations):
            raise ValueError('exact two derived_from declarations required')
        nodes = {n.reference: n for n in self.nodes}
        seq = [n.ingestion.ingestion_sequence for n in self.nodes]
        if len(nodes) != len(self.nodes) or seq != sorted(set(seq)):
            raise ValueError('unique lineage nodes in ingestion order required')
        if self.root not in nodes or set(nodes) - {self.root, *refs}:
            raise ValueError('lineage membership differs from declared graph')
        for node in self.nodes:
            if (node.ingestion.repository_id != self.cutoff.repository_id
                    or node.ingestion.ingestion_sequence > self.cutoff.fact_watermark):
                raise ValueError('lineage node outside repository prefix')
            expected = {self.root, *refs} if node.reference == self.root else {node.reference}
            if set(node.ancestry) != expected:
                raise ValueError('lineage ancestry differs')
        missing = [(i, r) for i, r in enumerate(refs) if r not in nodes]
        actual = []
        for item in self.unresolved:
            if (item.owner != self.root or item.role != 'dependency' or item.basis_ordinal is not None
                    or type(item.ordinal) is not int or item.reason != 'not_resolvable_in_scope_at_cutoff'):
                raise ValueError('unexpected unresolved disclosure for observation graph')
            actual.append((item.ordinal, item.reference))
        if actual != missing or self.coverage != ('partial' if missing else 'complete_for_declared_visible_graph'):
            raise ValueError('coverage and ordered unresolved disclosures disagree')
        canonical_payload(self)
        return self


def creatinine_trend_lineage_witness(lineage: LineageResult) -> CreatinineTrendLineageWitness:
    """Project actual supplied resolution; never silently prune an incompatible graph."""
    if not isinstance(lineage, LineageResult):
        raise TypeError('expected LineageResult')
    if lineage.associations or lineage.confirmations:
        raise ValueError('unsupported creatinine graph structure')
    ancestry = dict(lineage.ancestry)
    facts = tuple(validate_fact(n.stored.fact) for n in lineage.nodes)
    if len(ancestry) != len(lineage.ancestry) or any(f.binding.target != lineage.target for f in facts):
        raise ValueError('lineage ancestry or payload scope differs')
    roots = [f for f in facts if f.reference == lineage.reference]
    if len(roots) != 1 or not isinstance(roots[0], ClinicalInference):
        raise ValueError('exact inference root required')
    declarations = roots[0].provenance.upstream
    if roots[0].inputs != tuple(e.target for e in declarations) or any(
            f.provenance.upstream for f in facts if f.reference != lineage.reference):
        raise ValueError('payload dependencies differ')
    if any(type(item.ordinal) is not int for item in (*lineage.assertions, *lineage.dependencies)):
        raise ValueError('lineage declaration ordinals must be exact integers')
    if tuple((a.owner, a.ordinal, a.edge) for a in lineage.assertions) != tuple(
            (lineage.reference, i, e) for i, e in enumerate(declarations)):
        raise ValueError('resolved declarations differ')
    if tuple((d.owner, d.ordinal, d.basis_ordinal, d.source) for d in lineage.dependencies) != tuple(
            (lineage.reference, i, None, e.target) for i, e in enumerate(declarations)):
        raise ValueError('resolved dependencies differ')
    if set(ancestry) != {f.reference for f in facts} or tuple(
            (p.reference, p.lineage, p.limitations) for p in lineage.provenance) != tuple(
            (f.reference, f.provenance.lineage, f.provenance.limitations) for f in facts):
        raise ValueError('resolved ancestry or provenance disclosures differ')
    return CreatinineTrendLineageWitness(root=lineage.reference, target=lineage.target, cutoff=lineage.cutoff,
        declarations=declarations, coverage=lineage.coverage, unresolved=lineage.unresolved,
        nodes=tuple(CreatinineTrendLineageNodeWitness(reference=f.reference, ingestion=n.stored.ingestion,
            payload_digest=_digest(f), roles=n.roles, ancestry=tuple(ancestry[f.reference]),
            lineage=f.provenance.lineage, limitations=f.provenance.limitations)
            for f, n in zip(facts, lineage.nodes)))


class CreatinineTrendInferenceTerminalCheck(DomainModel):
    version: Literal['1'] = '1'
    target: ContextTarget
    historical_cutoff: RepositoryCutoff
    cutoff: RepositoryCutoff
    consumed: Reference
    consumed_payload_digest: Digest
    terminal: Reference | None
    terminal_payload_digest: Digest | None
    unavailable_reason: Literal['check_not_performed', 'reader_unavailable'] | None = None

    _cutoffs = field_validator('cutoff', 'historical_cutoff', mode='before')(_storage_fields)

    @model_validator(mode='after')
    def coherent(self):
        if self.target.encounter_id is None or self.consumed.kind != 'inference':
            raise ValueError('scoped consumed inference required')
        if (self.cutoff.repository_id != self.historical_cutoff.repository_id
                or self.cutoff.fact_watermark < self.historical_cutoff.fact_watermark):
            raise ValueError('final prefix precedes historical inference context')
        if self.terminal is None:
            if self.terminal_payload_digest is not None or self.unavailable_reason is None:
                raise ValueError('unavailability requires explicit inability to check, never family absence')
        elif (self.unavailable_reason is not None or self.terminal_payload_digest is None
                or (self.terminal.kind, self.terminal.id) != (self.consumed.kind, self.consumed.id)):
            raise ValueError('terminal must identify the checked inference family')
        elif self.terminal == self.consumed and self.terminal_payload_digest != self.consumed_payload_digest:
            raise ValueError('same exact inference has contradictory payload')
        canonical_payload(self)
        return self

    @property
    def status(self):
        return 'unavailable' if self.terminal is None else 'current' if self.terminal == self.consumed else 'superseded'


class CreatinineTrendFinalRecheck(DomainModel):
    policy: Reference = FINAL_RECHECK_POLICY
    implementation: Reference = FINAL_RECHECK_IMPLEMENTATION
    original: CreatinineTrendSelectionManifest
    final: CreatinineTrendSelectionManifest
    inference_terminal: CreatinineTrendInferenceTerminalCheck

    @model_validator(mode='after')
    def coherent(self):
        if self.policy != FINAL_RECHECK_POLICY or self.implementation != FINAL_RECHECK_IMPLEMENTATION:
            raise ValueError('unsupported final recheck version')
        before, after, terminal = self.original, self.final, self.inference_terminal
        if not before.successful or before.target != after.target or terminal.target != before.target:
            raise ValueError('recheck requires original successful evidence in the same scope')
        if (canonical_payload(before.policy) != canonical_payload(after.policy)
                or before.cutoff.repository_id != after.cutoff.repository_id
                or terminal.historical_cutoff.repository_id != before.cutoff.repository_id
                or terminal.historical_cutoff.fact_watermark <= before.cutoff.fact_watermark
                or canonical_payload(terminal.cutoff) != canonical_payload(after.cutoff)):
            raise ValueError('recheck policy or input/output/final cutoff relationship differs')
        originals = {r: (d, s, str(v), t.isoformat()) for r, d, s, v, t in zip(before.selected,
            before.selected_payload_digests, before.selected_samples, before.selected_values, before.selected_sample_times)}
        for ref, digest, sample, value, time in zip(after.selected, after.selected_payload_digests,
                after.selected_samples, after.selected_values, after.selected_sample_times):
            if ref in originals and originals[ref] != (digest, sample, str(value), time.isoformat()):
                raise ValueError('contradictory representation for same exact observation')
        return self

    @property
    def original_manifest_digest(self):
        return _digest(self.original)

    @property
    def reasons(self):
        reasons = []
        if not self.final.successful:
            reasons.append('final_selection_failed')
        elif self.final.selected != self.original.selected:
            reasons.append('selected_exact_references_changed')
        if self.inference_terminal.status != 'current':
            reasons.append('inference_' + self.inference_terminal.status)
        return tuple(reasons)

    @property
    def outcome(self):
        if any(r != 'inference_unavailable' for r in self.reasons):
            return 'materially_changed'
        return 'unavailable' if self.reasons else 'unchanged'


def assess_creatinine_trend_final_recheck(*, original, final,
        inference_terminal: CreatinineTrendInferenceTerminalCheck) -> CreatinineTrendFinalRecheck:
    """Compare supplied evidence only. Output-cutoff knowledge comes from terminal evidence."""
    before = (creatinine_trend_selection_manifest(original) if isinstance(original, CreatinineTrendSelectionResult)
              else CreatinineTrendSelectionManifest.model_validate(original))
    after = (creatinine_trend_selection_manifest(final) if isinstance(final, CreatinineTrendSelectionResult)
             else CreatinineTrendSelectionManifest.model_validate(final))
    terminal = CreatinineTrendInferenceTerminalCheck.model_validate(inference_terminal)
    old = dict(zip(before.selected, before.selected_payload_digests))
    if any(ref in old and old[ref] != digest for ref, digest in zip(after.selected, after.selected_payload_digests)):
        raise StorageIntegrityError('contradictory retained creatinine evidence')
    return CreatinineTrendFinalRecheck(original=before, final=after, inference_terminal=terminal)


class CreatinineTrendReviewRequest(DomainModel):
    execution_id: UUID
    target: OutputTarget
    actor: Text
    original: CreatinineTrendSelectionManifest
    comparison: RecordedCreatinineComparison
    inference: Reference
    lineage: CreatinineTrendLineageWitness
    requested_at: AwareDatetime

    @model_validator(mode='after')
    def coherent(self):
        if not self.original.successful or self.original.target != self.target.context:
            raise ValueError('request requires original successful selection in target scope')
        if canonical_payload(self.comparison) != canonical_payload(self.original.comparison):
            raise ValueError('comparison differs from original selected representations')
        if (self.inference.kind != 'inference' or self.lineage.root != self.inference
                or self.lineage.target != self.target.context
                or self.lineage.cutoff.repository_id != self.original.cutoff.repository_id
                or self.lineage.cutoff.fact_watermark <= self.original.cutoff.fact_watermark
                or self.lineage.direct_dependencies != self.original.selected):
            raise ValueError('historical inference and lineage differ from request')
        digests = dict(zip(self.original.selected, self.original.selected_payload_digests))
        for node in self.lineage.nodes:
            if node.reference == self.inference:
                if node.ingestion.ingestion_sequence <= self.original.cutoff.fact_watermark:
                    raise ValueError('inference must follow input prefix')
            elif (node.ingestion.ingestion_sequence > self.original.cutoff.fact_watermark
                    or node.payload_digest != digests[node.reference]):
                raise ValueError('lineage observation differs from original prefix or content')
        canonical_payload(self)
        return self


class CreatinineTrendExecutionRecord(DomainModel):
    execution_id: UUID
    execution_type: Literal['synthetic_creatinine_trend'] = 'synthetic_creatinine_trend'
    execution_version: Literal['1'] = '1'
    payload_version: Literal[1] = 1
    implementation: Reference = EXECUTION_IMPLEMENTATION
    target: OutputTarget
    actor: Text
    original: CreatinineTrendSelectionManifest
    comparison: RecordedCreatinineComparison
    inference: Reference
    lineage: CreatinineTrendLineageWitness
    final_recheck: CreatinineTrendFinalRecheck
    decision: ReleaseDecision
    requested_at: AwareDatetime
    started_at: AwareDatetime
    finalized_at: AwareDatetime

    @field_validator('payload_version', mode='before')
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('unsupported execution payload version')
        return value

    @property
    def request(self):
        return CreatinineTrendReviewRequest(execution_id=self.execution_id, target=self.target, actor=self.actor,
            original=self.original, comparison=self.comparison, inference=self.inference,
            lineage=self.lineage, requested_at=self.requested_at)

    @property
    def repository_id(self):
        return self.original.cutoff.repository_id

    @property
    def disposition(self):
        return 'completed_' + self.decision.outcome

    @model_validator(mode='after')
    def coherent(self):
        request = self.request
        check = self.final_recheck
        if self.implementation != EXECUTION_IMPLEMENTATION:
            raise ValueError('unsupported execution implementation')
        if (canonical_payload(check.original) != canonical_payload(self.original)
                or check.inference_terminal.consumed != self.inference
                or canonical_payload(check.inference_terminal.historical_cutoff) != canonical_payload(self.lineage.cutoff)):
            raise ValueError('final recheck differs from historical request')
        if self.lineage.coverage != 'complete_for_declared_visible_graph' or self.lineage.unresolved:
            raise ValueError('completed protected evidence requires resolved historical lineage')
        nodes = {n.reference: n for n in self.lineage.nodes}
        if check.inference_terminal.consumed_payload_digest != nodes[self.inference].payload_digest:
            raise ValueError('terminal check consumed digest differs from historical inference')
        decision, assessment = self.decision, self.decision.assessment
        if assessment.assessor != WORKFLOW_ASSESSOR:
            raise ValueError('expected protected creatinine workflow marker')
        if (decision.actor != self.actor or assessment.target != self.target
                or assessment.review.candidate.snapshot.binding.target != self.target.context):
            raise ValueError('decision actor or target differs from request')
        times = (self.requested_at, self.started_at, assessment.assessed_at, decision.at, self.finalized_at)
        if any(_instant(a) > _instant(b) for a, b in zip(times, times[1:])):
            raise ValueError('execution and governance times must be ordered by actual instant')
        snapshot = assessment.review.candidate.snapshot
        review = assessment.review
        if review.rendering is None:
            raise ValueError('completed creatinine execution requires rendering')
        produced_at = (snapshot.created_at, review.candidate.created_at, review.rendering.rendered_at,
            *(evaluation.evaluated_at for evaluation in review.evaluations),
            assessment.content_validation.assessed_at, assessment.state.freshness.assessed_at,
            assessment.state.observed_at, assessment.state.authorization.issued_at)
        if any(not _instant(self.started_at) <= _instant(t) <= _instant(decision.at) for t in produced_at):
            raise ValueError('governance artifacts must be produced within the execution interval')
        facts = snapshot.facts
        if tuple(f.reference for f in facts) != (*self.original.selected, self.inference):
            raise ValueError('decision snapshot must retain exact historical facts in order')
        for fact in facts:
            node = nodes[fact.reference]
            if (_digest(fact) != node.payload_digest or (fact.provenance.lineage, fact.provenance.limitations)
                    != (node.lineage, node.limitations)):
                raise ValueError('retained snapshot contradicts lineage content or provenance')
        selection = CreatinineTrendSelectionResult(target=self.original.target, policy=self.original.policy,
            cutoff=self.original.cutoff, selected=facts[:2], exclusions=self.original.exclusions)
        if canonical_payload(creatinine_trend_selection_manifest(selection)) != canonical_payload(self.original):
            raise ValueError('snapshot sample identities or representations differ from manifest')
        root = facts[-1]
        if not isinstance(root, ClinicalInference) or root.time.event is None:
            raise ValueError('exact historical inference required')
        expected = build_creatinine_trend_inference(selection=selection, comparison=request.comparison,
            inference_id=root.id, revision=root.revision, executed_at=root.time.event)
        # Revision metadata is retained, but never projected into evidence dependencies.
        expected = ClinicalInference.model_validate({**expected.model_dump(),
            'supersedes': root.supersedes, 'correction_reason': root.correction_reason})
        if canonical_payload(expected) != canonical_payload(root) or root.provenance.upstream != self.lineage.declarations:
            raise ValueError('retained inference differs from exact creatinine contract')
        freshness = assessment.state.freshness
        if freshness.assessor != FINAL_CONTEXT_ASSESSOR:
            raise ValueError('protected final-context marker required')
        changed = check.outcome == 'materially_changed'
        if freshness.material_change != changed:
            raise ValueError('final context material-change flag differs from recheck')
        if check.outcome != 'unchanged' and (decision.outcome != 'withheld' or freshness.adequate):
            raise ValueError('changed or unavailable recheck cannot support release or adequate context')
        canonical_payload(self)
        return self


class StoredCreatinineTrendExecution(DomainModel):
    """Supplied retained envelope, not proof of an insert or successful commit."""
    record: CreatinineTrendExecutionRecord
    ingested_at: AwareDatetime

    @model_validator(mode='after')
    def utc_storage_time(self):
        if self.ingested_at.utcoffset() != timedelta(0):
            raise ValueError('storage ingestion metadata must be UTC')
        canonical_payload(self)
        return self


def creatinine_trend_request_projection(value: CreatinineTrendReviewRequest | CreatinineTrendExecutionRecord) -> str:
    """Canonical immutable caller fields only; no matching, lookup or reconciliation."""
    if isinstance(value, CreatinineTrendExecutionRecord):
        value = CreatinineTrendExecutionRecord.model_validate(value).request
    else:
        value = CreatinineTrendReviewRequest.model_validate(value)
    return canonical_payload(value)
