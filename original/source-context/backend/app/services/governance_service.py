"""Pure governance operations: no UI, persistence, authorization issuer, or clinical engine.

Callers supply authenticated policy/assertion producers and a trustworthy clock.
All outputs are immutable audit records, including unsuccessful attempts.
"""
from datetime import datetime

from app.models.clinical.common import Reference
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.governance import (
    ContentValidationAssertion, GovernancePolicy, OutputTarget,
    PresentationEligibilityAssessment, PresentationReceipt, PresentationRecord,
    ReleaseDecision, ReleaseEligibilityAssessment, RuntimeState, ValidityWindow,
    WarningException, PresentationPayload, FinalDestinationVerification, presentation_result,
    validate_governance_bundle,
)


def assess_release(*, reference: Reference, review: RecommendationReview, target: OutputTarget,
                   payload: PresentationPayload, policy: GovernancePolicy, content_validation: ContentValidationAssertion,
                   state: RuntimeState, assessor: str, at: datetime, validity: ValidityWindow,
                   exceptions: tuple[WarningException, ...] = ()) -> ReleaseEligibilityAssessment:
    return ReleaseEligibilityAssessment(
        reference=reference, review=review, payload=payload, target=target, policy=policy,
        content_validation=content_validation, state=state, exceptions=exceptions,
        assessor=assessor, assessed_at=at, validity=validity,
    )


def decide_release(*, reference: Reference, assessment: ReleaseEligibilityAssessment,
                   actor: str, at: datetime) -> ReleaseDecision:
    assessment = ReleaseEligibilityAssessment.model_validate(assessment)
    reasons = assessment.decision_reasons(at, actor)
    return ReleaseDecision(reference=reference, assessment=assessment, actor=actor, at=at,
                           outcome='withheld' if reasons else 'released', reasons=reasons)


def assess_presentation(*, reference: Reference, release: ReleaseDecision,
                        payload: PresentationPayload, state: RuntimeState,
                        assessor: str, at: datetime, validity: ValidityWindow) -> PresentationEligibilityAssessment:
    return PresentationEligibilityAssessment(reference=reference, release=release, payload=payload,
        state=state, assessor=assessor, assessed_at=at, validity=validity)


def record_presentation(*, reference: Reference, assessment: PresentationEligibilityAssessment,
                        final_state: RuntimeState, actor: str, at: datetime,
                        receipt: PresentationReceipt | None = None,
                        final_verification: FinalDestinationVerification | None = None) -> PresentationRecord:
    assessment = PresentationEligibilityAssessment.model_validate(assessment)
    final_state = RuntimeState.model_validate(final_state)
    if receipt is not None:
        receipt = PresentationReceipt.model_validate(receipt)
    if final_verification is not None:
        final_verification = FinalDestinationVerification.model_validate(final_verification)
    validate_governance_bundle(assessment, final_state, receipt, final_verification)
    outcome, reasons = presentation_result(assessment, final_state, at, actor, receipt, reference, final_verification)
    return PresentationRecord(reference=reference, assessment=assessment, final_state=final_state,
        actor=actor, at=at, receipt=receipt, final_verification=final_verification, outcome=outcome, reasons=reasons)
