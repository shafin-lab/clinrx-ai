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


def candidate_context(repository):
    return {'version':'CandidateDoseReview/v1','profile_version':'test-profile','source':'https://idmp.ucsf.edu/content/ceftriaxone',
        'suggestion':{'medicine':'Ceftriaxone','amount':'2','unit':'g','route':'IV','schedule':'Every 24 hours','initial':None,'band':'CrCl 38'},
        'inputs':{'age':'62','weight':'74','creatinine':'2.1','factor':'male'},'crcl':38.17460317460317,
        'context':{'indication':'standard','infusion':'short','phase':'maintenance','bodySize':'standard','hepatic':'reviewed','special':'none','safetyReviewed':True,'renalFunction':'stable','support':'none','cvvhMode':'','flow':'','flowDefinitionReviewed':False,'residual':'','downtime':'','hdFlux':'','hdStable':'','hdInterval':'','hdTimingReviewed':False},
        'basis':'empiric','scope':{'repository':repository,'patient':'synthetic-p1','encounter':'synthetic-e1','cutoff':0,'start':'2026-10-08T08:00:00Z','end':'2026-10-08T10:00:00Z'},'sources':[]}

def test_candidate_context_can_pin_shared_patient_context_and_exact_lab_component():
    from app.api.schemas.antibiotic_chart import DoseReview
    from app.persistence.canonical import canonical_payload
    import json
    review=candidate_context(str(uuid4()));review['scope']['cutoff']=20
    review['sources']=[
        {'role':'patient_context','reference':{'kind':'circulatory_event','id':'ctx','version':'1'},'digest':'a'*64,'ingestion':10},
        {'role':'creatinine','reference':{'kind':'laboratory_report','id':'panel','version':'1'},'digest':'b'*64,'ingestion':11,'component':'serum-cr'}]
    parsed=DoseReview.model_validate(review)
    assert json.loads(canonical_payload(parsed))==review
    with pytest.raises(ValueError):DoseReview.model_validate({**review,'sources':[{**review['sources'][0],'reference':{'kind':'observation','id':'wrong','version':'1'}}]})
    with pytest.raises(ValueError):DoseReview.model_validate({**review,'sources':[{**review['sources'][1],'component':''}]})

def test_serum_creatinine_is_a_supported_explicit_lab_mapping():
    from app.models.clinical.laboratory import LaboratoryComponent
    item=LaboratoryComponent.model_validate({'source_component_id':'cr','test_code':{'namespace':'source.lab','code':'CREAT','raw_display':'Creatinine'},'mapping_status':'mapped','mapped_concept':'creatinine','mapping_version':'clinrx-shared-labs/2','result':{'kind':'numeric','comparator':'=','raw_value':'3.0','unit':{'namespace':'UCUM','code':'mg/dL','raw_display':'mg/dL'}}})
    assert item.mapped_concept=='creatinine'

def test_explicit_new_dose_review_correction_keeps_original_review_in_history(case):
    from copy import deepcopy
    client,_=case;v=catalog(client);review=candidate_context(v['renal']['repository']);review['scope']['cutoff']=v['renal']['cutoff']['fact_watermark']
    original={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours','dose_review':review}
    saved=post(client,'save',original);assert saved.status_code==200,saved.text
    updated=deepcopy(review);updated['suggestion']['amount']='1'
    correction={**original,'revision':str(uuid4()),'amount':'1','dose_review':updated,'dose_review_amendment':True,'predecessor':{'kind':'antimicrobial_order','id':original['id'],'version':original['revision']},'predecessor_digest':saved.json()['digest'],'correction_reason':'Reviewed dose after changed patient evidence'}
    result=post(client,'save',correction);assert result.status_code==200,result.text
    assert post(client,'lookup',original).json()['request_canonical']==saved.json()['request_canonical']
    assert result.json()['fact']['prescribed_dose']['amount']['value']=='1'

def test_optional_candidate_context_preserves_absent_canonical_and_explicit_null():
    import json
    from app.api.schemas.antibiotic_chart import AntibioticDraft
    from app.persistence.canonical import canonical_payload
    body=draft(str(uuid4()),culture_ref=None)
    assert json.loads(canonical_payload(AntibioticDraft.model_validate(body)))==body
    assert json.loads(canonical_payload(AntibioticDraft.model_validate({**body,'dose_review':None})))=={**body,'dose_review':None}

def test_candidate_context_retained_through_save_retry_reload_and_correction(case):
    import json
    client,app=case;v=catalog(client);review=candidate_context(v['renal']['repository']);review['scope']['cutoff']=v['renal']['cutoff']['fact_watermark']
    body={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours','dose_review':review}
    response=post(client,'validate',body);assert response.status_code==200,response.text
    saved=post(client,'save',body);assert saved.status_code==200,saved.text
    data=saved.json();assert data['execution_enabled'] is False
    assert json.loads(data['request_canonical'])['dose_review']==review
    assert post(client,'lookup',body).json()==data;assert post(client,'save',body).json()==data
    corrected={**body,'amount':'3','revision':str(uuid4()),'predecessor':{'kind':'antimicrobial_order','id':body['id'],'version':body['revision']},'predecessor_digest':data['digest'],'correction_reason':'Final field correction'}
    response=post(client,'save',corrected);assert response.status_code==200,response.text
    assert json.loads(response.json()['request_canonical'])['dose_review']['suggestion']['amount']=='2'
    fact=next(i['fact'] for i in catalog(client)['micro']['assembly']['snapshot']['items'] if i['fact']['id']==body['id'])
    assert json.loads(next(c['code'] for c in fact['source_identifiers'] if c['namespace']=='clinrx.local.antibiotic-chart/v1'))['dose_review']==review

def test_invalid_candidate_context_never_appends(case):
    from copy import deepcopy
    client,app=case;v=catalog(client);before=v['renal']['cutoff']['fact_watermark'];review=candidate_context(v['renal']['repository']);review['scope']['cutoff']=before
    for change in ('version','oversize','scope','pin','future'):
        bad=deepcopy(review)
        if change=='version':bad['version']='validated-policy'
        if change=='oversize':bad['suggestion']['schedule']='x'*5000
        if change=='scope':bad['scope']['repository']=str(uuid4())
        if change=='pin':bad['sources']=[{'role':'weight','reference':{'kind':'observation','id':'missing','version':'1'},'digest':'0'*64,'ingestion':1}]
        if change=='future':bad['scope']['cutoff']=before+1000
        response=post(client,'save',{**draft(v['renal']['repository']),'mode':'prescription','schedule':'daily','dose_review':bad})
        assert response.status_code in (404,409,422),response.text
    assert catalog(client)['renal']['cutoff']['fact_watermark']==before


def test_five_source_candidate_metadata_bound_includes_complete_request():
    from app.api.schemas.antibiotic_chart import AntibioticDraft
    from app.persistence.canonical import canonical_payload
    from app.services.antibiotic_chart_service import build_fact
    from pydantic import ValidationError
    repository=str(uuid4());review=candidate_context(repository);review['scope']['cutoff']=100;review['basis']='ast'
    review['sources']=[{'role':role,'reference':{'kind':kind,'id':str(uuid4()),'version':str(uuid4())},'digest':'a'*64,'ingestion':1} for role,kind in [('weight','circulatory_event'),('creatinine','observation'),('ast','microbiology_susceptibility'),('isolate','microbiology_isolate'),('specimen','microbiology_specimen')]]
    body={**draft(repository),'mode':'prescription','schedule':'Every 24 hours','culture_ref':review['sources'][2]['reference'],'dose_review':review}
    model=AntibioticDraft.model_validate(body);size=len(canonical_payload(model).encode());assert size<4096,size
    assert build_fact(model).source_identifiers[0].code==canonical_payload(model)
    # Each field stays within its own bound, but their aggregate must still fail.
    oversized={**body,'product':'x'*256,'indication':'x'*1000,'actor':'x'*256,'source_record':'x'*256}
    with pytest.raises(ValidationError,match='metadata exceeds'):AntibioticDraft.model_validate(oversized)


def test_legacy_fixture_canonical_request_fact_and_digest_are_byte_identical():
    import json
    from hashlib import sha256
    from app.api.schemas.antibiotic_chart import AntibioticDraft
    from app.persistence.canonical import canonical_payload
    from app.services.antibiotic_chart_service import build_fact
    fixture=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/antibiotic-workflow.json').read_text())
    body=AntibioticDraft.model_validate(fixture['draft']);reply=fixture['validated']
    assert canonical_payload(body)==reply['request_canonical']
    assert sha256(canonical_payload(body).encode()).hexdigest()==reply['request_digest']
    original_code=next(c['code'] for c in reply['fact']['source_identifiers'] if c['namespace']=='clinrx.local.antibiotic-chart/v1')
    # This older fixture predates culture_ref. Historical reconstruction must retain
    # those original metadata bytes as well as the newer optional field's absence.
    original=build_fact(body,metadata_payload=original_code)
    assert canonical_payload(original)==reply['canonical_fact']
    assert sha256(canonical_payload(original).encode()).hexdigest()==reply['digest']

def test_exact_candidate_source_mismatch_staleness_and_historical_correction(case):
    from copy import deepcopy
    from app.models.clinical.facts import ClinicalObservation
    from app.models.clinical.common import Reference
    from app.demo.patient_state import TARGET
    client,app=case;v=catalog(client);obs=v['renal']['combined']['laboratory']['observations'][0];fact=obs['fact'];review=candidate_context(v['renal']['repository']);review['scope']['cutoff']=v['renal']['cutoff']['fact_watermark']
    review['sources']=[{'role':'creatinine','reference':{'kind':fact['kind'],'id':fact['id'],'version':fact['revision']},'digest':obs['expected_digest'],'ingestion':obs['ingestion']['ingestion_sequence']}]
    body={**draft(v['renal']['repository']),'mode':'prescription','schedule':'Every 24 hours','dose_review':review}
    bad=deepcopy(body);bad['dose_review']['sources'][0]['digest']='0'*64
    assert post(client,'validate',bad).status_code==409
    saved=post(client,'save',body);assert saved.status_code==200,saved.text;saved=saved.json()
    engine=create_database(app.config.database_path)
    with transaction(engine) as repo:
        old=repo.load_fact(Reference.model_validate(review['sources'][0]['reference']),target=TARGET).fact
        repo.append_revision(ClinicalObservation.model_validate({**old.model_dump(),'revision':'source-correction','supersedes':old.reference,'correction_reason':'Correct recorded creatinine'}),target=TARGET)
    engine.dispose()
    new={**body,'id':str(uuid4()),'revision':str(uuid4()),'source_record':'NEW-'+str(uuid4())}
    assert post(client,'validate',new).status_code==409
    correction={**body,'revision':str(uuid4()),'amount':'3','predecessor':{'kind':'antimicrobial_order','id':body['id'],'version':body['revision']},'predecessor_digest':saved['digest'],'correction_reason':'Correct final fields only'}
    altered=deepcopy(correction);altered['dose_review']['suggestion']['amount']='3'
    assert post(client,'validate',altered).status_code==409
    response=post(client,'save',correction);assert response.status_code==200,response.text
    assert response.json()['execution_enabled'] is False
    assert post(client,'lookup',body).json()==saved

def test_course_history_includes_previous_days_at_original_cutoff_and_excludes_future(case):
    client,_=case;v=catalog(client);repository=v['renal']['repository']
    order={**draft(repository),'mode':'prescription','point':'2026-10-08T08:30:00Z','schedule':'Every 24 hours'}
    assert post(client,'save',order).status_code==200
    reference={'kind':'antimicrobial_order','id':order['id'],'version':order['revision']}
    for at in ('2026-10-06T09:00:00Z','2026-10-08T11:00:00Z'):
        assert post(client,'save',{**draft(repository),'point':at,'order':reference}).status_code==200
    selected=catalog(client);before=selected['renal']['cutoff']['fact_watermark']
    assert post(client,'save',{**draft(repository),'point':'2026-10-07T09:00:00Z','order':reference}).status_code==200
    response=post(client,'course-history',{'state_context':selected['micro']['state_context'],'reference':reference})
    assert response.status_code==200,response.text
    state=response.json();assert state['assembly']['request']['scope']['repository_cutoff']['fact_watermark']==before
    times=[i['fact'].get('administered',{}).get('value') for i in state['assembly']['snapshot']['items']]
    assert '2026-10-06T09:00:00Z' in times
    assert '2026-10-08T11:00:00Z' not in times
    assert '2026-10-07T09:00:00Z' not in times
    assert catalog(client)['renal']['cutoff']['fact_watermark']==before+1
