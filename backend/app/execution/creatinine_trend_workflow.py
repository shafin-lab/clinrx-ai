"""Protected synthetic creatinine composition; no reconciliation or delivery."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from app.execution.creatinine_trend import (
    _instant, build_creatinine_trend_inference, compare_recorded_creatinine,
    select_creatinine_observations,
)
from app.execution.creatinine_trend_execution import (
    FINAL_CONTEXT_ASSESSOR, WORKFLOW_ASSESSOR, CreatinineTrendExecutionRecord,
    CreatinineTrendFinalRecheck, CreatinineTrendInferenceTerminalCheck,
    CreatinineTrendReviewRequest, StoredCreatinineTrendExecution,
    assess_creatinine_trend_final_recheck, creatinine_trend_lineage_witness,
    creatinine_trend_request_projection, creatinine_trend_selection_manifest,
)
from app.execution.creatinine_trend_release import (
    LIMITATIONS, assemble_creatinine_trend_runtime, assess_creatinine_trend_context,
    assess_creatinine_trend_dependencies, build_creatinine_trend_candidate,
    build_creatinine_trend_snapshot, creatinine_trend_governance_policy,
    evaluate_creatinine_trend, issue_synthetic_creatinine_release, render_creatinine_trend,
    validate_creatinine_trend_content,
)
from app.models.clinical.common import Reference
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.facts import ClinicalInference
from app.models.clinical.governance import ContextFreshnessAssessment, ValidityWindow, required_payload
from app.persistence.errors import (
    PersistenceInputError, QueryLimitExceeded, RecordConflict, RecordNotFound, SchemaMismatch,
    ScopeMismatch, StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown, UnsupportedOperation,
)
from app.persistence.history import FactIdentity
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.shared_transaction import execution_transaction
from app.services.governance_service import assess_release, decide_release


def _digest(value):
    return sha256(canonical_payload(value).encode('utf-8')).hexdigest()


def _ref(kind, identity):
    return Reference(kind=kind, id=identity, version='1')


def _utc_now():
    return datetime.now(timezone.utc)


def _tick(clock, previous):
    value = clock()
    if not isinstance(value, datetime) or value.utcoffset() is None or _instant(value) < _instant(previous):
        raise TransactionAborted('invalid execution clock')
    return value.astimezone(timezone.utc)


def _validate_request(request):
    try:
        if type(request) is not CreatinineTrendReviewRequest:
            raise ValueError()
        request = CreatinineTrendReviewRequest.model_validate(request)
        creatinine_trend_request_projection(request)
        return request
    except Exception:
        raise PersistenceInputError('invalid creatinine review request') from None


def _require_creatinine_request_match(stored, request):
    if (stored.record.decision.assessment.assessor != WORKFLOW_ASSESSOR
            or creatinine_trend_request_projection(stored.record) != creatinine_trend_request_projection(request)):
        raise RecordConflict('execution identity already has different request or workflow')


def assess_creatinine_trend_final_context(*, selection, comparison, inference, lineage, snapshot,
                                          recheck, at, validity, id):
    """Bind verified historical evidence and protected recheck in the existing assertion."""
    recheck = CreatinineTrendFinalRecheck.model_validate(recheck)
    manifest = creatinine_trend_selection_manifest(selection)
    witness = creatinine_trend_lineage_witness(lineage)
    terminal = recheck.inference_terminal
    if (canonical_payload(recheck.original) != canonical_payload(manifest)
            or terminal.consumed != inference.reference
            or terminal.consumed_payload_digest != _digest(inference)
            or canonical_payload(terminal.historical_cutoff) != canonical_payload(witness.cutoff)
            or witness.root != inference.reference or witness.target != manifest.target
            or witness.direct_dependencies != manifest.selected
            or witness.coverage != 'complete_for_declared_visible_graph' or witness.unresolved):
        raise StorageIntegrityError('final context differs from verified historical evidence')
    historical = assess_creatinine_trend_context(selection=selection, comparison=comparison,
        inference=inference, lineage=lineage, snapshot=snapshot, at=at, validity=validity, id=id)
    changed = recheck.outcome == 'materially_changed'
    adequate = historical.adequate and recheck.outcome == 'unchanged'
    items = tuple(type(item).model_validate({**item.model_dump(),
        'state': item.state if adequate else 'stale' if changed else 'unknown',
        'validity': item.validity if adequate else None,
        'rationale': 'Bounded historical suitability plus protected final recheck; no biological truth claim.'})
        for item in historical.items)
    # Full objects remain in the execution record. Digests bind this assertion to
    # their exact canonical representations without changing generic governance types.
    binding = ('protected_cutoff=' + _digest(recheck.final.cutoff)
        + '; scope=' + _digest(manifest.target) + '; inference=' + _digest(inference.reference)
        + '; lineage=' + _digest(witness) + '; final_selection=' + _digest(recheck.final)
        + '; terminal=' + _digest(terminal) + '; recheck=' + _digest(recheck)
        + '; outcome=' + recheck.outcome)
    return ContextFreshnessAssessment.model_validate({**historical.model_dump(),
        'adequate': adequate, 'material_change': changed, 'items': items,
        'assessor': FINAL_CONTEXT_ASSESSOR, 'rationale': binding})


def _replay(repo, request):
    target = request.target.context
    selection = select_creatinine_observations(repo, target=target,
        cutoff=request.original.cutoff, policy=request.original.policy)
    if canonical_payload(creatinine_trend_selection_manifest(selection)) != canonical_payload(request.original):
        raise StorageIntegrityError('original selection replay differs from requested evidence')
    comparison = compare_recorded_creatinine(selection)
    if canonical_payload(comparison) != canonical_payload(request.comparison):
        raise StorageIntegrityError('original comparison differs from retained evidence')
    try:
        lineage = repo.resolve_lineage(request.inference, target=target,
            cutoff=request.lineage.cutoff, limits=LineageLimits())
    except RecordNotFound:
        raise StorageIntegrityError('required historical inference is absent') from None
    try:
        witness = creatinine_trend_lineage_witness(lineage)
    except (ValueError, TypeError):
        raise StorageIntegrityError('retained lineage is outside the creatinine evidence contract') from None
    if (canonical_payload(witness) != canonical_payload(request.lineage)
            or witness.coverage != 'complete_for_declared_visible_graph' or witness.unresolved):
        raise StorageIntegrityError('historical lineage differs from required evidence')
    inference = next(n.stored.fact for n in lineage.nodes if n.stored.fact.reference == request.inference)
    if not isinstance(inference, ClinicalInference) or inference.time.event is None:
        raise StorageIntegrityError('required inference has invalid historical content')
    try:
        expected = build_creatinine_trend_inference(selection=selection, comparison=comparison,
            inference_id=inference.id, revision=inference.revision, executed_at=inference.time.event)
        expected = ClinicalInference.model_validate({**expected.model_dump(),
            'supersedes': inference.supersedes, 'correction_reason': inference.correction_reason})
    except (ValueError, TypeError):
        raise StorageIntegrityError('retained inference violates the Phase B contract') from None
    if canonical_payload(expected) != canonical_payload(inference):
        raise StorageIntegrityError('retained inference differs from exact Phase B construction')
    return selection, comparison, inference, lineage, witness


def _new_execution(tx, request, clock):
    repo, target = tx.repository, request.target.context
    started_at = _tick(clock, request.requested_at)
    final_cutoff = repo.capture_cutoff()
    if (final_cutoff.repository_id != request.original.cutoff.repository_id
            or request.lineage.cutoff.fact_watermark > final_cutoff.fact_watermark):
        raise StorageIntegrityError('historical evidence is outside the protected repository prefix')
    original, comparison, inference, lineage, witness = _replay(repo, request)
    final = select_creatinine_observations(repo, target=target, cutoff=final_cutoff, policy=original.policy)
    latest = repo.load_latest_known(FactIdentity(kind='inference', id=inference.id), target=target, cutoff=final_cutoff)
    if len(latest.records) != 1:
        raise StorageIntegrityError('verified inference family absent from final prefix')
    terminal = latest.records[0].fact
    try:
        terminal_check = CreatinineTrendInferenceTerminalCheck(target=target,
            historical_cutoff=lineage.cutoff, cutoff=final_cutoff, consumed=inference.reference,
            consumed_payload_digest=_digest(inference), terminal=terminal.reference,
            terminal_payload_digest=_digest(terminal))
    except (ValueError, TypeError):
        raise StorageIntegrityError('terminal inference contradicts verified historical evidence') from None
    recheck = assess_creatinine_trend_final_recheck(original=original, final=final, inference_terminal=terminal_check)
    patient = repo.load_patient(target.patient_id)
    encounter = repo.load_encounter(patient_id=target.patient_id, encounter_id=target.encounter_id)
    observed_at = _tick(clock, started_at)
    identity = 'protected-creatinine-' + str(request.execution_id)
    validity = ValidityWindow(start=observed_at, end=observed_at + timedelta(seconds=30))
    snapshot = build_creatinine_trend_snapshot(selection=original, inference=inference, lineage=lineage,
        patient=patient, encounter=encounter, at=observed_at, id=identity+'-snapshot')
    candidate = build_creatinine_trend_candidate(snapshot=snapshot, comparison=comparison,
        inference=inference, at=observed_at, id=identity+'-candidate')
    rendering = render_creatinine_trend(candidate=candidate, comparison=comparison, target=request.target,
        at=observed_at, id=identity+'-rendering')
    evaluation = evaluate_creatinine_trend(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, candidate=candidate, rendering=rendering,
        target=request.target, at=observed_at, id=identity+'-safety')
    review = RecommendationReview(candidate=candidate, rendering=rendering, evaluations=(evaluation,))
    payload = required_payload(review, (), LIMITATIONS)
    validation = validate_creatinine_trend_content(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, review=review, payload=payload, target=request.target,
        at=observed_at, validity=validity, id=identity+'-content')
    policy = creatinine_trend_governance_policy(snapshot=snapshot, selection=original, inference=inference)
    freshness = assess_creatinine_trend_final_context(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, recheck=recheck, at=observed_at, validity=validity, id=identity+'-context')
    dependencies = assess_creatinine_trend_dependencies(selection=original, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, policy=policy, at=observed_at, validity=validity)
    decision_at = _tick(clock, observed_at)
    authority = issue_synthetic_creatinine_release(selection=original, inference=inference, review=review,
        payload=payload, policy=policy, target=request.target, actor=request.actor, at=decision_at,
        id=identity+'-authorization')
    state = assemble_creatinine_trend_runtime(snapshot=snapshot, candidate=candidate, target=request.target,
        active_request=request.target, active_output=candidate.reference, authorization=authority,
        freshness=freshness, dependencies=dependencies, at=decision_at)
    assessment = assess_release(reference=_ref('release_eligibility', identity), review=review, payload=payload,
        target=request.target, policy=policy, content_validation=validation, state=state,
        assessor=WORKFLOW_ASSESSOR, at=decision_at, validity=validity)
    decision = decide_release(reference=_ref('release_decision', identity), assessment=assessment,
        actor=request.actor, at=decision_at)
    finalized_at = _tick(clock, decision_at)
    record = CreatinineTrendExecutionRecord(**request.model_dump(),
        final_recheck=recheck, decision=decision, started_at=started_at, finalized_at=finalized_at)
    return tx.creatinine_executions.append(record, target=target)


def execute_creatinine_trend_review(engine, request: CreatinineTrendReviewRequest, *, clock=_utc_now
                                   ) -> StoredCreatinineTrendExecution:
    """Return retained completion only after context exit; exact retries skip new work.

    The injected clock is a trusted runtime dependency, not an authorization grant.
    No operational-failure row or automatic recovery is produced.
    """
    request = _validate_request(request)
    try:
        with execution_transaction(engine) as tx:
            existing = tx.creatinine_executions.find(request.execution_id, target=request.target.context)
            if existing is not None:
                _require_creatinine_request_match(existing, request)
                result = existing
            else:
                result = _new_execution(tx, request, clock)
    except TransactionCompletionUnknown:
        raise TransactionCompletionUnknown('transaction completion could not be confirmed') from None
    except TransactionAborted:
        raise TransactionAborted('protected creatinine execution failed') from None
    except (PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch, StorageIntegrityError,
            QueryLimitExceeded, SchemaMismatch, UnsupportedOperation) as error:
        messages = {PersistenceInputError:'invalid creatinine execution input',
            RecordConflict:'execution identity already has different request or content',
            RecordNotFound:'required historical evidence not found in requested context',
            ScopeMismatch:'creatinine execution scope mismatch', StorageIntegrityError:'creatinine execution integrity failure',
            QueryLimitExceeded:'creatinine execution resource limit exceeded', SchemaMismatch:'unsupported execution storage schema',
            UnsupportedOperation:'unsupported creatinine execution operation'}
        category = next(kind for kind in messages if isinstance(error, kind))
        raise category(messages[category]) from None
    except Exception:
        raise TransactionAborted('protected creatinine execution failed') from None
    return result
