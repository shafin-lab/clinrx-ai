"""M10 exact source workflow and conservative exposure accounting."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.demo.transfusion_gateway import SyntheticM10Gateway,M10
from app.demo.circulatory import bootstrap
from app.persistence.database import create_database

@pytest.fixture
def case(tmp_path):
    database=tmp_path/'synthetic.sqlite3';engine=create_database(database);bootstrap(engine);engine.dispose()
    frontend=tmp_path/'frontend';frontend.mkdir();(frontend/'assets').mkdir();(frontend/'index.html').write_text('<html>test</html>')
    app=SyntheticM10Gateway(database,frontend,'a9'*32,'http://127.0.0.1:5290')
    with TestClient(app,base_url='http://127.0.0.1:5290',client=('127.0.0.1',40000)) as client:yield client,app

def catalog(client,end='2026-10-08T10:00:00Z'):
    r=client.get(M10,params={'review_start':'2026-10-08T08:00:00Z','review_end':end});assert r.status_code==200,r.text;return r.json()
def draft(repository,kind='transfusion_administration',data=None,**extra):
    return dict(repository=repository,command_id=str(uuid4()),id=str(uuid4()),revision=str(uuid4()),kind=kind,source_record=str(uuid4()),source_issuer='synthetic-blood-bank',actor='Synthetic nurse',recorded_at='2026-10-08T09:30:00Z',available_at='2026-10-08T09:30:00Z',patient_id='synthetic-p1',encounter_id='synthetic-e1',data=data or {'title':'PRBC given','product':{'family':'prbc','preparation':'PRBC','label':'Leukodepleted red cells','modifications':[{'name':'leukodepleted','value':'yes','source':'bag label'},{'name':'irradiated','value':'unknown','source':'not documented'}]},'delivery_id':str(uuid4()),'status':'completed','amounts':[{'dimension':'count','value':'2','unit':'units','basis':'PRBC units'},{'dimension':'volume','value':'500','unit':'mL','basis':'actual administered'}],'indication':'Recorded blood loss','occurred':{'status':'known','precision':'instant','value':'2026-10-08T09:00:00Z'}},**extra)
def post(client,action,body):return client.post(M10+'/'+action,json=body,headers={'origin':'http://127.0.0.1:5290'})
def save(client,body):
    r=post(client,'save',body);assert r.status_code==200,r.text;return r.json()
def pin(saved):return {'reference':{'kind':saved['fact']['kind'],'id':saved['fact']['id'],'version':saved['fact']['revision']},'digest':saved['digest']}
def correction(body,saved,**data):
    return {**body,'command_id':str(uuid4()),'revision':str(uuid4()),'predecessor':pin(saved)['reference'],'predecessor_digest':saved['digest'],'correction_reason':'Correct original source','data':{**body['data'],**data}}

def bounded_catalog(client,repository,cutoff):
    return client.get(M10,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z','repository':repository,'cutoff':cutoff})

def test_bounded_catalog_excludes_corrections_committed_after_selected_watermark(case):
    c,_=case;b=draft(catalog(c)['repository']);s=save(c,b);before=catalog(c)
    changed=correction(b,s,amounts=[{'dimension':'count','value':'1','unit':'units','basis':'PRBC units'}]);save(c,changed)
    response=bounded_catalog(c,b['repository'],before['cutoff']['fact_watermark'])
    assert response.status_code==200,response.text
    view=response.json();assert view['cutoff']['fact_watermark']==before['cutoff']['fact_watermark']
    assert view['repository']==before['repository']
    assert view['items'][0]['fact']['revision']==b['revision']
    assert view['totals']['groups'][0]['known_subtotal']=='2'

@pytest.mark.parametrize('scope',['repository_only','cutoff_only','negative','future','foreign'])
def test_bounded_catalog_rejects_partial_or_invalid_scope(case,scope):
    c,_=case;view=catalog(c);params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z','repository':view['repository'],'cutoff':view['cutoff']['fact_watermark']}
    if scope=='repository_only':params.pop('cutoff')
    elif scope=='cutoff_only':params.pop('repository')
    elif scope=='negative':params['cutoff']=-1
    elif scope=='future':params['cutoff']+=1
    else:params['repository']=str(uuid4())
    response=c.get(M10,params=params)
    assert response.status_code==(409 if scope in ('future','foreign') else 422),response.text

def test_durable_command_recovery_correction_and_cutoff(case):
    c,_=case;b=draft(catalog(c)['repository']);s=save(c,b)
    assert post(c,'lookup',b).json()==s
    assert post(c,'save',b).json()==s
    assert post(c,'save',{**b,'data':{**b['data'],'status':'stopped'}}).status_code==409
    before=catalog(c);changed=correction(b,s,amounts=[{'dimension':'count','value':'1','unit':'units','basis':'PRBC units'}]);changed['available_at']='2026-10-08T11:00:00Z';save(c,changed)
    assert catalog(c)['items'][0]['fact']['revision']==b['revision']
    assert catalog(c,'2026-10-08T12:00:00Z')['items'][0]['fact']['revision']==changed['revision']
    assert post(c,'lookup',b).json()==s
    assert post(c,'save',correction(b,s,status='stopped')).status_code==409
    h=post(c,'history',{'repository':b['repository'],'reference':pin(s)['reference'],'cutoff':before['cutoff']['fact_watermark'],'review_end':'2026-10-08T10:00:00Z'});assert h.status_code==200,h.text;assert len(h.json()['items'])==1

def test_foreign_scope_and_not_given_fail_before_write(case):
    c,_=case;b=draft(catalog(c)['repository']);before=catalog(c)['cutoff']['fact_watermark']
    assert post(c,'save',{**b,'patient_id':'another-patient'}).status_code in (409,422)
    assert post(c,'save',{**b,'data':{**b['data'],'status':'not_given'}}).status_code==422
    assert post(c,'save',{**b,'recorded_at':'1e9'}).status_code==422
    assert post(c,'save',{**b,'recorded_at':None}).status_code==422
    assert catalog(c)['cutoff']['fact_watermark']==before

def test_lifecycle_and_component_bases_are_independent(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);save(c,b)
    r=draft(repo,'transfusion_request',{'title':'Request','product':b['data']['product'],'indication':'bleeding','quantities':[{'dimension':'count','value':'4','unit':'units','basis':'PRBC units'}]});save(c,r)
    totals=catalog(c)['totals'];assert next(x for x in totals['groups'] if x['dimension']=='count')['known_subtotal']=='2'
    stopped=draft(repo);stopped['data'].update(status='stopped',amounts=[{'dimension':'volume','value':'90','unit':'mL','basis':'actual administered'}]);save(c,stopped)
    assert next(x for x in catalog(c)['totals']['groups'] if x['dimension']=='volume')['known_subtotal']=='590'

def test_aggregate_coverage_pins_prevent_duplicate_count(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);b['data']['grain']='reported_aggregate';b['data']['amounts']=[{'dimension':'count','value':'4','unit':'units','basis':'PRBC units'}];a=save(c,b)
    bags=[]
    for _ in range(2):
        x=draft(repo);x['data']['amounts']=[{'dimension':'count','value':'1','unit':'units','basis':'PRBC units'}];bags.append(save(c,x))
    link=draft(repo,'transfusion_coverage_link',{'title':'Verified aggregate coverage','aggregate':pin(a),'constituents':[pin(x) for x in bags],'relationship':'included_in_aggregate','basis':'PRBC units'});save(c,link)
    assert catalog(c)['totals']['groups'][0]['known_subtotal']=='4'
    save(c,correction(b,a,amounts=[{'dimension':'count','value':'5','unit':'units','basis':'PRBC units'}]))
    assert catalog(c)['totals']['complete'] is False

def test_vet_patch_preserves_previous_and_full_replacement_omits(case):
    c,_=case;repo=catalog(c)['repository'];data={'title':'ROTEM','device':'ROTEM sigma','profile_id':'custom-capture','profile_version':'1','cartridge':'Complete','run_id':'run-1','report_status':'preliminary','observations':[{'id':'ct','assay':'EXTEM C','parameter':'CT','state':'final','value':'60','unit':'s'},{'id':'a5','assay':'EXTEM C','parameter':'A5','state':'preliminary','value':'40','unit':'mm'}]};b=draft(repo,'viscoelastic_report',data);s=save(c,b)
    patch=correction(b,s,update_mode='patch',base_digest=s['digest'],observations=[{'id':'a10','assay':'EXTEM C','parameter':'A10','state':'preliminary','value':'45','unit':'mm'}]);sp=save(c,patch)
    assert {x['id'] for x in sp['fact']['data']['observations']}=={'ct','a5','a10'}
    full=correction(patch,sp,update_mode='full',base_digest=None,observations=[{'id':'ct','assay':'EXTEM C','parameter':'CT','state':'final','value':'61','unit':'s'}]);sf=save(c,full);assert len(sf['fact']['data']['observations'])==1
    assert post(c,'save',{**patch,'command_id':str(uuid4()),'revision':str(uuid4())}).status_code==409

def test_suspected_aggregate_overlap_and_excess_constituents(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);b['data']['grain']='reported_aggregate';b['data']['amounts']=[{'dimension':'count','value':'4','unit':'units','basis':'PRBC units'}];aggregate=save(c,b)
    x=draft(repo);x['data']['amounts']=[{'dimension':'count','value':'5','unit':'units','basis':'PRBC units'}];part=save(c,x)
    totals=catalog(c)['totals'];assert totals['complete'] is False;assert not totals['groups']
    link=draft(repo,'transfusion_coverage_link',{'title':'Impossible coverage','aggregate':pin(aggregate),'constituents':[pin(part)],'relationship':'included_in_aggregate','basis':'PRBC units'})
    assert post(c,'save',link).status_code==409

def test_atomic_medication_completion_is_one_delivery(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo,'haemostatic_medication_course');b['data'].update(product={'family':'pcc','preparation':'Four factor PCC','label':'Synthetic PCC','factor_basis':'factor IX'},amounts=[{'dimension':'dose','value':'1000','unit':'IU','basis':'factor IX'}],status='in_progress')
    first=save(c,b);next_body=correction(b,first,status='completed',promote_to_medication=True);second=save(c,next_body)
    assert second['fact']['data']['completed_as']['reference']['kind']=='medication_administration'
    view=catalog(c);assert len(view['medication_exposures'])==1;assert view['medication_exposures'][0]['owner']=='medication_administration'
    assert view['totals']['groups'][0]['known_subtotal']=='1000'
    assert post(c,'lookup',next_body).json()==second

def test_duplicate_json_and_oversized_request_rejected(case):
    c,_=case
    h={'origin':'http://127.0.0.1:5290','content-type':'application/json'}
    assert c.post(M10+'/save',content='{"kind":"a","kind":"b"}',headers=h).status_code==422
    assert c.post(M10+'/save',content='x'*262145,headers=h).status_code==413

def test_attachment_must_be_pinned_in_visible_report(case):
    import base64,hashlib
    c,_=case;repo=catalog(c)['repository'];raw=b'Original synthetic report';h=hashlib.sha256(raw).hexdigest()
    r=post(c,'attachments',{'repository':repo,'digest':h,'media_type':'text/plain','data_base64':base64.b64encode(raw).decode()});assert r.status_code==200,r.text
    params={'repository':repo,'cutoff':catalog(c)['cutoff']['fact_watermark'],'review_end':'2026-10-08T10:00:00Z'}
    assert c.get(M10+'/attachments/'+h,params=params).status_code==404
    b=draft(repo,'viscoelastic_report',{'title':'Original report','device':'Other','profile_id':'capture-only','profile_version':'1','cartridge':'Source cartridge','run_id':'run-a','report_status':'final','attachment_digests':[h],'observations':[{'id':'comment','assay':'source','parameter':'comment','result_type':'narrative','raw_value':'Clot appearance source note','state':'final'}]});save(c,b)
    params['cutoff']=catalog(c)['cutoff']['fact_watermark'];r=c.get(M10+'/attachments/'+h,params=params);assert r.status_code==200,r.text;assert r.content==raw

def test_evaluate_uses_stored_values_and_assessment_rechecks_source(case):
    from app.services.m10_profiles import device_profiles,protocol_profiles
    c,_=case;repo=catalog(c)['repository'];device=device_profiles()[0];channel=device['channels'][0];parameter=channel['parameters'][0]
    b=draft(repo,'viscoelastic_report',{'title':'TEG source','device':device['device'],'profile_id':device['id'],'profile_version':device['version'],'cartridge':device['configuration'],'run_id':'run-a','report_status':'final','observations':[{'id':'r','assay':channel['assay'],'parameter':parameter['name'],'value':'9','unit':parameter['unit'],'state':'final'}]});s=save(c,b)
    request={'repository':repo,'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','cutoff':catalog(c)['cutoff']['fact_watermark'],'review_end':'2026-10-08T10:00:00Z','device_profile_id':device['id'],'protocol_profile_id':protocol_profiles()[0]['id'],'context':{},'observations':[{'id':'r','value':'999','source_ref':{**pin(s)['reference'],'digest':s['digest']}}]}
    result=post(c,'evaluate',request);assert result.status_code==200,result.text;result=result.json();assert result['observations'][0]['value']=='9'
    a=draft(repo,'m10_assessment',{'title':'Review','findings':'Reviewed report','decision':'Clinical review','rationale':'Synthetic review','plan':'Reassess','interpretation':result});saved=save(c,a)
    assert saved['fact']['data']['interpretation']['signature']==result['signature']
    altered={**result,'options':[{'product':'fabricated'}]};assert post(c,'save',{**draft(repo,'m10_assessment',{**a['data'],'interpretation':altered})}).status_code==409
    save(c,correction(b,s,observations=[{'id':'r','assay':channel['assay'],'parameter':parameter['name'],'value':'10','unit':parameter['unit'],'state':'final'}]))
    assert post(c,'save',draft(repo,'m10_assessment',a['data'])).status_code==409

def test_multiple_coverage_links_cannot_overallocate_parent(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);b['data']['grain']='reported_aggregate';b['data']['amounts']=[{'dimension':'count','value':'4','unit':'units','basis':'PRBC units'}];a=save(c,b)
    bags=[]
    for _ in range(2):
        p=draft(repo);p['data']['amounts']=[{'dimension':'count','value':'3','unit':'units','basis':'PRBC units'}];bags.append(save(c,p))
    def link(p):return draft(repo,'transfusion_coverage_link',{'title':'Coverage','aggregate':pin(a),'constituents':[pin(p)],'relationship':'included_in_aggregate','basis':'PRBC units'})
    save(c,link(bags[0]));assert post(c,'save',link(bags[1])).status_code==409

def test_interval_boundaries_spanning_and_unknown_time(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);b['data']['occurred']['value']='2026-10-08T10:00:00Z';b['recorded_at']='2026-10-08T10:00:00Z';b['available_at']='2026-10-08T10:00:00Z';save(c,b)
    assert not catalog(c)['totals']['groups']
    x=draft(repo);x['data'].update(started={'status':'known','precision':'instant','value':'2026-10-08T07:30:00Z'},ended={'status':'known','precision':'instant','value':'2026-10-08T08:30:00Z'});save(c,x)
    totals=catalog(c)['totals'];assert len(totals['spanning'])==1;assert not totals['groups']
    y=draft(repo);y['data']['occurred']={'status':'known','precision':'day','value':'2026-10-08T00:00:00Z'};save(c,y)
    assert any('time unavailable' in x['reason'] for x in catalog(c)['totals']['excluded'])

def test_stale_profile_and_omitted_counterevidence(case):
    from app.services.m10_profiles import device_profiles,protocol_profiles
    c,_=case;repo=catalog(c)['repository'];device=device_profiles()[0]
    obs=[{'id':'r','assay':'K','parameter':'R','value':'9','unit':'min','state':'final'},{'id':'kh','assay':'KH','parameter':'R','value':'3','unit':'min','state':'final'},{'id':'ly','assay':'K','parameter':'LY30','value':'8','unit':'%','state':'final'}]
    b=draft(repo,'viscoelastic_report',{'title':'All channels','device':device['device'],'profile_id':device['id'],'profile_version':device['version'],'cartridge':device['configuration'],'run_id':'run-a','report_status':'final','observations':obs});s=save(c,b)
    request={'repository':repo,'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','cutoff':catalog(c)['cutoff']['fact_watermark'],'review_end':'2026-10-08T10:00:00Z','device_profile_id':device['id'],'protocol_profile_id':protocol_profiles()[0]['id'],'context':{},'observations':[{'id':'r','source_ref':{**pin(s)['reference'],'digest':s['digest']}}]}
    r=post(c,'evaluate',request);assert r.status_code==200,r.text;assert len(r.json()['observations'])==3;assert next(o for o in r.json()['observations'] if o['id']=='ly')['status']=='pending'
    b2=correction(b,s,profile_version='old-unsupported');s2=save(c,b2);request['cutoff']=catalog(c)['cutoff']['fact_watermark'];request['observations'][0]['source_ref']={**pin(s2)['reference'],'digest':s2['digest']}
    assert post(c,'evaluate',request).status_code==409

def test_source_identity_duplicate_and_decimal_precision(case):
    c,_=case;repo=catalog(c)['repository'];b=draft(repo);save(c,b)
    dup={**b,'command_id':str(uuid4()),'id':str(uuid4()),'revision':str(uuid4())};assert post(c,'save',dup).status_code==409
    invalid=draft(repo);invalid['data']['amounts'][0]['value']='1e2';assert post(c,'save',invalid).status_code==422
    invalid=draft(repo);invalid['data']['occurred']['value']='2026-10-08T09:00:00.0000001Z';assert post(c,'save',invalid).status_code==422
    assert post(c,'save',{**draft(repo),'kind':'transfusion_administration','data':{'title':'Medicine misclassified','product':{'family':'pcc','label':'PCC','preparation':'Four factor','factor_basis':'IX'},'delivery_id':'pcc-1','status':'completed','amounts':[{'dimension':'dose','value':'500','unit':'IU','basis':'factor IX'}],'indication':'Reversal'}}).status_code==422
