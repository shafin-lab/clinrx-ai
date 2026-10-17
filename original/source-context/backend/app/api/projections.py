"""Pure transport projections; retained execution is the only audit input."""
from pydantic import ValidationError
from app.api.schemas.common import ExactReference, QuantityView, TimesView, SourceView, ScopeView, CutoffView
from app.api.schemas.patient_state import LaboratoryView, MedicationView, PatientStateViewResponse
from app.api.schemas.temporal_review import (TemporalExecutionResponse, ContextView, GovernanceView,
    ProvenanceView, InferenceView, DirectDependencyView)
from app.persistence.errors import QueryLimitExceeded


def reference(value):
    return ExactReference.model_validate(value.model_dump())


def quantity(value):
    if value is None:
        return None
    return QuantityView(value=str(value.value), unit_raw=value.unit.raw,
        unit_code=value.unit.code, unit_system=value.unit.system, unit_status=value.unit.status)


def common(value, selection_digest, ingested_at, disclosures):
    provenance = value.provenance
    return dict(reference=reference(value.reference), selection_digest=selection_digest,
        time=TimesView.model_validate(value.time.model_dump()), source=SourceView.model_validate(provenance.source.model_dump()),
        origin=value.origin, verification=value.verification, conflict=value.conflict, temporal_status=value.temporal_status,
        provenance_recorded_at=provenance.recorded_at, provenance_actor=provenance.actor,
        provenance_limitations=provenance.limitations, provenance_completeness=provenance.lineage,
        ingested_at=ingested_at, disclosures=disclosures)


def laboratory(fields, concept_id, value):
    return LaboratoryView(**fields, concept_id=concept_id, quantity=quantity(value.value))


def medication(fields, kind, identity, dose, route, status, schedule):
    frequency = dose.frequency if dose is not None else None
    return MedicationView(**fields, event_type=kind, product_id=identity.product_id,
        ingredient_ids=identity.ingredient_ids, formulation=identity.formulation, status=status,
        dose=quantity(dose.amount) if dose is not None else None,
        dose_basis=dose.basis if dose is not None else None, route=route, schedule_text=schedule,
        frequency_occurrences=frequency.occurrences if frequency else None,
        frequency_interval=quantity(frequency.interval) if frequency else None)


def state(assembly, envelope):
    snapshot = assembly.snapshot
    if len(snapshot.laboratory) > 1000 or len(snapshot.medication) > 1000 or len(assembly.issues) > 2000:
        raise QueryLimitExceeded('state view limit exceeded')
    try:
        labs, meds = [], []
        for item in snapshot.ordered_items:
            fields = common(item, item.canonical_digest, item.ingestion.ingested_at, item.disclosures)
            payload = item.payload
            if item.domain == 'laboratory':
                labs.append(laboratory(fields, payload.concept_id, payload.value))
            else:
                meds.append(medication(fields, item.reference.kind, payload.medication, payload.dose,
                    payload.route, payload.status, payload.schedule_text))
        return PatientStateViewResponse(scope=ScopeView.model_validate(snapshot.scope.model_dump(exclude={'state_contract_version'})),
            state_context=envelope, laboratory=tuple(labs), medication=tuple(meds),
            coverage=tuple(c.model_dump() for c in assembly.coverage), issues=tuple(i.model_dump() for i in assembly.issues),
            disclosures=snapshot.disclosures)
    except ValidationError:
        raise QueryLimitExceeded('state cannot be represented within transport limits') from None


def execution(stored):
    # Never reassemble, resolve lineage, access a repository, or assess release.
    record = stored.record
    decision, recheck = record.decision, record.final_recheck
    assessment = decision.assessment
    snapshot = assessment.review.candidate.snapshot
    a, b, m, inference = snapshot.facts
    views = []
    for fact, witness in zip((a, b, m), recheck.evidence, strict=True):
        fields = common(fact, witness.item_digest, witness.original_ingestion.ingested_at,
            ('Retained synthetic audit evidence; consumed and terminal revisions are distinct fields. Complete ancestry is not established.',))
        if fact.kind == 'observation':
            views.append(laboratory(fields, fact.concept_id, fact.value))
        else:
            order = fact.kind == 'medication_order'
            views.append(medication(fields, fact.kind, fact.medication,
                fact.prescribed_dose if order else fact.administered_dose, fact.route,
                fact.order_status if order else 'administered', fact.schedule_text if order else None))
    return TemporalExecutionResponse(execution_id=record.request.execution_id,
        finalized_at=record.runtime.finalized_at, ingested_at=stored.ingested_at,
        context=ContextView(reference=reference(snapshot.reference), evidence_references=tuple(reference(f.reference) for f in snapshot.facts),
            limitations=snapshot.limitations),
        governance=GovernanceView(outcome=decision.outcome, decision_reference=reference(decision.reference),
            decided_at=decision.at, assessed_at=assessment.assessed_at, reasons=decision.reasons, safety_status=assessment.review.evaluations[0].outcome,
            fidelity_status=assessment.content_validation.outcome, freshness_status=assessment.state.freshness.items[0].state,
            authority_status=assessment.state.authorization.outcome, limitations=assessment.payload.limitations),
        provenance=ProvenanceView(inference=InferenceView(reference=reference(inference.reference), method=reference(inference.method),
            statement=inference.statement if decision.outcome == 'released' else None,
            applicability=inference.applicability, uncertainty=inference.uncertainty,
            limitations=(inference.validation_limitations, *inference.provenance.limitations), inputs=tuple(reference(r) for r in inference.inputs)),
            earlier_laboratory=views[0], later_laboratory=views[1], medication=views[2],
            terminal_references=tuple(reference(w.terminal) for w in recheck.evidence),
            inference_terminal_reference=reference(recheck.inference.terminal),
            direct_dependencies=tuple(DirectDependencyView(target=reference(edge.target), relationship=edge.relationship) for edge in inference.provenance.upstream),
            input_cutoff=CutoffView.model_validate(recheck.scope.repository_cutoff.model_dump()),
            inference_cutoff=CutoffView.model_validate(recheck.inference_cutoff.model_dump()),
            final_cutoff=CutoffView.model_validate(recheck.final_cutoff.model_dump()),
            final_recheck=recheck.outcome, recheck_reasons=recheck.reasons))
