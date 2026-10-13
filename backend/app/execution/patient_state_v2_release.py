"""Pure bounded M6.4 assertion producers; no workflow, clock or authorization I/O."""
from functools import wraps

from pydantic import ValidationError

from app.execution.patient_state_v2_execution import (
    AUTHORIZATION, FIDELITY, FIDELITY_ASSESSOR, FINAL_ASSESSOR, FRESHNESS,
    GRANT_ACTOR, GRANT_ISSUER, GRANT_TARGET, GRANT_WINDOW, LIMITATIONS, METHOD,
    RULES, SAFETY, USE, MicroAntimicrobialExecutionError, MicroAntimicrobialEvidence,
    MicroAntimicrobialFinalRecheck, digest, freshness_binding, instant,
    micro_antimicrobial_policy, presentation_limitations, ref, require, same, validate_evidence_recheck,
)
from app.execution.patient_state_v2_inference import APPLICABILITY, MANDATORY_UNCERTAINTY, VALIDATION_LIMITATION
from app.models.clinical.common import LineageEdge, Provenance, Quantity, Source
from app.models.clinical.decisions import (
    ClinicalClaim, ClinicalRecommendation, RecommendationReview, RenderedRecommendation,
    SafetyCheck, SafetyEvaluation,
)
from app.models.clinical.facts import ContextSnapshot
from app.models.clinical.governance import (
    AuthorizationAssertion, ContentValidationAssertion, ContextFreshnessAssessment,
    DependencyState, FreshnessItem, OutputTarget, PresentationPayload, ValidityWindow,
    required_payload,
)
from app.persistence.errors import PersistenceInputError, UnsupportedOperation

RATIONALE = 'Descriptive temporal ordering of four explicitly selected recorded facts only.'
SOURCE = Source(namespace='clinrx.synthetic',identifier='SyntheticMicroAntimicrobialRelease',version='1',channel='system')


def bounded(function):
    @wraps(function)
    def call(*args,**kwargs):
        try:
            return function(*args,**kwargs)
        except (ValidationError,ValueError,TypeError,PersistenceInputError,UnsupportedOperation):
            raise MicroAntimicrobialExecutionError('invalid_governance_input') from None
    return call


def _scope(evidence):
    return 'Exact original S/I/U/D and inference only; request='+digest(evidence.request)+'.'


def _meaning(evidence):
    # Canonical M6.3 reconstruction is required by protected replay before governance.
    # Retained validation never recomputes clinical meaning.
    i=evidence.inference
    return () if i.method == METHOD and i.inputs == evidence.request.inputs else ('inference_mismatch',)


@bounded
def build_micro_antimicrobial_context(*,evidence,patient,encounter,at,id):
    evidence=MicroAntimicrobialEvidence.model_validate(evidence)
    facts=(evidence.inference,)
    return ContextSnapshot(id=id,version='1',patient=patient,encounter=encounter,binding=evidence.inference.binding,
        facts=facts,sources=tuple(dict.fromkeys(f.provenance.source for f in facts)),created_at=at,temporal_cutoff=at,
        completeness='partial',completeness_scope=_scope(evidence),limitations=LIMITATIONS)


def _context(evidence,snapshot):
    snapshot=ContextSnapshot.model_validate(snapshot)
    require(tuple(f.reference for f in snapshot.facts)==(evidence.request.inference_reference,)
            and all(same(a,b) for a,b in zip(snapshot.facts,(evidence.inference,),strict=True))
            and same(snapshot.binding,evidence.inference.binding) and snapshot.completeness=='partial'
            and snapshot.completeness_scope==_scope(evidence) and snapshot.limitations==LIMITATIONS
            and not snapshot.lineage_nodes and snapshot.sources==tuple(dict.fromkeys(f.provenance.source for f in snapshot.facts)), 'context_mismatch')
    return snapshot


@bounded
def build_micro_antimicrobial_candidate(*,evidence,snapshot,at,id):
    evidence=MicroAntimicrobialEvidence.model_validate(evidence)
    snapshot=_context(evidence,snapshot)
    i=evidence.inference
    return ClinicalRecommendation(id=id,revision='1',snapshot=snapshot,intended_use=USE,
        claims=(ClinicalClaim(id='recorded-micro-antimicrobial-temporal-relation',action=i.statement,rationale=RATIONALE,
            classifications=('deterministic',),basis=(i.reference,),conditions=(i.applicability,),
            warnings=(i.validation_limitations,*i.provenance.limitations),uncertainty=i.uncertainty),),limitations=LIMITATIONS,
        provenance=Provenance(source=SOURCE,actor='SyntheticMicroAntimicrobialCandidate/v1',recorded_at=at,
            upstream=(LineageEdge(target=i.reference,relationship='copied_from'),),lineage='complete',limitations=LIMITATIONS),created_at=at)


@bounded
def render_micro_antimicrobial(*,candidate,target,at,id):
    candidate=ClinicalRecommendation.model_validate(candidate)
    target=OutputTarget.model_validate(target)
    require(len(candidate.claims)==1,'invalid_candidate')
    return RenderedRecommendation(id=id,revision='1',candidate=candidate.reference,snapshot=candidate.snapshot.reference,
        content=candidate.claims[0].action,destination=target.destination,rendered_at=at)


def _output(evidence,snapshot,candidate,rendering,target):
    failed=list(_meaning(evidence))
    i=evidence.inference
    if not same(candidate.snapshot,snapshot) or candidate.intended_use!=USE or candidate.knowledge or candidate.evidence or candidate.alternatives or candidate.monitoring or candidate.limitations!=LIMITATIONS:
        failed.append('candidate_envelope_mismatch')
    if len(candidate.claims)!=1:
        failed.append('claim_count_mismatch')
    else:
        c=candidate.claims[0]
        if (c.id!='recorded-micro-antimicrobial-temporal-relation' or c.action!=i.statement or c.rationale!=RATIONALE
                or c.classifications!=('deterministic',) or c.basis!=(i.reference,) or c.conditions!=(i.applicability,)
                or c.warnings!=(i.validation_limitations,*i.provenance.limitations) or c.uncertainty!=i.uncertainty):
            failed.append('claim_mismatch')
    if candidate.provenance!=Provenance(source=SOURCE,actor='SyntheticMicroAntimicrobialCandidate/v1',recorded_at=candidate.created_at,
            upstream=(LineageEdge(target=i.reference,relationship='copied_from'),),lineage='complete',limitations=LIMITATIONS):
        failed.append('candidate_provenance_mismatch')
    if (rendering.content!=i.statement or rendering.candidate!=candidate.reference or rendering.snapshot!=snapshot.reference
            or rendering.destination!=target.destination or target!=evidence.request.target):
        failed.append('rendering_mismatch')
    return tuple(dict.fromkeys(failed))


@bounded
def evaluate_micro_antimicrobial(*,evidence,recheck,snapshot,candidate,rendering,target,at,id):
    evidence,recheck=validate_evidence_recheck(evidence,recheck)
    snapshot=_context(evidence,snapshot)
    candidate=ClinicalRecommendation.model_validate(candidate)
    rendering=RenderedRecommendation.model_validate(rendering)
    target=OutputTarget.model_validate(target)
    failures=_output(evidence,snapshot,candidate,rendering,target)
    terminal='no_detected_violation' if recheck.outcome=='unchanged' else 'hard_failure' if recheck.outcome=='materially_changed' else 'unavailable'
    outcomes=('no_detected_violation',terminal,'hard_failure' if failures else 'no_detected_violation')
    reasons=('Exact supplied source binding checked.', ','.join(recheck.reasons) or 'Exact protected terminal evidence unchanged.',
             ','.join(failures) or 'Bounded descriptive content matches canonically replayed inference.')
    return SafetyEvaluation(id=id,revision='1',candidate=candidate.reference,rendering=rendering.reference,snapshot=snapshot.reference,
        policy=SAFETY,checks=tuple(SafetyCheck(id=rule.id,rule=rule,required=True,overrideable=False,outcome=outcome,reason=reason,
            coverage='Exact selected S/I/U/D and original inference only.') for rule,outcome,reason in zip(RULES,outcomes,reasons,strict=True)),
        exact_meaning='failed' if failures else 'matched',coverage='Exact selected S/I/U/D and original inference only.',limitations=presentation_limitations(evidence.inference),evaluated_at=at)


@bounded
def validate_micro_antimicrobial_content(*,evidence,recheck,snapshot,review,payload,target,at,validity,id):
    evidence,recheck=validate_evidence_recheck(evidence,recheck)
    snapshot=_context(evidence,snapshot)
    review=RecommendationReview.model_validate(review)
    payload=PresentationPayload.model_validate(payload)
    target=OutputTarget.model_validate(target)
    require(review.rendering is not None,'rendering_required')
    failures=list(_output(evidence,snapshot,review.candidate,review.rendering,target))
    if len(review.evaluations)!=1: failures.append('evaluation_count_mismatch')
    for evaluation in review.evaluations:
        expected=evaluate_micro_antimicrobial(evidence=evidence,recheck=recheck,snapshot=snapshot,candidate=review.candidate,
            rendering=review.rendering,target=target,at=evaluation.evaluated_at,id=evaluation.id)
        if not same(expected,evaluation): failures.append('evaluation_mismatch')
    if not same(payload,required_payload(review,(),LIMITATIONS)): failures.append('disclosure_mismatch')
    return ContentValidationAssertion(reference=ref('content_validation',id),method=FIDELITY,target=target,
        content_digest=digest(review),payload_digest=digest(payload),coverage='in_scope',outcome='failed' if failures else 'matched',
        assessor=FIDELITY_ASSESSOR,assessed_at=at,validity=validity,rationale=','.join(failures) or 'Canonical replay fidelity and bounded payload checked.',limitations=presentation_limitations(evidence.inference))


@bounded
def assess_micro_antimicrobial_context(*,evidence,recheck,snapshot,at,validity,id):
    evidence,recheck=validate_evidence_recheck(evidence,recheck)
    snapshot=_context(evidence,snapshot)
    validity=ValidityWindow.model_validate(validity)
    adequate=recheck.outcome=='unchanged'
    return ContextFreshnessAssessment(reference=ref('freshness_assessment',id),snapshot=snapshot.reference,policy=FRESHNESS,
        assessed_at=at,adequate=adequate,material_change=recheck.outcome=='materially_changed',
        items=tuple(FreshnessItem(reference=r,state='fresh' if adequate else 'stale' if recheck.outcome=='materially_changed' else 'unknown',
            validity=validity if adequate else None,rationale='Exact protected subset; no complete clinical-state claim.')
            for r in (snapshot.reference,*evidence.request.inputs,evidence.request.inference_reference)),
        assessor=FINAL_ASSESSOR,rationale=freshness_binding(recheck))


@bounded
def assess_micro_antimicrobial_dependencies(*,evidence,recheck,snapshot,validity):
    evidence,recheck=validate_evidence_recheck(evidence,recheck)
    snapshot=_context(evidence,snapshot)
    policy=micro_antimicrobial_policy(snapshot)
    clinical=(*evidence.request.inputs,evidence.request.inference_reference)
    return tuple(DependencyState(reference=x.reference,state='unavailable' if x.reference in clinical and recheck.outcome!='unchanged' else 'available',
        updates='not_required',validity=None if x.reference in clinical and recheck.outcome!='unchanged' else validity,
        rationale='Exact selected evidence or bounded local implementation only.') for x in policy.required_dependencies)


@bounded
def issue_synthetic_micro_antimicrobial_authority(*,request,review,payload,policy,at,id):
    """Pure evaluation of the fixed synthetic profile at a supplied runtime instant."""
    from app.execution.patient_state_v2_execution import MicroAntimicrobialExecutionRequest
    request=MicroAntimicrobialExecutionRequest.model_validate(request)
    review=RecommendationReview.model_validate(review)
    payload=PresentationPayload.model_validate(payload)
    expected=micro_antimicrobial_policy(review.candidate.snapshot)
    permitted=(request.actor==GRANT_ACTOR and request.target==GRANT_TARGET and same(policy,expected)
               and review.candidate.intended_use==USE and review.candidate.snapshot.binding.target==request.target.context
               and same(payload,required_payload(review,(),LIMITATIONS)) and GRANT_WINDOW.contains(at)
               and review.candidate.created_at<=at and review.rendering is not None and review.rendering.rendered_at<=at
               and all(e.evaluated_at<=at for e in review.evaluations))
    return AuthorizationAssertion(reference=ref('authorization',id),policy=AUTHORIZATION,subject=request.actor,
        role='synthetic-micro-antimicrobial-reviewer',issuer=GRANT_ISSUER,action='release',target=request.target,
        content_digest=digest(review),payload_digest=digest(payload),governance_policy_digest=digest(policy),
        outcome='allow' if permitted else 'deny',issued_at=at,validity=GRANT_WINDOW,
        rationale='Fixed synthetic profile only; no authentication or patient-care authority.')
