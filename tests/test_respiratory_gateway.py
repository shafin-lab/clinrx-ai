"""RF2 respiratory admission and exact historical evidence on disposable DB copies."""
from copy import deepcopy
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from app.demo.renal_fluid_entry_gateway import RF2
from app.demo.antibiotic_gateway import ABX, SyntheticAntibioticGateway
from tests.test_renal_fluid_entry import ORIGIN, seed, ws, pin
from tests.test_respiratory_contract import record
from tests.test_synthetic_hosting import rows


def body(client,item=None):return {'repository':client.get(RF2).json()['repository'],'record':(item or record()).model_dump(mode='json')}
def post(client,item=None):return client.post(RF2+'/respiratory',json=body(client,item))


def test_respiratory_admission_retry_correction_resolve_and_history(ws):
    client,db,_=ws;original=record();saved=post(client,original)
    assert saved.status_code==200,saved.text
    evidence=saved.json();snapshot=rows(db)
    assert evidence['fact']['measurements'][0]['result']['raw_value']=='80.00'
    assert post(client,original).json()['fact']==evidence['fact']

    assert rows(db)==snapshot
    corrected=record('2',supersedes=original.reference,change_state='corrected',report_status='corrected',correction_reason='Issuer correction')
    revised=post(client,corrected);assert revised.status_code==200,revised.text
    cat=client.get(RF2).json();assert [x['fact']['revision'] for x in cat['respiratory_records']]==['2']
    selected=pin(revised.json())
    resolved=client.post(RF2+'/resolve',json={'repository':cat['repository'],'pins':[selected]})
    assert resolved.status_code==200,resolved.text
    history=client.post(RF2+'/history',json={'repository':cat['repository'],'pins':[selected]})
    assert history.status_code==200,history.text
    assert [x['fact']['revision'] for x in history.json()['items']]==['1','2']
    assert post(client,original).json()['fact']==evidence['fact']


def test_support_episode_survives_catalog_reload_and_source_correction(ws):
    client,db,_=ws;data=record(category='support').model_dump(mode='json')
    data['times']['occurred']=deepcopy(data['times']['collected'])
    data['context']['support_episode']={'type':'hfnc','until':None}
    from app.models.clinical.respiratory import RespiratoryRecord
    original=RespiratoryRecord.model_validate(data)
    saved=post(client,original);assert saved.status_code==200,saved.text
    before=rows(db);assert post(client,original).status_code==200;assert rows(db)==before
    reloaded=client.get(RF2).json()['respiratory_records'][0]
    assert reloaded['fact']['context']['support_episode']=={'type':'hfnc','until':None}
    data.update(revision='2',change_state='corrected',report_status='corrected',supersedes=original.reference.model_dump(),correction_reason='Correct oxygen device')
    data['source_identity']['source_version']='2';data['context']['support_episode']['type']='nasal_cannula'
    corrected=post(client,RespiratoryRecord.model_validate(data));assert corrected.status_code==200,corrected.text
    history=client.post(RF2+'/history',json={'repository':client.get(RF2).json()['repository'],'pins':[pin(corrected.json())]})
    assert [x['fact']['context']['support_episode']['type'] for x in history.json()['items']]==['hfnc','nasal_cannula']


def test_later_correction_retains_last_available_revision_and_hides_its_future_history(ws):
    client,_,_=ws;original=record();assert post(client,original).status_code==200
    times=deepcopy(original.model_dump(mode='json')['times'])
    times['available']['value']='2026-10-08T09:40:00Z';times['reported']['value']='2026-10-08T09:35:00Z'
    later=record('2',times=times,supersedes=original.reference,change_state='corrected',report_status='corrected',correction_reason='Later source correction')
    assert post(client,later).status_code==200
    cat=client.get(RF2,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T09:30:00Z'}).json()
    assert [x['fact']['revision'] for x in cat['respiratory_records']]==['1']
    evidence=cat['respiratory_records'][0]
    assert evidence['terminal_reference']['version']=='1' and not evidence['superseded']
    history=client.post(RF2+'/history',json={'repository':cat['repository'],'pins':[pin(evidence)]})
    assert [x['fact']['revision'] for x in history.json()['items']]==['1']
    early=client.get(RF2,params={'review_end':'2026-10-08T08:30:00Z'}).json()
    assert early['respiratory_records']==[]


@pytest.mark.parametrize('mutation',['repository','patient','owner','conflict','stale','category','accession','link_missing','link_cross_patient'])
def test_conflicts_are_rejected_without_append(ws,mutation):
    client,db,app=ws;original=record();assert post(client,original).status_code==200
    request=body(client,record('2',supersedes=original.reference,change_state='corrected',report_status='corrected',correction_reason='Source correction'))
    if mutation=='repository':request['repository']='00000000-0000-0000-0000-000000000000'
    if mutation=='patient':request['record']['binding']['target']['patient_id']='foreign-patient'
    if mutation=='owner':request['record']['id']='resp-forged'
    if mutation=='conflict':request=body(client,original);request['record']['title']='Changed same revision'
    if mutation=='stale':request['record']['supersedes']['version']='missing'
    if mutation=='category':request['record']['category']='imaging'
    if mutation=='accession':request['record']['source_identity']['accession_id']='different'
    if mutation=='link_missing':request['record']['linked_sources']=[{'kind':'observation','id':'missing','version':'1'}]
    if mutation=='link_cross_patient':
        from app.persistence.repository import transaction
        from test_persistence import patient,encounter,fact,replace
        from app.models.clinical.common import ContextTarget
        with transaction(app.core.state.dependencies.engine) as repo:
            repo.register_patient(patient('foreign-patient'));repo.register_encounter(encounter('foreign-encounter','foreign-patient'))
            foreign=fact();foreign=replace(foreign,binding=replace(foreign.binding,target=ContextTarget(patient_id='foreign-patient',encounter_id='foreign-encounter')))
            repo.append_fact(foreign,target=foreign.binding.target)
        request['record']['linked_sources']=[foreign.reference.model_dump()]
    before=rows(db);response=client.post(RF2+'/respiratory',json=request)
    assert response.status_code in (404,409,422),response.text
    assert rows(db)==before


def test_exact_linked_source_and_category_coverage_do_not_leak_to_other_domains(ws):
    client,db,app=ws;catalog=client.get(RF2).json();source=catalog['combined']['laboratory']['observations'][0]['fact']
    linked={'kind':source['kind'],'id':source['id'],'version':source['revision']}
    for category in ('bedside','support','blood_gas','mechanics','imaging','procedure','treatment','liberation','lung_function','sleep','extracorporeal','assessment'):
        item=record(category=category,linked_sources=[linked])
        data=item.model_dump(mode='json');data['source_identity']['source_report_id']=category
        from hashlib import sha256
        data['id']='resp-'+sha256(('lab.example\0'+category).encode()).hexdigest()[:32]
        response=client.post(RF2+'/respiratory',json={'repository':catalog['repository'],'record':data})
        assert response.status_code==200,response.text
    catalog=client.get(RF2);assert catalog.status_code==200,catalog.text
    assert len(catalog.json()['respiratory_records'])==12
    assert not any(x['fact']['kind']=='respiratory_record' for x in catalog.json()['combined']['circulatory']['assembly']['snapshot']['items'])
    abx=SyntheticAntibioticGateway(db,Path(app.static.directory),'ab'*32,ORIGIN)
    with TestClient(abx,base_url=ORIGIN,client=('127.0.0.1',1)) as c:state=c.get(ABX,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z'})
    assert state.status_code==200,state.text
    assert not any(x['fact']['kind']=='respiratory_record' for x in state.json()['micro']['assembly']['snapshot']['items'])


def test_same_origin_and_duplicate_member_guards_cover_respiratory(ws):
    client,db,_=ws;before=rows(db)
    assert client.post(RF2+'/respiratory',json=body(client),headers={'Origin':'https://foreign.example'}).status_code==403
    assert client.post(RF2+'/respiratory',content='{"repository":"x","repository":"y"}',headers={'Content-Type':'application/json'}).status_code==422
    assert rows(db)==before


def test_historical_resolve_does_not_disclose_a_later_correction(ws):
    client,_,_=ws;original=record();assert post(client,original).status_code==200
    times=deepcopy(original.model_dump(mode='json')['times']);times['available']['value']='2026-10-08T09:50:00Z'
    changed=record('2',times=times,supersedes=original.reference,change_state='corrected',report_status='corrected',correction_reason='Later correction')
    assert post(client,changed).status_code==200
    cat=client.get(RF2,params={'review_end':'2026-10-08T09:30:00Z'}).json();evidence=cat['respiratory_records'][0]
    resolved=client.post(RF2+'/resolve',json={'repository':cat['repository'],'pins':[pin(evidence)]})
    assert resolved.status_code==200,resolved.text
    assert resolved.json()['items'][0]['terminal_reference']['version']=='1'
    assert resolved.json()['items'][0]['superseded'] is False


def test_observed_bedside_source_is_admitted_and_inferred_origin_is_rejected(ws):
    client,db,_=ws
    observed=record(category='bedside',origin='observed')
    response=post(client,observed)
    assert response.status_code==200,response.text
    assert response.json()['fact']['origin']=='observed'
    before=rows(db);request=body(client);request['record']['origin']='inferred'
    assert client.post(RF2+'/respiratory',json=request).status_code==422
    assert rows(db)==before


def test_respiratory_exact_reimport_keeps_payload_and_acquisition_persists(ws):
    import json
    from app.models.clinical.respiratory import RespiratoryRecord
    client,db,_=ws
    from app.persistence.canonical import canonical_payload
    source=record()
    raw=canonical_payload(source)
    first=post(client,source)
    assert first.status_code==200,first.text
    assert first.json()['canonical_fact']==raw
    before=rows(db)
    replay=post(client,source)
    assert replay.status_code==200,replay.text
    assert replay.json()['canonical_fact']==raw
    assert rows(db)==before
    data=json.loads(raw)
    data.update(revision='task3-acquisition',report_status='corrected',change_state='corrected',supersedes=source.reference.model_dump(),correction_reason='Explicit source acquisition metadata')
    data['source_identity']['source_version']='task3-acquisition'
    data['measurements'][0]['acquisition']={'breath_channel':'spontaneous','acquisition_id':'source-period'}
    changed=post(client,RespiratoryRecord.model_validate(data))
    assert changed.status_code==200,changed.text
    assert changed.json()['fact']['measurements'][0]['acquisition']==data['measurements'][0]['acquisition']
    history=client.post(RF2+'/history',json={'repository':changed.json()['repository'],'pins':[pin(changed.json())]})
    assert history.status_code==200,history.text
    assert history.json()['items'][0]['canonical_fact']==raw


def linked_support_catalog(client):
    """Real gateway envelopes used by the bounded resolver regression fixture."""
    from hashlib import sha256
    from app.models.clinical.respiratory import RespiratoryRecord
    support=record().model_dump(mode='json')
    support['source_identity']['source_report_id']='task3-support'
    support['id']='resp-'+sha256(b'lab.example\0task3-support').hexdigest()[:32]
    support['category']='support';support['title']='Exact simultaneous support'
    support['times']['occurred']=deepcopy(support['times']['collected'])
    support['measurements']=[{'concept':'fio2','label':'Recorded FiO2','role':'set','quality':'usable','method':None,'result':{'kind':'numeric','raw_value':'40','comparator':'=','unit':{'namespace':'UCUM','code':'%','raw_display':'%','version':None}}}]
    s=RespiratoryRecord.model_validate(support)
    response=post(client,s);assert response.status_code==200,response.text
    gas=record().model_dump(mode='json');gas['measurements'][0]['result']['unit']['namespace']='UCUM'
    gas['linked_sources']=[s.reference.model_dump()]
    response=post(client,RespiratoryRecord.model_validate(gas));assert response.status_code==200,response.text
    return client.get(RF2,params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z'}).json()


def test_current_linked_support_and_gas_share_selected_catalog_cutoff(ws):
    catalog=linked_support_catalog(ws[0]);sources=catalog['respiratory_records']
    assert len(sources)==2
    for source in sources:
        assert source['cutoff']==catalog['cutoff']['fact_watermark']
        assert source['repository']==catalog['repository']
        assert source['terminal_reference']=={'kind':source['fact']['kind'],'id':source['fact']['id'],'version':source['fact']['revision']}
        assert not source['superseded']
    gas=next(e['fact'] for e in sources if e['fact']['category']=='blood_gas')
    support=next(e['fact'] for e in sources if e['fact']['category']=='support')
    assert gas['times']['collected']==support['times']['occurred']
    assert gas['context']['settings_confirmed_at_sample'] is True
