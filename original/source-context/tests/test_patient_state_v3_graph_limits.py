"""Independently counted graph boundaries, including shared-parent revisits."""
from datetime import timedelta
import pytest
from app.execution.patient_state_v3_assembly import AssemblyLimitsV3, assemble_patient_state_v3
from app.persistence.errors import QueryLimitExceeded
from test_persistence import database, registered
from test_patient_state_v3 import AT, TARGET, PROV, h, change, measurement, records, stamp, code
from test_patient_state_v3_persistence import save, request


def link(owner, parents):
    return change(owner,associations=tuple(h.EvidenceBinding(role='context',scope=TARGET,status='resolved',exact=p.reference,provenance=PROV) for p in parents))


def shared_graph():
    root=change(records()[11],id='root',occurred=stamp(AT-timedelta(days=2)))
    shared=link(change(records()[11],id='shared',occurred=stamp(AT-timedelta(days=1))),[root])
    return link(measurement(name='a'),[shared]),link(measurement(name='b'),[shared]),shared,root


def case(dimension):
    if dimension=='max_fanout':
        a,b=measurement(name='a'),measurement(name='b');facts=(link(measurement(name='fanout'),[a,b]),a,b)
    elif dimension=='max_groups':
        facts=tuple(change(measurement(name=f'p{n}'),acquisition=change(measurement().acquisition,episode=code(f'episode{n}'))) for n in range(2))
    elif dimension=='max_signals':facts=tuple(change(records()[14],id=f'signal{n}') for n in range(2))
    elif dimension=='max_issues':facts=tuple(change(measurement(name=f'p{n}'),record_status='withdrawn') for n in range(2))
    else:facts=shared_graph()
    return facts


@pytest.mark.parametrize('dimension,exact', [('max_depth',2),('max_fanout',2),('max_relationships',4),('max_steps',4),('max_contextual',2),('max_groups',2),('max_signals',2),('max_issues',2)])
def test_each_graph_limit_accepts_exact_and_rejects_limit_plus_one(registered,dimension,exact):
    facts=case(dimension)
    cutoff=save(registered,*facts)
    ar=request(cutoff,limits=AssemblyLimitsV3(**{dimension:exact}))
    a=assemble_patient_state_v3(registered,request=ar)
    assert len(a.snapshot.items)==len(facts)
    if dimension=='max_contextual':assert sum(i.inclusion=='contextual' for i in a.snapshot.items)==exact
    if dimension=='max_issues':assert len(a.snapshot.issues)==exact
    ar=change(ar,limits=change(ar.limits,**{dimension:exact-1}))
    with pytest.raises(QueryLimitExceeded):assemble_patient_state_v3(registered,request=ar)


def test_shared_parent_contextual_children_exact_64_and_65(registered):
    parent=change(records()[11],occurred=stamp(AT-timedelta(days=1)))
    children=tuple(link(measurement(name=f'p{n:02d}'),[parent]) for n in range(65))
    cutoff=save(registered,parent,*children[:64]);ar=request(cutoff)
    result=assemble_patient_state_v3(registered,request=ar)
    assert len(next(i for i in result.snapshot.items if i.reference==parent.reference).contextual_for)==64
    cutoff=save(registered,children[64])
    ar=change(ar,scope=change(ar.scope,repository_cutoff=cutoff))
    with pytest.raises(QueryLimitExceeded):assemble_patient_state_v3(registered,request=ar)


def test_overdepth_support_chain_abstains(registered):
    from app.models.clinical.common import LineageEdge
    nodes=[change(records()[11],id=f'n{n}') for n in range(10)]
    for n in range(9):nodes[n]=change(nodes[n],provenance=change(PROV,upstream=(LineageEdge(target=nodes[n+1].reference,relationship='derived_from'),)))
    cutoff=save(registered,*nodes)
    with pytest.raises(QueryLimitExceeded):assemble_patient_state_v3(registered,request=request(cutoff))

@pytest.mark.parametrize('dimension,limit', [('max_depth',1),('max_fanout',1),('max_relationships',3),('max_steps',3),('max_contextual',1),('max_groups',1),('max_signals',1),('max_issues',1)])
def test_graph_exhaustion_rolls_back_workflow_and_provisional_fact(registered,monkeypatch,dimension,limit):
    from uuid import uuid4
    from app.execution.patient_state_v3_inference import build_circulatory_timing_inference
    from app.execution import patient_state_v3_workflow as w, patient_state_v3_execution as c
    from app.persistence.repository import transaction
    from test_patient_state_v3_inference import inputs, selected
    from test_patient_state_v3_workflow import clock, count
    a,r=selected(registered,(*inputs(),*case(dimension)))
    i=build_circulatory_timing_inference(assembly=a,request=r);cutoff=save(registered,i)
    ar=change(a.request,limits=change(a.request.limits,**{dimension:limit}))
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=ar,inference_cutoff=cutoff,expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    original=w._replay
    def replay(repo,*args,**kw):
        repo.append_fact(measurement(name='provisional'),target=TARGET)
        return original(repo,*args,**kw)
    monkeypatch.setattr(w,'_replay',replay)
    with pytest.raises(QueryLimitExceeded):w.execute_circulatory_review(registered,req,clock=clock)
    assert count(registered)==0
    with transaction(registered) as repo:
        after=repo.capture_cutoff()
        assert after.repository_id==cutoff.repository_id and after.fact_watermark==cutoff.fact_watermark


def test_exact_support_pin_cap_32_then_33_rejected(registered):
    from pydantic import ValidationError
    from app.models.clinical.common import LineageEdge
    from app.execution.patient_state_v3_inference import EvidencePin, build_circulatory_timing_inference
    from test_patient_state_v3_inference import inputs, selected
    p,l,v=inputs();supports=tuple(change(records()[11],id=f's{n:02d}') for n in range(32))
    p=change(p,provenance=change(PROV,upstream=tuple(LineageEdge(target=s.reference,relationship='derived_from') for s in supports)))
    a,r=selected(registered,(p,l,v,*supports))
    pins=tuple(EvidencePin(reference=s.reference,expected_digest=s.canonical_digest) for s in supports)
    r=change(r,supporting=pins)
    assert len(build_circulatory_timing_inference(assembly=a,request=r).inputs)==35
    extra=change(records()[11],id='s32')
    with pytest.raises(ValidationError):change(r,supporting=(*pins,EvidencePin(reference=extra.reference,expected_digest=extra.canonical_digest)))
