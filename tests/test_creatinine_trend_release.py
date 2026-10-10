"""Synthetic Phase C: reopened evidence, independent grammar and negative governance."""
from dataclasses import replace as dc_replace
from datetime import timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text

import app.execution.creatinine_trend_release as release
from app.execution.creatinine_trend import compare_recorded_creatinine
from app.execution.creatinine_trend_release import (
    AUTHORIZATION, FIDELITY, GRANT_ACTOR, GRANT_TARGET, GRANT_WINDOW, INTENDED_USE, ISSUER,
    LIMITATIONS, RULES, USE, assess_creatinine_trend_context, assess_creatinine_trend_dependencies,
    assemble_creatinine_trend_runtime, build_creatinine_trend_candidate, build_creatinine_trend_snapshot,
    creatinine_trend_governance_policy, evaluate_creatinine_trend, issue_synthetic_creatinine_release,
    release_creatinine_trend, render_creatinine_trend, validate_creatinine_trend_content,
)
from app.models.clinical.common import Reference
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.governance import (
    ReleaseDecision, ValidityWindow, content_digest, required_payload, review_digest, validate_governance_bundle,
)
from app.persistence.database import create_database
from app.persistence.errors import StorageIntegrityError
from app.persistence.lineage import UnresolvedReference
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from app.services.governance_service import assess_release, decide_release
from test_persistence import AT, TARGET, database, registered, replace
from test_revision_chains import revision
from test_creatinine_trend import changed_unit, select
from test_creatinine_trend_inference import selected_pair, build, persist, resolve

NOW = GRANT_WINDOW.start + timedelta(seconds=1)
WINDOW = ValidityWindow(start=NOW, end=NOW + timedelta(seconds=20))


def compose(case):
    snapshot = build_creatinine_trend_snapshot(selection=case['selection'], inference=case['inference'],
        lineage=case['lineage'], patient=case['patient'], encounter=case['encounter'], at=NOW, id='creatinine-snapshot')
    candidate = build_creatinine_trend_candidate(snapshot=snapshot, comparison=case['comparison'],
        inference=case['inference'], at=NOW, id='creatinine-candidate')
    rendering = render_creatinine_trend(candidate=candidate, comparison=case['comparison'],
        target=case['target'], at=NOW, id='creatinine-rendering')
    return {**case, 'snapshot': snapshot, 'candidate': candidate, 'rendering': rendering}


def evidence(engine, a='1.00', b='1.20'):
    selection, _ = selected_pair(engine, a, b)
    inference = build(selection)
    stored, cutoff = persist(engine, inference)
    engine.dispose()
    reopened = create_database(engine.url.database)
    try:
        with transaction(reopened) as repo:
            inference = repo.load_fact(stored.fact.reference, target=TARGET).fact
            patient = repo.load_patient(TARGET.patient_id)
            encounter = repo.load_encounter(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id)
        lineage = resolve(reopened, inference.reference, cutoff)
    finally:
        reopened.dispose()
    return compose(dict(selection=selection, comparison=compare_recorded_creatinine(selection),
        inference=inference, lineage=lineage, patient=patient, encounter=encounter, target=GRANT_TARGET))


@pytest.fixture
def case(registered):
    return evidence(registered)


def arguments(case):
    return {k: v for k, v in case.items() if k not in ('patient', 'encounter')}


def run(case, **updates):
    data = dict(arguments(case), active_request=GRANT_TARGET, active_output=case['candidate'].reference,
        actor=GRANT_ACTOR, at=NOW, validity=WINDOW, id='creatinine-attempt')
    data.update(updates)
    return release_creatinine_trend(**data)


def fidelity(case, review, payload):
    return validate_creatinine_trend_content(**{k: v for k, v in arguments(case).items()
        if k not in ('candidate', 'rendering')}, review=review, payload=payload,
        at=NOW, validity=WINDOW, id='creatinine-validation')


def issuer(case, assessment, **updates):
    data = dict(selection=case['selection'], inference=case['inference'], review=assessment.review,
        payload=assessment.payload, policy=assessment.policy, target=assessment.target,
        actor=GRANT_ACTOR, at=NOW, id='creatinine-reissued')
    data.update(updates)
    return issue_synthetic_creatinine_release(**data)


def decide(assessment, at=NOW):
    return decide_release(reference=Reference(kind='release_decision', id='creatinine-negative', version='1'),
        assessment=assessment, actor=GRANT_ACTOR, at=at)


@pytest.mark.parametrize('a,b,statement', [
    ('1.00', '1.20', 'Recorded serum creatinine increased from 1.00 mg/dL to 1.20 mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.'),
    ('1.20', '1.00', 'Recorded serum creatinine decreased from 1.20 mg/dL to 1.00 mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.'),
    ('1.00', '1.0', 'Recorded serum creatinine was unchanged between the selected samples (1.00 mg/dL then 1.0 mg/dL). Synthetic evaluation only; bounded historical comparison.'),
])
def test_reopened_evidence_releases_exact_bounded_statement(registered, a, b, statement):
    c = evidence(registered, a, b)
    decision = run(c)
    assert decision.outcome == 'released' and decision.reasons == ()
    assert c['candidate'].claims[0].action == c['rendering'].content == c['inference'].statement == statement
    claim = c['candidate'].claims[0]
    assert claim.id == 'recorded-creatinine-comparison'
    assert claim.basis == (Reference(kind='inference', id='creatinine-i1', version='1'),)
    assert claim.classifications == ('deterministic',)
    assert claim.conditions == ('Synthetic serum-creatinine comparison within the selected patient/encounter and sample-time window only.',)
    assert claim.warnings == ('Not clinically validated; recorded values and synthetic sample identity only.',
        'Synthetic evaluation only; no clinical validity or source-authenticity claim.')
    assert claim.uncertainty == ('Recorded comparison does not establish clinical significance or cause.',
        'Synthetic evaluation only; specimen identity and input authenticity are assumed.', 'synthetic uncertainty')
    snapshot = c['snapshot']
    assert snapshot.completeness == 'partial' and not snapshot.lineage_nodes
    assert content_digest(c['selection']) in snapshot.completeness_scope
    assert content_digest(c['comparison']) in snapshot.completeness_scope
    assert content_digest(c['lineage'].cutoff) in snapshot.completeness_scope
    assert tuple(f.reference for f in snapshot.facts) == (*tuple(f.reference for f in c['selection'].selected), c['inference'].reference)
    assert str(snapshot.facts[0].value.value.value) == a and str(snapshot.facts[1].value.value.value) == b
    assert snapshot.facts[0].time.event.isoformat() == c['comparison'].earlier_sample_time.isoformat()
    assert snapshot.facts[1].time.event.isoformat() == c['comparison'].later_sample_time.isoformat()
    assert c['lineage'].support_relationship(*c['inference'].inputs) == 'unknown'
    assessment = decision.assessment
    assert [(check.rule.id, check.rule.version, check.required, check.overrideable, check.outcome)
        for check in assessment.review.evaluations[0].checks] == [
        ('creatinine_exact_evidence_and_input_suitability', '1', True, False, 'no_detected_violation'),
        ('creatinine_bounded_descriptive_output', '1', True, False, 'no_detected_violation')]
    assert assessment.content_validation.outcome == 'matched'
    assert assessment.state.authorization.issuer == 'SyntheticCreatinineReleaseIssuer/v1'
    assert assessment.state.authorization.policy == Reference(kind='authorization_policy', id='SyntheticCreatinineReleaseGrant', version='1')
    assert assessment.state.authorization.outcome == 'allow'
    assert assessment.state.authorization.target == GRANT_TARGET
    assert assessment.state.authorization.governance_policy_digest == content_digest(assessment.policy)
    assert all(d.state == 'available' and d.updates == 'not_required' for d in assessment.state.dependencies)
    assert assessment.state.freshness.adequate and not assessment.state.freshness.material_change
    assert assessment.policy.degraded_mode is None and assessment.policy.warning_rules == ()
    assert not assessment.exceptions
    assert assessment.payload == required_payload(assessment.review, (), LIMITATIONS)
    assert assessment.payload.limitations[0] == ('Synthetic review of a bounded historical serum-creatinine comparison; '
        'no diagnosis, prediction, treatment recommendation, patient-care delivery, or assertion of current clinical eligibility.')
    assert decision.released_content == c['rendering']
    assert ReleaseDecision.model_validate_json(decision.model_dump_json()) == decision
    assert c['candidate'].state == 'candidate' and assessment.review.state == 'evaluated'
    assert not {'delivered', 'approved', 'clinically_valid'} & set(decision.model_dump())


@pytest.mark.parametrize('sentence', ['AKI is diagnosed.', 'Renal dysfunction is present.', 'Creatinine is abnormal.',
    'Creatinine is elevated.', 'Renal function is worsening.', 'Clinical improvement is established.',
    'Renal failure is predicted tomorrow.', 'Start treatment.', 'Reduce the medication dose.',
    'This is the current renal status.', 'The 20% increase is clinically significant.',
    'The absolute delta establishes significance.', 'Above the reference range.', 'eGFR is reduced.'])
def test_added_interpretation_withheld_even_with_fresh_hashes(case, sentence):
    result = run({**case, 'rendering': replace(case['rendering'], content=case['rendering'].content + ' ' + sentence)})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons
    assert result.assessment.review.evaluations[0].checks[1].outcome == 'hard_failure'
    assert result.assessment.content_validation.outcome == 'failed'
    assert result.assessment.state.authorization.content_digest == review_digest(result.assessment.review)


@pytest.mark.parametrize('change', ['scale', 'value', 'unit', 'direction', 'disclosure', 'earlier_prompt_grammar'])
def test_rendering_exactness(case, change):
    original = case['rendering'].content
    altered = {'scale': original.replace('1.00', '1.0'), 'value': original.replace('1.20', '1.30'),
        'unit': original.replace('mg/dL', 'umol/L'), 'direction': original.replace('increased', 'decreased'),
        'disclosure': original.replace('Synthetic evaluation only; bounded historical comparison.', ''),
        'earlier_prompt_grammar': 'Recorded serum creatinine increased between the selected samples (1.00 mg/dL then 1.20 mg/dL). Synthetic evaluation only; bounded historical comparison.'}[change]
    result = run({**case, 'rendering': replace(case['rendering'], content=altered)})
    assert result.outcome == 'withheld' and result.assessment.content_validation.outcome == 'failed'


@pytest.mark.parametrize('field', ['action', 'rationale', 'basis', 'conditions', 'warnings', 'uncertainty', 'classifications'])
def test_claim_forgery_withholds(case, field):
    claim = case['candidate'].claims[0]
    value = ('New interpretation.' if field in ('action', 'rationale') else
        (Reference(kind='inference', id='other', version='1'),) if field == 'basis' else
        ('ai_inferred',) if field == 'classifications' else ('New interpretation.',))
    changed = replace(case['candidate'], claims=(replace(claim, **{field: value}),))
    result = run({**case, 'candidate': changed})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


@pytest.mark.parametrize('field', ['alternatives', 'monitoring', 'limitations', 'extra_claim', 'actor'])
def test_candidate_envelope_closed(case, field):
    candidate = case['candidate']
    if field == 'extra_claim':
        candidate = replace(candidate, claims=(*candidate.claims, replace(candidate.claims[0], id='extra')))
    elif field == 'actor':
        candidate = replace(candidate, provenance=replace(candidate.provenance, actor='another-producer'))
    else:
        candidate = replace(candidate, **{field: ('unsupported addition',)})
    assert run({**case, 'candidate': candidate}).outcome == 'withheld'


@pytest.mark.parametrize('field', ['earlier_reference', 'earlier_value', 'earlier_sample_time', 'scale', 'offset'])
def test_comparison_fidelity(case, field):
    c = case['comparison']
    updates = {'earlier_reference': {'earlier_reference': replace(c.earlier_reference, version='new')},
        'earlier_value': {'earlier_value': Decimal('1.01')},
        'earlier_sample_time': {'earlier_sample_time': c.earlier_sample_time + timedelta(microseconds=1)},
        'scale': {'earlier_value': Decimal('1.0')},
        'offset': {'earlier_sample_time': c.earlier_sample_time.astimezone(timezone.utc)}}[field]
    result = run({**case, 'comparison': replace(c, **updates)})
    assert result.outcome == 'withheld' and result.assessment.review.evaluations[0].checks[0].outcome == 'hard_failure'


@pytest.mark.parametrize('field', ['concept', 'unit', 'value', 'time', 'sample', 'verification', 'conflict', 'provenance'])
def test_retained_observation_contradictions_are_hard_failures(case, field):
    graph = case['lineage']
    node = next(n for n in graph.nodes if n.stored.fact.id == 'b')
    fact = node.stored.fact
    if field == 'concept':
        fact = replace(fact, concept_id='urine-creatinine')
    elif field == 'unit':
        fact = changed_unit(fact, raw='µmol/L', code='umol/L')
    elif field == 'value':
        fact = replace(fact, value=replace(fact.value, value=replace(fact.value.value, value=Decimal('2.0'))))
    elif field == 'time':
        fact = replace(fact, time=replace(fact.time, event=fact.time.event + timedelta(microseconds=1)))
    elif field == 'sample':
        fact = replace(fact, provenance=replace(fact.provenance, source=case['selection'].selected[0].provenance.source))
    elif field == 'verification':
        fact = replace(fact, verification='unverified')
    elif field == 'conflict':
        fact = replace(fact, conflict='unresolved')
    else:
        fact = replace(fact, provenance=replace(fact.provenance, limitations=('unknown sample',)))
    nodes = tuple(dc_replace(n, stored=dc_replace(n.stored, fact=fact)) if n is node else n for n in graph.nodes)
    result = run({**case, 'lineage': dc_replace(graph, nodes=nodes)})
    assert result.outcome == 'withheld' and result.assessment.review.evaluations[0].checks[0].outcome == 'hard_failure'


@pytest.mark.parametrize('field', ['statement', 'method', 'applicability', 'uncertainty', 'limitations', 'target', 'horizon'])
def test_inference_closed_contract(case, field):
    inference = case['inference']
    updates = {'statement': {'statement': 'AKI is diagnosed.'},
        'method': {'method': replace(inference.method, id='RecordedWeightTrend')},
        'applicability': {'applicability': 'Current clinical status'}, 'uncertainty': {'uncertainty': ('certain',)},
        'limitations': {'validation_limitations': 'clinically validated'},
        'target': {'target': 'renal failure'}, 'horizon': {'horizon': 'tomorrow'}}[field]
    result = run({**case, 'inference': replace(inference, **updates)})
    assert result.outcome == 'withheld' and result.assessment.content_validation.outcome == 'failed'


@pytest.mark.parametrize('field', ['assertions', 'dependencies', 'ancestry', 'roles', 'disclosures', 'cutoff', 'scope'])
def test_lineage_contradictions(case, field):
    graph = case['lineage']
    if field in ('assertions', 'dependencies'):
        graph = dc_replace(graph, **{field: tuple(reversed(getattr(graph, field)))})
    elif field == 'ancestry':
        graph = dc_replace(graph, ancestry=())
    elif field == 'roles':
        graph = dc_replace(graph, nodes=tuple(dc_replace(n, roles=('association',)) for n in graph.nodes))
    elif field == 'disclosures':
        graph = dc_replace(graph, provenance=())
    elif field == 'cutoff':
        graph = dc_replace(graph, cutoff=case['selection'].cutoff)
    else:
        graph = dc_replace(graph, target=replace(TARGET, encounter_id='synthetic-e2'))
    result = run({**case, 'lineage': graph})
    assert result.outcome == 'withheld' and 'hard_safety_failure' in result.reasons


def partial_graph(case):
    graph = case['lineage']
    ref = case['selection'].selected[0].reference
    return dc_replace(graph, nodes=tuple(n for n in graph.nodes if n.stored.fact.reference != ref),
        ancestry=tuple(p for p in graph.ancestry if p[0] != ref),
        provenance=tuple(p for p in graph.provenance if p.reference != ref), coverage='partial',
        unresolved=(UnresolvedReference(case['inference'].reference, ref, 'dependency', 0, None,
            'not_resolvable_in_scope_at_cutoff'),))


@pytest.mark.parametrize('kind', ['partial', 'absent'])
def test_missing_evidence_is_unavailable_not_hard_failure(case, kind):
    changed = compose({**case, 'lineage': partial_graph(case) if kind == 'partial' else None})
    result = run(changed)
    assert result.outcome == 'withheld' and 'safety_check_unavailable' in result.reasons
    assert 'hard_safety_failure' not in result.reasons
    assert result.assessment.review.evaluations[0].checks[0].outcome == 'unavailable'
    assert result.assessment.content_validation.outcome == 'unavailable'
    assert not result.assessment.state.freshness.adequate
    assert all(d.state == 'unavailable' for d in result.assessment.state.dependencies[:3])


@pytest.mark.parametrize('field', ['payload', 'evaluation_reason', 'evaluation_required', 'evaluation_rule', 'evaluation_limits'])
def test_fidelity_checks_actual_evaluation_and_all_disclosures(case, field):
    assessment = run(case).assessment
    review, payload = assessment.review, assessment.payload
    if field == 'payload':
        payload = replace(payload, limitations=payload.limitations[:-1])
    else:
        evaluation = review.evaluations[0]
        if field == 'evaluation_limits':
            evaluation = replace(evaluation, limitations=('unsupported statement',))
        else:
            check = evaluation.checks[0]
            updates = {'evaluation_reason': {'reason': 'clinical improvement'},
                'evaluation_required': {'required': False},
                'evaluation_rule': {'rule': replace(check.rule, id='exact_evidence_and_input_suitability')}}[field]
            evaluation = replace(evaluation, checks=(replace(check, **updates), evaluation.checks[1]))
        review = replace(review, evaluations=(evaluation,))
        payload = required_payload(review, (), LIMITATIONS)
    validation = fidelity(case, review, payload)
    assert validation.outcome == 'failed'
    auth = issuer(case, assessment, review=review, payload=payload)
    changed = replace(assessment, review=review, payload=payload, content_validation=validation,
        state=replace(assessment.state, authorization=auth))
    assert decide(changed).outcome == 'withheld'


@pytest.mark.parametrize('field', ['actor', 'request_id', 'destination', 'recipient', 'intended_use', 'context', 'policy'])
def test_synthetic_grant_is_exactly_scoped(case, field):
    assessment = run(case).assessment
    data = {}
    if field == 'actor':
        data['actor'] = 'synthetic-orchestrator'
    elif field == 'policy':
        data['policy'] = replace(assessment.policy, required_dependencies=())
    else:
        value = Reference(kind='intended_use', id='SyntheticHistoricalWeightComparison', version='1') if field == 'intended_use' else (
            replace(TARGET, encounter_id='synthetic-e2') if field == 'context' else 'other')
        data['target'] = replace(GRANT_TARGET, **{field: value})
    auth = issuer(case, assessment, **data)
    assert auth.outcome == 'deny' and auth.issuer == ISSUER


@pytest.mark.parametrize('boundary,us,outcome', [('start', -1, 'deny'), ('start', 0, 'allow'),
    ('end', -1, 'allow'), ('end', 0, 'deny'), ('end', 1, 'deny')])
def test_authorization_window_boundaries(case, boundary, us, outcome):
    # Evidence was built at NOW, so check the start boundary using an earlier valid composition.
    assessment = run(case).assessment
    at = getattr(GRANT_WINDOW, boundary) + timedelta(microseconds=us)
    if boundary == 'start':
        early = GRANT_WINDOW.start - timedelta(seconds=1)
        snapshot = replace(case['snapshot'], created_at=early, temporal_cutoff=early)
        candidate = build_creatinine_trend_candidate(snapshot=snapshot, comparison=case['comparison'],
            inference=case['inference'], at=early, id='early-candidate')
        rendering = render_creatinine_trend(candidate=candidate, comparison=case['comparison'], target=GRANT_TARGET, at=early, id='early-render')
        review = RecommendationReview(candidate=candidate, rendering=rendering)
        payload = required_payload(review, (), LIMITATIONS)
        policy = creatinine_trend_governance_policy(snapshot=snapshot, selection=case['selection'], inference=case['inference'])
        auth = issuer(case, assessment, at=at, review=review, payload=payload, policy=policy)
    else:
        auth = issuer(case, assessment, at=at)
    assert auth.outcome == outcome


@pytest.mark.parametrize('actor', ['synthetic-orchestrator', 'unknown'])
def test_wrong_actor_cannot_release(case, actor):
    result = run(case, actor=actor)
    assert result.outcome == 'withheld' and 'authorization_not_allowed' in result.reasons


def test_expired_grant_with_fresh_assertions_still_withholds(case):
    at = GRANT_WINDOW.end
    result = run(case, at=at, validity=ValidityWindow(start=at, end=at + timedelta(seconds=10)))
    assert result.outcome == 'withheld' and 'authorization_not_allowed' in result.reasons
    assert result.assessment.content_validation.outcome == 'matched'


def test_weight_issuer_rejected_at_capability_runtime_boundary(case):
    assessment = run(case).assessment
    auth = replace(assessment.state.authorization, issuer='SyntheticWeightReleaseIssuer/v1')
    with pytest.raises(ValueError, match='creatinine synthetic issuer'):
        assemble_creatinine_trend_runtime(snapshot=case['snapshot'], candidate=case['candidate'], target=GRANT_TARGET,
            active_request=GRANT_TARGET, active_output=case['candidate'].reference, authorization=auth,
            freshness=assessment.state.freshness, dependencies=assessment.state.dependencies, at=NOW)


@pytest.mark.parametrize('change,reason', [('safety_fail', 'hard_safety_failure'),
    ('safety_unavailable', 'safety_check_unavailable'), ('safety_not_applicable', 'required_applicable_safety_coverage_missing'),
    ('fidelity_failed', 'exact_meaning_or_validated_scope_not_established'),
    ('dependency_missing', 'required_dependency_update_or_check_unavailable'),
    ('context_missing', 'required_context_not_fresh:snapshot:creatinine-snapshot:1'),
    ('context_inadequate', 'context_inadequate_or_materially_changed'),
    ('auth_denied', 'authorization_not_allowed'), ('runtime_stale', 'runtime_observation_expired_or_future')])
def test_generic_governance_withholds_and_reasons_deterministic(case, change, reason):
    assessment = run(case).assessment
    if change.startswith('safety_'):
        evaluation = assessment.review.evaluations[0]
        outcome = {'safety_fail': 'hard_failure', 'safety_unavailable': 'unavailable', 'safety_not_applicable': 'not_applicable'}[change]
        evaluation = replace(evaluation, checks=(replace(evaluation.checks[0], outcome=outcome), evaluation.checks[1]))
        review = replace(assessment.review, evaluations=(evaluation,))
        payload = required_payload(review, (), LIMITATIONS)
        validation = fidelity(case, review, payload)
        assessment = replace(assessment, review=review, payload=payload, content_validation=validation,
            state=replace(assessment.state, authorization=issuer(case, assessment, review=review, payload=payload)))
    elif change == 'fidelity_failed':
        assessment = replace(assessment, content_validation=replace(assessment.content_validation, outcome='failed'))
    else:
        state = assessment.state
        if change == 'dependency_missing':
            state = replace(state, dependencies=state.dependencies[1:])
        elif change == 'context_missing':
            state = replace(state, freshness=replace(state.freshness, items=state.freshness.items[1:]))
        elif change == 'context_inadequate':
            state = replace(state, freshness=replace(state.freshness, adequate=False))
        elif change == 'auth_denied':
            state = replace(state, authorization=replace(state.authorization, outcome='deny'))
        else:
            state = replace(state, observed_at=NOW - timedelta(seconds=31))
        assessment = replace(assessment, state=state)
    decision = decide(assessment)
    assert decision.outcome == 'withheld' and reason in decision.reasons
    assert decide(assessment).reasons == decision.reasons


@pytest.mark.parametrize('delta,outcome', [(-1, 'withheld'), (0, 'released'), (19_999_999, 'released'), (20_000_000, 'withheld')])
def test_assessment_validity_window(case, delta, outcome):
    assessment = run(case).assessment
    assert decide(assessment, at=NOW + timedelta(microseconds=delta)).outcome == outcome


@pytest.mark.parametrize('field', ['request', 'output', 'target_patient', 'target_encounter'])
def test_runtime_active_scope(case, field):
    if field == 'request':
        result = run(case, active_request=replace(GRANT_TARGET, request_id='superseded'))
    elif field == 'output':
        result = run(case, active_output=replace(case['candidate'].reference, version='other'))
    else:
        context = replace(TARGET, **({'patient_id': 'synthetic-p2'} if field == 'target_patient' else {'encounter_id': 'synthetic-e2'}))
        result = run(case, target=replace(GRANT_TARGET, context=context))
    assert result.outcome == 'withheld'


def test_policy_identity_depends_on_exact_resolved_requirements(case):
    first = creatinine_trend_governance_policy(snapshot=case['snapshot'], selection=case['selection'], inference=case['inference'])
    second = creatinine_trend_governance_policy(snapshot=replace(case['snapshot'], id='another'), selection=case['selection'], inference=case['inference'])
    assert first.reference != second.reference
    assert first.reference.id.startswith('SyntheticCreatinineHistoricalRelease/')
    validate_governance_bundle(first, second)
    assert first.required_rules == RULES and first.intended_use == USE
    assert all('Weight' not in r.id for r in (first.reference, first.safety_policy, first.freshness_policy,
        first.authorization_policy, first.content_validation_method, *first.required_rules))


@pytest.mark.parametrize('member', ['candidate', 'rendering', 'safety', 'fidelity', 'decision'])
def test_public_results_frozen(case, member):
    decision = run(case)
    obj, field, value = {'candidate': (case['candidate'].claims[0], 'action', 'other'),
        'rendering': (case['rendering'], 'content', 'other'),
        'safety': (decision.assessment.review.evaluations[0].checks[0], 'outcome', 'unavailable'),
        'fidelity': (decision.assessment.content_validation, 'outcome', 'failed'),
        'decision': (decision, 'outcome', 'withheld')}[member]
    with pytest.raises(ValidationError):
        setattr(obj, field, value)


def test_current_corrections_do_not_turn_historical_release_into_current_claim(case, registered):
    original = run(case)
    a = case['selection'].selected[0]
    with transaction(registered) as repo:
        corrected = revision(a, '2')
        repo.append_revision(corrected, target=TARGET)
        later = repo.capture_cutoff()
    assert select(registered, later).selected[0].reference == corrected.reference
    assert run(case) == original
    assert 'later corrections not assessed' in original.assessment.state.freshness.items[0].rationale
    assert 'current clinical eligibility' in original.assessment.payload.limitations[0]


def test_no_database_access_or_schema_changes_during_phase_c(case, registered):
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        decision = run(case)
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    assert not statements
    with registered.connect() as conn:
        assert set(inspect(conn).get_table_names()) == {'patient', 'encounter', 'fact_revision', 'revision_link',
            'repository_identity', 'weight_trend_execution', 'creatinine_trend_execution', 'patient_state_temporal_execution', 'alembic_version'}
    assert decision.outcome == 'released'


@pytest.mark.parametrize('damage', ['inference', 'history'])
def test_storage_integrity_errors_not_converted_into_withholding(case, registered, damage):
    if damage == 'history':
        with transaction(registered) as repo:
            repo.append_revision(revision(case['selection'].selected[0], '2'), target=TARGET)
            cutoff = repo.capture_cutoff()
        sql = 'DELETE FROM revision_link'
    else:
        cutoff = case['lineage'].cutoff
        sql = "UPDATE fact_revision SET payload='{}' WHERE kind='inference'"
    with registered.begin() as conn:
        conn.execute(text(sql))
    with pytest.raises(StorageIntegrityError):
        graph = resolve(registered, case['inference'].reference, cutoff)
        run({**case, 'lineage': graph})


@pytest.mark.parametrize('exception', [StorageIntegrityError, KeyboardInterrupt, SystemExit])
def test_producer_exceptions_escape_without_fake_decision(case, monkeypatch, exception):
    def fail(*args, **kwargs):
        raise exception('injected failure')
    monkeypatch.setattr(release, 'evaluate_creatinine_trend', fail)
    with pytest.raises(exception):
        run(case)


def test_impossible_structural_selection_raises(case):
    a, b = case['selection'].selected
    forged = case['selection'].model_copy(update={'selected': (a, b.model_copy(update={'id': a.id}))})
    with pytest.raises(ValidationError):
        run(case, selection=forged)


def test_independent_safety_does_not_trust_renderer_helper(case, monkeypatch):
    monkeypatch.setattr(release, '_render_statement', lambda comparison: 'AKI is diagnosed.')
    rendered = render_creatinine_trend(candidate=case['candidate'], comparison=case['comparison'], target=GRANT_TARGET, at=NOW, id='forged-render')
    result = run({**case, 'rendering': rendered})
    assert result.outcome == 'withheld' and result.assessment.content_validation.outcome == 'failed'
