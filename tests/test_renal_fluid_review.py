"""RF1 real API/storage, original observations, shared bounds and no-write evidence."""
import copy
import json
import shutil
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from app.demo.renal_fluid_fixture import bootstrap, observations
from app.demo.renal_fluid_gateway import SyntheticRenalFluidGateway, STATE, HISTORY
from app.demo.hosting import PREFIX
from app.api.circulatory_commands import CirculatoryStateCodec
from app.api.schemas.renal_fluid import RenalHistoryRequest, RenalFluidResponse
from app.models.clinical.facts import ClinicalObservation
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.bounded_history import AggregateHistoryBudget, HistoryBudget
from app.persistence.errors import QueryLimitExceeded, UnsupportedOperation
from app.services.renal_fluid_product_service import RenalFluidProductService
from tests.test_synthetic_hosting import rows
ORIGIN = 'http://127.0.0.1:5197'
PARAMS = {'review_start': '2026-10-08T08:00:00+00:00', 'review_end': '2026-10-08T10:00:00+00:00'}

@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    path = tmp_path_factory.mktemp('rf1-seed') / 'seed.sqlite3'
    engine = create_database(path)
    try: bootstrap(engine)
    finally: engine.dispose()
    return path

@pytest.fixture
def workspace(tmp_path, seeded):
    db = tmp_path / 'rf1.sqlite3'; shutil.copyfile(seeded, db)
    frontend = tmp_path / 'dist'; (frontend / 'assets').mkdir(parents=True); (frontend / 'index.html').write_text('synthetic RF1')
    app = SyntheticRenalFluidGateway(db, frontend, 'a7'*32, ORIGIN)
    with TestClient(app, base_url=ORIGIN, client=('127.0.0.1', 50000), headers={'Origin': ORIGIN}) as client:
        yield client, db, app

def get_state(client):
    response = client.get(STATE, params=PARAMS)
    assert response.status_code == 200, response.text
    return response.json()

def dependency(app):
    d=app.core.state.dependencies
    return replace(d, state_context=CirculatoryStateCodec(d.config.envelope_signing_key))

def test_complete_readonly_journey_originals_history_and_no_writes(workspace):
    client, db, app = workspace; before=rows(db)
    state=get_state(client); validated=RenalFluidResponse.model_validate(state)
    assert validated.execution_enabled is False
    scope=state['context']['scope']
    assert scope==state['laboratory']['scope']==state['circulatory']['assembly']['request']['scope']
    items={i['fact']['id']: i for i in state['laboratory']['observations']}
    assert len(items)==4
    assert items['demo-creatinine-A']['fact']['revision']=='2'
    assert items['demo-creatinine-A']['fact']['value']['value']['value']=='1.1000'
    assert items['rf1-creatinine-missing']['inclusion']=='unplaced'
    assert items['rf1-creatinine-missing']['fact']['value']['status']=='missing'
    assert items['rf1-creatinine-unlike-unit']['fact']['value']['value']['unit']['raw']=='umol/L'
    assert items['rf1-creatinine-unlike-unit']['fact']['conflict']=='unresolved'
    selected=items['demo-creatinine-A']['fact']
    response=client.post(HISTORY,json={'state_context':state['state_context'],'reference':{'kind':selected['kind'],'id':selected['id'],'version':selected['revision']}})
    assert response.status_code==200,response.text
    assert [i['fact']['value']['value']['value'] for i in response.json()['revisions']]==['1.00','1.1000']
    circ=state['circulatory']; fluid=next(i for i in circ['assembly']['snapshot']['items'] if i['fact']['id']=='fs-IO-output_urine-15')
    r=client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':circ['state_context'],'reference':{'kind':fluid['fact']['kind'],'id':fluid['fact']['id'],'version':fluid['fact']['revision']}})
    assert r.status_code==200,r.text
    assert r.json()['revisions'][0]['fact']==fluid['fact']
    assert len(state['circulatory']['assembly']['snapshot']['items'])==161
    assert client.get('/health').json()['execution_enabled'] is False
    for path in ('/circulatory-review-preparations','/circulatory-reviews','/renal-observations','/synthetic-renal-fluid/execute'):
        assert client.post(PREFIX+path,json={}).status_code==404
    fresh=get_state(client)
    assert [i['fact'] for i in fresh['laboratory']['observations']]==[i['fact'] for i in state['laboratory']['observations']]
    assert rows(db)==before  # every table, all prior facts and retained receipts

@pytest.mark.parametrize('fault',['signature','foreign_id','kind','old_revision','foreign_scope','extra'])
def test_history_rejects_ambiguity_or_non_selected_exact_revision_without_writes(workspace,fault):
    client,db,app=workspace; state=get_state(client); before=rows(db)
    body={'state_context':state['state_context'],'reference':{'kind':'observation','id':'demo-creatinine-A','version':'2'}}
    if fault=='signature': body['state_context']=body['state_context'][:-3]+'abc'
    if fault=='foreign_id':body['reference']['id']='not-allowed'
    if fault=='kind':body['reference']['kind']='circulatory_event'
    if fault=='old_revision':body['reference']['version']='1'
    if fault=='foreign_scope':body['state_context']=state['circulatory']['state_context']
    if fault=='extra':body['extra']='not accepted'
    assert client.post(HISTORY,json=body).status_code in (404,422)
    assert rows(db)==before

def test_terminal_outside_window_never_resurrects_original(workspace):
    client,db,app=workspace; old=get_state(client)
    a=observations()[2]; data=a.model_dump();data.update(revision='3',supersedes=a.reference,correction_reason='Later source correction outside review window')
    data['time']['event']=datetime.fromisoformat('2026-10-08T11:00:00+00:00')
    data['value']={'status':'unknown','reason':'Corrected source result unavailable'}
    with transaction(app.core.state.dependencies.engine) as repo:repo.append_revision(ClinicalObservation.model_validate(data),target=a.binding.target)
    fresh=get_state(client); current=next(i for i in fresh['laboratory']['observations'] if i['fact']['id']==a.id)
    assert current['fact']['revision']=='3' and current['inclusion']=='outside_window' and current['fact']['value']['status']=='unknown'
    previous=client.post(HISTORY,json={'state_context':old['state_context'],'reference':{'kind':'observation','id':a.id,'version':'2'}})
    assert previous.status_code==200
    assert [r['fact']['revision'] for r in previous.json()['revisions']]==['1','2']

@pytest.mark.parametrize('bound',['rows','aggregate','bytes','observations','response'])
def test_shared_accounting_and_combined_limits_fail_closed(workspace,bound):
    client,db,app=workspace; before=rows(db); d=dependency(app)
    kwargs={}
    if bound=='rows':kwargs['history_budget']=HistoryBudget(max_rows=1)
    if bound=='bytes':kwargs['history_budget']=HistoryBudget(max_payload_bytes=100)
    if bound=='aggregate':
        # One scan fits, the composite's second scan must be charged too.
        kwargs['aggregate_budget']=AggregateHistoryBudget(max_rows=len(before['fact_revision'])+1)
    if bound=='observations':kwargs['max_observations']=1
    if bound=='response':d=replace(d,config=d.config.model_copy(update={'max_response_bytes':1000}))
    service=RenalFluidProductService(d,**kwargs)
    with pytest.raises(QueryLimitExceeded):service.state('synthetic-p1','synthetic-e1',*(datetime.fromisoformat(PARAMS[k]) for k in ('review_start','review_end')))
    assert rows(db)==before

def test_enabled_configuration_cannot_be_reported_disabled(workspace):
    _,db,app=workspace;d=dependency(app);d=replace(d,config=d.config.model_copy(update={'circulatory_execution_enabled':True}))
    with pytest.raises(UnsupportedOperation):RenalFluidProductService(d).state('synthetic-p1','synthetic-e1',*(datetime.fromisoformat(PARAMS[k]) for k in ('review_start','review_end')))

def test_new_routes_not_present_in_default_gateway_or_normal_api(workspace,tmp_path):
    from app.demo.hosting import SyntheticDemoGateway
    client,db,app=workspace
    default=SyntheticDemoGateway(db,tmp_path/'dist','a7'*32)
    with TestClient(default,base_url=ORIGIN) as c:assert c.get(STATE,params=PARAMS).status_code==404
    assert not any(getattr(r,'path','')==STATE for r in default.core.routes)

def test_renal_schema_export_is_current():
    from tools.export_renal_fluid_transport import schema_bundle
    assert json.loads(Path('frontend/src/api/renalFluidSchemas.json').read_text())==schema_bundle()
