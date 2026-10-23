"""Real synthetic antibiotic chart persistence and one-cutoff composition."""
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from starlette.staticfiles import StaticFiles
from app.demo.antibiotic_gateway import SyntheticAntibioticGateway,ABX
from app.demo.circulatory import bootstrap
from app.persistence.database import create_database
from app.persistence.repository import transaction

@pytest.fixture
def case(tmp_path):
    database=tmp_path/'synthetic.sqlite3';engine=create_database(database);bootstrap(engine);engine.dispose()
    frontend=tmp_path/'frontend';frontend.mkdir();(frontend/'assets').mkdir();(frontend/'index.html').write_text('<html>test</html>')
    app=SyntheticAntibioticGateway(database,frontend,'a9'*32,'http://127.0.0.1:5290')
    with TestClient(app,base_url='http://127.0.0.1:5290',client=('127.0.0.1',40000)) as client:
        yield client,app

def catalog(client):
    r=client.get(ABX,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z'});assert r.status_code==200,r.text;return r.json()
def draft(repository,**extra):
    return dict(repository=repository,id=str(uuid4()),revision=str(uuid4()),mode='given',medicine='Ceftriaxone',product='Injection',amount='1.00',unit='g',dose_detail='Total product mass',route='IV',schedule=None,indication='Documented from existing medication source',point='2026-10-08T09:00:00Z',actor='Synthetic test nurse',source_record='MAR-'+str(uuid4()),recorded_at='2026-10-21T08:00:00Z',order=None,predecessor=None,predecessor_digest=None,correction_reason=None,**extra)
def post(client,action,body):return client.post(ABX+'/'+action,json=body,headers={'origin':'http://127.0.0.1:5290'})

def test_same_cutoff_durable_administration_exact_recovery_and_correction(case):
    client,app=case;v=catalog(client);assert v['renal']['cutoff']==v['micro']['assembly']['request']['scope']['repository_cutoff'];body=draft(v['renal']['repository'])
    assert post(client,'validate',body).json()['status']=='validated';saved=post(client,'save',body);assert saved.status_code==200,saved.text
    data=saved.json();assert data['fact']['administered_dose']['amount']['value']=='1.00';assert post(client,'lookup',body).json()==data;assert post(client,'save',body).json()==data
    changed={**body,'amount':'2.00','revision':str(uuid4()),'predecessor':{'kind':'antimicrobial_administration','id':body['id'],'version':body['revision']},'predecessor_digest':data['digest'],'correction_reason':'Correct source transcription'}
    corrected=post(client,'save',changed);assert corrected.status_code==200,corrected.text
    assert post(client,'lookup',body).json()==data
    current=catalog(client);items=current['micro']['assembly']['snapshot']['items'];assert next(i for i in items if i['fact']['id']==body['id'])['fact']['revision']==changed['revision']
    history=post(client,'history',{'state_context':current['micro']['state_context'],'reference':{'kind':'antimicrobial_administration','id':body['id'],'version':changed['revision']}})
    assert history.status_code==200,history.text;assert [i['fact']['administered_dose']['amount']['value'] for i in history.json()['items']]==['1.00','2.00']
    conflict={**body,'id':str(uuid4()),'revision':str(uuid4())};assert post(client,'save',conflict).status_code==409
    assert post(client,'save',{**body,'amount':'3'}).status_code==409


def test_prescription_is_not_administration_and_held_has_no_delivered_dose(case):
    client,app=case;v=catalog(client);prescribed={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours'};r=post(client,'save',prescribed);assert r.status_code==200,r.text;assert r.json()['fact']['kind']=='antimicrobial_order'
    held={**draft(v['renal']['repository']),'mode':'held','amount':None,'unit':None,'dose_detail':None,'order':{'kind':'antimicrobial_order','id':prescribed['id'],'version':prescribed['revision']}}
    r=post(client,'save',held);assert r.status_code==200,r.text;assert r.json()['fact']['kind']=='antimicrobial_non_delivery';assert 'administered_dose' not in r.json()['fact']
    assert post(client,'save',{**held,'id':str(uuid4()),'medicine':'Meropenem'}).status_code==409
    assert post(client,'save',{**held,'amount':'1.0','unit':'g','dose_detail':'Total product mass'}).status_code==422

def test_exact_culture_susceptibility_is_retained_with_prescription_draft(case):
    client,app=case
    from app.demo.micro_antimicrobial import facts as micro_facts
    engine=create_database(app.config.database_path)
    with transaction(engine) as repo:
        from app.demo.patient_state import TARGET
        for fact in micro_facts():repo.append_fact(fact,target=TARGET)
    engine.dispose();v=catalog(client);items=v['micro']['assembly']['snapshot']['items']
    ast=next(i['fact'] for i in items if i['fact']['kind']=='microbiology_susceptibility')
    body={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours','culture_ref':{'kind':ast['kind'],'id':ast['id'],'version':ast['revision']}}
    saved=post(client,'save',body);assert saved.status_code==200,saved.text
    fact=saved.json()['fact'];metadata=next(i for i in fact['source_identifiers'] if i['namespace']=='clinrx.local.antibiotic-chart/v1')
    import json
    assert json.loads(metadata['code'])['culture_ref']==body['culture_ref']
    assert post(client,'save',{**draft(v['renal']['repository']),'culture_ref':{'kind':'microbiology_culture','id':'wrong-kind','version':'1'}}).status_code==422
    assert post(client,'save',{**draft(v['renal']['repository']),'culture_ref':{'kind':'microbiology_susceptibility','id':'missing','version':'1'}}).status_code==404


def test_invalid_dose_scope_and_gateway_origin_do_not_append(case):
    client,app=case;v=catalog(client);before=v['renal']['cutoff']['fact_watermark'];body=draft(v['renal']['repository'])
    for change in ({'amount':'0'},{'point':'2026-10-08T09:00:00'},{'repository':str(uuid4())},{'dose_detail':None}):assert post(client,'save',{**body,**change}).status_code in (409,422)
    assert client.post(ABX+'/save',json=body,headers={'origin':'http://elsewhere.example'}).status_code==403
    assert catalog(client)['renal']['cutoff']['fact_watermark']==before

def test_correction_preserves_owner_identity_and_rejects_stale_predecessor(case):
    client,app=case;v=catalog(client);body=draft(v['renal']['repository']);saved=post(client,'save',body).json()
    corrected={**body,'amount':'2','revision':str(uuid4()),'predecessor':{'kind':'antimicrobial_administration','id':body['id'],'version':body['revision']},'predecessor_digest':saved['digest'],'correction_reason':'Synthetic correction'}
    assert post(client,'save',{**corrected,'predecessor_digest':'0'*64}).status_code==409
    assert post(client,'save',corrected).status_code==200
    assert post(client,'save',{**corrected,'revision':str(uuid4()),'amount':'3'}).status_code==409
    assert post(client,'lookup',body).json()['fact']['administered_dose']['amount']['value']=='1.00'

def test_production_api_does_not_expose_candidate_routes(case):
    client,app=case
    from app.main import create_app
    with TestClient(create_app(app.config)) as production:
        assert production.get(ABX,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z'}).status_code==404
