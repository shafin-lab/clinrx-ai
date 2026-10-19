import json
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.demo.renal_fluid_entry_gateway import SyntheticRF2Gateway,RF2
from app.demo.renal_fluid_fixture import bootstrap
from app.persistence.database import create_database
import shutil
from tests.test_synthetic_hosting import rows
ORIGIN='http://127.0.0.1:5201'
@pytest.fixture(scope='module')
def seed(tmp_path_factory):
    db=tmp_path_factory.mktemp('rf2-seed')/'seed.sqlite3';engine=create_database(db)
    try:
        from app.demo.patient_state import bootstrap as base_bootstrap, TARGET
        from app.demo.icu_chart_entries import context_facts
        from app.persistence.repository import transaction
        base_bootstrap(engine)
        with transaction(engine) as repo:
            for fact in context_facts()[:14]:repo.append_fact(fact,target=TARGET)
    finally:engine.dispose()
    return db
@pytest.fixture
def ws(tmp_path,seed):
    db=tmp_path/'rf2.sqlite3';shutil.copyfile(seed,db);front=tmp_path/'frontend';(front/'assets').mkdir(parents=True);(front/'index.html').write_text('synthetic')
    app=SyntheticRF2Gateway(db,front,'ab'*32,ORIGIN)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000),headers={'Origin':ORIGIN}) as c:yield c,db,app

def draft(c,category='output_urine',key=True):
    return {'repository':c.get(RF2).json()['repository'],'id':str(uuid4()),'revision':str(uuid4()),'actor':'Synthetic nurse','recorded_at':'2026-10-08T10:00:00Z','chart':{'category':category,'amount':'35.0000' if category!='weight' else '70.0000','unit':'mL' if category!='weight' else 'kg','point':'2026-10-08T09:45:00Z','start':'2026-10-08T09:30:00Z' if category!='weight' else None,'end':'2026-10-08T09:45:00Z' if category!='weight' else None,'acquisition':'measured' if category=='weight' else 'unknown','purpose':'body weight' if category=='weight' else None,'source_context':'Explicit local fictional measurement','uncertainty':'Collection method not verified','source_record':{'issuer_namespace':'clinrx.synthetic.chart','issuer':'nurse-chart-A','record_namespace':'chart-entry','record_id':'urine-0945' if category!='weight' else 'weight-0945','component':'volume' if category!='weight' else 'weight'} if key else None,'new_collection_reason':'New distinct collection' if not key else None},'note':None,'predecessor':None,'reason':None}
def pin(e):
    f=e['fact'];return {'repository':e['repository'],'reference':{'kind':f['kind'],'id':f['id'],'version':f['revision']},'digest':e['digest'],'ingestion':e['ingestion']['ingestion_sequence'],'cutoff':e['cutoff']}
def post(c,path,b):return c.post(RF2+path,json=b)
def saved(c,b):
    v=post(c,'/validate',b);assert v.status_code==200,v.text
    r=post(c,'/save',b);assert r.status_code==200,r.text
    return r.json()['evidence']
def test_chart_correction_replay_and_read_preservation(ws):
    c,db,_=ws;b=draft(c);original=saved(c,b);assert original['fact']['recorded_amount']['value']=='35.0000'
    before=rows(db);fresh=deepcopy(b);fresh['id']=str(uuid4());fresh['revision']=str(uuid4());fresh['actor']='Another recorder'
    r=post(c,'/save',fresh);assert r.status_code==200,r.text;assert r.json()['status']=='source_replay';assert rows(db)==before
    corr=deepcopy(b);corr.update(revision=str(uuid4()),predecessor=pin(original),reason='Transcription correction');corr['chart']['amount']='36.0000';successor=saved(c,corr)
    before=rows(db);r=post(c,'/save',fresh);assert r.status_code==200,r.text;e=r.json()['evidence'];assert e['fact']==original['fact'] and e['superseded'] and e['terminal_reference']['version']==successor['fact']['revision'];assert rows(db)==before
    r=post(c,'/resolve',{'repository':b['repository'],'pins':[pin(original),pin(successor)]});assert r.status_code==200,r.text;assert len(r.json()['items'])==2;assert rows(db)==before

def test_note_mixed_pins_and_weight_purpose(ws):
    c,db,_=ws;w=saved(c,draft(c,'weight'));catalog=c.get(RF2).json();lab0=next(x for x in catalog['combined']['laboratory']['observations'] if x['fact']['id']=='demo-creatinine-A');lab={'repository':catalog['repository'],'fact':lab0['fact'],'digest':lab0['expected_digest'],'ingestion':lab0['ingestion'],'cutoff':catalog['cutoff']['fact_watermark']};before=rows(db)
    note=draft(c);note['chart']=None;note['note']={'question':'Review source records','findings':'Recorded weight and creatinine','possibilities':'No conclusion established','gaps':'Source uncertainty remains','plan':'Unscheduled clinician review','pins':[pin(w),pin(lab)]}
    e=saved(c,note);assert e['metadata']['note']['pins']==note['note']['pins'];assert len(e['fact']['associations'])==2
    assert rows(db)['circulatory_execution']==before['circulatory_execution']
    r=post(c,'/resolve',{'repository':note['repository'],'pins':[pin(w)]});assert r.status_code==200;r=r.json()['items'][0];assert r['metadata']['chart']['acquisition']=='measured'
@pytest.mark.parametrize('field,value',[('issuer','other issuer'),('component','other component'),('record_id','other collection')])
def test_source_record_distinctions(ws,field,value):
    c,_,_=ws;b=draft(c);a=saved(c,b);other=deepcopy(b);other.update(id=str(uuid4()),revision=str(uuid4()));other['chart']['source_record'][field]=value
    e=saved(c,other);assert a['fact']['id']!=e['fact']['id']
def test_conflict_lookup_and_foreign_pin(ws):
    c,db,_=ws;b=draft(c);e=saved(c,b);before=rows(db);bad=deepcopy(b);bad.update(id=str(uuid4()),revision=str(uuid4()));bad['chart']['amount']='99.0'
    assert post(c,'/save',bad).status_code==409;assert rows(db)==before
    r=post(c,'/lookup',b);assert r.status_code==200 and r.json()['evidence']['fact']==e['fact']
    p=pin(e);p['digest']='a'*64;assert post(c,'/resolve',{'repository':b['repository'],'pins':[p]}).status_code==409
    assert rows(db)==before

def test_input_shape_bounds_and_closed_gate(ws):
    c,db,_=ws;b=draft(c);before=rows(db)
    for change in [{'amount':'-1'},{'unit':'kg'},{'start':'2026-10-08T10:00:00Z','end':'2026-10-08T09:00:00Z'},{'point':1.25}]:
        bad=deepcopy(b);bad['chart'].update(change);assert post(c,'/save',bad).status_code==422
    whole=deepcopy(b);whole['chart']['source_record']['component']='whole-record';assert post(c,'/save',whole).status_code==422
    bad=deepcopy(b);bad['chart']['source_record']['record_namespace']='infusion-series';assert post(c,'/save',bad).status_code==422
    assert c.post(RF2+'/save',content='{"repository":"x","repository":"y"}',headers={'Content-Type':'application/json'}).status_code==422
    assert c.post(RF2+'/save',content='x'*65537,headers={'Content-Type':'application/json'}).status_code==413
    assert c.post(RF2+'/save',json=b,headers={'Origin':'https://foreign.example'}).status_code==403
    assert c.post('/api/v1/patients/synthetic-p1/encounters/synthetic-e1/circulatory-review-preparations',json={}).status_code==404
    assert c.get('/health').json()['execution_enabled'] is False
    assert rows(db)==before

@pytest.mark.parametrize('variant',['zero','missing','unplaced','overlap'])
def test_interval_missing_and_zero_are_distinct(ws,variant):
    c,_,_=ws;b=draft(c,key=False)
    if variant=='zero':b['chart']['amount']='0.0000'
    if variant=='missing':b['chart'].update(amount=None,unit=None,missing_reason='Not measured; not zero')
    if variant=='unplaced':b['chart'].update(point=None,start=None,end=None)
    if variant=='overlap':b['chart'].update(start='2026-10-08T09:35:00Z',end='2026-10-08T09:50:00Z',source_context='Overlaps another source interval; accounting unavailable')
    e=saved(c,b);assert e['metadata']['chart']['amount']==b['chart']['amount'];assert e['metadata']['chart']['start']==b['chart']['start']

def test_multiple_source_matches_and_budget_failure_do_not_insert(ws):
    from app.services.renal_fluid_entry_service import RF2Service
    from app.demo.renal_fluid_entry_gateway import service
    from app.api.schemas.renal_fluid_entry import RF2Draft
    from app.persistence.repository import transaction
    from app.persistence.bounded_history import AggregateHistoryBudget
    c,db,app=ws;b=draft(c);saved(c,b)
    # Simulate two upstream owning records with the same key without using the guarded entry route.
    other=deepcopy(b);other.update(id=str(uuid4()),revision=str(uuid4()))
    svc=RF2Service(app.core.state.dependencies)
    with transaction(svc.dependencies.engine) as repo:
        f=svc.build_fact(repo,RF2Draft.model_validate(other),svc.accounting());repo.append_fact(f,target=__import__('app.demo.authoring',fromlist=['TARGET']).TARGET)
    before=rows(db);third=deepcopy(b);third.update(id=str(uuid4()),revision=str(uuid4()));assert post(c,'/save',third).status_code==409;assert rows(db)==before
    app.core.dependency_overrides[service]=lambda:RF2Service(app.core.state.dependencies,aggregate_budget=AggregateHistoryBudget(max_rows=1))
    assert post(c,'/save',third).status_code==422;assert rows(db)==before

def test_weight_dosing_reuse_and_unavailable_historical_acquisition(ws):
    c,db,_=ws;w=saved(c,draft(c,'weight'));before=rows(db)
    r=post(c,'/resolve',{'repository':w['repository'],'pins':[pin(w)]});assert r.status_code==200;assert r.json()['items'][0]['metadata']['chart']['acquisition']=='measured';assert rows(db)==before
    # The already charted dosing weight is carried in the shared assembly, not copied.
    cat=c.get(RF2).json();dose=next(x for x in cat['combined']['circulatory']['assembly']['snapshot']['items'] if x['fact']['id']=='fs-WEIGHT')
    assert not any(x.get('namespace')=='clinrx.local.rf2/v1' for x in dose['fact']['external_evidence'])
    separate=draft(c,'weight',False);separate['chart'].update(acquisition='unknown',purpose='separately asserted dosing weight');e=saved(c,separate);assert e['fact']['id']!=w['fact']['id'] and e['metadata']['chart']['acquisition']=='unknown'

def test_pin_history_stale_correction_and_receipt_preservation(ws):
    c,db,_=ws;b=draft(c,'weight');e=saved(c,b);first=deepcopy(b);first.update(revision=str(uuid4()),predecessor=pin(e),reason='Source transcription correction');first['chart']['amount']='71.0000';later=saved(c,first)
    before=rows(db);stale=deepcopy(first);stale['revision']=str(uuid4());stale['chart']['amount']='72';assert post(c,'/save',stale).status_code in (409,422);assert rows(db)==before
    r=post(c,'/history',{'repository':e['repository'],'pins':[pin(later)]});assert r.status_code==200,r.text;assert [x['fact']['revision'] for x in r.json()['items']]==[e['fact']['revision'],later['fact']['revision']];assert rows(db)==before
    # Reconciliation is lookup-only and retains the exact confirmed request result.
    r=post(c,'/lookup',first);assert r.status_code==200 and r.json()['evidence']['fact']==later['fact'];assert rows(db)==before

def test_aggregate_budget_is_shared_across_individually_valid_pins(ws):
    from app.demo.renal_fluid_entry_gateway import service
    from app.services.renal_fluid_entry_service import RF2Service
    from app.persistence.bounded_history import AggregateHistoryBudget
    c,db,app=ws;u=saved(c,draft(c));w=saved(c,draft(c,'weight'));before=rows(db)
    app.core.dependency_overrides[service]=lambda:RF2Service(app.core.state.dependencies,aggregate_budget=AggregateHistoryBudget(max_rows=3))
    for e in (u,w):assert post(c,'/resolve',{'repository':u['repository'],'pins':[pin(e)]}).status_code==200
    assert post(c,'/resolve',{'repository':u['repository'],'pins':[pin(u),pin(w)]}).status_code==422
    assert rows(db)==before

def test_twelve_pins_fit_and_schema_export_is_current(ws):
    from tools.export_rf2_transport import bundle
    c,_,_=ws;cat=c.get(RF2).json();items=cat['combined']['circulatory']['assembly']['snapshot']['items'][:12]
    pins=[{'repository':cat['repository'],'reference':{'kind':x['fact']['kind'],'id':x['fact']['id'],'version':x['fact']['revision']},'digest':x['expected_digest'],'ingestion':x['ingestion']['ingestion_sequence'],'cutoff':cat['cutoff']['fact_watermark']} for x in items]
    assert len(pins)==12
    b=draft(c);b['chart']=None;b['note']={'question':'Review twelve sources','findings':'Recorded assertions','possibilities':'Not established','gaps':'Unknown source context','plan':'Unscheduled','pins':pins};e=saved(c,b)
    assert len(e['fact']['external_evidence'])==13 and len(e['fact']['associations'])==12
    assert max(len(x['code'].encode()) for x in e['fact']['external_evidence'])<=4096
    assert bundle()==json.loads((Path(__file__).resolve().parents[1]/'frontend/src/api/rf2Schemas.json').read_text())


def test_interval_end_does_not_become_an_unknown_point_observation(ws):
    c,_,_=ws;b=draft(c,key=False);b['chart']['point']=None
    e=saved(c,b);assert e['fact']['occurred']['recorded']['status']=='not_recorded'
    assert e['fact']['occurred']['source_timestamp'] is None
    assert e['fact']['recorded_interval']['end']['source_timestamp']=='2026-10-08T09:45:00Z'
    assert e['metadata']['chart']['point'] is None


@pytest.fixture(scope='module')
def full_seed(tmp_path_factory):
    db=tmp_path_factory.mktemp('rf2-full-seed')/'seed.sqlite3';engine=create_database(db)
    try:bootstrap(engine)
    finally:engine.dispose()
    return db

def test_full_episode_reuse_and_note_preserve_all_originals_and_receipts(tmp_path,full_seed):
    db=tmp_path/'full.sqlite3';shutil.copyfile(full_seed,db);front=tmp_path/'front';(front/'assets').mkdir(parents=True);(front/'index.html').write_text('synthetic')
    app=SyntheticRF2Gateway(db,front,'bc'*32,ORIGIN)
    before=rows(db)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',1),headers={'Origin':ORIGIN}) as c:
        cat=c.get(RF2).json();snapshot=cat['combined']['circulatory']['assembly']['snapshot']['items']
        event=next(x for x in snapshot if x['fact']['id']=='fs-N-CHANGE');pump=next(x for x in snapshot if x['fact']['id']=='fs-PUMP-RATE-N-CHANGE')
        assert event['fact']['source_identifiers'][0]==pump['fact']['source_identifiers'][0]
        assert event['fact']['id']!=pump['fact']['id']
        lab=cat['combined']['laboratory']['observations'][0]
        p={'repository':cat['repository'],'reference':{'kind':lab['fact']['kind'],'id':lab['fact']['id'],'version':lab['fact']['revision']},'digest':lab['expected_digest'],'ingestion':lab['ingestion']['ingestion_sequence'],'cutoff':cat['cutoff']['fact_watermark']}
        assert post(c,'/resolve',{'repository':cat['repository'],'pins':[p]}).status_code==200
        assert rows(db)==before
        b=draft(c);b['chart']=None;b['note']={'question':'Full episode review','findings':'Source creatinine only','possibilities':'Not established','gaps':'Uncertainty retained','plan':'Unscheduled','pins':[p]};saved(c,b)
        assert c.get(RF2).status_code==200
    after=rows(db)
    assert len(before['fact_revision'])==170 and len(before['circulatory_execution'])==2
    assert after['fact_revision'][:-1]==before['fact_revision']
    for name in before:
        if name not in ('fact_revision','sqlite_sequence'):assert after[name]==before[name]
