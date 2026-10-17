"""Real scoped M7 service/HTTP lifecycle, independent of M5/M6 clinical behavior."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.api.config import APIConfig
from app.api.circulatory_commands import CirculatoryStateCodec, CirculatoryCommandCodec
from app.api.micro_commands import MicroCommandCodec
from app.main import create_app
from app.demo.circulatory import bootstrap, correct, manifest, SIMULATION_AT, TARGET
from app.models.clinical.hemodynamics import M7_FACTS
from app.persistence.database import create_database
from app.persistence.repository import transaction

P='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
@pytest.fixture
def case(tmp_path):
    path=tmp_path/'demo.sqlite3';engine=create_database(path);bootstrap(engine)
    config=APIConfig(database_path=path,environment='test',envelope_signing_key='a9'*32,
        clock_mode='historical_simulation',simulation_at=SIMULATION_AT,circulatory_execution_enabled=True)
    app=create_app(config,engine=engine)
    with TestClient(app) as client:yield client,app,engine,config
    engine.dispose()
def state(client):
    r=client.get(P+'/patient-state-v3',params={k:manifest()[k] for k in ('review_start','review_end')})
    assert r.status_code==200,r.text
    return r.json()
def preparation(client):
    v=state(client);body=dict(execution_id=str(uuid4()),state_context=v['state_context'])
    for field,id in [('pressure','m7-P'),('lactate','m7-L'),('vasopressor','m7-V')]:
        item=next(i for i in v['assembly']['snapshot']['items'] if i['fact']['id']==id)
        f=item['fact'];body[field]=dict(reference=dict(kind=f['kind'],id=f['id'],version=f['revision']),expected_digest=item['expected_digest'])
    return body
def prepared(client):
    r=client.post(P+'/circulatory-review-preparations',json=preparation(client));assert r.status_code==200,r.text
    return r.json()
def execute(client,v):return client.post(P+'/circulatory-reviews',json={'command':v['command']})
def reconcile(client,v):return client.post(P+'/circulatory-review-reconciliations',json={'command':v['command']})

def test_all_families_uncertain_unplaced_and_decimal_retained(case):
    client,app,engine,config=case;v=state(client);items=v['assembly']['snapshot']['items']
    assert set(i['fact']['kind'] for i in items)==set(M7_FACTS)
    assert len(items)==21 and any(i['inclusion']=='unplaced' for i in items)
    assert any(i['inclusion']=='contextual' for i in items)
    assert any(i['fact'].get('acquisition',{}).get('quality',{}).get('status')=='unknown' for i in items)
    p=next(i for i in items if i['fact']['id']=='m7-P');assert p['fact']['result']['quantity']['value']=='65.00'
    assert v['assembly']['snapshot']['coverage']['continuity']=='not_established'
    assert CirculatoryStateCodec(config.envelope_signing_key).verify(v['state_context']).assembly_digest==v['assembly_digest']

@pytest.mark.parametrize('changed',[False,True])
def test_full_lifecycle_and_exact_recovery(case,changed):
    client,app,engine,config=case;v=prepared(client)
    command=CirculatoryCommandCodec(config.envelope_signing_key).verify(v['command'])
    assert command.inference_request.eligibility_policy=='SyntheticPLVEligibility/1'
    if changed:correct(engine)
    r=execute(client,v);assert r.status_code==200,r.text;body=r.json()
    assert body['record']['decision']['outcome']==('withheld' if changed else 'released')
    assert (body['statement'] is None)==changed
    assert execute(client,v).json()==body
    assert client.get(P+'/circulatory-reviews/'+v['execution_id']).json()==body
    assert reconcile(client,v).json()=={'status':'committed_match','execution':body}
    assert r.headers['cache-control']=='no-store'


def test_default_gate_blocks_new_work_but_not_browsing(case):
    from dataclasses import replace
    client,app,engine,config=case
    gated=APIConfig.model_validate({**config.model_dump(),'circulatory_execution_enabled':False})
    app.state.dependencies=replace(app.state.dependencies,config=gated)
    assert state(client)['execution_enabled'] is False
    with transaction(engine) as repo:before=repo.capture_cutoff().fact_watermark
    r=client.post(P+'/circulatory-review-preparations',json=preparation(client));assert r.status_code==422
    with transaction(engine) as repo:assert repo.capture_cutoff().fact_watermark==before

@pytest.mark.parametrize('changed',[False,True])
def test_gate_closure_preserves_retained_recovery(case,changed):
    from dataclasses import replace
    client,app,engine,config=case;v=prepared(client)
    if changed:correct(engine)
    saved=execute(client,v).json()
    app.state.dependencies=replace(app.state.dependencies,config=APIConfig.model_validate({**config.model_dump(),'circulatory_execution_enabled':False}))
    assert execute(client,v).json()==saved
    assert reconcile(client,v).json()['execution']==saved

@pytest.mark.parametrize('field',['pressure','lactate','vasopressor'])
@pytest.mark.parametrize('part',['reference','digest','role'])
def test_wrong_pins_are_sanitized_and_do_not_write(case,field,part):
    client,app,engine,_=case;body=preparation(client)
    if part=='reference':body[field]['reference']['id']='PRIVATE'
    elif part=='digest':body[field]['expected_digest']='0'*64
    else:body[field]=body['lactate' if field!='lactate' else 'pressure']
    with transaction(engine) as repo:before=repo.capture_cutoff().fact_watermark
    r=client.post(P+'/circulatory-review-preparations',json=body);assert r.status_code==422,r.text
    assert 'PRIVATE' not in r.text
    with transaction(engine) as repo:assert repo.capture_cutoff().fact_watermark==before

@pytest.mark.parametrize('part',['purpose','tamper','scope'])
def test_envelopes_are_purpose_and_scope_bound(case,part):
    client,app,engine,config=case;v=prepared(client)
    if part=='purpose':
        from app.api.review_commands import InvalidCommand
        with pytest.raises(InvalidCommand):MicroCommandCodec(config.envelope_signing_key).verify(v['command'])
        return
    path=P if part=='tamper' else P.replace('synthetic-p1','foreign')
    token=v['command']+'x' if part=='tamper' else v['command']
    r=client.post(path+'/circulatory-reviews',json={'command':token});assert r.status_code in (404,422)
    assert token not in r.text


def test_history_is_cutoff_bounded_and_corrections_inspectable(case):
    client,app,engine,config=case;old=state(client);correct(engine)
    ref=dict(kind='circulatory_pressure',id='m7-P',version='1')
    r=client.post(P+'/circulatory-evidence-history',json={'state_context':old['state_context'],'reference':ref})
    assert r.status_code==200,r.text;assert len(r.json()['revisions'])==1
    current=state(client)
    r=client.post(P+'/circulatory-evidence-history',json={'state_context':current['state_context'],'reference':ref})
    assert r.status_code==200,r.text
    assert [i['fact']['revision'] for i in r.json()['revisions']]==['1','2']
    assert r.json()['revisions'][1]['fact']['supersedes']==ref


def test_absence_is_not_execution(case):
    client,app,engine,config=case;v=prepared(client)
    assert reconcile(client,v).json()=={'status':'absent','execution':None}
    assert client.get(P+'/circulatory-reviews/'+v['execution_id']).status_code==404
    assert execute(client,v).status_code==200


def test_post_commit_projection_failure_can_reconcile(case,monkeypatch):
    from app.services import circulatory_product_service as service
    client,app,engine,config=case;v=prepared(client);original=service.execution
    def fail(*args):raise ValueError('PRIVATE payload')
    monkeypatch.setattr(service,'execution',fail)
    r=execute(client,v);assert r.status_code==500 and 'PRIVATE' not in r.text
    monkeypatch.setattr(service,'execution',original)
    assert reconcile(client,v).json()['status']=='committed_match'


def test_frontend_transport_schema_matches_authoritative_serialization():
    import json,runpy
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    generated=runpy.run_path(str(root/'tools/export_circulatory_transport.py'))['schema_bundle']()
    assert json.loads((root/'frontend/src/api/circulatorySchemas.json').read_text())==generated


@pytest.mark.parametrize('committed',[False,True])
def test_completion_unknown_preserves_exact_explicit_recovery(case,monkeypatch,committed):
    from app.services import circulatory_product_service as service
    from app.persistence.errors import TransactionCompletionUnknown
    client,app,engine,config=case;v=prepared(client);original=service.execute_circulatory_review
    def uncertain(*args,**kwargs):
        if committed:original(*args,**kwargs)
        raise TransactionCompletionUnknown('PRIVATE cause')
    monkeypatch.setattr(service,'execute_circulatory_review',uncertain)
    response=execute(client,v);assert response.status_code==503
    assert response.json()['status']=='completion_unknown'
    assert response.json()['execution_id']==v['execution_id']
    assert 'PRIVATE' not in response.text and v['command'] not in response.text
    recovery=reconcile(client,v).json()
    assert recovery['status']==('committed_match' if committed else 'absent')
    monkeypatch.setattr(service,'execute_circulatory_review',original)
    assert execute(client,v).status_code==200


def test_explicit_support_roundtrip_and_support_only_successor(case):
    from app.models.clinical.common import LineageEdge
    from app.models.clinical.hemodynamics import PressureObservation
    from app.demo.circulatory import facts
    client,app,engine,config=case;p=facts()[0];support=facts()[11]
    data=p.model_dump();data.update(revision='2',supersedes=p.reference,correction_reason='Synthetic exact support assertion')
    ref={**p.reference.model_dump(),'version':'2'}
    for name in ('calibration_application','zeroing_application'):data['acquisition'][name]['acquisition']=ref
    data['acquisition']['calibration_application']['provenance']['upstream']=(LineageEdge(target=support.reference,relationship='derived_from'),)
    revised=PressureObservation.model_validate(data)
    with transaction(engine) as repo:repo.append_revision(revised,target=TARGET)
    body=preparation(client);view=state(client);item=next(i for i in view['assembly']['snapshot']['items'] if i['fact']['id']=='m7-CAL')
    body['supporting']=[dict(reference=support.reference.model_dump(),expected_digest=item['expected_digest'])]
    response=client.post(P+'/circulatory-review-preparations',json=body);assert response.status_code==200,response.text
    v=response.json();assert len(v['inference']['inputs'])==4
    corrected=type(support).model_validate({**support.model_dump(),'revision':'2','supersedes':support.reference,'correction_reason':'Synthetic support-only correction'})
    with transaction(engine) as repo:repo.append_revision(corrected,target=TARGET)
    result=execute(client,v);assert result.status_code==200,result.text
    record=result.json()['record'];assert record['decision']['outcome']=='withheld'
    assert record['final_recheck']['evidence'][-1]['terminal']['version']=='2'
    assert record['evidence']['facts'][-1]['revision']=='1'
