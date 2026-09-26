"""Bounded, in-memory output governance. Assertions require trusted producers.

These contracts enforce supplied evidence, not identity authentication, clinical
validation, persistence, or actual display. No universal clinical-validity claim.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from .common import (
    ContextTarget, DomainModel, IdentityVerification, Reference, Text,
    ensure_consistent_revisions, require_kind,
)
from .decisions import RecommendationReview, RenderedRecommendation, SafetyEvaluation

Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


def content_digest(value: DomainModel) -> str:
    """Canonical content binding, not a signature or clinical validation."""
    payload = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def review_digest(review: RecommendationReview) -> str:
    """Pin the supplied records, including exact text; hashing does not validate meaning."""
    return content_digest(review)


class ValidityWindow(DomainModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode='after')
    def ordered(self):
        if self.start >= self.end:
            raise ValueError('validity window requires start < end')
        return self

    def contains(self, at: datetime) -> bool:
        return self.start <= at < self.end


class OutputTarget(DomainModel):
    context: ContextTarget
    request_id: Text
    intended_use: Reference
    destination: Text
    recipient: Text

    @model_validator(mode='after')
    def intended_use_kind(self):
        require_kind(self.intended_use, 'intended_use')
        return self


class AuthorizationAssertion(DomainModel):
    reference: Reference
    policy: Reference
    subject: Text
    role: Text
    issuer: Text
    action: Literal['release', 'present', 'warning_exception']
    target: OutputTarget
    content_digest: Digest
    outcome: Literal['allow', 'deny', 'unknown']
    issued_at: AwareDatetime
    validity: ValidityWindow
    rationale: Text
    governance_policy_digest: Digest
    payload_digest: Digest | None = None
    exception_digest: Digest | None = None
    warning_evaluation: Reference | None = None
    warning_check_id: Text | None = None

    @model_validator(mode='after')
    def scope(self):
        require_kind(self.reference, 'authorization')
        require_kind(self.policy, 'authorization_policy')
        if self.action == 'warning_exception':
            if not self.warning_evaluation or not self.warning_check_id or not self.exception_digest:
                raise ValueError('warning authority must name exact evaluation and check')
            require_kind(self.warning_evaluation, 'safety_evaluation')
            if self.payload_digest is not None:
                raise ValueError('exception authority binds its proposal, not a later payload')
        elif self.warning_evaluation or self.warning_check_id or self.exception_digest:
            raise ValueError('warning scope belongs only to warning-exception authority')
        elif self.payload_digest is None:
            raise ValueError('release/presentation authority requires the exact payload')
        return self


class DependencyRequirement(DomainModel):
    reference: Reference
    updates_required: StrictBool


class WarningRule(DomainModel):
    rule: Reference
    response: Literal['advisory', 'exception_required']

    @model_validator(mode='after')
    def rule_kind(self):
        require_kind(self.rule, 'safety_rule')
        return self


class GovernancePolicy(DomainModel):
    """Resolved requirements for this use; no institution-specific rules are invented."""
    reference: Reference
    intended_use: Reference
    safety_policy: Reference
    freshness_policy: Reference
    authorization_policy: Reference
    content_validation_method: Reference
    required_rules: Annotated[tuple[Reference, ...], Field(min_length=1)]
    required_context: Annotated[tuple[Reference, ...], Field(min_length=1)]
    required_dependencies: tuple[DependencyRequirement, ...]
    warning_rules: tuple[WarningRule, ...] = ()
    max_assessment_age: Annotated[timedelta, Field(gt=timedelta(0))]
    # A separately validated scope for optional dependency loss; never a hard-stop bypass.
    degraded_mode: Reference | None = None
    degraded_dependencies: tuple[Reference, ...] = ()

    @model_validator(mode='after')
    def policy_contract(self):
        for reference, kind in (
            (self.reference, 'governance_policy'), (self.intended_use, 'intended_use'),
            (self.safety_policy, 'safety_policy'), (self.freshness_policy, 'freshness_policy'),
            (self.authorization_policy, 'authorization_policy'),
            (self.content_validation_method, 'content_validation_method'),
        ):
            require_kind(reference, kind)
        for rule in self.required_rules:
            require_kind(rule, 'safety_rule')
        if self.degraded_mode:
            require_kind(self.degraded_mode, 'validated_degraded_mode')
        if bool(self.degraded_mode) != bool(self.degraded_dependencies):
            raise ValueError('degraded scope must name both its approval and permitted optional losses')
        if set(self.degraded_dependencies) & {d.reference for d in self.required_dependencies}:
            raise ValueError('degraded scope cannot waive required dependencies')
        for identities in (self.required_rules, self.required_context,
                           tuple(d.reference for d in self.required_dependencies),
                           tuple(w.rule for w in self.warning_rules), self.degraded_dependencies):
            if len(set(identities)) != len(identities):
                raise ValueError('duplicate governance requirement')
        return self


class ContentValidationAssertion(DomainModel):
    payload_digest: Digest
    reference: Reference
    method: Reference
    target: OutputTarget
    content_digest: Digest
    outcome: Literal['matched', 'failed', 'unavailable']
    coverage: Literal['in_scope', 'out_of_scope', 'unknown']
    assessor: Text
    assessed_at: AwareDatetime
    validity: ValidityWindow
    rationale: Text
    limitations: tuple[Text, ...]

    @model_validator(mode='after')
    def reference_kinds(self):
        require_kind(self.reference, 'content_validation')
        require_kind(self.method, 'content_validation_method')
        return self


class FreshnessItem(DomainModel):
    reference: Reference
    state: Literal['fresh', 'stale', 'unknown']
    clinical_time: AwareDatetime | None = None
    validity: ValidityWindow | None = None
    rationale: Text

    @model_validator(mode='after')
    def fresh_needs_window(self):
        if self.state == 'fresh' and self.validity is None:
            raise ValueError('freshness requires a validity window')
        return self


class ContextFreshnessAssessment(DomainModel):
    reference: Reference
    snapshot: Reference
    policy: Reference
    assessed_at: AwareDatetime
    adequate: StrictBool
    material_change: StrictBool
    items: tuple[FreshnessItem, ...]
    assessor: Text
    rationale: Text

    @model_validator(mode='after')
    def references(self):
        require_kind(self.reference, 'freshness_assessment')
        require_kind(self.snapshot, 'snapshot')
        require_kind(self.policy, 'freshness_policy')
        if len({item.reference for item in self.items}) != len(self.items):
            raise ValueError('duplicate freshness item')
        return self


class DependencyState(DomainModel):
    reference: Reference
    state: Literal['available', 'unavailable', 'unknown', 'suspended']
    updates: Literal['available', 'unavailable', 'unknown', 'not_required']
    validity: ValidityWindow | None = None
    rationale: Text

    @model_validator(mode='after')
    def available_needs_window(self):
        if self.state == 'available' and not self.validity:
            raise ValueError('available dependency requires a validity window')
        return self


class RuntimeState(DomainModel):
    """Latest protected destination/request and source-state observation."""
    target: OutputTarget
    identity: IdentityVerification
    request_state: Literal['active', 'superseded', 'unknown']
    output_state: Literal['current', 'stale', 'withdrawn', 'superseded', 'unknown']
    observed_at: AwareDatetime
    authorization: AuthorizationAssertion
    freshness: ContextFreshnessAssessment
    dependencies: tuple[DependencyState, ...]

    @model_validator(mode='after')
    def unique_dependencies(self):
        if len({d.reference for d in self.dependencies}) != len(self.dependencies):
            raise ValueError('duplicate dependency state')
        return self


class WarningExceptionProposal(DomainModel):
    reference: Reference
    evaluation: Reference
    check_id: Text
    safety_policy: Reference
    target: OutputTarget
    content_digest: Digest
    actor: Text
    rationale: Text
    conditions: Text
    at: AwareDatetime
    validity: ValidityWindow

    @model_validator(mode='after')
    def reference_kinds(self):
        require_kind(self.reference, 'warning_exception')
        require_kind(self.evaluation, 'safety_evaluation')
        require_kind(self.safety_policy, 'safety_policy')
        return self


class WarningException(WarningExceptionProposal):
    authority: AuthorizationAssertion

    @property
    def proposal(self) -> WarningExceptionProposal:
        return WarningExceptionProposal.model_validate(self.model_dump(exclude={'authority'}))


class WarningDisclosure(DomainModel):
    evaluation: Reference
    check_id: Text
    rule: Reference
    reason: Text


class PresentationPayload(DomainModel):
    """All material the adapter must deliver; no UI or semantic interpretation."""
    rendering: RenderedRecommendation
    warnings: tuple[WarningDisclosure, ...]
    exceptions: tuple[WarningExceptionProposal, ...]
    limitations: tuple[Text, ...]


def required_payload(review: RecommendationReview, exceptions: tuple[WarningException, ...],
                     limitations: tuple[str, ...]) -> PresentationPayload:
    if review.rendering is None:
        raise ValueError('a presentation payload requires rendered content')
    return PresentationPayload(
        rendering=review.rendering,
        warnings=tuple(WarningDisclosure(evaluation=e.reference, check_id=c.id, rule=c.rule, reason=c.reason)
                       for e in review.evaluations for c in e.checks if c.outcome == 'warning'),
        exceptions=tuple(e.proposal for e in exceptions),
        limitations=tuple(dict.fromkeys((*limitations, *(v for e in review.evaluations for v in e.limitations)))),
    )


class ReleaseEligibilityAssessment(DomainModel):
    reference: Reference
    review: RecommendationReview
    payload: PresentationPayload
    target: OutputTarget
    policy: GovernancePolicy
    content_validation: ContentValidationAssertion
    state: RuntimeState
    exceptions: tuple[WarningException, ...] = ()
    assessor: Text
    assessed_at: AwareDatetime
    validity: ValidityWindow

    @model_validator(mode='after')
    def local_integrity(self):
        require_kind(self.reference, 'release_eligibility')
        validate_governance_bundle(self)
        return self

    def reasons_at(self, at: datetime, actor: str) -> tuple[str, ...]:
        return _release_reasons(self, at, actor)

    def decision_reasons(self, at: datetime, actor: str) -> tuple[str, ...]:
        reasons = list(self.reasons_at(at, actor))
        if self.reasons:
            reasons.append('release_assessment_withheld')
        return _unique(reasons)

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reasons_at(self.assessed_at, self.state.authorization.subject)

    @property
    def eligible(self) -> bool:
        return not self.reasons

    @property
    def availability(self) -> Literal['available', 'degraded', 'unavailable']:
        return _availability(self.policy, self.state, self.assessed_at, self.review)


class ReleaseDecision(DomainModel):
    reference: Reference
    assessment: ReleaseEligibilityAssessment
    actor: Text
    at: AwareDatetime
    outcome: Literal['released', 'withheld']
    reasons: tuple[Text, ...]

    @model_validator(mode='after')
    def justified_decision(self):
        require_kind(self.reference, 'release_decision')
        validate_governance_bundle(self)
        reasons = self.assessment.decision_reasons(self.at, self.actor)
        if self.reasons != reasons or self.outcome != ('withheld' if reasons else 'released'):
            raise ValueError('release decision must preserve the evaluated eligibility outcome and reasons')
        return self

    @property
    def availability(self) -> Literal['available', 'degraded', 'unavailable']:
        return _availability(self.assessment.policy, self.assessment.state, self.at, self.assessment.review)

    @property
    def released_payload(self) -> PresentationPayload | None:
        return self.assessment.payload if self.outcome == 'released' else None

    @property
    def released_content(self) -> RenderedRecommendation | None:
        """Rendering component only; adapters must deliver released_payload."""
        return self.assessment.review.rendering if self.outcome == 'released' else None


class PresentationEligibilityAssessment(DomainModel):
    reference: Reference
    release: ReleaseDecision
    payload: PresentationPayload
    state: RuntimeState
    assessor: Text
    assessed_at: AwareDatetime
    validity: ValidityWindow

    @model_validator(mode='after')
    def reference_kind(self):
        require_kind(self.reference, 'presentation_eligibility')
        validate_governance_bundle(self)
        return self

    @property
    def rendering(self) -> RenderedRecommendation:
        return self.payload.rendering

    def reasons_at(self, at: datetime, actor: str, state: RuntimeState) -> tuple[str, ...]:
        return _presentation_reasons(self, at, actor, state)

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reasons_at(self.assessed_at, self.state.authorization.subject, self.state)

    @property
    def eligible(self) -> bool:
        return not self.reasons


class ConditionSatisfactionAssertion(DomainModel):
    """Adapter assertion about this exact exception's continuing conditions."""
    reference: Reference
    exception_digest: Digest
    attempt: Reference
    target: OutputTarget
    at: AwareDatetime
    assessor: Text
    outcome: Literal['satisfied', 'unsatisfied', 'unknown']

    @model_validator(mode='after')
    def kinds(self):
        require_kind(self.reference, 'condition_satisfaction')
        require_kind(self.attempt, 'presentation_record')
        return self


class FinalDestinationVerification(DomainModel):
    """Adapter attestation at the logical atomic verify-and-deliver event.

    This evidence is distinct from eligibility-time context observations.
    The adapter, not this model, must implement atomic destination enforcement.
    """
    reference: Reference
    attempt: Reference
    eligibility: Reference
    release: Reference
    payload_digest: Digest
    state_digest: Digest
    target: OutputTarget
    verified_at: AwareDatetime
    verifier: Text
    outcome: Literal['verified', 'mismatch', 'unavailable']
    conditions: tuple[ConditionSatisfactionAssertion, ...] = ()

    @model_validator(mode='after')
    def kinds(self):
        for reference, kind in ((self.reference, 'final_destination_verification'),
                                (self.attempt, 'presentation_record'),
                                (self.eligibility, 'presentation_eligibility'),
                                (self.release, 'release_decision')):
            require_kind(reference, kind)
        validate_governance_bundle(self)
        return self


class PresentationReceipt(DomainModel):
    evidence: Reference
    attempt: Reference
    final_verification: Reference
    release: Reference
    payload: PresentationPayload
    target: OutputTarget
    shown_at: AwareDatetime
    observer: Text

    @property
    def rendering(self) -> RenderedRecommendation:
        return self.payload.rendering

    @model_validator(mode='after')
    def reference_kinds(self):
        require_kind(self.evidence, 'presentation_receipt')
        require_kind(self.release, 'release_decision')
        require_kind(self.attempt, 'presentation_record')
        require_kind(self.final_verification, 'final_destination_verification')
        return self


class PresentationRecord(DomainModel):
    reference: Reference
    assessment: PresentationEligibilityAssessment
    final_state: RuntimeState
    final_verification: FinalDestinationVerification | None = None
    actor: Text
    at: AwareDatetime
    receipt: PresentationReceipt | None = None
    outcome: Literal['presented', 'withheld', 'unconfirmed', 'rejected']
    reasons: tuple[Text, ...]

    @property
    def availability(self) -> Literal['available', 'degraded', 'unavailable']:
        original = self.assessment.release.assessment
        return _availability(original.policy, self.final_state, self.at, original.review)

    @model_validator(mode='after')
    def justified_record(self):
        require_kind(self.reference, 'presentation_record')
        validate_governance_bundle(self)
        outcome, reasons = presentation_result(self.assessment, self.final_state, self.at, self.actor, self.receipt,
                                               self.reference, self.final_verification)
        if self.outcome != outcome or self.reasons != reasons:
            raise ValueError('presentation record must preserve final eligibility and delivery evidence')
        return self


def _unique(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


def _authorization_reasons(auth: AuthorizationAssertion, policy: GovernancePolicy,
                           target: OutputTarget, digest: str, action: str,
                           actor: str, at: datetime) -> list[str]:
    reasons = []
    if auth.outcome != 'allow':
        reasons.append('authorization_not_allowed')
    if auth.action != action or auth.subject != actor or auth.target != target:
        reasons.append('authorization_scope_mismatch')
    if (auth.content_digest != digest or auth.policy != policy.authorization_policy
            or auth.governance_policy_digest != content_digest(policy)):
        reasons.append('authorization_content_or_policy_mismatch')
    if auth.issued_at > at or not auth.validity.contains(at):
        reasons.append('authorization_expired_or_not_yet_valid')
    return reasons


def _dependency_available(dependency: DependencyState, at: datetime) -> bool:
    return dependency.state == 'available' and dependency.validity is not None and dependency.validity.contains(at)


def _availability(policy: GovernancePolicy, state: RuntimeState, at: datetime,
                  review: RecommendationReview) -> Literal['available', 'degraded', 'unavailable']:
    states = {d.reference: d for d in state.dependencies}
    for requirement in policy.required_dependencies:
        current = states.get(requirement.reference)
        if not current or not _dependency_available(current, at):
            return 'unavailable'
        if requirement.updates_required and current.updates != 'available':
            return 'unavailable'
    if any(c.outcome == 'unavailable' for e in review.evaluations for c in e.checks):
        return 'unavailable'
    if any(not _dependency_available(d, at) or d.updates in ('unavailable', 'unknown') for d in state.dependencies):
        return 'degraded'
    return 'available'


def _runtime_reasons(policy: GovernancePolicy, review: RecommendationReview, target: OutputTarget,
                     state: RuntimeState, at: datetime, actor: str, action: str,
                     payload: PresentationPayload) -> list[str]:
    reasons = []
    if state.target != target:
        reasons.append('patient_encounter_request_destination_or_recipient_mismatch')
    if state.identity.status != 'verified' or state.identity.assessed_at > state.observed_at:
        reasons.append('identity_not_verified')
    if state.observed_at > at or at - state.observed_at > policy.max_assessment_age:
        reasons.append('runtime_observation_expired_or_future')
    if state.request_state != 'active':
        reasons.append('request_not_active')
    if state.output_state != 'current':
        reasons.append('output_not_current')
    reasons.extend(_authorization_reasons(state.authorization, policy, target, review_digest(review), action, actor, at))
    if state.authorization.payload_digest != content_digest(payload):
        reasons.append('authorization_payload_mismatch')
    freshness = state.freshness
    if freshness.snapshot != review.candidate.snapshot.reference or freshness.policy != policy.freshness_policy:
        reasons.append('freshness_snapshot_or_policy_mismatch')
    if freshness.assessed_at > state.observed_at or at - freshness.assessed_at > policy.max_assessment_age:
        reasons.append('freshness_assessment_expired_or_future')
    if not freshness.adequate or freshness.material_change:
        reasons.append('context_inadequate_or_materially_changed')
    items = {item.reference: item for item in freshness.items}
    for required in policy.required_context:
        item = items.get(required)
        if not item or item.state != 'fresh' or not item.validity or not item.validity.contains(at):
            reasons.append(f'required_context_not_fresh:{required.kind}:{required.id}:{required.version}')
    availability = _availability(policy, state, at, review)
    if availability == 'unavailable':
        reasons.append('required_dependency_update_or_check_unavailable')
    elif availability == 'degraded':
        if policy.degraded_mode is None:
            reasons.append('degraded_mode_not_approved')
        losses = {d.reference for d in state.dependencies
                  if not _dependency_available(d, at) or d.updates in ('unavailable', 'unknown')}
        if not losses.issubset(policy.degraded_dependencies):
            reasons.append('degraded_loss_outside_approved_scope')
    return reasons


def _exception_reasons(assessment: ReleaseEligibilityAssessment, at: datetime) -> list[str]:
    reasons = []
    evaluations = {e.reference: e for e in assessment.review.evaluations}
    for exception in assessment.exceptions:
        evaluation = evaluations.get(exception.evaluation)
        check = next((c for c in evaluation.checks if c.id == exception.check_id), None) if evaluation else None
        if not check or check.outcome != 'warning' or not check.overrideable:
            reasons.append('exception_targets_nonoverrideable_or_missing_warning')
        if not evaluation or exception.safety_policy != evaluation.policy:
            reasons.append('exception_safety_policy_mismatch')
        if exception.target != assessment.target or exception.content_digest != review_digest(assessment.review):
            reasons.append('exception_content_or_target_mismatch')
        if exception.at > at or not exception.validity.contains(at):
            reasons.append('exception_expired_or_future')
        if evaluation and exception.at < evaluation.evaluated_at:
            reasons.append('exception_precedes_evaluation')
        auth = exception.authority
        if auth.exception_digest != content_digest(exception.proposal):
            reasons.append('exception_proposal_authority_mismatch')
        reasons.extend(_authorization_reasons(auth, assessment.policy, assessment.target,
            review_digest(assessment.review), 'warning_exception', exception.actor, exception.at))
        # A previously permitted exception does not outlive its authority.
        reasons.extend(_authorization_reasons(auth, assessment.policy, assessment.target,
            review_digest(assessment.review), 'warning_exception', exception.actor, at))
        if auth.warning_evaluation != exception.evaluation or auth.warning_check_id != exception.check_id:
            reasons.append('exception_authority_warning_mismatch')
    return reasons


def _release_reasons(assessment: ReleaseEligibilityAssessment, at: datetime, actor: str) -> tuple[str, ...]:
    reasons = []
    review, policy, target = assessment.review, assessment.policy, assessment.target
    if at < assessment.assessed_at or not assessment.validity.contains(at):
        reasons.append('release_eligibility_expired_or_future')
    if target.context != review.candidate.snapshot.binding.target or target.intended_use != review.candidate.intended_use:
        reasons.append('candidate_context_or_intended_use_mismatch')
    if policy.intended_use != target.intended_use:
        reasons.append('policy_intended_use_mismatch')
    if not review.rendering or review.rendering.destination != target.destination:
        reasons.append('rendering_missing_or_destination_mismatch')
    if not review.evaluations:
        reasons.append('safety_evaluation_missing')
    validation = assessment.content_validation
    if review.rendering is not None and assessment.payload != required_payload(review, assessment.exceptions, validation.limitations):
        reasons.append('required_presentation_disclosures_mismatch')
    if validation.payload_digest != content_digest(assessment.payload):
        reasons.append('validated_payload_mismatch')
    if validation.content_digest != review_digest(review) or validation.target != target:
        reasons.append('exact_evaluated_content_or_target_mismatch')
    if validation.method != policy.content_validation_method or validation.outcome != 'matched' or validation.coverage != 'in_scope':
        reasons.append('exact_meaning_or_validated_scope_not_established')
    if validation.assessed_at > at or not validation.validity.contains(at):
        reasons.append('content_validation_expired_or_future')
    if any(validation.assessed_at < e.at for e in assessment.exceptions):
        reasons.append('payload_validation_precedes_exception_proposal')
    if review.evaluations and validation.assessed_at < max(e.evaluated_at for e in review.evaluations):
        reasons.append('content_attestation_precedes_evaluations')
    seen_rules = set()
    warning_rules = {w.rule: w.response for w in policy.warning_rules}
    for evaluation in review.evaluations:
        if evaluation.evaluated_at > at or evaluation.policy != policy.safety_policy:
            reasons.append('evaluation_time_or_policy_mismatch')
        if evaluation.exact_meaning != 'matched':
            reasons.append('evaluated_exact_meaning_not_matched')
        for check in evaluation.checks:
            if check.outcome == 'hard_failure':
                reasons.append('hard_safety_failure')
            if check.outcome == 'unavailable':
                reasons.append('safety_check_unavailable')
            if check.outcome not in ('unavailable', 'not_applicable'):
                seen_rules.add(check.rule)
            if check.outcome == 'warning':
                response = warning_rules.get(check.rule)
                if response is None:
                    reasons.append('warning_response_unclassified')
                elif response == 'exception_required':
                    matching = [e for e in assessment.exceptions if e.evaluation == evaluation.reference and e.check_id == check.id]
                    if not check.overrideable or not matching:
                        reasons.append('required_warning_exception_missing_or_prohibited')
    if not set(policy.required_rules).issubset(seen_rules):
        reasons.append('required_applicable_safety_coverage_missing')
    reasons.extend(_exception_reasons(assessment, at))
    reasons.extend(_runtime_reasons(policy, review, target, assessment.state, at, actor, 'release', assessment.payload))
    return _unique(reasons)


def _presentation_reasons(assessment: PresentationEligibilityAssessment, at: datetime,
                          actor: str, state: RuntimeState) -> tuple[str, ...]:
    reasons = []
    release = assessment.release
    original = release.assessment
    if release.outcome != 'released':
        reasons.append('release_was_withheld')
    if at < release.at or at < assessment.assessed_at or not assessment.validity.contains(at):
        reasons.append('presentation_eligibility_expired_or_future')
    # Preserve release/content/exception expiry; reassess current context using new evidence below.
    if not original.validity.contains(at) or not original.content_validation.validity.contains(at):
        reasons.append('release_no_longer_eligible')
    reasons.extend(_exception_reasons(original, at))
    if assessment.payload != release.released_payload:
        reasons.append('presentation_content_differs_from_exact_release')
    if state.observed_at < assessment.assessed_at:
        reasons.append('destination_not_rechecked_for_presentation')
    reasons.extend(_runtime_reasons(original.policy, original.review, original.target, state, at, actor, 'present', original.payload))
    return _unique(reasons)


def presentation_result(assessment: PresentationEligibilityAssessment, state: RuntimeState,
                        at: datetime, actor: str, receipt: PresentationReceipt | None,
                        attempt: Reference, verification: FinalDestinationVerification | None) -> tuple[str, tuple[str, ...]]:
    reasons = list(assessment.reasons_at(at, actor, state))
    if assessment.reasons:
        reasons.append('presentation_assessment_withheld')
    reasons.extend(_final_verification_reasons(assessment, state, at, attempt, verification))
    if receipt:
        if (verification is None or receipt.final_verification != verification.reference or receipt.attempt != attempt
                or receipt.release != assessment.release.reference or receipt.target != state.target or
                receipt.payload != assessment.payload or receipt.shown_at != at):
            reasons.append('delivery_receipt_content_target_or_time_mismatch')
        return ('rejected' if reasons else 'presented', _unique(reasons))
    if reasons:
        return 'withheld', _unique(reasons)
    return 'unconfirmed', ('presentation_not_confirmed',)


def _final_verification_reasons(assessment: PresentationEligibilityAssessment, state: RuntimeState,
                                at: datetime, attempt: Reference,
                                verification: FinalDestinationVerification | None) -> list[str]:
    if verification is None:
        return ['final_destination_verification_missing']
    reasons = []
    if (verification.outcome != 'verified' or verification.attempt != attempt
            or verification.eligibility != assessment.reference
            or verification.release != assessment.release.reference
            or verification.target != assessment.release.assessment.target
            or verification.target != state.target
            or verification.payload_digest != content_digest(assessment.payload)
            or verification.state_digest != content_digest(state)):
        reasons.append('final_destination_verification_scope_mismatch')
    if verification.verified_at != at or state.observed_at != at:
        reasons.append('final_destination_verification_not_at_delivery')
    required = {content_digest(e.proposal) for e in assessment.release.assessment.exceptions}
    satisfied = set()
    for assertion in verification.conditions:
        if (assertion.exception_digest not in required or assertion.attempt != attempt
                or assertion.target != verification.target or assertion.at != at
                or assertion.outcome != 'satisfied'):
            reasons.append('exception_conditions_not_confirmed')
        else:
            satisfied.add(assertion.exception_digest)
    if required != satisfied:
        reasons.append('exception_conditions_not_confirmed')
    return reasons


def validate_governance_bundle(*roots: DomainModel | None) -> None:
    """Reject conflicting assertion revisions locally, not changing resource observations.

    The explicit type list is intentional: a dependency/freshness item references
    a resource, not an immutable assertion about that resource. No global registry.
    Call this boundary for multiple separately supplied records as well.
    """
    assertion_types = (GovernancePolicy, AuthorizationAssertion, ContentValidationAssertion,
                       ContextFreshnessAssessment, WarningException, ReleaseEligibilityAssessment,
                       ReleaseDecision, PresentationEligibilityAssessment, FinalDestinationVerification,
                       ConditionSatisfactionAssertion, PresentationRecord, SafetyEvaluation)
    records = []
    proposals = []

    def visit(value):
        if isinstance(value, assertion_types):
            records.append((value.reference, value))
        elif isinstance(value, PresentationReceipt):
            records.append((value.evidence, value))
        # Compare projections separately from the full authorized assertion.
        if isinstance(value, WarningException):
            proposals.append((value.reference, value.proposal))
        elif isinstance(value, WarningExceptionProposal):
            proposals.append((value.reference, value))
        if isinstance(value, DomainModel):
            for field in type(value).model_fields:
                visit(getattr(value, field))
        elif isinstance(value, (tuple, list)):
            for item in value:
                visit(item)
    for root in roots:
        if root is not None and not isinstance(root, DomainModel):
            raise TypeError('governance bundle requires validated model records')
        visit(root)
    ensure_consistent_revisions(records)
    ensure_consistent_revisions(proposals)
