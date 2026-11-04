"""M11 shared source ownership and temporal visibility on disposable repositories."""
from copy import deepcopy
from hashlib import sha256
import pytest
from tests.test_renal_fluid_entry import ws, seed, pin
from tests.test_laboratory_contract import report
from app.demo.renal_fluid_entry_gateway import RF2


def gi(version='1', **changes):
    data=report().model_dump(mode='json')
    for name in ('source_panel','specimen','components','original_report','original_report_digest'):data.pop(name)
    data.update(kind='gastrointestinal_record',id='gi-'+sha256(b'lab.example\0gi-1').hexdigest()[:32],revision=version,
        source_identity={'issuer_namespace':'lab.example','source_report_id':'gi-1','source_version':version,'accession_id':None},
        category='symptoms',title='GI symptoms',narrative='Nausea reduced; no vomiting reported.',linked_sources=[],
        times={'occurred':{'status':'known','precision':'instant','value':'2026-10-08T09:00:00Z'},'reported':{'status':'known','precision':'instant','value':'2026-10-08T09:05:00Z'},'available':{'status':'known','precision':'instant','value':'2026-10-08T09:05:00Z'}})
    data.update(changes)
    return data


def send(client, data):
    return client.post(RF2+'/gastrointestinal',json={'repository':client.get(RF2).json()['repository'],'record':data})


def test_gi_exact_retry_correction_history_and_visible_predecessor(ws):
    client,db,_=ws
    original=gi(); first=send(client,original)
    assert first.status_code==200,first.text
    from tests.test_synthetic_hosting import rows
    before=rows(db)
    assert send(client,original).json()==first.json()
    assert rows(db)==before
    amended=gi('2',change_state='corrected',report_status='corrected',supersedes={'kind':'gastrointestinal_record','id':original['id'],'version':'1'},correction_reason='Same finding; amended report')
    amended['times']['reported']['value']='2026-10-08T09:40:00Z';amended['times']['available']['value']='2026-10-08T09:40:00Z'
    latest=send(client,amended);assert latest.status_code==200,latest.text
    cat=client.get(RF2).json();assert cat['gastrointestinal_records'][0]['fact']['revision']=='2'
    history=client.post(RF2+'/history',json={'repository':cat['repository'],'pins':[pin(latest.json())]})
    assert [x['fact']['revision'] for x in history.json()['items']]==['1','2']
    early=client.get(RF2,params={'review_end':'2026-10-08T09:30:00Z'}).json()
    assert early['gastrointestinal_records'][0]['fact']['revision']=='1'
    h=client.post(RF2+'/history',json={'repository':cat['repository'],'pins':[pin(early['gastrointestinal_records'][0])]})
    assert [x['fact']['revision'] for x in h.json()['items']]==['1']


@pytest.mark.parametrize('case',['foreign','owner','predecessor','category','link','blank'])
def test_gi_invalid_source_does_not_append(ws,case):
    client,db,_=ws;data=gi()
    if case=='foreign':data['binding']['target']['patient_id']='other'
    if case=='owner':data['id']='gi-forged'
    if case=='predecessor':data.update(change_state='corrected',report_status='corrected',correction_reason='Unknown predecessor',supersedes={'kind':'gastrointestinal_record','id':data['id'],'version':'0'})
    if case=='category':data['category']='invented'
    if case=='link':data['linked_sources']=[{'kind':'observation','id':'missing','version':'1'}]
    if case=='blank':data['narrative']='  '
    from tests.test_synthetic_hosting import rows
    before=rows(db); response=send(client,data)
    assert response.status_code in (404,409,422),response.text
    assert rows(db)==before


def test_shared_liver_lab_mapping_and_correction_at_earlier_cutoff(ws):
    client,_,_=ws
    original=report(); data=original.model_dump(mode='json')
    data['id']='lab-'+sha256(b'lab.example\0report-1').hexdigest()[:32]
    data['components'][0].update(mapped_concept='total_bilirubin',mapping_status='mapped',mapping_version='gi-lab/1')
    first=client.post(RF2+'/laboratory',json=data);assert first.status_code==200,first.text
    changed=deepcopy(data);changed.update(revision='2',change_state='corrected',report_status='corrected',correction_reason='Issuer corrected same result',supersedes={'kind':'laboratory_report','id':data['id'],'version':'1'})
    changed['source_identity']['source_version']='2'
    changed['times']['available']['value']='2026-10-08T09:40:00Z';changed['times']['reported']['value']='2026-10-08T09:40:00Z'
    assert client.post(RF2+'/laboratory',json=changed).status_code==200
    early=client.get(RF2,params={'review_end':'2026-10-08T09:30:00Z'}).json()
    assert [e['fact']['revision'] for e in early['laboratory_reports'] if e['fact']['id']==data['id']]==['1']


def test_gi_lookup_recovers_committed_exact_payload_without_retry(ws):
    client,db,_=ws;data=gi();request={'repository':client.get(RF2).json()['repository'],'record':data}
    assert client.post(RF2+'/gastrointestinal/lookup',json=request).json()['status']=='absent'
    assert send(client,data).status_code==200
    from tests.test_synthetic_hosting import rows
    before=rows(db)
    recovered=client.post(RF2+'/gastrointestinal/lookup',json=request)
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['status']=='committed_match'
    assert recovered.json()['evidence']['fact']['narrative']==data['narrative']
    assert rows(db)==before
    request['record']['narrative']='Different request under same version'
    assert client.post(RF2+'/gastrointestinal/lookup',json=request).status_code==409


def test_future_gi_observation_is_not_current_when_availability_is_missing(ws):
    client,_,_=ws;data=gi();data['times']={'occurred':{'status':'known','precision':'instant','value':'2026-10-08T11:00:00Z'},'reported':{'status':'not_recorded'},'available':{'status':'not_recorded'}}
    assert send(client,data).status_code==200
    assert client.get(RF2).json()['gastrointestinal_records']==[]
