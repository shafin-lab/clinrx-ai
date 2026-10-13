"""Real reopened synthetic evidence and independently specified release expectations."""
from dataclasses import replace as dc_replace
from datetime import timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text

from app.execution.weight_trend import compare_recorded_weights
from app.execution.weight_trend_release import (
    AUTHORIZATION, FIDELITY, GRANT_TARGET, GRANT_WINDOW, INTENDED_USE, LIMITATIONS, RULES,
    assess_weight_trend_context, assess_weight_trend_dependencies, assemble_weight_trend_runtime,
    build_weight_trend_candidate, build_weight_trend_snapshot, evaluate_weight_trend,
    issue_synthetic_weight_release, release_weight_trend, render_weight_trend,
    validate_weight_trend_content, weight_trend_governance_policy,
)
from app.models.clinical.common import LineageEdge, Reference, Unit
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.governance import (
    FreshnessItem, ReleaseDecision, RuntimeState, ValidityWindow, content_digest, required_payload, review_digest,
)
from app.persistence.database import create_database
from app.persistence.errors import StorageIntegrityError
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from app.services.governance_service import assess_release, decide_release
from test_persistence import AT, TARGET, database, registered, replace
from test_revision_chains import revision
from test_weight_trend import POLICY, save, select, weight
from test_weight_trend_inference import build, persist, resolve

NOW = POLICY.available_at + timedelta(seconds=1)
WINDOW = ValidityWindow(start=NOW, end=NOW + timedelta(seconds=20))


def evidence(engine, a='82', b='79', uncertainty='synthetic uncertainty'):
    observations = weight('a', a, label='z'), weight('b', b, AT + timedelta(hours=1), label='0')
    observations = (replace(observations[0],uncertainty=(uncertainty,)),observations[1])
    cutoff = save(engine, *reversed(observations))
    path = engine.url.database
    engine.dispose()
    reopened = create_database(path)
    try:
        selection = select(reopened, cutoff)
        comparison = compare_recorded_weights(selection)
        inference = build(selection)
        stored, output = persist(reopened, inference)
    finally:
        reopened.dispose()
    reopened = create_database(path)
    try:
        with transaction(reopened) as repo:
            inference = repo.load_fact(stored.fact.reference, target=TARGET).fact
            patient = repo.load_patient(TARGET.patient_id)
            encounter = repo.load_encounter(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id)
        lineage = resolve(reopened, inference, output)
    finally:
        reopened.dispose()
    snapshot = build_weight_trend_snapshot(selection=selection, inference=inference, lineage=lineage,
        patient=patient, encounter=encounter, at=NOW, id='snapshot')
    candidate = build_weight_trend_candidate(snapshot=snapshot, comparison=comparison, inference=inference, at=NOW, id='candidate')
    rendering = render_weight_trend(candidate=candidate, comparison=comparison, target=GRANT_TARGET, at=NOW, id='rendering')
    return dict(selection=selection, comparison=comparison, inference=inference, lineage=lineage,
                snapshot=snapshot, candidate=candidate, rendering=rendering, target=GRANT_TARGET)


@pytest.fixture
def case(registered):
    return evidence(registered)


def run(case, **changes):
    args = dict(case, active_request=GRANT_TARGET, active_output=case['candidate'].reference,
                actor='synthetic-orchestrator', at=NOW, validity=WINDOW, id='attempt')
    args.update(changes)
    return release_weight_trend(**args)


def validation(case, review, payload):
    return validate_weight_trend_content(**{k:v for k,v in case.items() if k not in ('candidate','rendering')},
        review=review, payload=payload, at=NOW, validity=WINDOW, id='validation')


def decide(assessment, at=NOW):
    return decide_release(reference=Reference(kind='release_decision', id='negative', version='1'),
                          assessment=assessment, actor='synthetic-orchestrator', at=at)


def claim_change(case, **updates):
    claim = replace(case['candidate'].claims[0], **updates)
    return {**case, 'candidate': replace(case['candidate'], claims=(claim,))}


@pytest.mark.parametrize('a,b,statement', [
    ('82','79','Recorded weight decreased from 82 kg to 79 kg between the selected observations. This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.'),
    ('82','82','Recorded weight was unchanged at 82 kg between the selected observations. This comparison does not establish nutritional status. Synthetic evaluation only.'),
    ('79','82','Recorded weight increased from 79 kg to 82 kg between the selected observations. This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.'),
])
def test_principal_real_reopen_composition(registered, a, b, statement):
    case = evidence(registered, a, b)
    decision = run(case)
    assert decision.outcome == 'released' and decision.reasons == ()
    assert tuple(f.reference for f in case['snapshot'].facts) == (
        Reference(kind='observation', id='a', version='z'), Reference(kind='observation', id='b', version='0'),
        Reference(kind='inference', id='weight-trend-1', version='1'))
    assert case['snapshot'].facts[-1] == case['inference']
    assert case['snapshot'].temporal_cutoff >= case['inference'].time.recorded
    assert len(case['candidate'].claims) == 1
    claim = case['candidate'].claims[0]
    assert claim.basis == (case['inference'].reference,) and claim.action == statement
    assert claim.classifications == ('deterministic',)
    assert case['rendering'].content == statement
    assessment = decision.assessment
    assert [(c.rule.id,c.rule.version,c.outcome,c.required,c.overrideable) for c in assessment.review.evaluations[0].checks] == [
        ('exact_evidence_and_input_suitability','1','no_detected_violation',True,False),
        ('bounded_descriptive_output','1','no_detected_violation',True,False)]
    assert assessment.review.evaluations[0].exact_meaning == 'matched'
    assert assessment.payload == required_payload(assessment.review, (), LIMITATIONS)
    assert assessment.payload.limitations == (
        'Synthetic evaluation of a fixed historical recorded-weight comparison, with no patient-care use or delivery.',
        'No clinical validation or continuing clinical eligibility; no delivery.')
    assert assessment.content_validation.outcome == 'matched'
    auth = assessment.state.authorization
    assert auth.issuer == 'SyntheticWeightReleaseIssuer/v1' and auth.subject == decision.actor
    assert auth.target == GRANT_TARGET and auth.action == 'release'
    assert auth.content_digest == review_digest(assessment.review)
    assert auth.payload_digest == content_digest(assessment.payload)
    assert auth.governance_policy_digest == content_digest(assessment.policy)
    assert all(d.state == 'available' and d.updates == 'not_required' for d in assessment.state.dependencies)
    assert all(item.state == 'fresh' for item in assessment.state.freshness.items)
    assert decision.assessment.review.state == 'evaluated'
    assert decision.assessment.review.candidate.state == 'candidate'
    assert ReleaseDecision.model_validate_json(decision.model_dump_json()) == decision
    assert not {'presented','clinically_valid','approved'} & set(decision.model_dump())


@pytest.mark.parametrize('mutation', ['earlier','later','unit','direction','limitation','diagnosis','cause','treatment'])
def test_literal_rendering_mutations_withhold(case, mutation):
    text = case['rendering'].content
    changed = {
        'earlier': text.replace('82 kg','83 kg'), 'later': text.replace('79 kg','78 kg'),
        'unit': text.replace('kg','lb'), 'direction': text.replace('decreased','increased'),
        'limitation': text.replace('Synthetic evaluation only.',''),
        'diagnosis': text + ' Malnutrition is diagnosed.', 'cause': text + ' This was caused by catabolism.',
        'treatment': text + ' Start enteral feeding.',
    }[mutation]
    result = run({**case, 'rendering': replace(case['rendering'], content=changed)})
    assert result.outcome == 'withheld'
    assert 'hard_safety_failure' in result.reasons
    assert result.assessment.content_validation.outcome == 'failed'
    # Real issuer still derives hashes of actual changed content; hashes cannot repair semantics.
    assert result.assessment.state.authorization.content_digest == review_digest(result.assessment.review)
    assert result.assessment.state.authorization.payload_digest == content_digest(result.assessment.payload)


@pytest.mark.parametrize('field', ['action','rationale','conditions','warnings','uncertainty','basis'])
def test_claim_field_injection_withholds(case, field):
    claim = case['candidate'].claims[0]
    value = ('Malnutrition diagnosed.' if field in ('action','rationale') else
             (Reference(kind='inference', id='wrong', version='1'),) if field == 'basis' else
             (*getattr(claim, field), 'Start treatment.'))
    result = run(claim_change(case, **{field:value}))
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


@pytest.mark.parametrize('field', ['alternatives','monitoring','limitations','knowledge','provenance','extra_claim'])
def test_candidate_envelope_injection_withholds(case, field):
    c = case['candidate']
    if field in ('alternatives','monitoring','limitations'):
        c = replace(c, **{field:('Start treatment.',)})
    elif field == 'knowledge':
        from app.models.clinical.decisions import KnowledgeReference
        c = replace(c, knowledge=(KnowledgeReference(id='unassessed',version='1',applicability='all patients'),))
    elif field == 'provenance':
        c = replace(c, provenance=replace(c.provenance, actor='Diagnosis confirmed'))
    else:
        c = replace(c, claims=(*c.claims, replace(c.claims[0], id='extra')))
    result = run({**case,'candidate':c})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


@pytest.mark.parametrize('change', ['decimal','offset','value','ref'])
def test_comparison_exact_representation_checked(case, change):
    cmp = case['comparison']
    updates = {'decimal':dict(earlier_kg=Decimal('82.0')),
        'offset':dict(earlier_event=cmp.earlier_event.astimezone(timezone.utc)),
        'value':dict(earlier_kg=Decimal('83')),
        'ref':dict(earlier_reference=replace(cmp.earlier_reference, version='other'))}[change]
    result = run({**case,'comparison':replace(cmp, **updates)})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


@pytest.mark.parametrize('field', ['statement','method','applicability','uncertainty','limitations','extra_edge'])
def test_inference_tamper_does_not_gain_trust_from_same_reference(case, field):
    i = case['inference']
    updates = {
        'statement':dict(statement='Malnutrition diagnosed.'),
        'method':dict(method=replace(i.method,version='2')),
        'applicability':dict(applicability='All clinical patients'),
        'uncertainty':dict(uncertainty=('Start treatment.',)),
        'limitations':dict(validation_limitations='Clinically validated'),
        'extra_edge':dict(provenance=replace(i.provenance,upstream=(*i.provenance.upstream,
            LineageEdge(target=Reference(kind='observation',id='extra',version='1'),relationship='derived_from')))),
    }[field]
    result = run({**case,'inference':replace(i, **updates)})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


@pytest.mark.parametrize('case_change', ['missing_edge','extra_edge','missing_node','wrong_root','wrong_scope','wrong_cutoff','payload','supersedes_evidence'])
def test_lineage_evidence_negative(case, case_change):
    graph = case['lineage']
    if case_change == 'missing_edge':
        graph = dc_replace(graph, assertions=graph.assertions[:-1])
    elif case_change == 'extra_edge':
        graph = dc_replace(graph, assertions=(*graph.assertions,graph.assertions[-1]))
    elif case_change == 'missing_node':
        graph = dc_replace(graph, nodes=tuple(n for n in graph.nodes if n.stored.fact.id != 'a'))
    elif case_change == 'wrong_root':
        graph = dc_replace(graph, reference=Reference(kind='inference',id='wrong',version='1'))
    elif case_change == 'wrong_scope':
        graph = dc_replace(graph, target=replace(TARGET,encounter_id='synthetic-e2'))
    elif case_change == 'wrong_cutoff':
        graph = dc_replace(graph, cutoff=case['selection'].cutoff)
    elif case_change == 'payload':
        nodes = list(graph.nodes)
        n = next(n for n in nodes if n.stored.fact.id == 'a')
        altered = replace(n.stored.fact,value=replace(n.stored.fact.value,value=replace(n.stored.fact.value.value,
            unit=Unit(raw='g',status='assessed',system='UCUM',code='g'))))
        nodes[nodes.index(n)] = dc_replace(n,stored=dc_replace(n.stored,fact=altered))
        graph = dc_replace(graph,nodes=tuple(nodes))
    else:
        graph = dc_replace(graph,dependencies=(*graph.dependencies,dc_replace(graph.dependencies[0],source=Reference(kind='observation',id='a',version='earlier'))))
    result = run({**case,'lineage':graph})
    assert result.outcome == 'withheld'
    assert result.assessment.review.evaluations[0].checks[0].outcome in ('hard_failure','unavailable')


def test_unresolved_required_lineage_is_unavailable(case):
    graph = dc_replace(case['lineage'],coverage='partial')
    result = run({**case,'lineage':graph})
    assert result.outcome == 'withheld'
    assert 'safety_check_unavailable' in result.reasons
    assert result.assessment.content_validation.outcome == 'unavailable'


@pytest.mark.parametrize('field', ['payload','evaluation_reason','evaluation_limits'])
def test_full_payload_and_evaluation_disclosures_checked(case, field):
    result = run(case)
    review, payload = result.assessment.review,result.assessment.payload
    if field == 'payload':
        payload = replace(payload,limitations=(*payload.limitations,'Start treatment.'))
    else:
        e = review.evaluations[0]
        if field == 'evaluation_reason':
            e = replace(e,checks=(replace(e.checks[0],reason='Malnutrition diagnosed.'),e.checks[1]))
        else:
            e = replace(e,limitations=('Start treatment.',))
        review = replace(review,evaluations=(e,))
        payload = required_payload(review,(),LIMITATIONS)
    checked = validation(case,review,payload)
    assert checked.outcome == 'failed'
    assert checked.content_digest == review_digest(review) and checked.payload_digest == content_digest(payload)


@pytest.mark.parametrize('mutation,reason', [
    ('check_missing','required_applicable_safety_coverage_missing'),
    ('check_unavailable','safety_check_unavailable'),
    ('check_na','required_applicable_safety_coverage_missing'),
    ('check_failed','hard_safety_failure'), ('evaluation_missing','safety_evaluation_missing'),
    ('validation_payload','validated_payload_mismatch'),
    ('validation_review','exact_evaluated_content_or_target_mismatch'),
    ('validation_target','exact_evaluated_content_or_target_mismatch'),
    ('validation_method','exact_meaning_or_validated_scope_not_established'),
    ('auth_deny','authorization_not_allowed'), ('auth_unknown','authorization_not_allowed'),
    ('auth_subject','authorization_scope_mismatch'), ('auth_target','authorization_scope_mismatch'),
    ('auth_action','authorization_scope_mismatch'),
    ('auth_review','authorization_content_or_policy_mismatch'),
    ('auth_payload','authorization_payload_mismatch'), ('auth_policy','authorization_content_or_policy_mismatch'),
    ('auth_expired','authorization_expired_or_not_yet_valid'), ('auth_future','authorization_expired_or_not_yet_valid'),
    ('fresh_snapshot','freshness_snapshot_or_policy_mismatch'),
    ('fresh_missing','required_context_not_fresh:snapshot:snapshot:1'),
    ('fresh_stale','required_context_not_fresh:snapshot:snapshot:1'),
    ('fresh_unknown','required_context_not_fresh:snapshot:snapshot:1'),
    ('fresh_policy','freshness_snapshot_or_policy_mismatch'),
    ('runtime_target','patient_encounter_request_destination_or_recipient_mismatch'),
    ('runtime_old','runtime_observation_expired_or_future'),
    ('policy','authorization_content_or_policy_mismatch'),
    ('dependency_missing','required_dependency_update_or_check_unavailable'),
])
def test_existing_governance_withholds_independent_evidence_mutations(case,mutation,reason):
    a = run(case).assessment
    if mutation.startswith('check_') or mutation == 'evaluation_missing':
        e = a.review.evaluations[0]
        outcome = {'check_unavailable':'unavailable','check_na':'not_applicable','check_failed':'hard_failure'}.get(mutation)
        checks = e.checks[1:] if mutation == 'check_missing' else e.checks if outcome is None else (replace(e.checks[0],outcome=outcome),e.checks[1])
        review = replace(a.review,evaluations=() if mutation == 'evaluation_missing' else (replace(e,checks=checks),))
        payload = required_payload(review,(),LIMITATIONS)
        v = validation(case,review,payload)
        auth = issue_synthetic_weight_release(selection=case['selection'],inference=case['inference'],review=review,
            payload=payload,policy=a.policy,target=GRANT_TARGET,actor='synthetic-orchestrator',at=NOW,id='reissued')
        a = replace(a,review=review,payload=payload,content_validation=v,state=replace(a.state,authorization=auth))
    elif mutation.startswith('validation_'):
        v = a.content_validation
        changes = {'validation_payload':dict(payload_digest='0'*64),'validation_review':dict(content_digest='0'*64),
            'validation_target':dict(target=replace(GRANT_TARGET,request_id='other')),
            'validation_method':dict(method=replace(FIDELITY,version='2'))}[mutation]
        a = replace(a,content_validation=replace(v,**changes))
    elif mutation.startswith('auth_'):
        auth = a.state.authorization
        changes = {'auth_deny':dict(outcome='deny'),'auth_unknown':dict(outcome='unknown'),
            'auth_subject':dict(subject='other'),'auth_target':dict(target=replace(GRANT_TARGET,recipient='other')),
            'auth_action':dict(action='present'),'auth_review':dict(content_digest='0'*64),
            'auth_payload':dict(payload_digest='0'*64),'auth_policy':dict(governance_policy_digest='0'*64),
            'auth_expired':dict(validity=ValidityWindow(start=NOW-timedelta(seconds=1),end=NOW)),
            'auth_future':dict(issued_at=NOW+timedelta(microseconds=1))}[mutation]
        a = replace(a,state=replace(a.state,authorization=replace(auth,**changes)))
    elif mutation.startswith('fresh_'):
        f = a.state.freshness
        if mutation in ('fresh_stale','fresh_unknown'):
            f = replace(f,items=(replace(f.items[0],state=mutation.split('_')[1]),*f.items[1:]))
        elif mutation == 'fresh_missing':
            f = replace(f,items=f.items[1:])
        elif mutation == 'fresh_snapshot':
            f = replace(f,snapshot=replace(f.snapshot,id='other'))
        else:
            f = replace(f,policy=replace(f.policy,version='2'))
        a = replace(a,state=replace(a.state,freshness=f))
    elif mutation == 'runtime_target':
        a = replace(a,state=replace(a.state,target=replace(GRANT_TARGET,request_id='wrong')))
    elif mutation == 'runtime_old':
        a = replace(a,state=replace(a.state,observed_at=NOW-timedelta(seconds=31)))
    elif mutation == 'dependency_missing':
        a = replace(a,state=replace(a.state,dependencies=()))
    else:
        a = replace(a,policy=replace(a.policy,reference=replace(a.policy.reference,version='2')))
    decision = decide(a)
    assert decision.outcome == 'withheld' and reason in decision.reasons


@pytest.mark.parametrize('actor,outcome', [('synthetic-orchestrator','allow'),('synthetic-denied','deny'),('unknown','unknown')])
def test_real_issuer_authority_lookup(case,actor,outcome):
    result = run(case,actor=actor)
    assert result.assessment.state.authorization.outcome == outcome
    assert result.outcome == ('released' if outcome == 'allow' else 'withheld')


@pytest.mark.parametrize('delta,outcome', [(-1,'deny'),(0,'allow'),(1,'allow')])
def test_issuer_grant_start_boundary(case,delta,outcome):
    a = run(case).assessment
    auth = issue_synthetic_weight_release(selection=case['selection'],inference=case['inference'],review=a.review,
        payload=a.payload,policy=a.policy,target=a.target,actor='synthetic-orchestrator',
        at=GRANT_WINDOW.start+timedelta(microseconds=delta),id='boundary')
    assert auth.outcome == outcome


@pytest.mark.parametrize('delta,outcome', [(-1,'allow'),(0,'deny'),(1,'deny')])
def test_issuer_grant_end_boundary(case,delta,outcome):
    a = run(case).assessment
    auth = issue_synthetic_weight_release(selection=case['selection'],inference=case['inference'],review=a.review,
        payload=a.payload,policy=a.policy,target=a.target,actor='synthetic-orchestrator',
        at=GRANT_WINDOW.end+timedelta(microseconds=delta),id='boundary')
    assert auth.outcome == outcome


@pytest.mark.parametrize('delta,outcome', [(-1,'withheld'),(0,'released'),(19_999_999,'released'),(20_000_000,'withheld')])
def test_release_window_actual_boundaries(case,delta,outcome):
    result = decide(run(case).assessment,at=NOW+timedelta(microseconds=delta))
    assert result.outcome == outcome


@pytest.mark.parametrize('field', ['target','policy','payload'])
def test_issuer_checks_grant_not_caller_allow(case,field):
    a = run(case).assessment
    data = dict(selection=case['selection'],inference=case['inference'],review=a.review,payload=a.payload,
        policy=a.policy,target=a.target,actor='synthetic-orchestrator',at=NOW,id='issuer-negative')
    if field == 'target':
        data[field] = replace(a.target,context=replace(TARGET,encounter_id='synthetic-e2'))
    elif field == 'policy':
        data[field] = replace(a.policy,required_dependencies=())
    else:
        data[field] = replace(a.payload,limitations=())
    assert issue_synthetic_weight_release(**data).outcome == 'deny'


@pytest.mark.parametrize('field', ['request','output'])
def test_runtime_uses_harness_owned_active_identity(case,field):
    changed = dict(active_request=replace(GRANT_TARGET,request_id='other')) if field == 'request' else dict(
        active_output=replace(case['candidate'].reference,id='other'))
    result = run(case,**changed)
    assert result.outcome == 'withheld'
    assert ('request_not_active' if field == 'request' else 'output_not_current') in result.reasons


def test_nested_immutability_and_malformed_contracts(case):
    result = run(case)
    for target,field,value in [(result.assessment.review.candidate.claims[0],'action','other'),
        (result.assessment.state.authorization.target,'recipient','other'),
        (result.assessment.state.freshness.items[0],'state','fresh')]:
        with pytest.raises(ValidationError):
            setattr(target,field,value)
    with pytest.raises(ValidationError):
        RuntimeState.model_validate({**result.assessment.state.model_dump(),'request_state':'invalid'})
    with pytest.raises(ValidationError):
        review = replace(result.assessment.review,evaluations=(result.assessment.review.evaluations[0],
            replace(result.assessment.review.evaluations[0],limitations=('conflict',))))
    assert ReleaseDecision.model_validate_json(result.model_dump_json()) == result


def test_later_correction_still_proves_only_fixed_historical_release(case,registered):
    original = run(case)
    a = case['selection'].selected[0]
    a2 = revision(a,'new',value=replace(a.value,value=replace(a.value.value,value=Decimal('80'))))
    with transaction(registered) as repo:
        repo.append_revision(a2,target=TARGET)
        current = repo.capture_cutoff()
    assert select(registered,current).selected[0].reference == a2.reference
    assert select(registered,case['selection'].cutoff) == case['selection']
    assert resolve(registered,case['inference'],case['lineage'].cutoff) == case['lineage']
    assert run(case) == original
    assert 'no patient-care use or delivery' in original.assessment.payload.limitations[0]
    assert 'later corrections not assessed' in original.assessment.state.freshness.items[0].rationale


def test_pure_post_persistence_and_unchanged_schema(case,registered):
    before = canonical_payload(case['inference'])
    statements = []
    def capture(conn,cursor,statement,parameters,context,executemany):
        statements.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        run(case)
    finally:
        event.remove(registered,'before_cursor_execute',capture)
    assert statements == []
    assert canonical_payload(case['inference']) == before
    with registered.connect() as conn:
        assert set(inspect(conn).get_table_names()) == {'patient','encounter','fact_revision','revision_link','repository_identity','weight_trend_execution', 'creatinine_trend_execution','patient_state_temporal_execution','micro_antimicrobial_execution','alembic_version'}


def test_malformed_retained_inference_remains_integrity_exception(case,registered):
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='{}' WHERE kind='inference'"))
    with pytest.raises(StorageIntegrityError):
        resolve(registered,case['inference'],case['lineage'].cutoff)


@pytest.mark.parametrize('field', ['statement','method','target','horizon','execution'])
def test_reproducible_inference_grammar_contradictions_withhold(case,field):
    i = case['inference']
    changes = {'statement':dict(statement=i.statement.replace('79','78')),
        'method':dict(method=replace(i.method,id='OtherMethod')),
        'target':dict(target='malnutrition'),'horizon':dict(horizon='tomorrow'),
        'execution':dict(time=replace(i.time,event=POLICY.available_at-timedelta(microseconds=1)))}[field]
    result = run({**case,'inference':replace(i,**changes)})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


def test_missing_snapshot_member_does_not_get_fresh_assessment(case):
    snapshot = replace(case['snapshot'],facts=case['snapshot'].facts[1:])
    changed = {**case,'snapshot':snapshot,'candidate':replace(case['candidate'],snapshot=snapshot)}
    result = run(changed)
    assert result.outcome == 'withheld'
    assert not result.assessment.state.freshness.adequate
    assert all(item.state == 'unknown' for item in result.assessment.state.freshness.items)


@pytest.mark.parametrize('at', [NOW-timedelta(microseconds=1),WINDOW.end])
def test_context_producer_does_not_assert_future_or_expired_suitability(case,at):
    assessment = assess_weight_trend_context(**{k:v for k,v in case.items() if k not in ('candidate','rendering','target')},
        at=at,validity=WINDOW,id='bounded-context')
    assert not assessment.adequate
    assert all(item.state == 'unknown' for item in assessment.items)


def test_unsupported_registered_uncertainty_not_accepted_by_copying(registered):
    case = evidence(registered,uncertainty='Malnutrition diagnosed.')
    # Selector and builder legitimately preserve this source text; the closed
    # Phase 3 grammar must not endorse it, even when every retained link matches.
    assert case['selection'].successful
    assert 'Malnutrition diagnosed.' in case['inference'].uncertainty
    result = run(case)
    assert result.outcome == 'withheld'
    assert result.assessment.review.evaluations[0].checks[1].outcome == 'hard_failure'


def test_forged_nested_invalid_selection_is_structural_failure(case):
    first,later = case['selection'].selected
    forged = case['selection'].model_copy(update={'selected':(first,later.model_copy(update={'id':first.id}))})
    with pytest.raises(ValidationError):
        run({**case,'selection':forged})


def test_missing_rendering_is_explicit_invalid_fidelity_contract(case):
    decision = run(case)
    review = RecommendationReview(candidate=case['candidate'])
    with pytest.raises(ValueError,match='requires rendered content'):
        validation(case,review,decision.assessment.payload)


def test_dependencies_fail_closed_on_wrong_resolved_scope(case):
    graph = dc_replace(case['lineage'],target=replace(TARGET,encounter_id='synthetic-e2'))
    policy = weight_trend_governance_policy(snapshot=case['snapshot'],selection=case['selection'],inference=case['inference'])
    states = assess_weight_trend_dependencies(selection=case['selection'],comparison=case['comparison'],
        inference=case['inference'],lineage=graph,snapshot=case['snapshot'],policy=policy,at=NOW,validity=WINDOW)
    assert [d.state for d in states[:3]] == ['unavailable']*3


def test_same_revision_nested_runtime_assertions_rejected(case):
    result = run(case)
    data = result.model_dump(mode='json')
    duplicate = dict(data['assessment']['state']['dependencies'][0])
    data['assessment']['state']['dependencies'].append(duplicate)
    with pytest.raises(ValidationError,match='duplicate dependency'):
        ReleaseDecision.model_validate(data)


@pytest.mark.parametrize('part', ['ancestry','nonroot_dependency','disclosures','roles'])
def test_auxiliary_lineage_contract_tampering_cannot_claim_suitability(case,part):
    graph = case['lineage']
    if part == 'ancestry':
        graph = dc_replace(graph,ancestry=())
    elif part == 'nonroot_dependency':
        graph = dc_replace(graph,dependencies=(*graph.dependencies,
            dc_replace(graph.dependencies[0],owner=case['selection'].selected[0].reference)))
    elif part == 'disclosures':
        graph = dc_replace(graph,provenance=())
    else:
        graph = dc_replace(graph,nodes=tuple(dc_replace(n,roles=('association',)) for n in graph.nodes))
    decision = run({**case,'lineage':graph})
    assert decision.outcome == 'withheld' and 'hard_safety_failure' in decision.reasons


def test_resolved_policy_identity_cannot_collide_across_contexts(case):
    from app.models.clinical.governance import validate_governance_bundle
    first = weight_trend_governance_policy(snapshot=case['snapshot'],selection=case['selection'],inference=case['inference'])
    another_snapshot = replace(case['snapshot'],id='another-snapshot')
    second = weight_trend_governance_policy(snapshot=another_snapshot,selection=case['selection'],inference=case['inference'])
    assert first.required_context != second.required_context
    assert first.reference != second.reference
    validate_governance_bundle(first,second)
    assert weight_trend_governance_policy(snapshot=case['snapshot'],selection=case['selection'],inference=case['inference']) == first


@pytest.mark.parametrize('substitution', ['optional_flag', 'different_optional_rule'])
def test_optional_checks_cannot_replace_performed_required_checks(case, substitution):
    a = run(case).assessment
    e = a.review.evaluations[0]
    check = replace(e.checks[0], required=False)
    if substitution == 'different_optional_rule':
        check = replace(check, rule=replace(check.rule, id='optional-substitute'))
    review = replace(a.review, evaluations=(replace(e, checks=(check, e.checks[1])),))
    payload = required_payload(review, (), LIMITATIONS)
    checked = validation(case, review, payload)
    auth = issue_synthetic_weight_release(selection=case['selection'], inference=case['inference'],
        review=review, payload=payload, policy=a.policy, target=a.target,
        actor='synthetic-orchestrator', at=NOW, id='optional-check-authorization')
    assert checked.outcome == 'failed'
    assert checked.content_digest == auth.content_digest == review_digest(review)
    changed = replace(a, review=review, payload=payload, content_validation=checked,
        state=replace(a.state, authorization=auth))
    assert decide(changed).outcome == 'withheld'


@pytest.mark.parametrize('field', ['required_rules', 'required_context', 'required_dependencies'])
def test_issuer_rejects_weakened_resolved_requirements_with_new_digest(case, field):
    a = run(case).assessment
    policy = replace(a.policy, **{field: getattr(a.policy, field)[1:]})
    auth = issue_synthetic_weight_release(selection=case['selection'], inference=case['inference'],
        review=a.review, payload=a.payload, policy=policy, target=a.target,
        actor='synthetic-orchestrator', at=NOW, id='weakened-policy-authorization')
    assert auth.governance_policy_digest == content_digest(policy)
    assert auth.outcome == 'deny'
    result = decide(replace(a, policy=policy, state=replace(a.state, authorization=auth)))
    assert result.outcome == 'withheld' and 'authorization_not_allowed' in result.reasons


@pytest.mark.parametrize('field', ['request_id', 'destination', 'recipient'])
def test_freshly_bound_changed_target_cannot_escape_fixed_grant(case, field):
    target = replace(GRANT_TARGET, **{field: 'another-synthetic-target'})
    rendering = replace(case['rendering'], destination=target.destination)
    result = run({**case, 'rendering': rendering, 'target': target}, active_request=target)
    a = result.assessment
    assert a.content_validation.outcome == 'matched'
    assert a.content_validation.target == a.state.authorization.target == target
    assert a.state.authorization.content_digest == review_digest(a.review)
    assert a.state.authorization.payload_digest == content_digest(a.payload)
    assert a.state.authorization.outcome == 'deny'
    assert result.outcome == 'withheld' and 'authorization_not_allowed' in result.reasons


@pytest.mark.parametrize('change', ['extra_ancestor', 'wrong_revision_ancestor', 'reversed_assertions', 'reversed_dependencies'])
def test_lineage_membership_and_declaration_order_are_exact(case, change):
    graph = case['lineage']
    if change in ('extra_ancestor', 'wrong_revision_ancestor'):
        root = case['inference'].reference
        earlier = case['selection'].selected[0].reference
        extra = replace(earlier, version='unconsumed-revision')
        ancestry = tuple((ref, (ancestors | {extra}) - ({earlier} if change == 'wrong_revision_ancestor' else set()))
                         if ref == root else (ref, ancestors) for ref, ancestors in graph.ancestry)
        graph = dc_replace(graph, ancestry=ancestry)
    else:
        field = 'assertions' if change == 'reversed_assertions' else 'dependencies'
        graph = dc_replace(graph, **{field: tuple(reversed(getattr(graph, field)))})
    result = run({**case, 'lineage': graph})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons
    assert not result.assessment.state.freshness.adequate


@pytest.mark.parametrize('field', ['context', 'dependency'])
def test_same_id_other_revision_cannot_satisfy_required_runtime_evidence(case, field):
    a = run(case).assessment
    if field == 'context':
        f = a.state.freshness
        item = replace(f.items[0], reference=replace(f.items[0].reference, version='other'))
        state = replace(a.state, freshness=replace(f, items=(item, *f.items[1:])))
        reason = 'required_context_not_fresh:snapshot:snapshot:1'
    else:
        item = a.state.dependencies[0]
        item = replace(item, reference=replace(item.reference, version='other'))
        state = replace(a.state, dependencies=(item, *a.state.dependencies[1:]))
        reason = 'required_dependency_update_or_check_unavailable'
    result = decide(replace(a, state=state))
    assert result.outcome == 'withheld' and reason in result.reasons


def test_model_construct_cannot_bypass_nested_runtime_validation(case):
    a = run(case).assessment
    malformed = a.state.model_copy(update={'identity': a.state.identity.model_copy(update={'status': 'invented'})})
    forged = a.model_copy(update={'state': malformed})
    with pytest.raises(ValidationError):
        decide(forged)


@pytest.mark.parametrize('hash_seed', ['1', '8675309'])
def test_fresh_process_reopen_preserves_policy_and_entire_decision(case, registered, hash_seed):
    import json
    import os
    import subprocess
    import sys
    from test_persistence import ROOT

    expected = run(case)
    registered.dispose()
    script = '''
import json, sys
from app.persistence.metadata import RepositoryCutoff
from test_weight_trend_release import (
    create_database, select, compare_recorded_weights, transaction, TARGET, resolve,
    build_weight_trend_snapshot, build_weight_trend_candidate, render_weight_trend,
    GRANT_TARGET, NOW, run,
)
from app.models.clinical.common import Reference
inputs = json.load(sys.stdin)
engine = create_database(sys.argv[1])
try:
    selection = select(engine, RepositoryCutoff.model_validate(inputs['input']))
    comparison = compare_recorded_weights(selection)
    with transaction(engine) as repo:
        inference = repo.load_fact(Reference.model_validate(inputs['inference']), target=TARGET).fact
        patient = repo.load_patient(TARGET.patient_id)
        encounter = repo.load_encounter(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id)
    lineage = resolve(engine, inference, RepositoryCutoff.model_validate(inputs['output']))
    snapshot = build_weight_trend_snapshot(selection=selection, inference=inference, lineage=lineage,
        patient=patient, encounter=encounter, at=NOW, id='snapshot')
    candidate = build_weight_trend_candidate(snapshot=snapshot, comparison=comparison,
        inference=inference, at=NOW, id='candidate')
    rendering = render_weight_trend(candidate=candidate, comparison=comparison,
        target=GRANT_TARGET, at=NOW, id='rendering')
    print(run(dict(selection=selection, comparison=comparison, inference=inference,
        lineage=lineage, snapshot=snapshot, candidate=candidate, rendering=rendering,
        target=GRANT_TARGET)).model_dump_json())
finally:
    engine.dispose()
'''
    env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join((str(ROOT / 'backend'), str(ROOT / 'tests'))))
    process = subprocess.run([sys.executable, '-c', script, registered.url.database],
        input=json.dumps({'input': case['selection'].cutoff.model_dump(mode='json'),
                          'output': case['lineage'].cutoff.model_dump(mode='json'),
                          'inference': case['inference'].reference.model_dump(mode='json')}),
        text=True, capture_output=True, env=env, check=True, timeout=30)
    replayed = ReleaseDecision.model_validate_json(process.stdout)
    assert replayed.outcome == 'released' and replayed.reasons == ()
    assert replayed.model_dump_json() == expected.model_dump_json()
