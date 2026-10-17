"""Protected explicit-subset review and explicit recovery; synthetic use only."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import model_validator

from app.execution import patient_state_v3_execution as c
from app.execution import patient_state_v3_release as g
from app.execution.patient_state_v3_assembly import _assemble
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError
from app.models.clinical.common import DomainModel
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.governance import RuntimeState, ValidityWindow, required_payload
from app.persistence.errors import (
    PersistenceInputError, QueryLimitExceeded, RecordConflict, RecordNotFound,
    SchemaMismatch, ScopeMismatch, StorageIntegrityError, TransactionAborted,
    TransactionCompletionUnknown, UnsupportedOperation,
)
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.history import FactIdentity
from app.persistence.circulatory_executions import (
    StoredCirculatoryExecution, find_circulatory_execution,
)
from app.persistence.shared_transaction import execution_transaction
from app.services.governance_service import assess_release, decide_release

# The existing immutable storage receipt is the committed execution result.
CirculatoryExecutionResult = StoredCirculatoryExecution


def _utc_now():
    return datetime.now(timezone.utc)


def _tick(clock, previous):
    value = clock()
    if (not isinstance(value, datetime) or value.utcoffset() is None
            or c.instant(value) < c.instant(previous)):
        raise TransactionAborted('invalid execution clock')
    return value.astimezone(timezone.utc)


def _validate_request(request):
    try:
        if type(request) is not c.CirculatoryExecutionRequest:
            raise ValueError()
        request = c.CirculatoryExecutionRequest.model_validate(request)
        c.circulatory_request_projection(request)
        return request
    except Exception:
        raise PersistenceInputError('invalid circulatory execution request') from None


def _history(repo, reference, target, cutoff, *, latest, history_budget=None, family_budget=None, accounting=None):
    identity = FactIdentity(kind=reference.kind, id=reference.id)
    result = repo.list_bounded_history(identity=identity, target=target, cutoff=cutoff, latest=latest,
        budget=HistoryBudget() if history_budget is None else history_budget,
        family_budget=family_budget, accounting=accounting)
    if (result.target != target or not c.same(result.cutoff, cutoff) or result.identity != identity
            or result.selection != ('latest_known' if latest else 'history')
            or result.clinical_filter is not None or result.ingestion_filter is not None):
        raise StorageIntegrityError('historical result differs from protected request')
    for stored in result.records:
        f, meta = stored.fact, stored.ingestion
        if (f.binding.target != target or (f.kind,f.id) != (reference.kind,reference.id)
                or meta.repository_id != cutoff.repository_id or meta.ingestion_sequence > cutoff.fact_watermark):
            raise StorageIntegrityError('historical evidence lies outside protected scope')
    matches = result.records if latest else tuple(s for s in result.records if s.fact.reference == reference)
    if len(matches) != 1:
        raise StorageIntegrityError('required protected evidence is absent or ambiguous')
    return matches[0]


def _replay(repo, request, **reads):
    scope = request.inference_request.scope
    assembly = _assemble(repo, request.assembly_request, **reads)
    selected = []
    for pin in request.pins:
        matches = tuple(i for i in assembly.snapshot.items if i.reference == pin.reference)
        if len(matches) != 1 or matches[0].expected_digest != pin.expected_digest:
            raise StorageIntegrityError('original selected evidence differs from request')
        selected.append(matches[0])
    original = _history(repo, request.inference_reference, request.target.context, request.inference_cutoff, latest=False, **reads)
    sources = tuple(_history(repo, pin.reference, request.target.context, scope.repository_cutoff, latest=False, **reads)
                    for pin in request.pins)
    if any(not c.same(s.ingestion,i.ingestion) for s,i in zip(sources,selected,strict=True)):
        raise StorageIntegrityError('selected ingestion metadata contradicts original replay')
    try:
        evidence = c.CirculatoryEvidence(request=request, items=tuple(selected),
            facts=tuple(s.fact for s in sources), inference=original.fact, inference_ingestion=original.ingestion)
    except c.CirculatoryExecutionError as error:
        if error.code == 'unverified_admission':
            raise UnsupportedOperation('protected evidence requires verified binding') from None
        raise StorageIntegrityError('original inference or evidence contradicts request') from None
    # Original canonical mismatch is an integrity failure, never a withheld row.
    try:
        reconstructed = build_circulatory_timing_inference(assembly=assembly, request=request.inference_request)
    except CirculatoryInferenceError:
        raise StorageIntegrityError('original inference reconstruction failed') from None
    reconstruction_digest = c.digest(reconstructed)
    if not c.same(reconstructed, original.fact) or reconstruction_digest != request.expected_inference_digest:
        raise StorageIntegrityError('inconsistent original inference comparison')
    return evidence, reconstruction_digest


def _final_recheck(repo, evidence, reconstruction_digest, cutoff, **reads):
    request = evidence.request
    witnesses = []
    terminal_facts = []
    for role,item,fact in zip(('P','L','V')+('support',)*(len(evidence.items)-3),evidence.items,evidence.facts,strict=True):
        terminal = _history(repo, fact.reference, request.target.context, cutoff, latest=True, **reads)
        terminal_facts.append(terminal.fact)
        # Exact retained source/item content was admitted above. A successor is
        # never remapped or substituted: currentness alone already makes it material.
        witnesses.append(c.CirculatoryEvidenceWitness(role=role, consumed=fact.reference,
            item_digest=item.expected_digest, source_digest=c.digest(fact), original_ingestion=item.ingestion,
            terminal=terminal.fact.reference, terminal_source_digest=c.digest(terminal.fact),
            terminal_ingestion=terminal.ingestion,
            suitability='established' if terminal.fact.reference == fact.reference else 'unavailable'))
    i = evidence.inference
    terminal = _history(repo,i.reference,request.target.context,cutoff,latest=True, **reads)
    witness = c.CirculatoryInferenceWitness(reference=i.reference, expected_digest=request.expected_inference_digest,
        observed_digest=c.digest(i), ingestion=evidence.inference_ingestion,
        terminal=terminal.fact.reference, terminal_digest=c.digest(terminal.fact), terminal_ingestion=terminal.ingestion,
        method=i.method, inputs=i.inputs, dependencies=i.provenance.dependencies,
        declarations=i.provenance.upstream, reconstruction_digest=reconstruction_digest)
    return c.CirculatoryFinalRecheck(scope=request.inference_request.scope,
        inference_cutoff=request.inference_cutoff, final_cutoff=cutoff, evidence=tuple(witnesses), terminal_facts=tuple(terminal_facts), inference=witness)


def _new_execution(tx, request, clock, *, history_budget=None, family_budget=None, aggregate_budget=None):
    # Construct only after retained lookup; one counter covers every new-work read.
    reads = dict(history_budget=history_budget, family_budget=family_budget,
        accounting=HistoryAccounting(AggregateHistoryBudget() if aggregate_budget is None else aggregate_budget))
    repo, target = tx.repository, request.target.context
    started_at = _tick(clock,request.requested_at)
    cutoff = repo.capture_cutoff()
    if (cutoff.repository_id != request.inference_cutoff.repository_id
            or cutoff.fact_watermark < request.inference_cutoff.fact_watermark):
        raise StorageIntegrityError('requested evidence is outside protected prefix')
    evidence, reconstruction_digest = _replay(repo,request, **reads)
    try:
        recheck = _final_recheck(repo,evidence,reconstruction_digest,cutoff, **reads)
    except c.CirculatoryExecutionError:
        raise StorageIntegrityError('terminal evidence contradicts original evidence') from None
    observed_at = _tick(clock,started_at)
    patient = repo.load_patient(target.patient_id)
    encounter = repo.load_encounter(patient_id=target.patient_id,encounter_id=target.encounter_id)
    identity = 'protected-circulatory-'+str(request.execution_id)
    validity = ValidityWindow(start=observed_at,end=observed_at+timedelta(seconds=30))
    snapshot = g.build_circulatory_context(evidence=evidence,patient=patient,encounter=encounter,
        at=observed_at,id=identity+'-context')
    candidate = g.build_circulatory_candidate(evidence=evidence,snapshot=snapshot,at=observed_at,id=identity+'-candidate')
    rendering = g.render_circulatory(candidate=candidate,target=request.target,at=observed_at,id=identity+'-rendering')
    evaluation = g.evaluate_circulatory(evidence=evidence,recheck=recheck,snapshot=snapshot,candidate=candidate,
        rendering=rendering,target=request.target,at=observed_at,id=identity+'-safety')
    review = RecommendationReview(candidate=candidate,rendering=rendering,evaluations=(evaluation,))
    payload = required_payload(review,(),c.LIMITATIONS)
    validation = g.validate_circulatory_content(evidence=evidence,recheck=recheck,snapshot=snapshot,review=review,
        payload=payload,target=request.target,at=observed_at,validity=validity,id=identity+'-fidelity')
    freshness = g.assess_circulatory_context(evidence=evidence,recheck=recheck,snapshot=snapshot,
        at=observed_at,validity=validity,id=identity+'-freshness')
    dependencies = g.assess_circulatory_dependencies(evidence=evidence,recheck=recheck,snapshot=snapshot,validity=validity)
    policy = c.circulatory_policy(snapshot)
    decision_at = _tick(clock,observed_at)
    authority = g.issue_synthetic_circulatory_authority(request=request,review=review,payload=payload,
        policy=policy,at=decision_at,id=identity+'-authority')
    state = RuntimeState(target=request.target,identity=snapshot.binding.verification,request_state='active',output_state='current',
        observed_at=observed_at,authorization=authority,freshness=freshness,dependencies=dependencies)
    assessment = assess_release(reference=c.ref('release_eligibility',identity),review=review,payload=payload,target=request.target,
        policy=policy,content_validation=validation,state=state,assessor=c.WORKFLOW,at=decision_at,validity=validity)
    decision = decide_release(reference=c.ref('release_decision',identity),assessment=assessment,actor=request.actor,at=decision_at)
    finalized_at = _tick(clock,decision_at)
    record = c.CirculatoryExecutionRecord(request=request,evidence=evidence,final_recheck=recheck,context_digest=c.digest(snapshot),decision=decision,
        runtime=c.CirculatoryRuntime(started_at=started_at,observed_at=observed_at,decision_at=decision_at,finalized_at=finalized_at))
    return tx.circulatory_executions.append(record,target=target)


def execute_circulatory_review(engine, request: c.CirculatoryExecutionRequest, *, clock=None,
                                         history_budget=None, family_budget=None, aggregate_budget=None
                                         ) -> CirculatoryExecutionResult:
    """Return only after transaction completion; clock is a trusted runtime dependency."""
    request = _validate_request(request)
    try:
        with execution_transaction(engine) as tx:
            stored = tx.circulatory_executions.find(request.execution_id,target=request.target.context)
            if stored is not None:
                c.require_circulatory_request_match(stored.record,request)
                result = stored
            else:
                result = _new_execution(tx,request,_utc_now if clock is None else clock,
                    history_budget=history_budget, family_budget=family_budget, aggregate_budget=aggregate_budget)
    except TransactionCompletionUnknown:
        raise TransactionCompletionUnknown('transaction completion could not be confirmed') from None
    except (PersistenceInputError,RecordConflict,RecordNotFound,ScopeMismatch,StorageIntegrityError,
            QueryLimitExceeded,SchemaMismatch,UnsupportedOperation) as error:
        messages = {PersistenceInputError:'invalid circulatory execution input',RecordConflict:'execution request conflicts with retained content',
            RecordNotFound:'required evidence not found in requested context',ScopeMismatch:'circulatory execution scope mismatch',
            StorageIntegrityError:'circulatory execution integrity failure',QueryLimitExceeded:'circulatory execution resource limit exceeded',
            SchemaMismatch:'unsupported execution schema',UnsupportedOperation:'unsupported circulatory execution admission'}
        category = next(kind for kind in messages if isinstance(error,kind))
        raise category(messages[category]) from None
    except Exception:
        raise TransactionAborted('protected circulatory execution failed') from None
    return result


class CirculatoryReconciliationResult(DomainModel):
    status: Literal['committed_match','absent']
    stored: StoredCirculatoryExecution | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.status == 'committed_match') != (self.stored is not None):
            raise ValueError('reconciliation status differs from retained execution')
        return self


def reconcile_circulatory_execution(engine, request: c.CirculatoryExecutionRequest
                                               ) -> CirculatoryReconciliationResult:
    """Explicit scoped historical lookup; no execution or current clinical evaluation."""
    request = _validate_request(request)
    try:
        stored = find_circulatory_execution(engine,request.execution_id,target=request.target.context)
        if stored is not None:
            c.require_circulatory_request_match(stored.record,request)
        return CirculatoryReconciliationResult(status='absent' if stored is None else 'committed_match',stored=stored)
    except (PersistenceInputError,RecordConflict,StorageIntegrityError,SchemaMismatch,QueryLimitExceeded) as error:
        messages = {PersistenceInputError:'invalid circulatory reconciliation input',RecordConflict:'execution request conflicts with retained content',
            StorageIntegrityError:'circulatory reconciliation integrity failure',SchemaMismatch:'unsupported execution schema',
            QueryLimitExceeded:'circulatory reconciliation resource limit exceeded'}
        category = next(kind for kind in messages if isinstance(error,kind))
        raise category(messages[category]) from None
    except Exception:
        raise TransactionAborted('circulatory reconciliation failed') from None
