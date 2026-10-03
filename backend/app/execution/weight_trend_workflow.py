"""Protected synthetic recorded-weight review only; explicit recovery, no delivery."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, model_validator
from sqlalchemy import Engine

from app.execution.weight_trend import (
    RecordedWeightComparison, _instant, build_weight_trend_inference,
    compare_recorded_weights, select_weight_observations,
)
from app.execution.weight_trend_execution import (
    WeightTrendExecutionRecord, WeightTrendFinalRecheck, WeightTrendInferenceTerminalCheck,
    WeightTrendLineageWitness, WeightTrendSelectionManifest, assess_weight_trend_final_recheck,
    weight_trend_lineage_witness, weight_trend_selection_manifest,
)
from app.execution.weight_trend_release import (
    LIMITATIONS, assemble_weight_trend_runtime, assess_weight_trend_context,
    assess_weight_trend_dependencies, build_weight_trend_candidate, build_weight_trend_snapshot,
    evaluate_weight_trend, issue_synthetic_weight_release, render_weight_trend,
    validate_weight_trend_content, weight_trend_governance_policy,
)
from app.models.clinical.common import DomainModel, Reference, Text
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.facts import ClinicalInference
from app.models.clinical.governance import ContextFreshnessAssessment, OutputTarget, ValidityWindow, required_payload
from app.persistence.errors import (
    PersistenceInputError, QueryLimitExceeded, RecordConflict, RecordNotFound, SchemaMismatch,
    ScopeMismatch, StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown, UnsupportedOperation,
)
from app.persistence.executions import StoredWeightTrendExecution, load_weight_trend_execution
from app.persistence.history import FactIdentity
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.shared_transaction import execution_transaction
from app.services.governance_service import assess_release, decide_release

WORKFLOW_ASSESSOR = 'SyntheticWeightProtectedExecution/v1'
FINAL_CONTEXT_ASSESSOR = 'SyntheticWeightFinalContext/v1'


class WeightTrendReviewRequest(DomainModel):
    """Historical assertions to verify, never caller-supplied final governance."""
    execution_id: UUID
    target: OutputTarget
    actor: Text
    original: WeightTrendSelectionManifest
    comparison: RecordedWeightComparison
    inference: Reference
    lineage: WeightTrendLineageWitness
    requested_at: AwareDatetime

    @model_validator(mode='after')
    def coherent(self):
        if not self.original.successful or self.original.target != self.target.context:
            raise ValueError('a successful original selection in the requested encounter is required')
        if (self.inference.kind != 'inference' or self.lineage.root != self.inference
                or self.lineage.target != self.target.context
                or self.lineage.cutoff.repository_id != self.original.cutoff.repository_id
                or self.lineage.cutoff.fact_watermark <= self.original.cutoff.fact_watermark):
            raise ValueError('inference lineage must follow the original input prefix in scope')
        if ((self.comparison.earlier_reference, self.comparison.later_reference) != self.original.selected
                or self.lineage.direct_dependencies != self.original.selected):
            raise ValueError('original exact references must agree')
        return self


@dataclass(frozen=True)
class WeightTrendReconciliationResult:
    """Historical retention only; absence is scoped to this completed lookup."""
    status: Literal['committed_match', 'absent']
    execution: StoredWeightTrendExecution | None

    def __post_init__(self):
        if self.status == 'committed_match':
            if not isinstance(self.execution, StoredWeightTrendExecution):
                raise ValueError('committed match requires a retained execution')
        elif self.status != 'absent' or self.execution is not None:
            raise ValueError('absence requires no retained execution')


def _validate_request(request):
    try:
        if type(request) is not WeightTrendReviewRequest:
            raise ValueError()
        request = WeightTrendReviewRequest.model_validate(request)
        canonical_payload(request)
        return request
    except Exception:
        raise PersistenceInputError('invalid weight review request') from None


def _require_request_match(stored, request):
    record = stored.record
    if (record.decision is None or record.decision.assessment.assessor != WORKFLOW_ASSESSOR
            or canonical_payload(_request_from_record(record)) != canonical_payload(request)):
        raise RecordConflict('execution identity already has different request or workflow')


def _ref(kind, identity):
    return Reference(kind=kind, id=identity, version='1')


def _utc_now():
    return datetime.now(timezone.utc)


def _tick(clock, previous):
    value = clock()
    if not isinstance(value, datetime) or value.utcoffset() is None or _instant(value) < _instant(previous):
        raise TransactionAborted('invalid execution clock')
    return value.astimezone(timezone.utc)


def _request_from_record(record):
    return WeightTrendReviewRequest(execution_id=record.execution_id, target=record.target,
        actor=record.actor, original=record.original, comparison=record.comparison,
        inference=record.inference, lineage=record.lineage, requested_at=record.started_at)


def assess_weight_trend_final_context(*, selection, comparison, inference, lineage, snapshot,
                                      recheck, at, validity, id):
    """Historical suitability plus the protected v1 final recheck; no DB reads."""
    recheck = WeightTrendFinalRecheck.model_validate(recheck)
    original = weight_trend_selection_manifest(selection)
    if (recheck.original_selected != original.selected
            or recheck.original_payload_digests != original.selected_payload_digests
            or recheck.final.target != original.target
            or canonical_payload(recheck.final.policy) != canonical_payload(original.policy)
            or recheck.final.cutoff.repository_id != original.cutoff.repository_id
            or recheck.final.cutoff.fact_watermark < lineage.cutoff.fact_watermark
            or recheck.inference_terminal.consumed != inference.reference):
        raise StorageIntegrityError('final context differs from verified historical evidence')
    historical = assess_weight_trend_context(selection=selection, comparison=comparison,
        inference=inference, lineage=lineage, snapshot=snapshot, at=at, validity=validity, id=id)
    changed = recheck.outcome == 'materially_changed'
    adequate = historical.adequate and recheck.outcome == 'unchanged'
    items = historical.items if adequate else tuple(type(item).model_validate({**item.model_dump(),
        'state': 'stale' if changed else 'unknown', 'validity': None,
        'rationale': 'Protected final context does not establish eligibility for this attempt.'})
        for item in historical.items)
    reason = ('Protected final recheck: ' + ', '.join(recheck.reasons) if recheck.reasons else
              'Historical suitability and protected final recheck satisfied.' if adequate else
              'Historical suitability unavailable at final observation.')
    return ContextFreshnessAssessment.model_validate({**historical.model_dump(),
        'adequate': adequate, 'material_change': changed, 'items': items,
        'assessor': FINAL_CONTEXT_ASSESSOR, 'rationale': reason})


def _new_execution(tx, request, clock):
    repo, target = tx.repository, request.target.context
    acquired_at = _tick(clock, request.requested_at)
    final_cutoff = repo.capture_cutoff()
    if (final_cutoff.repository_id != request.original.cutoff.repository_id
            or request.lineage.cutoff.fact_watermark > final_cutoff.fact_watermark):
        raise StorageIntegrityError('historical evidence is outside the protected repository prefix')
    original = select_weight_observations(repo, target=target, cutoff=request.original.cutoff,
                                         policy=request.original.policy)
    manifest = weight_trend_selection_manifest(original)
    if canonical_payload(manifest) != canonical_payload(request.original):
        raise StorageIntegrityError('original selection replay differs from requested evidence')
    comparison = compare_recorded_weights(original)
    if canonical_payload(comparison) != canonical_payload(request.comparison):
        raise StorageIntegrityError('original comparison differs from retained evidence')
    lineage = repo.resolve_lineage(request.inference, target=target, cutoff=request.lineage.cutoff,
                                   limits=LineageLimits())
    try:
        witness = weight_trend_lineage_witness(lineage)
    except (ValueError, TypeError):
        raise StorageIntegrityError('retained lineage is outside the weight evidence contract') from None
    if canonical_payload(witness) != canonical_payload(request.lineage) or lineage.unresolved:
        raise StorageIntegrityError('historical lineage differs from requested evidence')
    inference = next(node.stored.fact for node in lineage.nodes if node.stored.fact.reference == request.inference)
    if not isinstance(inference, ClinicalInference) or inference.time.event is None:
        raise StorageIntegrityError('required inference has invalid historical content')
    if _instant(inference.time.event) < _instant(original.policy.available_at):
        raise StorageIntegrityError('retained inference precedes source availability')
    expected = build_weight_trend_inference(selection=original, comparison=comparison,
        inference_id=inference.id, revision=inference.revision, executed_at=inference.time.event)
    if canonical_payload(expected) != canonical_payload(inference):
        raise StorageIntegrityError('retained inference differs from exact Phase 2 construction')
    final = select_weight_observations(repo, target=target, cutoff=final_cutoff, policy=original.policy)
    terminal = repo.load_latest_known(FactIdentity(kind='inference', id=inference.id),
                                     target=target, cutoff=final_cutoff)
    if len(terminal.records) != 1:
        raise StorageIntegrityError('verified inference family absent from final prefix')
    terminal_check = WeightTrendInferenceTerminalCheck(target=target, cutoff=final_cutoff,
        consumed=inference.reference, terminal=terminal.records[0].fact.reference)
    recheck = assess_weight_trend_final_recheck(original=original, final=final, inference_terminal=terminal_check)
    patient = repo.load_patient(target.patient_id)
    encounter = repo.load_encounter(patient_id=target.patient_id, encounter_id=target.encounter_id)
    observed_at = _tick(clock, acquired_at)
    identity = 'protected-weight-' + str(request.execution_id)
    validity = ValidityWindow(start=observed_at, end=observed_at + timedelta(seconds=30))
    snapshot = build_weight_trend_snapshot(selection=original, inference=inference, lineage=lineage,
        patient=patient, encounter=encounter, at=observed_at, id=identity+'-snapshot')
    candidate = build_weight_trend_candidate(snapshot=snapshot, comparison=comparison,
        inference=inference, at=observed_at, id=identity+'-candidate')
    rendering = render_weight_trend(candidate=candidate, comparison=comparison, target=request.target,
        at=observed_at, id=identity+'-rendering')
    evaluation = evaluate_weight_trend(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, candidate=candidate, rendering=rendering,
        target=request.target, at=observed_at, id=identity+'-safety')
    review = RecommendationReview(candidate=candidate, rendering=rendering, evaluations=(evaluation,))
    payload = required_payload(review, (), LIMITATIONS)
    validation = validate_weight_trend_content(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, review=review, payload=payload, target=request.target,
        at=observed_at, validity=validity, id=identity+'-content')
    policy = weight_trend_governance_policy(snapshot=snapshot, selection=original, inference=inference)
    freshness = assess_weight_trend_final_context(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, recheck=recheck, at=observed_at, validity=validity, id=identity+'-context')
    dependencies = assess_weight_trend_dependencies(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, policy=policy, at=observed_at, validity=validity)
    decision_at = _tick(clock, observed_at)
    authorization = issue_synthetic_weight_release(selection=original, inference=inference, review=review,
        payload=payload, policy=policy, target=request.target, actor=request.actor, at=decision_at,
        id=identity+'-authorization')
    state = assemble_weight_trend_runtime(snapshot=snapshot, candidate=candidate, target=request.target,
        active_request=request.target, active_output=candidate.reference, authorization=authorization,
        freshness=freshness, dependencies=dependencies, at=decision_at)
    assessment = assess_release(reference=_ref('release_eligibility', identity), review=review, payload=payload,
        target=request.target, policy=policy, content_validation=validation, state=state,
        assessor=WORKFLOW_ASSESSOR, at=decision_at, validity=validity)
    decision = decide_release(reference=_ref('release_decision', identity), assessment=assessment,
        actor=request.actor, at=decision_at)
    finalized_at = _tick(clock, decision_at)
    record = WeightTrendExecutionRecord(execution_id=request.execution_id, target=request.target,
        actor=request.actor, original=manifest, comparison=comparison, inference=inference.reference,
        lineage=witness, final_recheck=recheck, decision=decision,
        started_at=request.requested_at, finalized_at=finalized_at)
    return tx.executions.append(record, target=target)


def execute_weight_trend_review(engine, request: WeightTrendReviewRequest, *, clock=_utc_now
                                ) -> StoredWeightTrendExecution:
    """Return only after commit; identical retries recover without re-evaluation.

    The clock is a trusted runtime dependency, not caller authorization. No
    operational-failure record, delivery or automatic reconciliation is attempted.
    """
    request = _validate_request(request)
    try:
        with execution_transaction(engine) as tx:
            existing = tx.executions.find(request.execution_id, target=request.target.context)
            if existing is not None:
                _require_request_match(existing, request)
                result = existing
            else:
                result = _new_execution(tx, request, clock)
    except TransactionCompletionUnknown:
        raise TransactionCompletionUnknown('transaction completion could not be confirmed') from None
    except TransactionAborted:
        raise TransactionAborted('protected weight execution failed') from None
    except (PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch,
            StorageIntegrityError, QueryLimitExceeded, SchemaMismatch, UnsupportedOperation) as error:
        messages = {PersistenceInputError: 'invalid weight execution input',
            RecordConflict: 'execution identity already has different request or content',
            RecordNotFound: 'required historical evidence not found in requested context',
            ScopeMismatch: 'weight execution scope mismatch', StorageIntegrityError: 'weight execution integrity failure',
            QueryLimitExceeded: 'weight execution resource limit exceeded', SchemaMismatch: 'unsupported execution storage schema',
            UnsupportedOperation: 'unsupported weight execution operation'}
        category = next(kind for kind in messages if isinstance(error, kind))
        raise category(messages[category]) from None
    except Exception:
        raise TransactionAborted('protected weight execution failed') from None
    return result


def reconcile_weight_trend_execution(engine: Engine, request: WeightTrendReviewRequest
                                     ) -> WeightTrendReconciliationResult:
    """Discover retained protected completion without executing clinical work.

    Absence describes only this scoped lookup, not proof of a historical rollback.
    The standalone loader owns its transaction, including the existing writer
    reservation. Errors leave any earlier completion uncertainty unresolved.
    """
    request = _validate_request(request)
    try:
        try:
            stored = load_weight_trend_execution(engine, request.execution_id, target=request.target.context)
        except RecordNotFound:
            # The standalone boundary has exited; no poisoned handle is reused.
            return WeightTrendReconciliationResult(status='absent', execution=None)
        _require_request_match(stored, request)
        return WeightTrendReconciliationResult(status='committed_match', execution=stored)
    except (PersistenceInputError, RecordConflict, StorageIntegrityError, SchemaMismatch) as error:
        messages = {PersistenceInputError: 'invalid weight reconciliation input',
            RecordConflict: 'execution identity already has different request or workflow',
            StorageIntegrityError: 'weight reconciliation integrity failure',
            SchemaMismatch: 'unsupported execution storage schema'}
        category = next(kind for kind in messages if isinstance(error, kind))
        raise category(messages[category]) from None
    except Exception:
        # Read/completion failure here is not an uncertain clinical execution commit.
        raise TransactionAborted('weight reconciliation failed') from None
