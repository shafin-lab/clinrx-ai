"""Retained-only transport projection; never fetch or recompute clinical state."""
from app.api.schemas.micro_antimicrobial import MicroExecutionResponse, MicroProvenance
from app.api.schemas.temporal_review import GovernanceView
from app.api.projections import reference

def execution(stored):
    record=stored.record
    decision=record.decision
    assessment=decision.assessment
    recheck=record.final_recheck
    return MicroExecutionResponse(execution_id=record.request.execution_id,
        statement=decision.released_content.content if decision.released_content is not None else None,
        finalized_at=record.runtime.finalized_at,ingested_at=stored.ingested_at,
        governance=GovernanceView(outcome=decision.outcome,decision_reference=reference(decision.reference),
            decided_at=decision.at,assessed_at=assessment.assessed_at,reasons=decision.reasons,
            safety_status=assessment.review.evaluations[0].outcome,
            fidelity_status=assessment.content_validation.outcome,
            freshness_status=recheck.outcome,authority_status=assessment.state.authorization.outcome,
            limitations=assessment.payload.limitations),
        provenance=MicroProvenance(inference=record.evidence.inference,consumed=record.evidence.items,
            original_cutoff=record.request.inference_request.scope.repository_cutoff,
            inference_cutoff=record.request.inference_cutoff,final_recheck=recheck,
            specimen_binding_matches=recheck.specimen_binding_matches,
            isolate_binding_matches=recheck.isolate_binding_matches,
            antimicrobial_identity_matches=recheck.antimicrobial_identity_matches,
            recheck_reasons=recheck.reasons, witness_statuses=tuple(w.status for w in recheck.evidence),
            governance_policy=reference(assessment.policy.reference)))
