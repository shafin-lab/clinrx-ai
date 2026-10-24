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


def test_owned_correction_retains_only_its_exact_historical_culture_reference(case):
    import json
    from app.demo.micro_antimicrobial import facts as micro_facts
    from app.demo.patient_state import TARGET
    from app.models.clinical.microbiology import SusceptibilityResult
    client,app=case
    engine=create_database(app.config.database_path)
    with transaction(engine) as repo:
        for fact in micro_facts():repo.append_fact(fact,target=TARGET)
        ast=next(fact for fact in micro_facts() if fact.kind=='microbiology_susceptibility')
        other_ast=SusceptibilityResult.model_validate({**ast.model_dump(),'id':'other-historical-ast'})
        repo.append_fact(other_ast,target=TARGET)
    v=catalog(client)
    original={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours','culture_ref':ast.reference.model_dump()}
    response=post(client,'save',original);assert response.status_code==200,response.text
    saved=response.json()
    with transaction(engine) as repo:
        successor=SusceptibilityResult.model_validate({**ast.model_dump(),'revision':'2','supersedes':ast.reference,'correction_reason':'Synthetic corrected AST','report':{**ast.report.model_dump(),'change':'corrected'},'interpretation':{**ast.interpretation.model_dump(),'raw':'R','category':'resistant'}})
        repo.append_revision(successor,target=TARGET)
        repo.append_revision(SusceptibilityResult.model_validate({**successor.model_dump(),'id':other_ast.id,'supersedes':other_ast.reference}),target=TARGET)
    correction={**original,'revision':str(uuid4()),'amount':'2','predecessor':{'kind':'antimicrobial_order','id':original['id'],'version':original['revision']},'predecessor_digest':saved['digest'],'correction_reason':'Correct source transcription, retain historical citation'}
    # New sources and corrections to sources without this citation cannot adopt stale AST.
    assert post(client,'validate',{**original,'id':str(uuid4()),'revision':str(uuid4()),'source_record':'NEW-'+str(uuid4())}).status_code==409
    unrelated=draft(v['renal']['repository']);other=post(client,'save',unrelated).json()
    assert post(client,'validate',{**unrelated,'revision':str(uuid4()),'culture_ref':original['culture_ref'],'predecessor':{'kind':'antimicrobial_administration','id':unrelated['id'],'version':unrelated['revision']},'predecessor_digest':other['digest'],'correction_reason':'Cannot add historical citation'}).status_code==409
    for invalid in ({'predecessor_digest':'0'*64},{'id':str(uuid4())},{'predecessor':{'kind':'antimicrobial_administration','id':unrelated['id'],'version':unrelated['revision']}}):
        assert post(client,'validate',{**correction,**invalid}).status_code in (409,422)
    assert post(client,'validate',{**correction,'culture_ref':other_ast.reference.model_dump()}).status_code==409
    # A foreign source with the exact same historical citation cannot gain ownership.
    from hashlib import sha256
    from app.persistence.canonical import canonical_payload
    from app.services.antibiotic_chart_service import build_fact
    from app.api.schemas.antibiotic_chart import AntibioticDraft
    foreign_body={**original,'id':str(uuid4()),'revision':str(uuid4()),'source_record':'FOREIGN-'+str(uuid4())}
    foreign=build_fact(AntibioticDraft.model_validate(foreign_body)).model_copy(update={'source_identifiers':()})
    with transaction(engine) as repo:repo.append_fact(foreign,target=TARGET)
    foreign_correction={**foreign_body,'revision':str(uuid4()),'predecessor':foreign.reference.model_dump(),'predecessor_digest':sha256(canonical_payload(foreign).encode()).hexdigest(),'correction_reason':'Foreign source remains read-only'}
    assert post(client,'validate',foreign_correction).status_code==409
    accepted=post(client,'validate',correction);assert accepted.status_code==200,accepted.text
    result=post(client,'save',correction);assert result.status_code==200,result.text
    assert post(client,'save',correction).json()==result.json()
    assert post(client,'lookup',original).json()==saved
    assert post(client,'validate',{**correction,'revision':str(uuid4()),'amount':'3'}).status_code==409
    metadata=next(c for c in result.json()['fact']['source_identifiers'] if c['namespace']=='clinrx.local.antibiotic-chart/v1')
    assert json.loads(metadata['code'])['culture_ref']==original['culture_ref']
    current=catalog(client)
    history=post(client,'history',{'state_context':current['micro']['state_context'],'reference':{'kind':'antimicrobial_order','id':original['id'],'version':correction['revision']}})
    assert history.status_code==200,history.text
    assert [i['fact']['revision'] for i in history.json()['items']]==[original['revision'],correction['revision']]
    assert [i['fact']['correction_reason'] for i in history.json()['items']]==[None,correction['correction_reason']]
    engine.dispose()
