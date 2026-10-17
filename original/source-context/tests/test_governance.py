"""Synthetic release/presentation contracts, not clinical-validation evidence."""
from datetime import datetime, timedelta, timezone
import json
from itertools import count

import pytest
from pydantic import ValidationError

from app.models.clinical.common import (
    Binding, ClinicalTime, ContextTarget, IdentityVerification, Provenance, Reference, Source,
)
from app.models.clinical.decisions import (
    ClinicalClaim, ClinicalRecommendation, HumanDecision, RecommendationReview,
    RenderedRecommendation, SafetyCheck, SafetyEvaluation,
)
from app.models.clinical.facts import ContextSnapshot, EncounterContext, PatientContext
from app.models.clinical.governance import (
    AuthorizationAssertion, ContentValidationAssertion, ContextFreshnessAssessment,
    DependencyRequirement, DependencyState, FreshnessItem, GovernancePolicy, OutputTarget,
    PresentationReceipt, PresentationRecord, ReleaseDecision, RuntimeState,
    ValidityWindow, WarningException, WarningExceptionProposal, WarningRule, review_digest,
    PresentationPayload, FinalDestinationVerification, ConditionSatisfactionAssertion,
    content_digest, required_payload, validate_governance_bundle,
)
from app.services.governance_service import (
    assess_presentation, assess_release, decide_release, record_presentation,
)

NOW = datetime(2026, 9, 26, 10, tzinfo=timezone.utc)
ASSERTIONS = count()
LIMITATIONS = ('synthetic only',)


def assertion_ref(kind):
    return ref(kind, f'assertion-{next(ASSERTIONS)}')


def payload_for(case):
    return case.get('payload') or required_payload(case['review'], (), LIMITATIONS)


def ref(kind, id='synthetic', version='1'):
    return Reference(kind=kind, id=id, version=version)


def change(model, **changes):
    return type(model).model_validate({**model.model_dump(), **changes})


def window(start=NOW, end=NOW+timedelta(hours=1)):
    return ValidityWindow(start=start, end=end)


@pytest.fixture
def case():
    source = Source(namespace='synthetic', identifier='source', channel='system')
    context = ContextTarget(patient_id='p1', encounter_id='e1')
    identity = IdentityVerification(status='verified', method='fixture', verifier='identity-service', assessed_at=NOW, source=source)
    binding = Binding(target=context, verification=identity)
    snapshot = ContextSnapshot(id='snapshot1', version='1', patient=PatientContext(patient_id='p1', source_identifiers=(source,)),
        encounter=EncounterContext(encounter_id='e1', patient_id='p1', time=ClinicalTime(precision='unknown'), source=source),
        binding=binding, sources=(source,), created_at=NOW, temporal_cutoff=NOW, completeness='complete_for_scope',
        completeness_scope='synthetic only')
    candidate = ClinicalRecommendation(id='candidate1', revision='1', snapshot=snapshot, intended_use=ref('intended_use'),
        claims=(ClinicalClaim(id='claim1', action='Synthetic review', rationale='fixture', classifications=('evidence_derived',),
                             basis=(ref('evidence'),)),),
        provenance=Provenance(source=source, actor='fixture', recorded_at=NOW, lineage='complete'), created_at=NOW)
    rendering = RenderedRecommendation(id='rendering1', revision='1', candidate=candidate.reference, snapshot=snapshot.reference,
        content='Synthetic review with limitations. Not clinically validated.', destination='chart-panel', rendered_at=NOW)
    check = SafetyCheck(id='check1', rule=ref('safety_rule'), required=True, outcome='no_detected_violation', reason='fixture', coverage='synthetic')
    evaluation = SafetyEvaluation(id='evaluation1', revision='1', candidate=candidate.reference, rendering=rendering.reference,
        snapshot=snapshot.reference, policy=ref('safety_policy'), checks=(check,), exact_meaning='matched',
        coverage='synthetic', limitations=('not clinical validation',), evaluated_at=NOW)
    review = RecommendationReview(candidate=candidate, rendering=rendering, evaluations=(evaluation,))
    target = OutputTarget(context=context, request_id='request1', intended_use=candidate.intended_use,
                          destination='chart-panel', recipient='clinician1')
    policy = GovernancePolicy(reference=ref('governance_policy'), intended_use=candidate.intended_use,
        safety_policy=ref('safety_policy'), freshness_policy=ref('freshness_policy'), authorization_policy=ref('authorization_policy'),
        content_validation_method=ref('content_validation_method'), required_rules=(check.rule,),
        required_context=(snapshot.reference,), required_dependencies=(DependencyRequirement(reference=ref('update_feed'), updates_required=True),),
        max_assessment_age=timedelta(seconds=30))
    return dict(review=review, target=target, policy=policy, identity=identity)


def authority(case, action='release', at=NOW, actor='orchestrator', **changes):
    data = dict(reference=assertion_ref('authorization'), policy=case['policy'].authorization_policy, subject=actor,
        role='fixture-scoped-role', issuer='trusted-policy-adapter', action=action, target=case['target'],
        content_digest=review_digest(case['review']), governance_policy_digest=content_digest(case['policy']),
        payload_digest=None if action == 'warning_exception' else content_digest(payload_for(case)), outcome='allow', issued_at=at, validity=window(), rationale='fixture only')
    data.update(changes)
    return AuthorizationAssertion(**data)


def runtime(case, action='release', at=NOW, **changes):
    freshness = ContextFreshnessAssessment(reference=assertion_ref('freshness_assessment'), snapshot=case['review'].candidate.snapshot.reference,
        policy=case['policy'].freshness_policy, assessed_at=at, adequate=True, material_change=False,
        items=(FreshnessItem(reference=case['review'].candidate.snapshot.reference, state='fresh', validity=window(), clinical_time=NOW, rationale='fixture'),),
        assessor='context-adapter', rationale='synthetic scope')
    data = dict(target=case['target'], identity=change(case['identity'], assessed_at=at), request_state='active', output_state='current',
        observed_at=at, authorization=authority(case, action, at), freshness=freshness,
        dependencies=(DependencyState(reference=ref('update_feed'), state='available', updates='available', validity=window(), rationale='fixture'),))
    data.update(changes)
    return RuntimeState(**data)


def eligibility(case, **changes):
    case = {**case, 'policy': changes.get('policy', case['policy'])}
    payload = required_payload(case['review'], changes.get('exceptions', ()), LIMITATIONS)
    case = {**case, 'payload': payload}
    data = dict(reference=ref('release_eligibility'), payload=payload, review=case['review'], target=case['target'], policy=case['policy'],
        content_validation=ContentValidationAssertion(reference=ref('content_validation'), payload_digest=content_digest(payload), method=case['policy'].content_validation_method,
            target=case['target'], content_digest=review_digest(case['review']), outcome='matched', coverage='in_scope',
            assessor='validation-adapter', assessed_at=NOW, validity=window(), rationale='fixture exact meaning assessment',
            limitations=('synthetic only',)),
        state=runtime(case), assessor='orchestrator', at=NOW, validity=window())
    data.update(changes)
    return assess_release(**data)


def release(case, assessment=None, at=NOW):
    return decide_release(reference=ref('release_decision'), assessment=assessment or eligibility(case), actor='orchestrator', at=at)


def presentation(case, released=None, at=NOW+timedelta(seconds=1), **changes):
    released = released or release(case)
    case = {**case, 'payload': released.assessment.payload, 'policy': released.assessment.policy}
    payload = case['payload']
    if 'rendering' in changes:
        payload = change(payload, rendering=changes.pop('rendering'))
    data = dict(reference=ref('presentation_eligibility'), release=released, payload=payload,
        state=runtime(case, 'present', at), assessor='orchestrator', at=at,
        validity=window(at, at+timedelta(seconds=15)))
    data.update(changes)
    return assess_presentation(**data)


def final_verification(assessment, state, at, attempt):
    return FinalDestinationVerification(
        reference=assertion_ref('final_destination_verification'), attempt=attempt,
        eligibility=assessment.reference, release=assessment.release.reference,
        payload_digest=content_digest(assessment.payload), state_digest=content_digest(state),
        target=state.target, verified_at=at, verifier='atomic-display-adapter', outcome='verified',
        conditions=tuple(ConditionSatisfactionAssertion(
            reference=assertion_ref('condition_satisfaction'), exception_digest=content_digest(e.proposal),
            attempt=attempt, target=state.target, at=at, assessor='scoped-condition-adapter', outcome='satisfied')
            for e in assessment.release.assessment.exceptions))


def record(case, assessment=None, at=NOW+timedelta(seconds=2), final_state=None, receipt=True,
           verification=True, attempt=None):
    assessment = assessment or presentation(case)
    case = {**case, 'payload': assessment.release.assessment.payload, 'policy': assessment.release.assessment.policy}
    state = final_state or runtime(case, 'present', at)
    attempt = attempt or ref('presentation_record')
    verification = final_verification(assessment, state, at, attempt) if verification is True else verification
    evidence = PresentationReceipt(evidence=assertion_ref('presentation_receipt'), attempt=attempt,
        final_verification=verification.reference if verification else ref('final_destination_verification','missing'),
        release=assessment.release.reference, payload=assessment.payload, target=state.target,
        shown_at=at, observer='display-adapter') if receipt is True else receipt
    # An existing receipt must be paired with its actual verification by callers.
    return record_presentation(reference=attempt, assessment=assessment, final_state=state,
        actor='orchestrator', at=at, receipt=evidence, final_verification=verification)


def with_check(case, **changes):
    e = case['review'].evaluations[0]
    revised = change(e, checks=(change(e.checks[0], **changes),))
    return {**case, 'review': change(case['review'], evaluations=(revised,))}


def exception(case, **changes):
    evaluation = case['review'].evaluations[0]
    data = dict(reference=ref('warning_exception'), evaluation=evaluation.reference, check_id='check1', safety_policy=evaluation.policy,
        target=case['target'], content_digest=review_digest(case['review']), actor='clinician1',
        rationale='qualified synthetic exception rationale', conditions='synthetic intended use only', at=NOW, validity=window())
    data.update(changes)
    proposal = WarningExceptionProposal(**data)
    auth = authority(case, 'warning_exception', actor='clinician1', warning_evaluation=evaluation.reference,
                     warning_check_id='check1', exception_digest=content_digest(proposal))
    return WarningException(**data, authority=auth)


def test_successful_evaluated_released_presented(case):
    assessed = eligibility(case)
    assert assessed.eligible and assessed.availability == 'available'
    released = release(case, assessed)
    assert released.outcome == 'released' and released.reasons == ()
    assert case['review'].state == 'evaluated' and case['review'].candidate.state == 'candidate'
    shown = record(case, presentation(case, released))
    assert shown.outcome == 'presented'
    assert shown.receipt.release == released.reference
    assert shown.receipt.rendering == released.released_content
    assert shown.receipt.target == released.assessment.target
    assert PresentationRecord.model_validate_json(shown.model_dump_json()) == shown
    assert ReleaseDecision.model_validate_json(released.model_dump_json()) == released
    assert 'clinically_valid' not in released.model_dump()


@pytest.mark.parametrize('field,value', [('patient_id','wrong'), ('encounter_id','wrong')])
def test_wrong_patient_or_encounter_withholds_release(case, field, value):
    wrong = change(case['target'], context=change(case['target'].context, **{field:value}))
    decision = release(case, eligibility(case, state=runtime(case, target=wrong)))
    assert decision.outcome == 'withheld'
    assert 'patient_encounter_request_destination_or_recipient_mismatch' in decision.reasons


@pytest.mark.parametrize('changes', [dict(request_id='old-request'), dict(destination='other-panel'), dict(recipient='other-clinician'),
                                    dict(intended_use=ref('intended_use','other'))])
def test_wrong_request_destination_recipient_or_use_withholds_release(case, changes):
    state = runtime(case, target=change(case['target'], **changes))
    assert release(case, eligibility(case, state=state)).outcome == 'withheld'


def test_reverification_does_not_change_clinical_target(case):
    verified_again = change(case['identity'], verifier='another-verifier')
    assessed = eligibility(case, state=runtime(case, identity=verified_again))
    assert release(case, assessed).outcome == 'released'
    assert assessed.review.candidate.snapshot.binding.verification != verified_again


@pytest.mark.parametrize('freshness_state', ['stale','unknown'])
def test_stale_or_unknown_required_context_blocks_both_paths(case, freshness_state):
    current = runtime(case)
    stale = change(current.freshness, items=(change(current.freshness.items[0], state=freshness_state),))
    assert release(case, eligibility(case, state=change(current, freshness=stale))).outcome == 'withheld'
    now = NOW+timedelta(seconds=2)
    present_state = runtime(case, 'present', now)
    bad = change(present_state, freshness=change(present_state.freshness, items=stale.items))
    result = record(case, final_state=bad, receipt=None)
    assert result.outcome == 'withheld'
    assert any(r.startswith('required_context_not_fresh') for r in result.reasons)


def test_context_windows_are_per_input_and_exclusive_at_end(case):
    current = runtime(case)
    expired = change(current.freshness.items[0], validity=window(NOW-timedelta(minutes=1), NOW))
    assert release(case, eligibility(case, state=change(current, freshness=change(current.freshness, items=(expired,))))).outcome == 'withheld'
    extra = ref('observation','required-weight')
    case = {**case, 'policy': change(case['policy'], required_context=(*case['policy'].required_context, extra))}
    assert not eligibility(case).eligible  # Missing manifest entry cannot mean fresh.


@pytest.mark.parametrize('state,updates', [('unavailable','available'), ('unknown','unknown'), ('suspended','available'),
                                         ('available','unavailable'), ('available','not_required')])
def test_required_dependency_or_updates_unavailable_blocks(case, state, updates):
    current = runtime(case)
    current = change(current, dependencies=(change(current.dependencies[0], state=state, updates=updates),))
    assessed = eligibility(case, state=current)
    assert assessed.availability == 'unavailable'
    assert release(case, assessed).outcome == 'withheld'
    # Even an approved optional degraded mode cannot waive a mandatory dependency.
    policy = change(case['policy'], degraded_mode=ref('validated_degraded_mode'), degraded_dependencies=(ref('optional_feed'),))
    assert not eligibility(case, state=current, policy=policy).eligible


def test_missing_required_dependency_and_optional_degradation(case):
    assert not eligibility(case, state=runtime(case, dependencies=())).eligible
    optional = DependencyState(reference=ref('optional_feed'), state='unavailable', updates='unavailable', rationale='optional feed offline')
    current = runtime(case)
    current = change(current, dependencies=(*current.dependencies, optional))
    assert release(case, eligibility(case, state=current)).outcome == 'withheld'
    policy = change(case['policy'], degraded_mode=ref('validated_degraded_mode'), degraded_dependencies=(ref('optional_feed'),))
    current = change(current, authorization=authority({**case, 'policy': policy}))
    assessed = eligibility(case, state=current, policy=policy)
    assert assessed.availability == 'degraded' and assessed.eligible
    assert release(case, assessed).assessment.state.dependencies[-1].state == 'unavailable'


def test_hard_failure_cannot_be_overridden_or_acknowledged(case):
    case = with_check(case, outcome='hard_failure', reason='identity hard failure')
    attempted = exception(case)
    assessed = eligibility(case, exceptions=(attempted,))
    assert release(case, assessed).outcome == 'withheld'
    assert 'hard_safety_failure' in assessed.reasons
    assert 'exception_targets_nonoverrideable_or_missing_warning' in assessed.reasons
    event = HumanDecision(id='ack', evaluation=case['review'].evaluations[0], actor='clinician1', role='clinician',
        authority=ref('authority'), at=NOW, action='acknowledge', rationale='awareness only')
    assert event.evaluation.outcome == 'hard_failure'
    assert not eligibility(case).eligible


def test_permitted_warning_exception_preserves_original_warning(case):
    case = with_check(case, outcome='warning', overrideable=True)
    case = {**case, 'policy': change(case['policy'], warning_rules=(WarningRule(rule=ref('safety_rule'), response='exception_required'),))}
    assert not eligibility(case).eligible
    waiver = exception(case)
    released = release(case, eligibility(case, exceptions=(waiver,)))
    assert released.outcome == 'released'
    assert released.assessment.review.evaluations[0].outcome == 'warning'
    assert released.assessment.exceptions[0].rationale == waiver.rationale
    assert record(case, presentation(case, released)).outcome == 'presented'
    with pytest.raises(ValidationError):
        released.assessment.review.evaluations[0].checks[0].outcome = 'no_detected_violation'


@pytest.mark.parametrize('failure', ['denied','wrong_check','expired','wrong_target'])
def test_warning_exception_requires_scoped_current_authority(case, failure):
    case = with_check(case, outcome='warning', overrideable=True)
    case = {**case, 'policy': change(case['policy'], warning_rules=(WarningRule(rule=ref('safety_rule'), response='exception_required'),))}
    waiver = exception(case)
    if failure == 'denied':
        waiver = change(waiver, authority=change(waiver.authority, outcome='deny'))
    elif failure == 'wrong_check':
        waiver = change(waiver, authority=change(waiver.authority, warning_check_id='different'))
    elif failure == 'expired':
        waiver = change(waiver, validity=window(NOW-timedelta(minutes=1), NOW))
    else:
        waiver = change(waiver, target=change(case['target'], request_id='other'))
    assert release(case, eligibility(case, exceptions=(waiver,))).outcome == 'withheld'


def test_advisory_warning_is_not_an_exception_or_pass(case):
    case = with_check(case, outcome='warning')
    assert not eligibility(case).eligible  # No implicit default response.
    policy = change(case['policy'], warning_rules=(WarningRule(rule=ref('safety_rule'), response='advisory'),))
    released = release(case, eligibility(case, policy=policy))
    assert released.outcome == 'released'
    assert released.assessment.review.evaluations[0].outcome == 'warning'


@pytest.mark.parametrize('outcome', ['unavailable','not_applicable'])
def test_unperformed_or_inapplicable_checks_do_not_establish_required_coverage(case, outcome):
    case = with_check(case, outcome=outcome)
    result = release(case)
    assert result.outcome == 'withheld'
    assert 'required_applicable_safety_coverage_missing' in result.reasons


def test_missing_evaluation_and_exact_meaning_failure_block(case):
    empty = {**case, 'review': change(case['review'], evaluations=())}
    assert not eligibility(empty).eligible
    e = change(case['review'].evaluations[0], exact_meaning='failed')
    failed = {**case, 'review': change(case['review'], evaluations=(e,))}
    assert not eligibility(failed).eligible
    assert not eligibility(case, content_validation=change(eligibility(case).content_validation, coverage='out_of_scope')).eligible


def test_same_revision_changed_content_cannot_reuse_validation(case):
    old = eligibility(case)
    altered = change(case['review'], rendering=change(case['review'].rendering, content='Different clinical meaning'))
    result = release(case, change(old, review=altered))
    assert result.outcome == 'withheld'
    assert 'exact_evaluated_content_or_target_mismatch' in result.reasons


def test_exact_revision_mismatch_at_release_and_presentation(case):
    with pytest.raises(ValidationError):
        change(case['review'], rendering=change(case['review'].rendering, revision='2'))
    released = release(case)
    assessed = presentation(case, released, rendering=change(case['review'].rendering, revision='2'))
    assert not assessed.eligible
    assert 'presentation_content_differs_from_exact_release' in assessed.reasons
    assert record(case, assessed).outcome == 'rejected'


def test_released_output_presentation_eligibility_expires(case):
    released = release(case)
    assessed = presentation(case, released, validity=window(NOW+timedelta(seconds=1), NOW+timedelta(seconds=2)))
    assert assessed.eligible
    result = record(case, assessed, at=NOW+timedelta(seconds=2), receipt=None)
    assert result.outcome == 'withheld'
    assert 'presentation_eligibility_expired_or_future' in result.reasons
    assert released.outcome == 'released'


def test_expired_release_requires_new_release_even_with_fresh_destination(case):
    released = release(case, eligibility(case, validity=window(NOW, NOW+timedelta(seconds=1))))
    assessed = presentation(case, released)
    assert not assessed.eligible and 'release_no_longer_eligible' in assessed.reasons


@pytest.mark.parametrize('changes', [dict(request_id='new-request'), dict(destination='other-panel'),
                                    dict(context=ContextTarget(patient_id='p2', encounter_id='e1')),
                                    dict(context=ContextTarget(patient_id='p1', encounter_id='e2'))])
def test_destination_switch_immediately_before_presentation(case, changes):
    assessed = presentation(case)
    assert assessed.eligible
    now = NOW+timedelta(seconds=2)
    latest = runtime(case, 'present', now, target=change(case['target'], **changes))
    blocked = record(case, assessed, final_state=latest, receipt=None)
    assert blocked.outcome == 'withheld'
    assert 'patient_encounter_request_destination_or_recipient_mismatch' in blocked.reasons


def test_release_does_not_prove_presentation_and_receipt_must_match(case):
    assessed = presentation(case)
    unknown = record(case, assessed, receipt=None)
    assert unknown.outcome == 'unconfirmed' and unknown.reasons == ('presentation_not_confirmed',)
    valid = record(case, assessed)
    bad_receipt = change(valid.receipt, payload=change(valid.receipt.payload, rendering=change(valid.receipt.rendering, content='Changed text using same revision')))
    rejected = record(case, assessed, final_state=valid.final_state,
                      verification=valid.final_verification, receipt=bad_receipt)
    assert rejected.outcome == 'rejected'
    assert 'delivery_receipt_content_target_or_time_mismatch' in rejected.reasons


def test_withheld_release_and_presentation_are_serialized_audit_records(case):
    denied = runtime(case, authorization=authority(case, outcome='deny'))
    withheld = release(case, eligibility(case, state=denied))
    assert withheld.released_content is None
    assert json.loads(withheld.model_dump_json())['reasons']
    assessed = presentation(case, withheld)
    attempted = record(case, assessed, receipt=None)
    assert attempted.outcome == 'withheld'
    assert 'release_was_withheld' in attempted.reasons
    assert PresentationRecord.model_validate_json(attempted.model_dump_json()) == attempted


def test_caller_cannot_forge_successful_decision_fields(case):
    denied = release(case, eligibility(case, state=runtime(case, authorization=authority(case, outcome='deny'))))
    with pytest.raises(ValidationError):
        change(denied, outcome='released', reasons=())
    unconfirmed = record(case, receipt=None)
    with pytest.raises(ValidationError):
        change(unconfirmed, outcome='presented', reasons=())


def test_blocked_presentation_assessment_cannot_be_silently_reactivated(case):
    now = NOW+timedelta(seconds=1)
    bad = runtime(case, 'present', now, request_state='superseded')
    assessed = presentation(case, state=bad)
    assert not assessed.eligible
    result = record(case, assessed)  # A later good observation requires a new assessment.
    assert result.outcome == 'rejected'
    assert 'presentation_assessment_withheld' in result.reasons


def test_material_change_withdrawal_and_lost_updates_block_final_presentation(case):
    now = NOW+timedelta(seconds=2)
    state = runtime(case, 'present', now)
    bad_states = [change(state, output_state='withdrawn'),
                  change(state, freshness=change(state.freshness, material_change=True)),
                  change(state, dependencies=(change(state.dependencies[0], updates='unavailable'),))]
    for bad in bad_states:
        assert record(case, final_state=bad, receipt=None).outcome == 'withheld'


def test_stale_runtime_observation_requires_a_new_destination_check(case):
    assessed = presentation(case)
    old = runtime(case, 'present', NOW)
    result = record(case, assessed, final_state=old, receipt=None)
    assert result.outcome == 'withheld'
    assert 'destination_not_rechecked_for_presentation' in result.reasons


def test_configurable_windows_and_naive_time_rejection(case):
    with pytest.raises(ValidationError):
        window(NOW, NOW)
    with pytest.raises(ValidationError):
        window(NOW.replace(tzinfo=None), NOW+timedelta(seconds=1))
    with pytest.raises(ValidationError):
        change(case['policy'], max_assessment_age=timedelta(0))
    assert release(case, at=NOW+timedelta(seconds=31)).outcome == 'withheld'


def test_withheld_release_assessment_cannot_mature_into_permission(case):
    future = NOW+timedelta(seconds=1)
    current = runtime(case, authorization=authority(case, at=future))
    assessed = eligibility(case, state=current)
    assert not assessed.eligible
    result = release(case, assessed, at=future)
    assert result.outcome == 'withheld'
    assert 'release_assessment_withheld' in result.reasons


def test_degraded_mode_is_scoped_to_identified_optional_losses(case):
    policy = change(case['policy'], degraded_mode=ref('validated_degraded_mode'), degraded_dependencies=(ref('optional_feed'),))
    current = runtime(case)
    other_loss = DependencyState(reference=ref('different_optional_feed'), state='unavailable', updates='unknown', rationale='not covered by approval')
    result = release(case, eligibility(case, policy=policy, state=change(current, dependencies=(*current.dependencies, other_loss))))
    assert result.availability == 'degraded' and result.outcome == 'withheld'
    assert 'degraded_loss_outside_approved_scope' in result.reasons
    with pytest.raises(ValidationError, match='cannot waive required'):
        change(policy, degraded_dependencies=(ref('update_feed'),))


def test_exception_expiry_blocks_presentation_without_mutating_release(case):
    case = with_check(case, outcome='warning', overrideable=True)
    case = {**case, 'policy': change(case['policy'], warning_rules=(WarningRule(rule=ref('safety_rule'), response='exception_required'),))}
    waiver = exception(case, validity=window(NOW, NOW+timedelta(seconds=2)))
    released = release(case, eligibility(case, exceptions=(waiver,)))
    assert released.outcome == 'released'
    assessed = presentation(case, released)
    assert assessed.eligible
    result = record(case, assessed, at=NOW+timedelta(seconds=2), receipt=None)
    assert result.outcome == 'withheld' and 'exception_expired_or_future' in result.reasons
    assert released.assessment.review.evaluations[0].outcome == 'warning'


@pytest.mark.parametrize('auth_change', [dict(outcome='deny'), dict(subject='other'), dict(action='release'),
                                       dict(content_digest='0'*64)])
def test_final_presentation_authority_is_separate_and_scoped(case, auth_change):
    now = NOW+timedelta(seconds=2)
    current = runtime(case, 'present', now)
    current = change(current, authorization=change(current.authorization, **auth_change))
    assert record(case, final_state=current, receipt=None).outcome == 'withheld'


def test_each_context_input_uses_its_own_validity_window(case):
    extra = ref('observation','weight')
    policy = change(case['policy'], required_context=(*case['policy'].required_context, extra))
    current = runtime(case)
    item = FreshnessItem(reference=extra, state='fresh', validity=window(NOW, NOW+timedelta(seconds=1)), rationale='independent source freshness policy')
    current = change(current, freshness=change(current.freshness, items=(*current.freshness.items, item)))
    current = change(current, authorization=authority({**case, 'policy': policy}))
    assessed = eligibility(case, state=current, policy=policy)
    assert release(case, assessed).outcome == 'released'
    delayed = release(case, assessed, at=NOW+timedelta(seconds=1))
    assert delayed.outcome == 'withheld'
    assert any('weight' in reason for reason in delayed.reasons)


def test_context_can_be_reassessed_without_reusing_old_destination_observation(case):
    # Old runtime observation expires, but a still-valid release supports a new presentation assessment.
    now = NOW+timedelta(seconds=40)
    released = release(case)
    assessed = presentation(case, released, at=now, validity=window(now, now+timedelta(seconds=10)))
    assert assessed.eligible
    assert record(case, assessed, at=now+timedelta(seconds=1)).outcome == 'presented'


def test_exact_meaning_attestation_is_not_replaced_by_automated_no_violation(case):
    original = eligibility(case)
    for change_fields in (dict(outcome='unavailable'), dict(coverage='unknown'), dict(method=ref('content_validation_method','wrong'))):
        assessed = change(original, content_validation=change(original.content_validation, **change_fields))
        assert not assessed.eligible
    assert original.review.evaluations[0].outcome == 'no_detected_violation'
    assert 'clinically_valid' not in ReleaseDecision.model_json_schema()['properties']


def test_authorship_and_final_binding_are_retained_on_rejected_receipt(case):
    assessed = presentation(case)
    good = record(case, assessed)
    receipt = change(good.receipt, release=ref('release_decision','unrelated'))
    rejected = record(case, assessed, final_state=good.final_state,
                      verification=good.final_verification, receipt=receipt)
    assert rejected.outcome == 'rejected'
    assert rejected.receipt == receipt
    assert rejected.actor and rejected.at and rejected.final_state.target



def warning_case(case):
    case = with_check(case, outcome='warning', overrideable=True,
                      reason='Material warning: synthetic interaction requires monitoring')
    return {**case, 'policy': change(case['policy'], warning_rules=(
        WarningRule(rule=ref('safety_rule'), response='exception_required'),))}


@pytest.mark.parametrize('field', ['freshness', 'authorization'])
@pytest.mark.parametrize('boundary', ['eligibility', 'delivery'])
def test_same_revision_assertion_conflicts_across_nested_bundle(case, field, boundary):
    released = release(case)
    assessed = presentation(case, released)
    at = NOW + timedelta(seconds=2)
    current = runtime(case, 'present', at)
    prior = getattr(released.assessment.state if boundary == 'eligibility' else assessed.state, field)
    changed_assertion = change(getattr(current, field), reference=prior.reference)
    current = change(current, **{field: changed_assertion})
    with pytest.raises(ValueError, match='conflicting'):
        if boundary == 'eligibility':
            presentation(case, released, at=at, state=current)
        else:
            record(case, assessed, final_state=current)


def test_conflicting_assertion_rejected_during_json_reconstruction(case):
    good = record(case)
    data = good.model_dump(mode='json')
    data['final_state']['freshness']['reference'] = data['assessment']['state']['freshness']['reference']
    with pytest.raises(ValidationError, match='conflicting'):
        PresentationRecord.model_validate_json(json.dumps(data))


def test_new_revision_reassessment_round_trips_and_resource_state_can_change(case):
    released = release(case)
    at = NOW + timedelta(seconds=1)
    current = runtime(case, 'present', at)
    old = released.assessment.state.freshness
    current = change(current, freshness=change(current.freshness,
        reference=change(old.reference, version='2')))
    assessed = presentation(case, released, state=current)
    at += timedelta(seconds=1)
    final = runtime(case, 'present', at)
    final = change(final, freshness=change(final.freshness, reference=change(old.reference, version='3')),
                   dependencies=(change(final.dependencies[0], rationale='New observation of the same feed'),))
    result = record(case, assessed, final_state=final)
    assert result.outcome == 'presented'
    assert result.final_state.dependencies[0].reference == released.assessment.state.dependencies[0].reference
    assert result.final_state.dependencies[0] != released.assessment.state.dependencies[0]
    assert PresentationRecord.model_validate_json(result.model_dump_json()) == result
    validate_governance_bundle(result, result)  # Identical reuse is allowed.


@pytest.mark.parametrize('field', ['policy', 'content_validation', 'assessment', 'decision', 'receipt'])
def test_separately_supplied_assertion_bundles_reject_conflicting_revisions(case, field):
    shown = record(case)
    decision = shown.assessment.release
    assessment = decision.assessment
    if field == 'policy':
        original = assessment.policy
        altered = change(original, required_dependencies=())
    elif field == 'content_validation':
        original = assessment.content_validation
        altered = change(original, rationale='Contradictory retained rationale')
    elif field == 'assessment':
        original = assessment
        altered = change(original, assessor='different assessor')
    elif field == 'decision':
        original = decision
        altered = change(original, at=NOW+timedelta(seconds=1))
    else:
        original = shown.receipt
        altered = change(original, observer='different observer')
    with pytest.raises(ValueError, match='conflicting'):
        validate_governance_bundle(original, altered)
    validate_governance_bundle(original, original)


@pytest.mark.parametrize('omitted', ['warnings', 'exceptions', 'limitations', 'all'])
def test_delivering_text_without_required_disclosures_is_rejected(case, omitted):
    case = warning_case(case)
    waiver = exception(case, conditions='Bedside monitoring must be in place')
    released = release(case, eligibility(case, exceptions=(waiver,)))
    assessed = presentation(case, released)
    shown = record(case, assessed)
    assert shown.outcome == 'presented'
    assert shown.receipt.payload.warnings[0].reason == case['review'].evaluations[0].checks[0].reason
    assert shown.receipt.payload.exceptions[0].conditions == waiver.conditions
    assert shown.receipt.payload.limitations
    fields = ('warnings', 'exceptions', 'limitations') if omitted == 'all' else (omitted,)
    stripped = change(shown.receipt.payload, **{name: () for name in fields})
    bad_receipt = change(shown.receipt, payload=stripped)
    rejected = record(case, assessed, final_state=shown.final_state,
                      verification=shown.final_verification, receipt=bad_receipt)
    assert rejected.outcome == 'rejected'
    assert rejected.reasons == ('delivery_receipt_content_target_or_time_mismatch',)
    assert PresentationRecord.model_validate_json(rejected.model_dump_json()) == rejected


def test_missing_disclosure_cannot_be_authorized_by_a_new_payload_hash(case):
    case = warning_case(case)
    a = eligibility(case, exceptions=(exception(case),))
    stripped = change(a.payload, warnings=(), exceptions=(), limitations=())
    # Even fresh digest assertions do not waive the known disclosure requirements.
    a = change(a, payload=stripped,
               content_validation=change(a.content_validation, payload_digest=content_digest(stripped)),
               state=change(a.state, authorization=change(a.state.authorization, payload_digest=content_digest(stripped))))
    result = release(case, a)
    assert result.outcome == 'withheld'
    assert 'required_presentation_disclosures_mismatch' in result.reasons


def test_payload_changes_require_new_validation_and_authorization(case):
    a = eligibility(case)
    altered = change(a.payload, limitations=(*a.payload.limitations, 'Additional material limitation'))
    result = release(case, change(a, payload=altered))
    assert 'validated_payload_mismatch' in result.reasons
    assert 'authorization_payload_mismatch' in result.reasons
    assert result.outcome == 'withheld'


def test_eligibility_time_evidence_cannot_be_reused_for_delayed_delivery(case):
    p = presentation(case)
    # Still inside both the general 30-second context age and presentation window.
    result = record(case, p, at=NOW+timedelta(seconds=14), final_state=p.state)
    assert result.outcome == 'rejected'
    assert result.reasons == ('final_destination_verification_not_at_delivery',)
    fresh = record(case, p, at=NOW+timedelta(seconds=14))
    assert fresh.outcome == 'presented'
    assert PresentationRecord.model_validate_json(fresh.model_dump_json()) == fresh


def test_final_verification_is_required_even_with_matching_receipt(case):
    result = record(case, verification=None)
    assert result.outcome == 'rejected'
    assert 'final_destination_verification_missing' in result.reasons
    assert record(case, verification=None, receipt=None).outcome == 'withheld'


@pytest.mark.parametrize('field,value', [
    ('attempt', ref('presentation_record','other')),
    ('eligibility', ref('presentation_eligibility','other')),
    ('release', ref('release_decision','other')),
    ('payload_digest', '0'*64), ('state_digest', '0'*64),
    ('outcome', 'unavailable'), ('outcome', 'mismatch'),
])
def test_delivery_verification_is_scoped_to_exact_attempt_and_evidence(case, field, value):
    good = record(case)
    verification = change(good.final_verification, **{field:value})
    result = record(case, good.assessment, final_state=good.final_state,
                    verification=verification, receipt=good.receipt)
    assert result.outcome == 'rejected'
    assert result.reasons == ('final_destination_verification_scope_mismatch',)


def test_old_verification_and_receipt_cannot_authorize_another_attempt(case):
    good = record(case)
    replay = record(case, good.assessment, final_state=good.final_state,
                    verification=good.final_verification, receipt=good.receipt,
                    attempt=ref('presentation_record','another-attempt'))
    assert replay.outcome == 'rejected'
    assert 'final_destination_verification_scope_mismatch' in replay.reasons
    assert 'delivery_receipt_content_target_or_time_mismatch' in replay.reasons


def test_delayed_receipt_requires_new_delivery_verification(case):
    good = record(case)
    later = NOW+timedelta(seconds=3)
    current = runtime(case, 'present', later)
    stale_verification = change(good.final_verification, state_digest=content_digest(current))
    receipt = change(good.receipt, shown_at=later)
    result = record(case, good.assessment, at=later, final_state=current,
                    verification=stale_verification, receipt=receipt)
    assert result.outcome == 'rejected'
    assert result.reasons == ('final_destination_verification_not_at_delivery',)


def test_final_verification_detects_destination_switch_despite_old_runtime_target(case):
    good = record(case)
    verification = change(good.final_verification, target=change(case['target'], request_id='switched'))
    result = record(case, good.assessment, final_state=good.final_state,
                    verification=verification, receipt=good.receipt)
    assert result.outcome == 'rejected'
    assert result.reasons == ('final_destination_verification_scope_mismatch',)


@pytest.mark.parametrize('field,value', [('conditions','No monitoring required'), ('rationale','Different justification')])
def test_unchanged_exception_authority_rejects_changed_proposal(case, field, value):
    case = warning_case(case)
    original = exception(case, conditions='Bedside monitoring must be in place')
    altered = change(original, **{field:value})
    # New payload validation/release authorization cannot repair old exception authority.
    result = release(case, eligibility(case, exceptions=(altered,)))
    assert altered.authority == original.authority
    assert result.outcome == 'withheld'
    assert 'exception_proposal_authority_mismatch' in result.reasons
    assert ReleaseDecision.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize('change_kind', ['missing','unknown','unsatisfied','wrong_exception','wrong_attempt','wrong_target','old'])
def test_continuing_exception_conditions_require_scoped_delivery_confirmation(case, change_kind):
    case = warning_case(case)
    released = release(case, eligibility(case, exceptions=(exception(case),)))
    good = record(case, presentation(case, released))
    assertion = good.final_verification.conditions[0]
    changes = {
        'unknown': {'outcome':'unknown'}, 'unsatisfied': {'outcome':'unsatisfied'},
        'wrong_exception': {'exception_digest':'0'*64},
        'wrong_attempt': {'attempt':ref('presentation_record','other')},
        'wrong_target': {'target':change(case['target'], request_id='other')},
        'old': {'at':NOW},
    }
    conditions = () if change_kind == 'missing' else (change(assertion, **changes[change_kind]),)
    verification = change(good.final_verification, conditions=conditions)
    result = record(case, good.assessment, final_state=good.final_state,
                    verification=verification, receipt=good.receipt)
    assert result.outcome == 'rejected'
    assert result.reasons == ('exception_conditions_not_confirmed',)


def test_conflicting_condition_assertions_cannot_be_locally_combined(case):
    case = warning_case(case)
    released = release(case, eligibility(case, exceptions=(exception(case),)))
    good = record(case, presentation(case, released))
    assertion = good.final_verification.conditions[0]
    with pytest.raises(ValidationError, match='conflicting'):
        change(good.final_verification, conditions=(assertion, change(assertion, outcome='unsatisfied')))


def test_same_policy_revision_cannot_drop_required_dependencies_under_old_authority(case):
    original = eligibility(case)
    unavailable = change(original.state, dependencies=())
    assert release(case, change(original, state=unavailable)).outcome == 'withheld'
    relaxed = change(original.policy, required_dependencies=())
    changed = change(original, state=unavailable, policy=relaxed)
    result = release(case, changed)
    assert changed.state.authorization == original.state.authorization
    assert relaxed.reference == original.policy.reference
    assert result.outcome == 'withheld'
    assert 'authorization_content_or_policy_mismatch' in result.reasons
    with pytest.raises(ValueError, match='conflicting'):
        validate_governance_bundle(original.policy, relaxed)
    assert ReleaseDecision.model_validate_json(result.model_dump_json()) == result


def test_new_policy_revision_requires_new_authority_and_round_trips(case):
    original = eligibility(case)
    policy = change(original.policy, reference=change(original.policy.reference, version='2'), required_dependencies=())
    old_authority = change(original, policy=policy)
    assert not old_authority.eligible
    updated_case = {**case, 'policy':policy}
    renewed = eligibility(updated_case)
    renewed = change(renewed, reference=change(renewed.reference, version='2'),
                     content_validation=change(renewed.content_validation,
                         reference=change(renewed.content_validation.reference, version='2')))
    result = release(updated_case, renewed)
    assert result.outcome == 'released'
    validate_governance_bundle(original, renewed)
    assert ReleaseDecision.model_validate_json(result.model_dump_json()) == result



def test_conflicting_exception_disclosure_revision_is_rejected(case):
    case = warning_case(case)
    original = eligibility(case, exceptions=(exception(case),))
    contradictory = change(original.payload.exceptions[0], conditions='Contradictory conditions')
    with pytest.raises(ValidationError, match='conflicting'):
        change(original, payload=change(original.payload, exceptions=(contradictory,)))


def test_conflicting_exception_authorities_are_rejected_locally(case):
    case = warning_case(case)
    first = exception(case)
    second = change(first, reference=change(first.reference, version='2'),
                    authority=change(first.authority, rationale='Changed authority content under same revision'))
    with pytest.raises(ValidationError, match='conflicting'):
        eligibility(case, exceptions=(first, second))


def test_payload_validation_cannot_predate_exception_proposal(case):
    case = warning_case(case)
    waiver = exception(case, at=NOW+timedelta(seconds=1))
    assessed = eligibility(case, exceptions=(waiver,), at=NOW+timedelta(seconds=2))
    result = release(case, assessed, at=NOW+timedelta(seconds=2))
    assert result.outcome == 'withheld'
    assert 'payload_validation_precedes_exception_proposal' in result.reasons


def test_corrected_contract_schema_and_json_round_trip(case):
    case = warning_case(case)
    released = release(case, eligibility(case, exceptions=(exception(case),)))
    shown = record(case, presentation(case, released))
    assert shown.outcome == 'presented'
    assert shown.receipt.payload == released.released_payload
    restored = PresentationRecord.model_validate_json(shown.model_dump_json())
    assert restored == shown
    assert restored.final_verification.conditions[0].exception_digest == content_digest(
        restored.assessment.release.assessment.exceptions[0].proposal)
    assert restored.assessment.release.assessment.state.authorization.governance_policy_digest == content_digest(case['policy'])
    assert {'payload', 'attempt', 'final_verification'} <= set(PresentationReceipt.model_json_schema()['required'])
    assert 'governance_policy_digest' in AuthorizationAssertion.model_json_schema()['required']
    assert 'payload_digest' in ContentValidationAssertion.model_json_schema()['required']
