"""M5.2 real SQLite HTTP composition and retained-only recovery."""
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.api.config import APIConfig
from app.main import create_app
from app.demo.patient_state import bootstrap, correct, manifest, SIMULATION_AT, TARGET
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.services import patient_state_product_service as service_module

PREFIX = '/api/v1/patients/synthetic-p1/encounters/synthetic-e1'


@pytest.fixture
def case(tmp_path):
    engine = create_database(tmp_path / 'demo.sqlite3')
    bootstrap(engine)
    config = APIConfig(database_path=tmp_path / 'demo.sqlite3', environment='test',
        envelope_signing_key='a9'*32, clock_mode='historical_simulation', simulation_at=SIMULATION_AT)
    app = create_app(config, engine=engine)
    with TestClient(app) as client:
        yield client, app, engine, config
    engine.dispose()


def state(client):
    scenario = manifest()
    response = client.get(PREFIX+'/state', params={k:scenario[k] for k in ('review_start','review_end')})
    assert response.status_code == 200, response.text
    return response


def preparation(client):
    view = state(client).json()
    return dict(execution_id=str(uuid4()), state_context=view['state_context'],
        earlier_laboratory=dict(reference=view['laboratory'][0]['reference'], expected_digest=view['laboratory'][0]['selection_digest']),
        later_laboratory=dict(reference=view['laboratory'][1]['reference'], expected_digest=view['laboratory'][1]['selection_digest']),
        medication=dict(reference=view['medication'][0]['reference'], expected_digest=view['medication'][0]['selection_digest']))


def prepared(client):
    response = client.post(PREFIX+'/temporal-review-preparations', json=preparation(client))
    assert response.status_code == 200, response.text
    return response.json()


def test_state_exact_bounds_and_coverage(case):
    client, app, engine, _ = case
    response = state(client); body = response.json()
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-clinrx-mode'] == 'historical-synthetic-simulation'
    assert body['scope']['repository_cutoff']['fact_watermark'] == 3
    assert len(body['coverage']) == 10
    assert all(c['mapping_support']=='unsupported' and c['retained_count'] is None for c in body['coverage'][2:])
    assert [x['quantity']['value'] for x in body['laboratory']] == ['1.00','2.000']
    context = app.state.dependencies.state_context.verify(body['state_context'])
    assert context.scope.repository_cutoff.fact_watermark == 3
    assert context.scope.review_start.isoformat() == manifest()['review_start']


@pytest.mark.parametrize('corrected', [False, True])
def test_prepare_execute_lookup_reconcile(case, corrected):
    client, app, engine, _ = case
    value = prepared(client)
    command = app.state.dependencies.execution_command.verify(value['command'])
    assert command.inference_cutoff.fact_watermark == 4
    assert command.actor == 'synthetic-patient-state-orchestrator'
    with transaction(engine) as repo:
        inference = repo.load_fact(command.inference_reference, target=TARGET).fact
    assert inference.inputs == command.inputs
    assert tuple(e.target for e in inference.provenance.upstream) == command.inputs
    assert command.inference_request.executed_at == SIMULATION_AT
    if corrected: correct(engine)
    result = client.post(PREFIX+'/temporal-reviews', json={'command':value['command']})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['governance']['outcome'] == ('withheld' if corrected else 'released')
    assert body['governance']['assessed_at'] == SIMULATION_AT.isoformat().replace('+00:00', 'Z')
    assert (body['provenance']['inference']['statement'] is None) == corrected
    assert body['provenance']['earlier_laboratory']['quantity']['value'] == '1.00'
    assert body['provenance']['terminal_references'][0]['version'] == ('2' if corrected else '1')
    assert client.post(PREFIX+'/temporal-reviews', json={'command':value['command']}).json() == body
    path = PREFIX+'/temporal-executions/'+value['execution_id']
    assert client.get(path).json() == body
    assert client.post(path+'/reconcile', json={'command':value['command']}).json() == {'status':'committed_match','execution':body}


@pytest.mark.parametrize('updates', [
    {'review_start':'2026-10-08T11:00:00Z'}, {'review_end':'2026-11-08T10:00:00Z'},
    {'review_start':'2026-10-08T08:00:00'}, {'repository_cutoff':'private-cutoff'},
    {'review_end':'1780000000'}, {'review_start':'private-invalid'},
])
def test_bad_state_query_bounded(case, updates):
    client, _, _, _ = case
    query = {k:manifest()[k] for k in ('review_start','review_end')}; query.update(updates)
    response = client.get(PREFIX+'/state', params=query)
    assert response.status_code == 422
    assert response.headers['cache-control'] == 'no-store'
    assert 'private-' not in response.text and 'input_value' not in response.text


@pytest.mark.parametrize('field', ['actor','authority','final_cutoff','inference','requested_at','workflow'])
def test_no_client_server_fields(case, field):
    client, _, _, _ = case
    body = preparation(client); body[field] = 'PRIVATE'
    result = client.post(PREFIX+'/temporal-review-preparations', json=body)
    assert result.status_code == 422 and 'PRIVATE' not in result.text


@pytest.mark.parametrize('role', ['earlier_laboratory','later_laboratory','medication'])
@pytest.mark.parametrize('part', ['reference','digest'])
def test_invalid_exact_selection_no_write(case, role, part):
    client, _, engine, _ = case
    body = preparation(client)
    if part == 'reference': body[role]['reference']['id'] = 'PRIVATE-missing'
    else: body[role]['expected_digest'] = '0'*64
    response = client.post(PREFIX+'/temporal-review-preparations', json=body)
    assert response.status_code == 422 and 'PRIVATE' not in response.text
    with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark == 3


@pytest.mark.parametrize('kind', ['tamper','purpose','scope'])
def test_envelope_rejection(case, kind):
    client, app, _, _ = case
    body = preparation(client)
    if kind == 'tamper': body['state_context'] += 'x'
    elif kind == 'purpose': body['state_context'] = prepared(client)['command']
    else:
        context = app.state.dependencies.state_context.verify(body['state_context'])
        scope = type(context.scope).model_validate({**context.scope.model_dump(), 'patient_id':'foreign'})
        body['state_context'] = app.state.dependencies.state_context.issue(type(context)(scope=scope))
    result = client.post(PREFIX+'/temporal-review-preparations', json=body)
    assert result.status_code == (404 if kind == 'scope' else 422)
    assert result.headers['cache-control'] == 'no-store'


def test_complete_historical_replay_after_correction(case):
    client, app, engine, _ = case
    body = preparation(client); correct(engine)
    response = client.post(PREFIX+'/temporal-review-preparations', json=body)
    assert response.status_code == 200, response.text
    request = app.state.dependencies.execution_command.verify(response.json()['command'])
    assert request.inference_request.scope.repository_cutoff.fact_watermark == 3
    assert request.inputs[0].version == '1' and request.inference_cutoff.fact_watermark == 5
    with transaction(engine) as repo: original = repo.load_fact(request.inference_reference, target=TARGET).fact
    assert '1.00 mg/dL' in original.statement and '1.50 mg/dL' not in original.statement


def test_no_execution_during_preparation(case, monkeypatch):
    client, _, engine, _ = case
    def forbidden(*a, **k): pytest.fail('execution during preparation')
    monkeypatch.setattr(service_module, 'execute_patient_state_temporal_review', forbidden)
    prepared(client)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM patient_state_temporal_execution')).scalar_one() == 0


@pytest.mark.parametrize('changed', ['actor','requested_at'])
def test_exact_retry_conflict(case, changed):
    client, app, _, _ = case; body = prepared(client)
    assert client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).status_code == 200
    request = app.state.dependencies.execution_command.verify(body['command'])
    update = {'actor':'other'} if changed == 'actor' else {'requested_at':request.requested_at+timedelta(seconds=1)}
    request = type(request).model_validate({**request.model_dump(), **update})
    command = app.state.dependencies.execution_command.issue(request)
    for path in ('/temporal-reviews', '/temporal-executions/'+body['execution_id']+'/reconcile'):
        result = client.post(PREFIX+path, json={'command':command})
        assert result.status_code == 409 and result.json()['code'] == 'execution_conflict'


@pytest.mark.parametrize('corrected', [False, True])
def test_retained_only_after_changes_and_clock_expiry(case, monkeypatch, corrected):
    client, app, engine, _ = case; body = prepared(client)
    if corrected: correct(engine)
    executed = client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).json()
    if not corrected: correct(engine)
    from test_patient_state_workflow import forbid_fresh
    forbidden = forbid_fresh(monkeypatch)
    monkeypatch.setattr(service_module, 'assemble_patient_state', forbidden)
    monkeypatch.setattr(service_module, 'build_patient_state_temporal_inference', forbidden)
    from dataclasses import replace
    app.state.dependencies = replace(app.state.dependencies, clock=forbidden)
    path = PREFIX+'/temporal-executions/'+body['execution_id']
    assert client.get(path).json() == executed
    assert client.post(path+'/reconcile', json={'command':body['command']}).json()['execution'] == executed
    assert client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).json() == executed


def test_absent_is_not_execution(case, monkeypatch):
    client, _, _, _ = case; body = prepared(client)
    def forbidden(*a, **k): pytest.fail('reconciliation executed')
    monkeypatch.setattr(service_module, 'execute_patient_state_temporal_review', forbidden)
    path = PREFIX+'/temporal-executions/'+body['execution_id']
    assert client.get(path).status_code == 404
    assert client.post(path+'/reconcile', json={'command':body['command']}).json() == {'status':'absent','execution':None}
    assert client.post(PREFIX+'/temporal-executions/'+str(uuid4())+'/reconcile', json={'command':body['command']}).status_code == 422


def test_foreign_scope_matches_absence(case):
    client, _, _, _ = case; body = prepared(client)
    client.post(PREFIX+'/temporal-reviews', json={'command':body['command']})
    absent = client.get(PREFIX+'/temporal-executions/'+str(uuid4()))
    foreign = client.get(PREFIX.replace('synthetic-p1','foreign')+'/temporal-executions/'+body['execution_id'])
    assert absent.status_code == foreign.status_code == 404
    assert {k:v for k,v in absent.json().items() if k!='correlation_id'} == {k:v for k,v in foreign.json().items() if k!='correlation_id'}
    for suffix in ('/temporal-reviews','/temporal-executions/'+body['execution_id']+'/reconcile'):
        assert client.post(PREFIX.replace('synthetic-p1','foreign')+suffix, json={'command':body['command']}).status_code == 404


def test_visible_corruption_is_integrity_failure(case):
    client, _, engine, _ = case; body = prepared(client)
    assert client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).status_code == 200
    with engine.begin() as conn:
        conn.execute(text("UPDATE patient_state_temporal_execution SET payload='PRIVATE malformed'"))
    path = PREFIX+'/temporal-executions/'+body['execution_id']
    for response in (client.get(path), client.post(path+'/reconcile', json={'command':body['command']})):
        assert response.status_code == 500 and response.json()['code'] == 'storage_integrity_failure'
        assert 'PRIVATE' not in response.text


@pytest.mark.parametrize('committed', [False, True])
def test_execution_unknown_explicit_reconciliation(case, monkeypatch, committed):
    from app.persistence.errors import TransactionCompletionUnknown
    client, _, _, _ = case; body = prepared(client)
    original = service_module.execute_patient_state_temporal_review
    calls = []
    def uncertain(*a, **k):
        calls.append(True)
        if committed: original(*a, **k)
        raise TransactionCompletionUnknown('PRIVATE SQL')
    monkeypatch.setattr(service_module, 'execute_patient_state_temporal_review', uncertain)
    result = client.post(PREFIX+'/temporal-reviews', json={'command':body['command']})
    assert result.status_code == 503 and calls == [True]
    assert result.json()['next_action']=='reconcile' and result.json()['automatic_retry'] is False
    assert result.json()['execution_id']==body['execution_id'] and 'PRIVATE' not in result.text
    recovered = client.post(PREFIX+'/temporal-executions/'+body['execution_id']+'/reconcile', json={'command':body['command']})
    assert recovered.json()['status'] == ('committed_match' if committed else 'absent')


@pytest.mark.parametrize('committed', [False, True])
def test_preparation_unknown_has_no_execution_recovery(case, monkeypatch, committed):
    from contextlib import contextmanager
    from app.persistence.errors import TransactionCompletionUnknown
    client, _, _, _ = case; body = preparation(client)
    original = service_module.execution_transaction
    calls = []
    @contextmanager
    def uncertain(engine):
        calls.append(True)
        with original(engine) as tx:
            yield tx
            if not committed: raise TransactionCompletionUnknown('PRIVATE')
        raise TransactionCompletionUnknown('PRIVATE')
    monkeypatch.setattr(service_module, 'execution_transaction', uncertain)
    result = client.post(PREFIX+'/temporal-review-preparations', json=body)
    assert result.status_code == 503 and result.json()['code']=='completion_unknown'
    assert calls == [True] and 'next_action' not in result.json() and 'execution_id' not in result.json()
    assert result.json()['message'] == 'Inference preparation completion could not be confirmed.'
    assert result.headers['x-clinrx-stage'] == 'inference_preparation'
    assert 'PRIVATE' not in result.text


def test_preparation_commit_failure_real_boundary(case):
    client, _, engine, _ = case; body = preparation(client)
    # Complete assembly has a read commit first; fail only the write commit.
    original = engine.dialect.do_commit
    commits = []
    def failing(connection):
        commits.append(True)
        if len(commits)==2: raise RuntimeError('PRIVATE commit')
        return original(connection)
    engine.dialect.do_commit = failing
    try: result = client.post(PREFIX+'/temporal-review-preparations', json=body)
    finally: engine.dialect.do_commit = original
    assert result.status_code == 503 and result.json()['code']=='completion_unknown'
    assert 'PRIVATE' not in result.text


@pytest.mark.parametrize('payload', ['{', 'x'*262145])
def test_early_error_no_store(case, payload):
    client, _, _, _ = case
    result = client.post(PREFIX+'/temporal-reviews', content=payload, headers={'content-type':'application/json'})
    assert result.status_code in (413,422) and result.headers['cache-control']=='no-store'


def test_response_bound_no_truncation(case):
    from dataclasses import replace
    client, app, _, config = case
    config = APIConfig.model_validate({**config.model_dump(), 'max_response_bytes':1024})
    app.state.dependencies = replace(app.state.dependencies, config=config)
    result = client.get(PREFIX+'/state', params={k:manifest()[k] for k in ('review_start','review_end')})
    assert result.status_code == 422 and result.json()['code']=='bounded_view_limit_exceeded'


def test_route_logging_has_no_payload_or_path_ids(case, caplog):
    import logging
    client, _, _, _ = case
    caplog.set_level(logging.INFO, logger='clinrx.api')
    prepared(client)
    records = [r for r in caplog.records if r.name=='clinrx.api']
    assert records
    for record in records:
        fields = str((record.msg, record.args, record.route_template, record.execution_id, record.outcome))
        assert 'synthetic-p1' not in fields and 'synthetic-e1' not in fields
        assert 'state-context.v1' not in fields and 'execution-command.v1' not in fields
        assert '1.00' not in fields and 'SELECT ' not in fields


def test_real_mode_does_not_backdate(case):
    from dataclasses import replace
    from app.api.dependencies import make_clock
    client, app, _, config = case
    config = APIConfig.model_validate({**config.model_dump(), 'clock_mode':'real', 'simulation_at':None})
    app.state.dependencies = replace(app.state.dependencies, config=config, clock=make_clock(config))
    body = prepared(client)
    request = app.state.dependencies.execution_command.verify(body['command'])
    assert request.requested_at != SIMULATION_AT
    result = client.post(PREFIX+'/temporal-reviews', json={'command':body['command']})
    assert result.status_code == 200 and result.json()['governance']['outcome']=='withheld'
    assert result.headers['x-clinrx-mode']=='synthetic-only-real-clock'


@pytest.mark.parametrize('kind', ['tamper','purpose'])
@pytest.mark.parametrize('operation', ['execute','reconcile'])
def test_invalid_command_before_execution(case, kind, operation):
    client, _, _, _ = case; body = prepared(client)
    token = body['command']+'x' if kind=='tamper' else state(client).json()['state_context']
    path = '/temporal-reviews' if operation=='execute' else '/temporal-executions/'+body['execution_id']+'/reconcile'
    result = client.post(PREFIX+path, json={'command':token})
    assert result.status_code == 422 and result.json()['code']=='invalid_command'


def test_configured_access_still_uses_scoped_lookup(case):
    from dataclasses import replace
    from app.api.dependencies import SyntheticAccessContext
    client, app, _, _ = case; body = prepared(client)
    assert client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).status_code==200
    app.state.dependencies = replace(app.state.dependencies, access=SyntheticAccessContext(scopes=(
        {'patient_id':'synthetic-p1','encounter_id':'synthetic-e1'},
        {'patient_id':'synthetic-p1','encounter_id':'foreign-encounter'})))
    path = PREFIX.replace('synthetic-e1','foreign-encounter')+'/temporal-executions/'+body['execution_id']
    assert client.get(path).status_code==404


def test_provenance_exact_order_cutoffs_and_metadata(case):
    client, app, engine, _ = case; body = prepared(client)
    command = app.state.dependencies.execution_command.verify(body['command'])
    result = client.post(PREFIX+'/temporal-reviews', json={'command':body['command']}).json()
    provenance = result['provenance']
    expected = [r.model_dump() for r in command.inputs]
    assert provenance['inference']['inputs'] == expected
    assert [x['target'] for x in provenance['direct_dependencies']] == expected
    assert [provenance[k]['reference'] for k in ('earlier_laboratory','later_laboratory','medication')] == expected
    assert provenance['terminal_references'] == expected
    assert provenance['inference']['method']=={'kind':'inference_method','id':'RecordedPatientStateTemporalRelation','version':'1'}
    assert provenance['input_cutoff']['fact_watermark']==3
    assert provenance['inference_cutoff']['fact_watermark']==4
    assert provenance['final_cutoff']['fact_watermark']==4
    assert provenance['inference']['uncertainty'] and provenance['inference']['limitations']
    assert provenance['medication']['event_type']=='medication_order'
    assert result['ingested_at'] != result['finalized_at']


def test_medication_administration_projection(case):
    from app.models.clinical.facts import MedicationAdministration
    from app.demo.patient_state import facts
    client, _, engine, _ = case
    _,_,m = facts()
    administration = MedicationAdministration.model_validate({
        **m.model_dump(exclude={'kind','prescribed_dose','schedule_text','order_status'}),
        'id':'demo-administration', 'administered_dose':{**m.prescribed_dose.model_dump(),'basis':'total_administered'},
        'administered_at':m.time.event, 'order':m.reference})
    with transaction(engine) as repo: repo.append_fact(administration, target=TARGET)
    view=state(client).json(); body=preparation(client)
    selected=next(x for x in view['medication'] if x['event_type']=='medication_administration')
    body['medication']={'reference':selected['reference'],'expected_digest':selected['selection_digest']}
    prep=client.post(PREFIX+'/temporal-review-preparations',json=body)
    assert prep.status_code==200,prep.text
    result=client.post(PREFIX+'/temporal-reviews',json={'command':prep.json()['command']})
    assert result.status_code==200,result.text
    med=result.json()['provenance']['medication']
    assert med['event_type']=='medication_administration' and med['dose_basis']=='total_administered'
    assert med['status']=='administered' and med['schedule_text'] is None


def test_original_complete_assembly_not_only_selected_facts(case, monkeypatch):
    client, _, engine, _ = case
    from app.demo.patient_state import facts
    a,_,_=facts()
    extra=type(a).model_validate({**a.model_dump(),'id':'unmapped-unselected','concept_id':'unsupported-profile'})
    with transaction(engine) as repo: repo.append_fact(extra,target=TARGET)
    body=preparation(client)
    original=service_module.assemble_patient_state; calls=[]
    def capture(*args,**kwargs):
        result=original(*args,**kwargs); calls.append(result)
        return result
    monkeypatch.setattr(service_module,'assemble_patient_state',capture)
    response=client.post(PREFIX+'/temporal-review-preparations',json=body)
    assert response.status_code==200
    assert len(calls)==1 and len(calls[0].coverage)==10
    assert len(calls[0].snapshot.ordered_items)==3
    assert len(calls[0].issues)==1 and calls[0].issues[0].reference.id=='unmapped-unselected'


def test_preparation_operational_failure_is_bounded(case, monkeypatch):
    from contextlib import contextmanager
    from app.persistence.errors import TransactionAborted
    client,_,_,_=case; body=preparation(client)
    @contextmanager
    def fail(*args):
        raise TransactionAborted('PRIVATE SQL failure')
        yield
    monkeypatch.setattr(service_module,'execution_transaction',fail)
    response=client.post(PREFIX+'/temporal-review-preparations',json=body)
    assert response.status_code==503 and response.json()['code']=='transaction_failed'
    assert 'PRIVATE' not in response.text


def test_closed_state_window_exact_boundary(case):
    client,_,_,_=case
    at=manifest()['review_start']
    response=client.get(PREFIX+'/state',params={'review_start':at,'review_end':at})
    assert response.status_code==200
    assert [x['reference']['id'] for x in response.json()['laboratory']]==['demo-creatinine-A']
    assert response.json()['medication']==[]


def test_service_forwards_exact_decoded_command(case, monkeypatch):
    client,app,_,_=case; body=prepared(client)
    original=service_module.execute_patient_state_temporal_review; received=[]
    def capture(engine, request, **kwargs):
        received.append(request)
        return original(engine,request,**kwargs)
    monkeypatch.setattr(service_module,'execute_patient_state_temporal_review',capture)
    expected=app.state.dependencies.execution_command.verify(body['command'])
    for _ in range(2):
        assert client.post(PREFIX+'/temporal-reviews',json={'command':body['command']}).status_code==200
    from app.persistence.mapping import canonical_payload
    assert [canonical_payload(r) for r in received]==[canonical_payload(expected)]*2



def test_demo_metadata_exposed_to_configured_browser_origin(case):
    from dataclasses import replace
    client,app,_,config=case
    config=APIConfig.model_validate({**config.model_dump(),'allowed_dev_origins':('http://localhost:3000',)})
    app.state.dependencies=replace(app.state.dependencies,config=config)
    response=client.get(PREFIX+'/state',params={k:manifest()[k] for k in ('review_start','review_end')},
        headers={'Origin':'http://localhost:3000'})
    assert response.status_code==200
    assert 'X-ClinRx-Mode' in response.headers['access-control-expose-headers']
    assert 'X-ClinRx-Stage' in response.headers['access-control-expose-headers']


def test_foreign_state_and_preparation_do_not_read_database(case, monkeypatch):
    client,_,_,_=case; body=preparation(client)
    def forbidden(*a,**k): pytest.fail('foreign scope accessed storage')
    monkeypatch.setattr(service_module,'transaction',forbidden)
    monkeypatch.setattr(service_module,'assemble_patient_state',forbidden)
    foreign=PREFIX.replace('synthetic-e1','foreign')
    response=client.get(foreign+'/state',params={k:manifest()[k] for k in ('review_start','review_end')})
    assert response.status_code==404
    assert client.post(foreign+'/temporal-review-preparations',json=body).status_code==404



def test_unsupported_laboratory_unit_delegates_to_m3(case):
    from app.demo.patient_state import facts
    client,_,engine,_=case
    a,_,_=facts()
    data=a.model_dump()
    data['value']['value']['unit'].update(raw='mg/L',code='mg/L')
    corrected=type(a).model_validate({**data,'revision':'2','supersedes':a.reference,'correction_reason':'Synthetic unit case.'})
    with transaction(engine) as repo: repo.append_revision(corrected,target=TARGET)
    response=client.post(PREFIX+'/temporal-review-preparations',json=preparation(client))
    assert response.status_code==422 and response.json()['code']=='unsupported_review_input'
    with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==4
