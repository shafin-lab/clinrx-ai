"""Real SQLite transport composition; expected outcomes are independently asserted."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.api.config import APIConfig
from app.api.micro_commands import MicroCommandCodec, MicroStateCodec
from app.main import create_app
from app.demo.micro_antimicrobial import bootstrap, correct, manifest, SIMULATION_AT, TARGET
from app.persistence.database import create_database
from app.persistence.repository import transaction

P='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
FIELDS=('specimen_ref','isolate_ref','susceptibility_ref','administration_ref')
KINDS=('microbiology_specimen','microbiology_isolate','microbiology_susceptibility','antimicrobial_administration')
@pytest.fixture
def case(tmp_path):
    path=tmp_path/'demo.sqlite3'; engine=create_database(path); bootstrap(engine)
    config=APIConfig(database_path=path,environment='test',envelope_signing_key='a9'*32,clock_mode='historical_simulation',simulation_at=SIMULATION_AT)
    app=create_app(config,engine=engine)
    with TestClient(app) as client: yield client,app,engine,config
    engine.dispose()
def state(client):
    q={k:manifest()[k] for k in ('review_start','review_end')}
    r=client.get(P+'/patient-state-v2',params=q); assert r.status_code==200,r.text
    return r

def preparation(client):
    view=state(client).json()
    body=dict(execution_id=str(uuid4()),state_context=view['state_context'])
    for field,kind in zip(FIELDS,KINDS):
        item=next(i for i in view['assembly']['snapshot']['items'] if i['fact']['kind']==kind)
        f=item['fact'];body[field]=dict(reference=dict(kind=f['kind'],id=f['id'],version=f['revision']),expected_digest=item['expected_digest'])
    return body

def prepared(client):
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=preparation(client));assert r.status_code==200,r.text
    return r.json()
def execute(client,v): return client.post(P+'/micro-antimicrobial-reviews',json={'command':v['command']})
def reconcile(client,v): return client.post(P+'/micro-antimicrobial-review-reconciliations',json={'command':v['command']})

def test_state(case):
    client,app,engine,config=case;r=state(client);v=r.json(); a=v['assembly']
    assert r.headers['cache-control']=='no-store'
    assert a['request']['scope']['repository_cutoff']['fact_watermark']==13
    assert a['request']['profile_version']=='2' and len(a['snapshot']['items'])==10
    assert len(a['snapshot']['coverage'])==2
    u=next(i for i in a['snapshot']['items'] if i['fact']['kind']=='microbiology_susceptibility')
    assert u['fact']['mic']['quantity']['value']=='1.000'
    assert MicroStateCodec(config.envelope_signing_key).verify(v['state_context']).assembly_request.scope.repository_cutoff.fact_watermark==13

@pytest.mark.parametrize('changed',[False,True])
def test_lifecycle(case,changed):
    client,app,engine,config=case; v=prepared(client)
    request=MicroCommandCodec(config.envelope_signing_key).verify(v['command'])
    assert request.inference_cutoff.fact_watermark==14
    assert request.inference_request.scope.repository_cutoff.fact_watermark==13
    with transaction(engine) as repo: inference=repo.load_fact(request.inference_reference,target=TARGET).fact
    assert [r.id for r in inference.inputs]==['demo-S','demo-I','demo-U','demo-D']
    assert tuple(e.target for e in inference.provenance.upstream)==inference.inputs
    if changed: correct(engine)
    r=execute(client,v);assert r.status_code==200,r.text
    body=r.json();assert body['governance']['outcome']==('withheld' if changed else 'released')
    assert (body['statement'] is None)==changed
    assert body['provenance']['inference']['statement']==inference.statement
    assert body['provenance']['witness_statuses'][2]==('superseded' if changed else 'current')
    assert execute(client,v).json()==body
    assert client.get(P+'/micro-antimicrobial-reviews/'+v['execution_id']).json()==body
    assert reconcile(client,v).json()=={'status':'committed_match','execution':body}
    assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('updates',[
    {'review_start':'2026-10-08T11:00:00Z'}, {'review_end':'2026-11-08T10:00:00Z'},
    {'review_start':'2026-10-08T08:00:00'}, {'repository_cutoff':'PRIVATE'},
    {'review_end':'1780000000'}, {'review_start':'PRIVATE'}])
def test_bad_window(case,updates):
    client,*_=case;q={k:manifest()[k] for k in ('review_start','review_end')};q.update(updates)
    r=client.get(P+'/patient-state-v2',params=q)
    assert r.status_code==422 and r.headers['cache-control']=='no-store'
    assert 'PRIVATE' not in r.text

@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('part',['reference','digest','role'])
def test_invalid_selection_no_write(case,field,part):
    client,app,engine,_=case;body=preparation(client)
    if part=='reference': body[field]['reference']['id']='PRIVATE-missing'
    elif part=='digest': body[field]['expected_digest']='0'*64
    else: body[field]=body[FIELDS[(FIELDS.index(field)+1)%4]]
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body)
    assert r.status_code==422 and 'PRIVATE' not in r.text
    with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==13

@pytest.mark.parametrize('field',['actor','authority','final_cutoff','inference','requested_at','workflow'])
def test_unsigned_extras_rejected(case,field):
    client,*_=case;body=preparation(client);body[field]='PRIVATE'
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body)
    assert r.status_code==422 and 'PRIVATE' not in r.text

@pytest.mark.parametrize('kind',['tamper','purpose','scope'])
def test_state_envelope(case,kind):
    client,app,engine,config=case;body=preparation(client)
    if kind=='tamper': body['state_context']+='x'
    elif kind=='purpose': body['state_context']=prepared(client)['command']
    else:
        codec=MicroStateCodec(config.envelope_signing_key); context=codec.verify(body['state_context'])
        data=context.model_dump();data['assembly_request']['scope']['patient_id']='foreign'
        body['state_context']=codec.issue(type(context).model_validate(data))
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body)
    assert r.status_code==(404 if kind=='scope' else 422)
    assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('endpoint',['micro-antimicrobial-reviews','micro-antimicrobial-review-reconciliations'])
@pytest.mark.parametrize('kind',['tamper','purpose','scope'])
def test_command_rejection(case,endpoint,kind):
    client,*_=case;v=prepared(client);prefix=P
    if kind=='tamper': v['command']+='x'
    elif kind=='purpose': v['command']=state(client).json()['state_context']
    else: prefix=P.replace('synthetic-p1','foreign')
    r=client.post(prefix+'/'+endpoint,json={'command':v['command']})
    assert r.status_code==(404 if kind=='scope' else 422)
    assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('mode',['binding','mapping','unsupported_mapping','time'])
def test_unsuitable_recorded_evidence(case,mode):
    from app.demo.micro_antimicrobial import facts
    client,app,engine,config=case;f=facts()[2]
    values=f.model_dump();values.update(revision='2',supersedes=f.reference,correction_reason='Synthetic adverse fixture')
    values['report']['change']='corrected'
    if mode=='binding': values['domain_bindings'][0]['exact']['id']='unavailable';values['domain_bindings'][0]['stable_target']['id']='unavailable'
    elif mode=='mapping': values['antimicrobial']['canonical_id']='other-canonical-identity'
    elif mode=='unsupported_mapping': values['antimicrobial'].update(mapping_status='unsupported',canonical_id=None,ingredient_ids=(),limitation='Synthetic source mapping unavailable.')
    else: values['report']['available']={'status':'unknown','precision':'unknown'}
    changed=type(f).model_validate(values)
    with transaction(engine) as repo: repo.append_revision(changed,target=TARGET)
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=preparation(client))
    assert r.status_code==422,r.text
    with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==14


def test_preparation_replays_original_cutoff(case,monkeypatch):
    from app.services import micro_antimicrobial_product_service as service
    client,app,engine,config=case;body=preparation(client);correct(engine)
    def forbidden(*a,**k): pytest.fail('execution during preparation')
    monkeypatch.setattr(service,'execute_micro_antimicrobial_review',forbidden)
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body);assert r.status_code==200,r.text
    request=MicroCommandCodec(config.envelope_signing_key).verify(r.json()['command'])
    assert request.inputs[2].version=='1' and request.inference_cutoff.fact_watermark==15
    assert request.inference_request.scope.repository_cutoff.fact_watermark==13
    with engine.connect() as conn: assert conn.execute(text('SELECT count(*) FROM micro_antimicrobial_execution')).scalar_one()==0

@pytest.mark.parametrize('changed',[False,True])
def test_retained_paths_no_recomputation(case,monkeypatch,changed):
    from app.services import micro_antimicrobial_product_service as service
    from app.execution import patient_state_v2_workflow as workflow
    from app.api.dependencies import get_workflow_clock
    from app.persistence.repository import PatientRepository
    client,app,engine,config=case;v=prepared(client)
    if changed: correct(engine)
    result=execute(client,v).json()
    if not changed: correct(engine)
    def forbidden(*a,**k): pytest.fail('retained path recomputed or sampled clock')
    app.dependency_overrides[get_workflow_clock]=lambda:forbidden
    for name in ('assemble_patient_state_v2','build_micro_antimicrobial_timing_inference'): monkeypatch.setattr(service,name,forbidden)
    for name in ('_new_execution','_assemble','build_micro_antimicrobial_timing_inference','assess_release','decide_release'): monkeypatch.setattr(workflow,name,forbidden)
    for name in ('load_fact','load_latest_known','capture_cutoff','list_bounded_history'): monkeypatch.setattr(PatientRepository,name,forbidden)
    engine.dispose()
    assert execute(client,v).json()==result
    assert client.get(P+'/micro-antimicrobial-reviews/'+v['execution_id']).json()==result
    assert reconcile(client,v).json()=={'status':'committed_match','execution':result}

@pytest.mark.parametrize('changed',['actor','requested_at'])
def test_exact_request_conflict(case,changed):
    from datetime import timedelta
    client,app,engine,config=case;v=prepared(client);assert execute(client,v).status_code==200
    codec=MicroCommandCodec(config.envelope_signing_key);request=codec.verify(v['command'])
    update={'actor':'other'} if changed=='actor' else {'requested_at':request.requested_at+timedelta(seconds=1)}
    v['command']=codec.issue(type(request).model_validate({**request.model_dump(),**update}))
    for r in (execute(client,v),reconcile(client,v)):
        assert r.status_code==409 and r.json()['code']=='execution_conflict'


def test_absence_is_not_execution(case,monkeypatch):
    from app.execution import patient_state_v2_workflow as workflow
    client,app,engine,config=case;v=prepared(client)
    def forbidden(*a,**k): pytest.fail('reconciliation executed')
    monkeypatch.setattr(workflow,'_new_execution',forbidden)
    r=reconcile(client,v);assert r.json()=={'status':'absent','execution':None}
    assert r.headers['cache-control']=='no-store'
    assert client.get(P+'/micro-antimicrobial-reviews/'+v['execution_id']).status_code==404


def test_foreign_scope_and_visible_corruption(case):
    from app.api.config import SyntheticScope
    from app.api.dependencies import get_access_context, SyntheticAccessContext
    client,app,engine,config=case;v=prepared(client);assert execute(client,v).status_code==200
    with engine.begin() as conn: conn.execute(text("UPDATE micro_antimicrobial_execution SET payload='PRIVATE-corruption'"))
    r=client.get(P+'/micro-antimicrobial-reviews/'+v['execution_id']);assert r.status_code==500
    assert r.json()['code']=='storage_integrity_failure' and 'PRIVATE' not in r.text
    assert reconcile(client,v).status_code==500
    # Even the existence of a corrupt foreign row must remain unavailable.
    assert client.get(P.replace('synthetic-p1','foreign')+'/micro-antimicrobial-reviews/'+v['execution_id']).status_code==404

@pytest.mark.parametrize('stage',['execute','prepare'])
def test_completion_unknown(case,monkeypatch,stage):
    from app.persistence.errors import TransactionCompletionUnknown
    from app.services import micro_antimicrobial_product_service as service
    client,app,engine,config=case;v=prepared(client)
    def unknown(*a,**k): raise TransactionCompletionUnknown('PRIVATE')
    monkeypatch.setattr(service,'execute_micro_antimicrobial_review' if stage=='execute' else 'execution_transaction',unknown)
    r=execute(client,v) if stage=='execute' else client.post(P+'/micro-antimicrobial-review-preparations',json=preparation(client))
    assert r.status_code==503 and r.headers['cache-control']=='no-store' and 'PRIVATE' not in r.text
    if stage=='execute': assert r.json()['status']=='completion_unknown' and r.json()['automatic_retry'] is False
    else: assert r.headers['x-clinrx-stage']=='inference_preparation'


def test_logging_opaque(case,caplog):
    import logging
    client,*_=case
    with caplog.at_level(logging.INFO):
        v=prepared(client);execute(client,v);reconcile(client,v)
    assert v['command'] not in caplog.text and v['inference']['statement'] not in caplog.text
    assert 'demo-S' not in caplog.text

@pytest.mark.parametrize('code',['invalid_assembly','assembly_digest_mismatch','scope_mismatch'])
def test_builder_integrity_is_not_selection_rejection(case,monkeypatch,code):
    from app.services import micro_antimicrobial_product_service as service
    from app.execution.patient_state_v2_inference import MicroAntimicrobialInferenceError
    client,*_=case;body=preparation(client)
    def fail(*a,**k): raise MicroAntimicrobialInferenceError(code)
    monkeypatch.setattr(service,'build_micro_antimicrobial_timing_inference',fail)
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body)
    assert r.status_code==500 and r.json()['code']=='storage_integrity_failure'


def test_demo_repeated_bootstrap_and_correction_are_idempotent(case):
    client,app,engine,config=case;bootstrap(engine);correct(engine);correct(engine)
    with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==14


def test_contextual_parent_transport(case):
    client,*_=case
    q={'review_start':'2026-10-08T09:00:00Z','review_end':'2026-10-08T10:00:00Z'}
    r=client.get(P+'/patient-state-v2',params=q);assert r.status_code==200,r.text
    s=next(i for i in r.json()['assembly']['snapshot']['items'] if i['fact']['id']=='demo-S')
    assert s['inclusion']=='contextual_parent' and s['contextual_for'] and s['disclosures']


def test_missing_pin(case):
    client,*_=case;body=preparation(client);del body['administration_ref']
    r=client.post(P+'/micro-antimicrobial-review-preparations',json=body)
    assert r.status_code==422 and r.headers['cache-control']=='no-store'
