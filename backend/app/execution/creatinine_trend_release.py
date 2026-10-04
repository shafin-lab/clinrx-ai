"""Synthetic historical creatinine governance over supplied committed reads.

No storage, current-state recheck, delivery or authentication. Local producers
establish bounded consistency; generic governance decides release or withholding.
"""
from datetime import datetime, timedelta, timezone

from pydantic import AwareDatetime, TypeAdapter

from app.execution.creatinine_trend import (
    RECORDED_CREATININE_TREND_METHOD, CreatinineTrendSelectionResult,
    RecordedCreatinineComparison, build_creatinine_trend_inference, compare_recorded_creatinine,
)
from app.models.clinical.common import IdentityVerification, LineageEdge, Provenance, Reference, Source
from app.models.clinical.decisions import (
    ClinicalClaim, ClinicalRecommendation, RecommendationReview, RenderedRecommendation,
    SafetyCheck, SafetyEvaluation,
)
from app.models.clinical.facts import ClinicalInference, ContextSnapshot
from app.models.clinical.governance import (
    AuthorizationAssertion, ContentValidationAssertion, ContextFreshnessAssessment,
    DependencyRequirement, DependencyState, FreshnessItem, GovernancePolicy, OutputTarget,
    PresentationPayload, RuntimeState, ValidityWindow, content_digest, required_payload, review_digest,
)
from app.persistence.lineage import LineageResult
from app.persistence.mapping import canonical_payload, validate_fact
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff
from app.services.governance_service import assess_release, decide_release

INTENDED_USE = ('Synthetic review of a bounded historical serum-creatinine comparison; '
    'no diagnosis, prediction, treatment recommendation, patient-care delivery, '
    'or assertion of current clinical eligibility.')
LIMITATIONS = (INTENDED_USE,
    'Synthetic sample identity and source authenticity are assumed; no independent specimen verification.',
    'No assay harmonization, reference-range interpretation or unit conversion.',
    'Fixed historical evidence only; later corrections are not assessed. No clinical validation or delivery.')
SCOPE = 'Two exact synthetic serum-creatinine observations and their inference at the supplied historical cutoffs only.'
RATIONALE = 'Descriptive comparison of two exact retained synthetic serum-creatinine sample values in mg/dL.'
SOURCE = Source(namespace='clinrx.synthetic', identifier='SyntheticCreatinineRelease', version='1', channel='system')


def _ref(kind, id):
    return Reference(kind=kind, id=id, version='1')


def _at(value):
    # Runtime observations use UTC; source sample/Decimal representations stay untouched.
    return TypeAdapter(AwareDatetime).validate_python(value).astimezone(timezone.utc)


USE = _ref('intended_use', 'SyntheticHistoricalCreatinineComparison')
SAFETY = _ref('safety_policy', 'SyntheticCreatinineSafety')
FIDELITY = _ref('content_validation_method', 'SyntheticCreatinineFidelity')
FRESHNESS = _ref('freshness_policy', 'SyntheticCreatinineHistoricalContext')
AUTHORIZATION = _ref('authorization_policy', 'SyntheticCreatinineReleaseGrant')
RULES = (_ref('safety_rule', 'creatinine_exact_evidence_and_input_suitability'),
         _ref('safety_rule', 'creatinine_bounded_descriptive_output'))
ISSUER = 'SyntheticCreatinineReleaseIssuer/v1'
GRANT_ACTOR = 'synthetic-creatinine-orchestrator'
GRANT_TARGET = OutputTarget(context={'patient_id': 'synthetic-p1', 'encounter_id': 'synthetic-e1'},
    request_id='synthetic-creatinine-request', intended_use=USE,
    destination='synthetic-creatinine-local', recipient='synthetic-creatinine-reviewer')
# Version 1 local fixture configuration. Dates are intentional, never inferred from a clock or evidence.
GRANT_WINDOW = ValidityWindow(start=datetime(2026, 10, 4, 12, tzinfo=timezone.utc),
    end=datetime(2026, 10, 4, 12, 5, tzinfo=timezone.utc))


def _render_statement(comparison):
    comparison = RecordedCreatinineComparison.model_validate(comparison)
    a, b = comparison.earlier_value, comparison.later_value
    if comparison.direction == 'unchanged':
        return (f'Recorded serum creatinine was unchanged between the selected samples ({a} mg/dL then {b} mg/dL). '
                'Synthetic evaluation only; bounded historical comparison.')
    verb = 'increased' if comparison.direction == 'increase' else 'decreased'
    return (f'Recorded serum creatinine {verb} from {a} mg/dL to {b} mg/dL between the selected samples. '
            'Synthetic evaluation only; bounded historical comparison.')


def _nodes(lineage):
    """Validate supplied retained contracts; do not catch operational/validation errors."""
    if lineage is None:
        return {}
    if not isinstance(lineage, LineageResult):
        raise TypeError('expected a generic LineageResult or explicit unavailable evidence')
    RepositoryCutoff.model_validate(lineage.cutoff.model_dump(warnings=False))
    result = {}
    for node in lineage.nodes:
        fact = validate_fact(node.stored.fact)
        IngestionMetadata.model_validate(node.stored.ingestion.model_dump(warnings=False))
        if fact.reference in result:
            raise ValueError('duplicate exact lineage node')
        result[fact.reference] = node.stored
    return result


def _snapshot_scope(selection, lineage):
    """Bind supplied evidence in the existing narrow scope field, without a new manifest type."""
    output = 'unavailable' if lineage is None else content_digest(lineage.cutoff)
    return (SCOPE + ' Intended use: SyntheticHistoricalCreatinineComparison:1; '
        'selection=' + content_digest(selection) + '; comparison=' + content_digest(compare_recorded_creatinine(selection))
        + '; output_cutoff=' + output + '.')


def build_creatinine_trend_snapshot(*, selection, inference, lineage, patient, encounter, at, id):
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    inference = ClinicalInference.model_validate(inference)
    nodes = _nodes(lineage)
    references = (*tuple(f.reference for f in selection.selected), inference.reference)
    # Missing evidence remains missing; never fill a durable-read gap from the selection.
    facts = tuple(nodes[ref].fact for ref in references if ref in nodes)
    return ContextSnapshot(id=id, version='1', patient=patient, encounter=encounter,
        binding=inference.binding, facts=facts, sources=tuple(dict.fromkeys(f.provenance.source for f in facts)),
        created_at=_at(at), temporal_cutoff=_at(at), completeness='partial',
        completeness_scope=_snapshot_scope(selection, lineage), limitations=LIMITATIONS)


def build_creatinine_trend_candidate(*, snapshot, comparison, inference, at, id):
    snapshot = ContextSnapshot.model_validate(snapshot)
    RecordedCreatinineComparison.model_validate(comparison)
    inference = ClinicalInference.model_validate(inference)
    return ClinicalRecommendation(id=id, revision='1', snapshot=snapshot, intended_use=USE,
        claims=(ClinicalClaim(id='recorded-creatinine-comparison', action=inference.statement,
            rationale=RATIONALE, classifications=('deterministic',), basis=(inference.reference,),
            conditions=(inference.applicability,), warnings=(inference.validation_limitations, *inference.provenance.limitations),
            uncertainty=inference.uncertainty),), limitations=LIMITATIONS,
        provenance=Provenance(source=SOURCE, actor='SyntheticCreatinineCandidate/v1', recorded_at=_at(at),
            upstream=(LineageEdge(target=inference.reference, relationship='copied_from'),),
            lineage='complete', limitations=LIMITATIONS), created_at=_at(at))


def render_creatinine_trend(*, candidate, comparison, target, at, id):
    candidate = ClinicalRecommendation.model_validate(candidate)
    target = OutputTarget.model_validate(target)
    return RenderedRecommendation(id=id, revision='1', candidate=candidate.reference,
        snapshot=candidate.snapshot.reference, content=_render_statement(comparison),
        destination=target.destination, rendered_at=_at(at))


def creatinine_trend_governance_policy(*, snapshot, selection, inference):
    snapshot = ContextSnapshot.model_validate(snapshot)
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    inference = ClinicalInference.model_validate(inference)
    evidence = (inference.reference, *tuple(f.reference for f in selection.selected))
    artifacts = (RECORDED_CREATININE_TREND_METHOD, FIDELITY, *RULES)
    policy = GovernancePolicy(reference=_ref('governance_policy', 'SyntheticCreatinineHistoricalRelease'),
        intended_use=USE, safety_policy=SAFETY, freshness_policy=FRESHNESS,
        authorization_policy=AUTHORIZATION, content_validation_method=FIDELITY,
        required_rules=RULES, required_context=(snapshot.reference, *evidence),
        required_dependencies=tuple(DependencyRequirement(reference=ref, updates_required=False)
            for ref in (*evidence, *artifacts)), max_assessment_age=timedelta(seconds=30))
    # Resolve per-context requirements without assigning different policies one immutable identity.
    return GovernancePolicy.model_validate({**policy.model_dump(),
        'reference': _ref('governance_policy', 'SyntheticCreatinineHistoricalRelease/' + content_digest(policy))})


def _evidence(selection, comparison, inference, lineage, snapshot):
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    comparison = RecordedCreatinineComparison.model_validate(comparison)
    inference = ClinicalInference.model_validate(inference)
    snapshot = ContextSnapshot.model_validate(snapshot)
    failed, missing = [], []
    if not selection.successful:
        return ['selection is not a usable exact pair'], []
    expected_comparison = compare_recorded_creatinine(selection)
    if (canonical_payload(comparison) != canonical_payload(expected_comparison)):
        failed.append('comparison does not preserve selected references values unit and sample times')
    refs = tuple(f.reference for f in selection.selected)
    edges = tuple(LineageEdge(target=ref, relationship='derived_from') for ref in refs)
    if inference.inputs != refs or inference.provenance.upstream != edges:
        failed.append('inference exact inputs or declarations differ')
    nodes = _nodes(lineage)
    expected_facts = (*selection.selected, inference)
    if lineage is None:
        missing.append('durable lineage unavailable')
    else:
        if lineage.reference != inference.reference or lineage.target != selection.target:
            failed.append('lineage root or scope differs')
        if (lineage.cutoff.repository_id != selection.cutoff.repository_id
                or lineage.cutoff.fact_watermark <= selection.cutoff.fact_watermark):
            failed.append('lineage output cutoff does not follow input cutoff')
        sequences = [n.stored.ingestion.ingestion_sequence for n in lineage.nodes]
        if sequences != sorted(set(sequences)):
            failed.append('lineage node ordering or ingestion identity differs')
        for fact in expected_facts:
            node = nodes.get(fact.reference)
            if node is None:
                missing.append('required exact retained fact unavailable')
            elif (canonical_payload(node.fact) != canonical_payload(fact)
                    or node.ingestion.repository_id != lineage.cutoff.repository_id
                    or node.ingestion.ingestion_sequence > lineage.cutoff.fact_watermark
                    or (node.ingestion.ingestion_sequence > selection.cutoff.fact_watermark
                        if fact.kind == 'observation' else node.ingestion.ingestion_sequence <= selection.cutoff.fact_watermark)):
                failed.append('retained fact body or prefix membership differs')
        if tuple((a.owner, a.ordinal, a.edge) for a in lineage.assertions) != tuple(
                (inference.reference, i, edge) for i, edge in enumerate(edges)):
            failed.append('resolved declarations differ')
        if tuple((d.owner, d.ordinal, d.basis_ordinal, d.source) for d in lineage.dependencies) != tuple(
                (inference.reference, i, None, ref) for i, ref in enumerate(refs)):
            failed.append('resolved dependencies differ')
        if set(nodes) - {inference.reference, *refs} or lineage.associations or lineage.confirmations:
            failed.append('unexpected lineage structure')
        if any(n.roles != ('evidence',) for n in lineage.nodes):
            failed.append('lineage evidence roles differ')
        expected_ancestry = tuple((ref, frozenset((inference.reference, *refs)) if ref == inference.reference
            else frozenset((ref,))) for ref in nodes)
        if lineage.ancestry != expected_ancestry:
            failed.append('lineage ancestry differs')
        if tuple((p.reference, p.lineage, p.limitations) for p in lineage.provenance) != tuple(
                (r, n.fact.provenance.lineage, n.fact.provenance.limitations) for r, n in nodes.items()):
            failed.append('lineage disclosures differ')
        if lineage.coverage != 'complete_for_declared_visible_graph' or lineage.unresolved:
            missing.append('required declared ancestry unresolved')
    expected_by_ref = {f.reference: f for f in expected_facts}
    snapshot_refs = tuple(f.reference for f in snapshot.facts)
    if set(expected_by_ref) - set(snapshot_refs):
        missing.append('snapshot required facts unavailable')
    if (snapshot_refs != tuple(ref for ref in expected_by_ref if ref in snapshot_refs)
            or any(canonical_payload(f) != canonical_payload(expected_by_ref[f.reference]) for f in snapshot.facts
                   if f.reference in expected_by_ref)):
        failed.append('snapshot exact membership or retained content differs')
    if (snapshot.binding != inference.binding or snapshot.binding.target != selection.target
            or snapshot.completeness != 'partial' or snapshot.completeness_scope != _snapshot_scope(selection, lineage)
            or snapshot.limitations != LIMITATIONS or snapshot.lineage_nodes
            or snapshot.sources != tuple(dict.fromkeys(f.provenance.source for f in snapshot.facts))):
        failed.append('snapshot scope or disclosures differ')
    return failed, missing


def _output(selection, comparison, inference, snapshot, candidate, rendering, target):
    selection = CreatinineTrendSelectionResult.model_validate(selection)
    comparison = RecordedCreatinineComparison.model_validate(comparison)
    inference = ClinicalInference.model_validate(inference)
    snapshot = ContextSnapshot.model_validate(snapshot)
    candidate = ClinicalRecommendation.model_validate(candidate)
    rendering = RenderedRecommendation.model_validate(rendering)
    target = OutputTarget.model_validate(target)
    failed, missing = [], []
    if not selection.successful:
        return ['selection is not a usable exact pair'], []
    # Independent meaning oracle: actual selected Decimal values, not renderer output or its helper.
    a, b = (fact.value.value.value for fact in selection.selected)
    if a == b:
        expected = (f'Recorded serum creatinine was unchanged between the selected samples ({a} mg/dL then {b} mg/dL). '
                    'Synthetic evaluation only; bounded historical comparison.')
    else:
        expected = (f'Recorded serum creatinine {"increased" if b > a else "decreased"} from {a} mg/dL to {b} mg/dL '
                    'between the selected samples. Synthetic evaluation only; bounded historical comparison.')
    if not callable(build_creatinine_trend_inference):
        missing.append('required inference implementation unavailable')
    elif inference.time.event is None:
        failed.append('inference execution time missing')
    else:
        try:
            rebuilt = build_creatinine_trend_inference(selection=selection, comparison=compare_recorded_creatinine(selection),
                inference_id=inference.id, revision=inference.revision, executed_at=inference.time.event)
        except ValueError:
            failed.append('inference execution violates source availability bound')
        else:
            # Reasoned generic revision links are retained metadata, never evidence dependencies.
            rebuilt = ClinicalInference.model_validate({**rebuilt.model_dump(),
                'supersedes': inference.supersedes, 'correction_reason': inference.correction_reason})
            if canonical_payload(inference) != canonical_payload(rebuilt):
                failed.append('inference outside exact Phase B contract')
    if inference.statement != expected or inference.method != RECORDED_CREATININE_TREND_METHOD:
        failed.append('inference wording or method differs')
    if len(candidate.claims) != 1:
        failed.append('exactly one descriptive claim required')
    else:
        claim = candidate.claims[0]
        if (claim.id != 'recorded-creatinine-comparison' or claim.action != expected or claim.rationale != RATIONALE
                or claim.classifications != ('deterministic',) or claim.basis != (inference.reference,)
                or claim.conditions != (inference.applicability,)
                or claim.warnings != (inference.validation_limitations, *inference.provenance.limitations)
                or claim.uncertainty != inference.uncertainty):
            failed.append('claim outside closed descriptive grammar')
    if (canonical_payload(candidate.snapshot) != canonical_payload(snapshot) or candidate.intended_use != USE
            or candidate.knowledge or candidate.evidence or candidate.alternatives or candidate.monitoring
            or candidate.limitations != LIMITATIONS or candidate.provenance != Provenance(
                source=SOURCE, actor='SyntheticCreatinineCandidate/v1', recorded_at=candidate.created_at,
                upstream=(LineageEdge(target=inference.reference, relationship='copied_from'),),
                lineage='complete', limitations=LIMITATIONS)):
        failed.append('candidate envelope differs')
    if (rendering.content != expected or rendering.candidate != candidate.reference
            or rendering.snapshot != snapshot.reference or rendering.destination != target.destination
            or target.context != selection.target or target.intended_use != USE):
        failed.append('rendering or target differs')
    return failed, missing


def evaluate_creatinine_trend(*, selection, comparison, inference, lineage, snapshot, candidate, rendering, target, at, id):
    candidate = ClinicalRecommendation.model_validate(candidate)
    rendering = RenderedRecommendation.model_validate(rendering)
    results = (_evidence(selection, comparison, inference, lineage, snapshot),
        _output(selection, comparison, inference, snapshot, candidate, rendering, target))
    checks = tuple(SafetyCheck(id=rule.id, rule=rule, required=True, overrideable=False,
        outcome='hard_failure' if failed else 'unavailable' if missing else 'no_detected_violation',
        reason='; '.join(failed or missing) if failed or missing else 'Exact bounded synthetic check passed.',
        coverage=SCOPE) for rule, (failed, missing) in zip(RULES, results))
    return SafetyEvaluation(id=id, revision='1', candidate=candidate.reference, rendering=rendering.reference,
        snapshot=snapshot.reference, policy=SAFETY, checks=checks,
        exact_meaning='failed' if any(f for f, _ in results) else 'unavailable' if any(m for _, m in results) else 'matched',
        coverage=SCOPE, limitations=LIMITATIONS, evaluated_at=_at(at))


def validate_creatinine_trend_content(*, selection, comparison, inference, lineage, snapshot, review, payload, target, at, validity, id):
    review = RecommendationReview.model_validate(review)
    payload = PresentationPayload.model_validate(payload)
    if review.rendering is None:
        raise ValueError('creatinine fidelity requires rendered content')
    failed, missing = _evidence(selection, comparison, inference, lineage, snapshot)
    output_failed, output_missing = _output(selection, comparison, inference, snapshot, review.candidate, review.rendering, target)
    failed += output_failed
    missing += output_missing
    if len(review.evaluations) != 1:
        failed.append('one performed evaluation required')
    for evaluation in review.evaluations:
        expected = evaluate_creatinine_trend(selection=selection, comparison=comparison, inference=inference,
            lineage=lineage, snapshot=snapshot, candidate=review.candidate, rendering=review.rendering,
            target=target, at=evaluation.evaluated_at, id=evaluation.id)
        if canonical_payload(evaluation) != canonical_payload(expected):
            failed.append('evaluation differs from performed checks')
    if canonical_payload(payload) != canonical_payload(required_payload(review, (), LIMITATIONS)):
        failed.append('required payload disclosures differ')
    return ContentValidationAssertion(reference=_ref('content_validation', id), method=FIDELITY, target=target,
        content_digest=review_digest(review), payload_digest=content_digest(payload), coverage='in_scope',
        outcome='failed' if failed else 'unavailable' if missing else 'matched',
        assessor='SyntheticCreatinineFidelity/v1', assessed_at=_at(at), validity=validity,
        rationale='; '.join(failed or missing) if failed or missing else 'Exact evidence meaning and complete payload checked.',
        limitations=LIMITATIONS)


def assess_creatinine_trend_context(*, selection, comparison, inference, lineage, snapshot, at, validity, id):
    failed, missing = _evidence(selection, comparison, inference, lineage, snapshot)
    at = _at(at)
    validity = ValidityWindow.model_validate(validity)
    adequate = not failed and not missing and snapshot.created_at <= at and validity.contains(at)
    refs = (snapshot.reference, inference.reference, *tuple(f.reference for f in selection.selected))
    times = (snapshot.temporal_cutoff, inference.time.event, *tuple(f.time.event for f in selection.selected))
    return ContextFreshnessAssessment(reference=_ref('freshness_assessment', id), snapshot=snapshot.reference,
        policy=FRESHNESS, assessed_at=at, adequate=adequate, material_change=False,
        items=tuple(FreshnessItem(reference=ref, state='fresh' if adequate else 'unknown', clinical_time=time,
            validity=validity if adequate else None,
            rationale='Suitability for the supplied historical prefix only; later corrections not assessed.')
            for ref, time in zip(refs, times)), assessor='SyntheticCreatinineHistoricalContext/v1',
        rationale='Bounded historical context only; no current clinical eligibility or protected final recheck.')


def assess_creatinine_trend_dependencies(*, selection, comparison, inference, lineage, snapshot, policy, at, validity):
    policy = GovernancePolicy.model_validate(policy)
    failed, missing = _evidence(selection, comparison, inference, lineage, snapshot)
    validity = ValidityWindow.model_validate(validity)
    at = _at(at)
    facts = {f.reference for f in (*selection.selected, inference)}
    nodes = _nodes(lineage)
    states = []
    for requirement in policy.required_dependencies:
        ref = requirement.reference
        available = (not failed and not missing and ref in nodes) if ref in facts else (
            (ref == RECORDED_CREATININE_TREND_METHOD and callable(build_creatinine_trend_inference))
            or (ref == FIDELITY and callable(validate_creatinine_trend_content))
            or (ref in RULES and callable(evaluate_creatinine_trend)))
        available = available and validity.contains(at)
        states.append(DependencyState(reference=ref, state='available' if available else 'unavailable',
            updates='not_required', validity=validity if available else None,
            rationale='Exact historical evidence or local versioned implementation; no biological independence claim.'))
    return tuple(states)


def issue_synthetic_creatinine_release(*, selection, inference, review, payload, policy, target, actor, at, id):
    """Evaluate the fixed v1 synthetic grant; never accept a caller-supplied allow flag."""
    review = RecommendationReview.model_validate(review)
    payload = PresentationPayload.model_validate(payload)
    policy = GovernancePolicy.model_validate(policy)
    target = OutputTarget.model_validate(target)
    at = _at(at)
    expected = creatinine_trend_governance_policy(snapshot=review.candidate.snapshot, selection=selection, inference=inference)
    permitted = (actor == GRANT_ACTOR and target == GRANT_TARGET
        and canonical_payload(policy) == canonical_payload(expected)
        and review.candidate.intended_use == USE and review.candidate.snapshot.binding.target == target.context
        and canonical_payload(payload) == canonical_payload(required_payload(review, (), LIMITATIONS))
        and review.candidate.created_at <= at and review.rendering is not None
        and review.rendering.rendered_at <= at and all(e.evaluated_at <= at for e in review.evaluations)
        and GRANT_WINDOW.contains(at))
    return AuthorizationAssertion(reference=_ref('authorization', id), policy=AUTHORIZATION,
        subject=actor, role='synthetic-creatinine-reviewer', issuer=ISSUER, action='release', target=target,
        content_digest=review_digest(review), payload_digest=content_digest(payload),
        governance_policy_digest=content_digest(policy), outcome='allow' if permitted else 'deny',
        issued_at=at, validity=GRANT_WINDOW,
        rationale='Fixed creatinine v1 synthetic fixture grant; not authentication or patient-care authorization.')


def assemble_creatinine_trend_runtime(*, snapshot, candidate, target, active_request, active_output,
                                     authorization, freshness, dependencies, at):
    snapshot = ContextSnapshot.model_validate(snapshot)
    candidate = ClinicalRecommendation.model_validate(candidate)
    target = OutputTarget.model_validate(target)
    authorization = AuthorizationAssertion.model_validate(authorization)
    if authorization.issuer != ISSUER or authorization.policy != AUTHORIZATION:
        raise ValueError('runtime requires the creatinine synthetic issuer and grant policy')
    registered = (snapshot.binding.target == target.context and snapshot.patient.patient_id == target.context.patient_id
        and snapshot.encounter is not None and snapshot.encounter.encounter_id == target.context.encounter_id
        and snapshot.encounter.patient_id == target.context.patient_id)
    identity = snapshot.binding.verification if registered else IdentityVerification(status='unresolved',
        method='synthetic-creatinine-context-comparison/v1', verifier='synthetic-creatinine-harness',
        assessed_at=_at(at), source=SOURCE, ambiguity='registered context differs from target')
    return RuntimeState(target=target, identity=identity,
        request_state='active' if target == active_request else 'superseded',
        output_state='current' if candidate.reference == active_output else 'superseded', observed_at=_at(at),
        authorization=authorization, freshness=freshness, dependencies=dependencies)


def release_creatinine_trend(*, selection, comparison, inference, lineage, snapshot, candidate, rendering,
                            target, active_request, active_output, actor, at, validity, id):
    """In-memory historical assessment only; exceptions escape without a fabricated decision."""
    at = _at(at)
    evaluation = evaluate_creatinine_trend(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, candidate=candidate, rendering=rendering, target=target, at=at, id=id+'-safety')
    review = RecommendationReview(candidate=candidate, rendering=rendering, evaluations=(evaluation,))
    payload = required_payload(review, (), LIMITATIONS)
    validation = validate_creatinine_trend_content(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, review=review, payload=payload, target=target,
        at=at, validity=validity, id=id+'-content')
    policy = creatinine_trend_governance_policy(snapshot=snapshot, selection=selection, inference=inference)
    freshness = assess_creatinine_trend_context(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, at=at, validity=validity, id=id+'-context')
    dependencies = assess_creatinine_trend_dependencies(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, policy=policy, at=at, validity=validity)
    authorization = issue_synthetic_creatinine_release(selection=selection, inference=inference, review=review,
        payload=payload, policy=policy, target=target, actor=actor, at=at, id=id+'-authorization')
    state = assemble_creatinine_trend_runtime(snapshot=snapshot, candidate=candidate, target=target,
        active_request=active_request, active_output=active_output, authorization=authorization,
        freshness=freshness, dependencies=dependencies, at=at)
    assessment = assess_release(reference=_ref('release_eligibility', id), review=review, payload=payload,
        target=target, policy=policy, content_validation=validation, state=state,
        assessor='SyntheticCreatinineHistoricalRelease/v1', at=at, validity=validity)
    return decide_release(reference=_ref('release_decision', id), assessment=assessment, actor=actor, at=at)
