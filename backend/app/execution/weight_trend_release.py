"""Version 1 synthetic historical weight governance; no delivery or durability.

Inputs are committed repository reads supplied by the local harness. These
functions do not authenticate those reads or inspect current repository state.
"""
from datetime import datetime, timedelta, timezone

from app.execution.weight_trend import (
    RECORDED_WEIGHT_TREND_METHOD, RecordedWeightComparison, WeightTrendSelectionResult,
    build_weight_trend_inference, compare_recorded_weights,
)
from app.models.clinical.common import (
    ContextTarget, IdentityVerification, LineageEdge, Provenance, Reference, Source,
)
from app.models.clinical.decisions import (
    ClinicalClaim, ClinicalRecommendation, RecommendationReview, RenderedRecommendation,
    SafetyCheck, SafetyEvaluation,
)
from app.models.clinical.facts import ClinicalInference, ContextSnapshot
from app.models.clinical.governance import (
    AuthorizationAssertion, ContentValidationAssertion, ContextFreshnessAssessment,
    DependencyRequirement, DependencyState, FreshnessItem, GovernancePolicy,
    OutputTarget, RuntimeState, ValidityWindow, content_digest, required_payload, review_digest,
)
from app.persistence.mapping import canonical_payload
from app.services.governance_service import assess_release, decide_release

INTENDED_USE = 'Synthetic evaluation of a fixed historical recorded-weight comparison, with no patient-care use or delivery.'
LIMITATIONS = (INTENDED_USE, 'No clinical validation or continuing clinical eligibility; no delivery.')
RATIONALE = 'Deterministic comparison of the two exact retained kilogram observations.'
SCOPE = 'Exact selected observations and inference for one fixed historical synthetic request only.'
SOURCE = Source(namespace='clinrx.synthetic', identifier='WeightTrendRelease', version='1', channel='system')


def _ref(kind, name):
    return Reference(kind=kind, id=name, version='1')


USE = _ref('intended_use', 'SyntheticHistoricalWeightComparison')
SAFETY = _ref('safety_policy', 'SyntheticHistoricalWeightSafety')
FRESHNESS = _ref('freshness_policy', 'SyntheticHistoricalWeightContext')
AUTHORIZATION = _ref('authorization_policy', 'SyntheticWeightReleaseGrant')
FIDELITY = _ref('content_validation_method', 'SyntheticWeightFidelity')
RULES = (_ref('safety_rule', 'exact_evidence_and_input_suitability'),
         _ref('safety_rule', 'bounded_descriptive_output'))
GRANT_TARGET = OutputTarget(context=ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1'),
    request_id='synthetic-weight-request', intended_use=USE, destination='synthetic-local', recipient='synthetic-reviewer')
GRANT_WINDOW = ValidityWindow(start=datetime(2026, 9, 25, 14, 0, 1, 123456, tzinfo=timezone.utc),
                             end=datetime(2026, 9, 25, 14, 1, 1, 123456, tzinfo=timezone.utc))


def _statement(comparison):
    comparison = RecordedWeightComparison.model_validate(comparison)
    if comparison.direction == 'unchanged':
        return (f'Recorded weight was unchanged at {comparison.earlier_kg} kg between the selected observations. '
                'This comparison does not establish nutritional status. Synthetic evaluation only.')
    verb = 'decreased' if comparison.direction == 'decrease' else 'increased'
    return (f'Recorded weight {verb} from {comparison.earlier_kg} kg to {comparison.later_kg} kg between the selected observations. '
            'This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.')


def build_weight_trend_snapshot(*, selection, inference, lineage, patient, encounter, at, id):
    """Embed actual resolved records, including partial evidence without fabrication."""
    selection = WeightTrendSelectionResult.model_validate(selection)
    inference = ClinicalInference.model_validate(inference)
    nodes = {node.stored.fact.reference: node.stored.fact for node in lineage.nodes}
    references = (*tuple(f.reference for f in selection.selected), inference.reference)
    facts = tuple(nodes[r] for r in references if r in nodes)
    return ContextSnapshot(id=id, version='1', patient=patient, encounter=encounter,
        binding=inference.binding, facts=facts,
        sources=tuple(dict.fromkeys(f.provenance.source for f in facts)), created_at=at,
        temporal_cutoff=at, completeness='partial', completeness_scope=SCOPE,
        limitations=LIMITATIONS)


def build_weight_trend_candidate(*, snapshot, comparison, inference, at, id):
    inference = ClinicalInference.model_validate(inference)
    return ClinicalRecommendation(id=id, revision='1', snapshot=snapshot, intended_use=USE,
        claims=(ClinicalClaim(id='recorded-weight-comparison', action=_statement(comparison),
            rationale=RATIONALE, classifications=('deterministic',), basis=(inference.reference,),
            conditions=(inference.applicability,),
            warnings=(inference.validation_limitations, *inference.provenance.limitations),
            uncertainty=inference.uncertainty),), limitations=LIMITATIONS,
        provenance=Provenance(source=SOURCE, actor='WeightTrendCandidate/v1', recorded_at=at,
            upstream=(LineageEdge(target=inference.reference, relationship='copied_from'),),
            lineage='complete', limitations=LIMITATIONS), created_at=at)


def render_weight_trend(*, candidate, comparison, target, at, id):
    return RenderedRecommendation(id=id, revision='1', candidate=candidate.reference,
        snapshot=candidate.snapshot.reference, content=_statement(comparison),
        destination=target.destination, rendered_at=at)


def weight_trend_governance_policy(*, snapshot, selection, inference):
    evidence = (inference.reference, *tuple(f.reference for f in selection.selected))
    artifacts = (RECORDED_WEIGHT_TREND_METHOD, FIDELITY, *RULES)
    policy = GovernancePolicy(reference=_ref('governance_policy', 'SyntheticHistoricalWeightRelease'),
        intended_use=USE, safety_policy=SAFETY, freshness_policy=FRESHNESS,
        authorization_policy=AUTHORIZATION, content_validation_method=FIDELITY,
        required_rules=RULES, required_context=(snapshot.reference, *evidence),
        required_dependencies=tuple(DependencyRequirement(reference=r, updates_required=False)
                                    for r in (*evidence, *artifacts)),
        max_assessment_age=timedelta(seconds=30))
    # The resolved requirements include execution-specific exact context. Give
    # different requirements different immutable identities under the same v1
    # profile; this digest establishes identity, never semantic conformity.
    return GovernancePolicy.model_validate({**policy.model_dump(),
        'reference': _ref('governance_policy', 'SyntheticHistoricalWeightRelease/' + content_digest(policy))})


def _evidence(selection, comparison, inference, lineage, snapshot):
    """Return checked contradiction and unavailability separately; never read latest."""
    selection = WeightTrendSelectionResult.model_validate(selection)
    comparison = RecordedWeightComparison.model_validate(comparison)
    inference = ClinicalInference.model_validate(inference)
    snapshot = ContextSnapshot.model_validate(snapshot)
    failed, unavailable = [], []
    if not selection.successful:
        return ['original selection unsuccessful'], []
    refs = tuple(f.reference for f in selection.selected)
    if comparison.model_dump(mode='json') != compare_recorded_weights(selection).model_dump(mode='json'):
        failed.append('comparison differs from original exact observations')
    if lineage.reference != inference.reference or lineage.target != selection.target:
        failed.append('lineage root or scope mismatch')
    if (lineage.cutoff.repository_id != selection.cutoff.repository_id
            or lineage.cutoff.fact_watermark <= selection.cutoff.fact_watermark):
        failed.append('lineage output prefix does not follow the input prefix')
    nodes = {n.stored.fact.reference: n.stored for n in lineage.nodes}
    if len(nodes) != len(lineage.nodes):
        failed.append('duplicate resolved record')
    root = nodes.get(inference.reference)
    if root is None:
        unavailable.append('required inference unavailable')
    elif (canonical_payload(root.fact) != canonical_payload(inference)
          or root.ingestion.repository_id != lineage.cutoff.repository_id
          or not selection.cutoff.fact_watermark < root.ingestion.ingestion_sequence <= lineage.cutoff.fact_watermark):
        failed.append('inference differs from retained visible root')
    for observation in selection.selected:
        node = nodes.get(observation.reference)
        if node is None:
            unavailable.append('required observation unavailable')
        elif (canonical_payload(node.fact) != canonical_payload(observation)
              or node.ingestion.repository_id != selection.cutoff.repository_id
              or node.ingestion.ingestion_sequence > selection.cutoff.fact_watermark):
            failed.append('selected observation differs from retained input prefix')
    edges = tuple(LineageEdge(target=r, relationship='derived_from') for r in refs)
    if inference.inputs != refs or inference.provenance.upstream != edges:
        failed.append('inference inputs or evidentiary edges mismatch')
    if tuple((a.ordinal, a.edge) for a in lineage.assertions if a.owner == inference.reference) != tuple(enumerate(edges)):
        failed.append('resolved assertions mismatch')
    if tuple((d.ordinal, d.basis_ordinal, d.source) for d in lineage.dependencies
             if d.owner == inference.reference) != tuple((i, None, r) for i, r in enumerate(refs)):
        failed.append('resolved dependencies mismatch')
    # V1 observations have no upstream assertions. Validate the entire supplied
    # resolution contract, not only the root-filtered projection.
    if any(a.owner != inference.reference for a in lineage.assertions) or any(
            d.owner != inference.reference for d in lineage.dependencies):
        failed.append('unexpected nonroot evidentiary declaration')
    if any(n.roles != ('evidence',) for n in lineage.nodes):
        failed.append('resolved evidence roles mismatch')
    ordered_refs = tuple(n.stored.fact.reference for n in lineage.nodes)
    expected_ancestry = tuple((r, frozenset((inference.reference, *refs)) if r == inference.reference
                              else frozenset((r,))) for r in ordered_refs)
    if lineage.ancestry != expected_ancestry:
        failed.append('resolved ancestry mismatch')
    if tuple((p.reference, p.lineage, p.limitations) for p in lineage.provenance) != tuple(
            (n.stored.fact.reference, n.stored.fact.provenance.lineage, n.stored.fact.provenance.limitations)
            for n in lineage.nodes):
        failed.append('resolved provenance disclosures mismatch')
    if lineage.coverage != 'complete_for_declared_visible_graph' or lineage.unresolved:
        unavailable.append('required declared lineage unresolved')
    if lineage.associations or lineage.confirmations or set(nodes) - {inference.reference, *refs}:
        failed.append('unexpected lineage structure')
    expected_facts = (*selection.selected, inference)
    if tuple(canonical_payload(f) for f in snapshot.facts) != tuple(canonical_payload(f) for f in expected_facts):
        (unavailable if len(snapshot.facts) < 3 else failed).append('snapshot exact membership mismatch')
    if (snapshot.binding != inference.binding or snapshot.binding.target != selection.target
            or snapshot.completeness_scope != SCOPE or snapshot.limitations != LIMITATIONS
            or snapshot.lineage_nodes or snapshot.completeness != 'partial'
            or snapshot.sources != tuple(dict.fromkeys(f.provenance.source for f in expected_facts))):
        failed.append('snapshot scope or disclosures mismatch')
    return failed, unavailable


def _bounded(comparison, selection, inference, snapshot, candidate, rendering, target):
    """Closed-field validation independent of renderer output or caller hashes."""
    selection = WeightTrendSelectionResult.model_validate(selection)
    comparison = RecordedWeightComparison.model_validate(comparison)
    inference = ClinicalInference.model_validate(inference)
    snapshot = ContextSnapshot.model_validate(snapshot)
    candidate = ClinicalRecommendation.model_validate(candidate)
    rendering = RenderedRecommendation.model_validate(rendering)
    target = OutputTarget.model_validate(target)
    failed = []
    # Derive direction from actual values; do not use rendering or inference text
    # as the oracle. Exact retained representation is checked by _evidence.
    a, b = comparison.earlier_kg, comparison.later_kg
    if b == a:
        expected = f'Recorded weight was unchanged at {a} kg between the selected observations. This comparison does not establish nutritional status. Synthetic evaluation only.'
    else:
        expected = f'Recorded weight {"decreased" if b < a else "increased"} from {a} kg to {b} kg between the selected observations. This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.'
    if not selection.successful:
        return ['original selection unsuccessful']
    allowed = {'synthetic uncertainty'}
    if any(text not in allowed for f in selection.selected for text in f.uncertainty):
        failed.append('unsupported synthetic input disclosure')
    if inference.time.event is None:
        failed.append('missing inference execution event')
    else:
        try:
            rebuilt = build_weight_trend_inference(selection=selection, comparison=compare_recorded_weights(selection),
                inference_id=inference.id, revision=inference.revision, executed_at=inference.time.event)
        except ValueError:
            failed.append('inference execution violates Phase 2 availability')
        else:
            if canonical_payload(inference) != canonical_payload(rebuilt):
                failed.append('inference outside exact Phase 2 grammar')
    if inference.statement != expected or inference.method != RECORDED_WEIGHT_TREND_METHOD:
        failed.append('inference meaning or method mismatch')
    if len(candidate.claims) != 1:
        failed.append('exactly one descriptive claim required')
    else:
        claim = candidate.claims[0]
        if (claim.id != 'recorded-weight-comparison' or claim.action != expected
                or claim.rationale != RATIONALE or claim.classifications != ('deterministic',)
                or claim.basis != (inference.reference,) or claim.conditions != (inference.applicability,)
                or claim.warnings != (inference.validation_limitations, *inference.provenance.limitations)
                or claim.uncertainty != inference.uncertainty):
            failed.append('claim outside closed descriptive grammar')
    if (canonical_payload(candidate.snapshot) != canonical_payload(snapshot)
            or candidate.intended_use != USE or candidate.knowledge or candidate.evidence
            or candidate.alternatives or candidate.monitoring or candidate.limitations != LIMITATIONS
            or candidate.provenance != Provenance(source=SOURCE, actor='WeightTrendCandidate/v1',
                recorded_at=candidate.created_at, upstream=(LineageEdge(target=inference.reference, relationship='copied_from'),),
                lineage='complete', limitations=LIMITATIONS)):
        failed.append('candidate envelope outside synthetic scope')
    if (rendering.content != expected or rendering.candidate != candidate.reference
            or rendering.snapshot != snapshot.reference or rendering.destination != target.destination
            or target.context != selection.target or target.intended_use != USE):
        failed.append('rendering or target mismatch')
    return failed


def evaluate_weight_trend(*, selection, comparison, inference, lineage, snapshot, candidate, rendering, target, at, id):
    candidate = ClinicalRecommendation.model_validate(candidate)
    rendering = RenderedRecommendation.model_validate(rendering)
    failed, unavailable = _evidence(selection, comparison, inference, lineage, snapshot)
    bounded = _bounded(comparison, selection, inference, snapshot, candidate, rendering, target)
    outcomes = ('hard_failure' if failed else 'unavailable' if unavailable else 'no_detected_violation',
                'hard_failure' if bounded else 'no_detected_violation')
    reasons = (failed or unavailable, bounded)
    checks = tuple(SafetyCheck(id=rule.id, rule=rule, required=True, outcome=outcome,
        reason='; '.join(problems) if problems else 'Closed synthetic check established conformity.',
        coverage=SCOPE, overrideable=False) for rule, outcome, problems in zip(RULES, outcomes, reasons))
    return SafetyEvaluation(id=id, revision='1', candidate=candidate.reference, rendering=rendering.reference,
        snapshot=snapshot.reference, policy=SAFETY, checks=checks,
        exact_meaning='failed' if failed or bounded else 'unavailable' if unavailable else 'matched',
        coverage=SCOPE, limitations=LIMITATIONS, evaluated_at=at)


def validate_weight_trend_content(*, selection, comparison, inference, lineage, snapshot, review, payload, target, at, validity, id):
    review = RecommendationReview.model_validate(review)
    if review.rendering is None:
        raise ValueError('weight fidelity requires rendered content')
    problems, missing = _evidence(selection, comparison, inference, lineage, snapshot)
    problems += _bounded(comparison, selection, inference, snapshot, review.candidate, review.rendering, target)
    if len(review.evaluations) != 1:
        problems.append('one concrete synthetic evaluation required')
    for evaluation in review.evaluations:
        expected = evaluate_weight_trend(selection=selection, comparison=comparison, inference=inference,
            lineage=lineage, snapshot=snapshot, candidate=review.candidate, rendering=review.rendering,
            target=target, at=evaluation.evaluated_at, id=evaluation.id)
        if canonical_payload(expected) != canonical_payload(evaluation):
            problems.append('evaluation differs from performed checks')
    if payload != required_payload(review, (), LIMITATIONS):
        problems.append('payload disclosure mismatch')
    return ContentValidationAssertion(reference=_ref('content_validation', id), method=FIDELITY,
        target=target, content_digest=review_digest(review), payload_digest=content_digest(payload),
        outcome='failed' if problems else 'unavailable' if missing else 'matched',
        coverage='in_scope', assessor='SyntheticWeightFidelity/v1', assessed_at=at, validity=validity,
        rationale='; '.join(problems or missing) if problems or missing else 'All retained meanings and complete payload checked.',
        limitations=LIMITATIONS)


def assess_weight_trend_context(*, selection, comparison, inference, lineage, snapshot, at, validity, id):
    failed, unavailable = _evidence(selection, comparison, inference, lineage, snapshot)
    # A historical suitability observation cannot precede context assembly.
    adequate = not failed and not unavailable and snapshot.created_at <= at and validity.contains(at)
    references = (snapshot.reference, inference.reference, *tuple(f.reference for f in selection.selected))
    times = (snapshot.temporal_cutoff, inference.time.event, *tuple(f.time.event for f in selection.selected))
    return ContextFreshnessAssessment(reference=_ref('freshness_assessment', id), snapshot=snapshot.reference,
        policy=FRESHNESS, assessed_at=at, adequate=adequate, material_change=False,
        items=tuple(FreshnessItem(reference=r, state='fresh' if adequate else 'unknown',
            clinical_time=t, validity=validity if adequate else None,
            rationale='Adequate only for the fixed historical prefix; later corrections not assessed.')
                    for r, t in zip(references, times)),
        assessor='SyntheticHistoricalWeightContext/v1', rationale='; '.join(failed or unavailable) if not adequate
            and (failed or unavailable) else 'Historical request only; no current physiological freshness or correction protection.')


def assess_weight_trend_dependencies(*, selection, comparison, inference, lineage, snapshot, policy, at, validity):
    failed, unavailable = _evidence(selection, comparison, inference, lineage, snapshot)
    nodes = {n.stored.fact.reference: n.stored.fact for n in lineage.nodes}
    expected = {f.reference: canonical_payload(f) for f in (*selection.selected, inference)}
    states = []
    for requirement in policy.required_dependencies:
        ref = requirement.reference
        if ref in expected:
            available = not failed and not unavailable and ref in nodes and canonical_payload(nodes[ref]) == expected[ref]
        else:
            available = ((ref == RECORDED_WEIGHT_TREND_METHOD and callable(build_weight_trend_inference))
                or (ref == FIDELITY and callable(validate_weight_trend_content))
                or (ref in RULES and callable(evaluate_weight_trend)))
        available = available and validity.contains(at)
        states.append(DependencyState(reference=ref, state='available' if available else 'unavailable',
            updates='not_required', validity=validity if available else None,
            rationale='Exact historical record or local v1 implementation checked; no live update claim.'))
    return tuple(states)


def issue_synthetic_weight_release(*, selection, inference, review, payload, policy, target, actor, at, id):
    """SyntheticWeightReleaseIssuer/v1: fixed local grant, not authentication."""
    expected_policy = weight_trend_governance_policy(snapshot=review.candidate.snapshot, selection=selection, inference=inference)
    known = actor in ('synthetic-orchestrator', 'synthetic-denied')
    permitted = (actor == 'synthetic-orchestrator' and target == GRANT_TARGET and policy == expected_policy
        and review.candidate.intended_use == USE and review.candidate.snapshot.binding.target == target.context
        and payload.rendering == review.rendering and payload == required_payload(review, (), LIMITATIONS)
        and review.candidate.created_at <= at and review.rendering is not None
        and review.rendering.rendered_at <= at and all(e.evaluated_at <= at for e in review.evaluations)
        and GRANT_WINDOW.contains(at))
    return AuthorizationAssertion(reference=_ref('authorization', id), policy=AUTHORIZATION,
        subject=actor, role='synthetic-release-role' if known else 'unknown-synthetic-role',
        issuer='SyntheticWeightReleaseIssuer/v1', action='release', target=target,
        content_digest=review_digest(review), payload_digest=content_digest(payload),
        governance_policy_digest=content_digest(policy), outcome='allow' if permitted else 'deny' if known else 'unknown',
        issued_at=at, validity=GRANT_WINDOW, rationale='Fixed local synthetic grant evaluated; no production identity or clinical authority.')


def assemble_weight_trend_runtime(*, snapshot, candidate, target, active_request, active_output,
                                  authorization, freshness, dependencies, at):
    registered = (snapshot.patient.patient_id == target.context.patient_id and snapshot.encounter is not None
                  and snapshot.encounter.encounter_id == target.context.encounter_id
                  and snapshot.encounter.patient_id == target.context.patient_id
                  and snapshot.binding.target == target.context)
    identity = snapshot.binding.verification if registered else IdentityVerification(status='unresolved',
        method='synthetic-registration-comparison/v1', verifier='synthetic-harness', assessed_at=at,
        source=SOURCE, ambiguity='registered context does not match request')
    return RuntimeState(target=target, identity=identity,
        request_state='active' if target == active_request else 'superseded',
        output_state='current' if candidate.reference == active_output else 'superseded', observed_at=at,
        authorization=authorization, freshness=freshness, dependencies=dependencies)


def release_weight_trend(*, selection, comparison, inference, lineage, snapshot, candidate, rendering,
                        target, active_request, active_output, actor, at, validity, id):
    """Compose actual producers into existing immutable release/withhold records."""
    evaluation = evaluate_weight_trend(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, candidate=candidate, rendering=rendering, target=target, at=at, id=id+'-safety')
    review = RecommendationReview(candidate=candidate, rendering=rendering, evaluations=(evaluation,))
    payload = required_payload(review, (), LIMITATIONS)
    validation = validate_weight_trend_content(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, review=review, payload=payload, target=target, at=at, validity=validity, id=id+'-content')
    policy = weight_trend_governance_policy(snapshot=snapshot, selection=selection, inference=inference)
    freshness = assess_weight_trend_context(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, at=at, validity=validity, id=id+'-context')
    dependencies = assess_weight_trend_dependencies(selection=selection, comparison=comparison, inference=inference, lineage=lineage,
        snapshot=snapshot, policy=policy, at=at, validity=validity)
    authorization = issue_synthetic_weight_release(selection=selection, inference=inference, review=review,
        payload=payload, policy=policy, target=target, actor=actor, at=at, id=id+'-authorization')
    state = assemble_weight_trend_runtime(snapshot=snapshot, candidate=candidate, target=target,
        active_request=active_request, active_output=active_output, authorization=authorization,
        freshness=freshness, dependencies=dependencies, at=at)
    assessment = assess_release(reference=_ref('release_eligibility', id), review=review, payload=payload,
        target=target, policy=policy, content_validation=validation, state=state,
        assessor='SyntheticWeightOrchestration/v1', at=at, validity=validity)
    return decide_release(reference=_ref('release_decision', id), assessment=assessment, actor=actor, at=at)
