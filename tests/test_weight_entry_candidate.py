"""Recorded-weight UI contract exercised through the existing RF2 owner."""
from copy import deepcopy
from uuid import uuid4
from tests.test_renal_fluid_entry import ws,seed,draft,saved,post,pin,RF2,rows

def test_weight_and_correction_return_to_one_catalog_owner(ws):
    c,db,_=ws;b=draft(c,'weight',key=False);b['chart']['point']=None
    original=saved(c,b)
    assert original['fact']['recorded_amount']['value']=='70.0000'
    assert original['fact']['occurred']['recorded']['status']=='not_recorded'
    correction=deepcopy(b);correction.update(revision=str(uuid4()),predecessor=pin(original),reason='Recorded scale transcription error')
    correction['chart']['amount']='71.2500';new=saved(c,correction)
    catalog=c.get(RF2).json()
    all_items=catalog['items']+catalog['combined']['circulatory']['assembly']['snapshot']['items']
    displayed=[e for e in all_items if e['fact']['id']==b['id']]
    assert len(displayed)==1 and displayed[0]['fact']['revision']==new['fact']['revision']
    history=c.post(RF2+'/history',json={'repository':b['repository'],'pins':[pin(new)]}).json()['items']
    assert [e['fact']['recorded_amount']['value'] for e in history]==['70.0000','71.2500']
    assert history[0]['superseded'] and not history[1]['superseded']
    assert new['fact']['supersedes']==pin(original)['reference']

def test_weight_lookup_recovers_committed_request_without_duplicate(ws):
    c,db,_=ws;b=draft(c,'weight',key=False);original=saved(c,b);before=rows(db)
    for _ in range(2):
        r=post(c,'/lookup',b);assert r.status_code==200;assert r.json()['evidence']['fact']==original['fact']
    assert rows(db)==before
    r=post(c,'/save',b);assert r.status_code==200 and r.json()['evidence']['fact']==original['fact'];assert rows(db)==before

def test_weight_absent_lookup_and_explicit_same_request_retry(ws):
    c,db,_=ws;b=draft(c,'weight',key=False)
    before=rows(db);r=post(c,'/lookup',b);assert r.status_code==200 and r.json()['status']=='absent';assert rows(db)==before
    original=saved(c,b);assert post(c,'/lookup',b).json()['evidence']['fact']==original['fact']

def test_stale_correction_and_wrong_repository_cannot_append(ws):
    c,db,_=ws;b=draft(c,'weight',key=False);original=saved(c,b)
    first=deepcopy(b);first.update(revision=str(uuid4()),predecessor=pin(original),reason='First correction');first['chart']['amount']='71';saved(c,first)
    stale=deepcopy(first);stale['revision']=str(uuid4());stale['chart']['amount']='72'
    before=rows(db);r=post(c,'/save',stale);assert r.status_code==409;assert rows(db)==before
    wrong=deepcopy(b);wrong['repository']=str(uuid4());r=post(c,'/save',wrong);assert r.status_code==409;assert rows(db)==before
