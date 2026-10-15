"""Director regressions: independently specified correction boundaries."""
import pytest
from app.models.clinical.common import LineageEdge
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError, EvidencePin
from test_persistence import database, registered
from test_patient_state_v3 import h, PROV, TARGET, change, records
from test_patient_state_v3_inference import inputs, selected


def binding_case():
    p,l,v=inputs();cal=records()[11];support=change(cal,id='binding-resolution-source')
    provenance=change(PROV,upstream=(LineageEdge(target=support.reference,relationship='derived_from'),))
    p=change(p,associations=(h.EvidenceBinding(role='calibration',scope=TARGET,status='resolved',exact=cal.reference,provenance=provenance),))
    return p,l,v,cal,support


def test_f3_omitted_binding_provenance_dependency_rejected(registered):
    p,l,v,cal,support=binding_case();a,r=selected(registered,(p,l,v,cal,support))
    r=change(r,supporting=(EvidencePin(reference=cal.reference,expected_digest=cal.canonical_digest),))
    with pytest.raises(CirculatoryInferenceError,match='supporting_dependency_mismatch'):
        build_circulatory_timing_inference(assembly=a,request=r)

from datetime import timedelta
from uuid import uuid4
from app.execution.patient_state_v3_assembly import assemble_patient_state_v3
from app.execution import patient_state_v3_workflow as w, patient_state_v3_execution as c
from app.persistence.repository import transaction, PatientRepository
from app.persistence.errors import ScopeMismatch, StorageIntegrityError, QueryLimitExceeded
from test_patient_state_v3 import AT, stamp
from test_patient_state_v3_persistence import save, revised
from test_patient_state_v3_workflow import clock, forbidden, count


def pinned(engine, facts=None):
    facts=binding_case() if facts is None else facts
    a,r=selected(engine,facts)
    r=change(r,supporting=tuple(EvidencePin(reference=f.reference,expected_digest=f.canonical_digest)
        for f in sorted(facts[3:],key=lambda f:(f.kind,f.id,f.revision))))
    return a,r


def execution(engine, facts=None):
    a,r=pinned(engine,facts)
    i=build_circulatory_timing_inference(assembly=a,request=r)
    cutoff=save(engine,i)
    return c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)


def test_f3_complete_closure_contextual_retention_and_historical_reconstruction(registered):
    p,l,v,cal,support=binding_case()
    support=change(support,occurred=stamp(AT-timedelta(days=1)))
    a,r=pinned(registered,(p,l,v,cal,support))
    item=next(i for i in a.snapshot.items if i.reference==support.reference)
    assert item.inclusion=='contextual' and item.contextual_for==(p.reference,)
    i=build_circulatory_timing_inference(assembly=a,request=r)
    assert tuple(ref.id for ref in i.inputs)==('p','l','v-initiation','binding-resolution-source','cal')
    assert tuple(e.target for e in i.provenance.upstream)==i.inputs
    save(registered,revised(support,record_status='withdrawn'))
    registered.dispose()
    replay=assemble_patient_state_v3(registered,request=a.request)
    assert replay.canonical_digest==a.canonical_digest
    assert build_circulatory_timing_inference(assembly=replay,request=r)==i


@pytest.mark.parametrize('correction',['same_value','provenance','withdrawn','invalid'])
def test_f3_support_only_successor_is_material_and_recovery_is_retained(registered,monkeypatch,correction):
    r=execution(registered);support=binding_case()[-1]
    fields={} if correction=='same_value' else {'provenance':change(support.provenance,actor='corrected assertion')} if correction=='provenance' else {'record_status':correction}
    save(registered,revised(support,**fields))
    receipt=w.execute_circulatory_review(registered,r,clock=clock)
    assert receipt.record.decision.outcome=='withheld'
    witness=next(e for e in receipt.record.final_recheck.evidence if e.consumed==support.reference)
    assert witness.terminal==revised(support).reference
    assert len(receipt.record.final_recheck.evidence)==5
    for name in ('_assemble','build_circulatory_timing_inference','_utc_now','assess_release','decide_release'):
        monkeypatch.setattr(w,name,forbidden)
    for name in ('load_fact','list_bounded_history','capture_cutoff'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    from app.persistence.bounded_history import AggregateHistoryBudget
    assert w.execute_circulatory_review(registered,r,clock=forbidden,aggregate_budget=AggregateHistoryBudget(max_rows=1))==receipt
    assert w.reconcile_circulatory_execution(registered,r).stored==receipt


def test_f3_released_support_receipt_stable_after_later_successor(registered,monkeypatch):
    r=execution(registered);receipt=w.execute_circulatory_review(registered,r,clock=clock)
    assert receipt.record.decision.outcome=='released'
    save(registered,revised(binding_case()[-1]))
    monkeypatch.setattr(w,'_new_execution',forbidden)
    from app.persistence.bounded_history import AggregateHistoryBudget
    assert w.execute_circulatory_review(registered,r,clock=forbidden,aggregate_budget=AggregateHistoryBudget(max_rows=1))==receipt
    assert w.reconcile_circulatory_execution(registered,r).stored==receipt


def test_f3_missing_support_cannot_be_hidden(registered):
    facts=binding_case();a,r=pinned(registered,facts[:-1])
    assert 'missing_association' in {i.reason for i in a.snapshot.issues}
    with pytest.raises(CirculatoryInferenceError,match='supporting_dependency_mismatch'):
        build_circulatory_timing_inference(assembly=a,request=r)


def test_f3_foreign_support_is_scope_failure(registered):
    from test_persistence import patient, encounter
    from app.models.clinical.common import ContextTarget
    from test_patient_state_v3_persistence import request
    p,l,v,cal,support=binding_case()
    other=ContextTarget(patient_id='foreign',encounter_id='foreign-e')
    support=change(support,binding=change(support.binding,target=other))
    save(registered,p,l,v,cal)
    with transaction(registered) as repo:
        repo.register_patient(patient('foreign'))
        repo.register_encounter(encounter('foreign-e','foreign'))
        repo.append_fact(support,target=other)
        cutoff=repo.capture_cutoff()
    with pytest.raises(ScopeMismatch):
        assemble_patient_state_v3(registered,request=request(cutoff))


def test_f3_cyclic_consumed_support_is_integrity_failure(registered):
    p,l,v,cal,support=binding_case()
    support=change(support,provenance=change(PROV,upstream=(LineageEdge(target=p.reference,relationship='derived_from'),)))
    with pytest.raises(StorageIntegrityError,match='circular'):
        selected(registered,(p,l,v,cal,support))


@pytest.mark.parametrize('role',['context','order','dosing_weight'])
def test_f3_unrelated_binding_provenance_not_inference_inputs(registered,role):
    p,l,v,cal,support=binding_case()
    p=change(p,associations=(change(p.associations[0],role=role),))
    a,r=selected(registered,(p,l,v,cal,support))
    assert build_circulatory_timing_inference(assembly=a,request=r).inputs==tuple(f.reference for f in (p,l,v))


def test_f3_previously_prepared_incomplete_request_rejected_without_receipt(registered,monkeypatch):
    # Simulate the checkpoint producer only while preparing an affected old command.
    from app.execution import patient_state_v3_inference as inference
    original=inference.required_support
    support=binding_case()[-1]
    monkeypatch.setattr(inference,'required_support',lambda f: original(f)-{support.reference})
    p,l,v,cal,_=binding_case();a,r=selected(registered,binding_case())
    r=change(r,supporting=(EvidencePin(reference=cal.reference,expected_digest=cal.canonical_digest),))
    i=build_circulatory_timing_inference(assembly=a,request=r);cutoff=save(registered,i)
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    monkeypatch.setattr(inference,'required_support',original)
    with pytest.raises(StorageIntegrityError):w.execute_circulatory_review(registered,req,clock=clock)
    assert count(registered)==0
    assert w.reconcile_circulatory_execution(registered,req).status=='absent'


def test_f3_existing_affected_receipt_is_not_rewritten_or_recomputed(registered,monkeypatch):
    from app.execution import patient_state_v3_inference as inference
    from sqlalchemy import text
    original=inference.required_support;support=binding_case()[-1]
    monkeypatch.setattr(inference,'required_support',lambda f: original(f)-{support.reference})
    p,l,v,cal,_=binding_case();a,r=selected(registered,binding_case())
    r=change(r,supporting=(EvidencePin(reference=cal.reference,expected_digest=cal.canonical_digest),))
    i=build_circulatory_timing_inference(assembly=a,request=r);cutoff=save(registered,i)
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    # Reproduce an old committed receipt while the old support rule is installed.
    receipt=w.execute_circulatory_review(registered,req,clock=clock)
    with registered.connect() as conn: before=conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one()
    monkeypatch.setattr(inference,'required_support',original)
    monkeypatch.setattr(w,'_new_execution',forbidden)
    assert w.reconcile_circulatory_execution(registered,req).stored==receipt
    assert w.execute_circulatory_review(registered,req,clock=forbidden)==receipt
    with registered.connect() as conn: assert conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one()==before


def test_f3_terminal_support_successor_never_substitutes_historical_pin(registered):
    a,r=pinned(registered);support=binding_case()[-1]
    cutoff=save(registered,revised(support))
    ar=change(a.request,scope=change(a.request.scope,repository_cutoff=cutoff))
    current=assemble_patient_state_v3(registered,request=ar)
    r=change(r,scope=ar.scope,expected_assembly_digest=current.canonical_digest)
    assert 'historical_association' in {i.reason for i in current.snapshot.issues}
    # Support1 is not eligible as a terminal item; Support2 cannot replace its pin.
    with pytest.raises(CirculatoryInferenceError,match='missing_selected_evidence'):
        build_circulatory_timing_inference(assembly=current,request=r)
