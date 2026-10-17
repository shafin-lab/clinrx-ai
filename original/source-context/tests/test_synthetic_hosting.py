"""The hosted surface reads real synthetic APIs and rejects all other operations."""
import sqlite3
import json
import secrets
import hashlib
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from app.demo.comprehensive import bootstrap, RELEASED_ID, WITHHELD_ID
from app.demo.hosting import SyntheticDemoGateway, PREFIX
from app.persistence.database import create_database


def rows(path):
    with sqlite3.connect(path) as db:
        tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return {name:db.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall() for name, in tables}


@pytest.fixture(params=[False,True],ids=['comprehensive-default','expanded-icu'])
def hosted(tmp_path,request):
    database=tmp_path/'synthetic.sqlite3';engine=create_database(database)
    from app.demo.icu_flowsheet import bootstrap as flowsheet_bootstrap
    try:manifest=(flowsheet_bootstrap if request.param else bootstrap)(engine)
    finally:engine.dispose()
    frontend=tmp_path/'dist';(frontend/'assets').mkdir(parents=True)
    (frontend/'index.html').write_text('<html>synthetic workspace</html>')
    (frontend/'assets'/'test.js').write_text('/* synthetic asset */')
    app=SyntheticDemoGateway(database,frontend,'a7'*32)
    return app,database,manifest


def test_hosted_browsing_real_history_and_retained_receipts_do_not_write(hosted):
    app,database,manifest=hosted;before=rows(database)
    assert app.config.circulatory_execution_enabled is False
    with TestClient(app,base_url='https://demo.example') as client:
        response=client.get('/');assert response.status_code==200
        assert response.headers['content-security-policy'].find("connect-src 'self'")>=0
        assert response.headers['cache-control']=='no-store'
        assert client.get('/assets/test.js').status_code==200
        assert client.get('/health').json()['execution_enabled'] is False
        state=client.get(PREFIX+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')})
        assert state.status_code==200 and state.json()['execution_enabled'] is False
        data=state.json();items=data['assembly']['snapshot']['items']
        assert len(items)==(156 if manifest.get('flowsheet_enabled') else 41)
        from app.models.clinical.hemodynamics import M7_FACTS
        assert len(M7_FACTS)==15
        assert {i['fact']['kind'] for i in items}==set(M7_FACTS)-{'circulatory_device_prediction'}
        assert manifest['optional_hpi_included'] is False
        from app.demo.comprehensive import demo_facts
        from app.demo.icu_flowsheet import flowsheet_facts
        by_id={i['fact']['id']:i for i in items}
        for fact in (*demo_facts(),*(flowsheet_facts() if manifest.get('flowsheet_enabled') else ())):
            if fact.id!='m7-CAL':assert by_id[fact.id]['fact']==fact.model_dump(mode='json')
        for id,outcome in ((RELEASED_ID,'released'),(WITHHELD_ID,'withheld')):
            result=client.get(PREFIX+'/circulatory-reviews/'+str(id))
            assert result.status_code==200 and result.json()['record']['decision']['outcome']==outcome
            record=result.json()['record']
            verify_retained_evidence(database,result.json())
            assert record['evidence']['facts'][-1]['id']=='m7-CAL' and record['evidence']['facts'][-1]['revision']=='1'
            assert record['final_recheck']['evidence'][-1]['terminal']['version']==('1' if outcome=='released' else '2')
            assert client.get(PREFIX+'/circulatory-reviews/'+str(id)).content==result.content
        support=next(i for i in items if i['fact']['id']=='m7-CAL')
        history=client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':data['state_context'],
            'reference':{'kind':support['fact']['kind'],'id':'m7-CAL','version':'2'}})
        assert history.status_code==200
        assert [r['fact']['revision'] for r in history.json()['revisions']]==['1','2']
        if manifest.get('flowsheet_enabled'):
            event=next(i for i in items if i['fact']['id']=='fs-D-CHANGE')
            h=client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':data['state_context'],'reference':{'kind':event['fact']['kind'],'id':event['fact']['id'],'version':'1'}})
            assert h.status_code==200 and h.json()['revisions'][0]['fact']==event['fact']
        assert client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':'invalid','reference':{}}).status_code==422
        assert client.get(PREFIX+'/patient-state-v3',params={'review_start':'bad','review_end':manifest['review_end']}).status_code==422
    assert rows(database)==before


@pytest.mark.parametrize('method,path',[
    ('POST',PREFIX+'/circulatory-review-preparations'),('POST',PREFIX+'/circulatory-reviews'),
    ('POST',PREFIX+'/circulatory-review-reconciliations'),('POST',PREFIX+'/temporal-review-preparations'),
    ('POST',PREFIX+'/temporal-reviews'),('GET',PREFIX+'/state'),('GET','/docs'),('GET','/openapi.json'),
    ('GET','/synthetic/synthetic.sqlite3'),('GET','/manifest.json'),('GET','/src/main.tsx'),
    ('GET','/assets/../synthetic/synthetic.sqlite3'),('GET','/assets/missing.js'),
    ('DELETE',PREFIX+'/patient-state-v3'),('POST','/'),('GET',PREFIX+'/circulatory-reviews/00000000-0000-4000-8000-00000000ffff'),
    ('GET',PREFIX.replace('synthetic-p1','foreign')+'/patient-state-v3')])
def test_hosted_gateway_denies_non_read_surface_without_changes(hosted,method,path):
    app,database,_=hosted;before=rows(database)
    with TestClient(app) as client:
        result=client.request(method,path,json={'command':'never-dispatch'})
        assert result.status_code==404
        assert result.headers['cache-control']=='no-store'
    assert rows(database)==before


def test_hosted_startup_refuses_missing_database_or_build(tmp_path):
    with pytest.raises(ValueError,match='database'):SyntheticDemoGateway(tmp_path/'missing',tmp_path/'dist','a7'*32)
    database=tmp_path/'exists';database.touch()
    with pytest.raises(ValueError,match='frontend'):SyntheticDemoGateway(database,tmp_path/'dist','a7'*32)


def test_hosted_environment_cannot_enable_execution(hosted,monkeypatch):
    app,database,_=hosted
    monkeypatch.setenv('CLINRX_CIRCULATORY_EXECUTION_ENABLED','true')
    monkeypatch.setenv('CLINRX_ENVIRONMENT','production')
    monkeypatch.setenv('CLINRX_SYNTHETIC_DATABASE',str(database))
    monkeypatch.setenv('CLINRX_SYNTHETIC_FRONTEND',str(app.static.directory))
    from app.demo.hosting import from_environment
    assert from_environment().config.circulatory_execution_enabled is False


def test_gateway_restart_preserves_receipts_rejects_stale_context_and_does_not_seed(hosted):
    app,database,manifest=hosted;before=rows(database)
    query={k:manifest[k] for k in ('review_start','review_end')}
    with TestClient(app) as client:
        state=client.get(PREFIX+'/patient-state-v3',params=query).json()
        receipts={str(id):client.get(PREFIX+'/circulatory-reviews/'+str(id)).content for id in (RELEASED_ID,WITHHELD_ID)}
    restarted=SyntheticDemoGateway(database,Path(app.static.directory),secrets.token_hex(32))
    history={'state_context':state['state_context'],'reference':{'kind':'circulatory_monitoring','id':'m7-CAL','version':'2'}}
    with TestClient(restarted) as client:
        stale=client.post(PREFIX+'/circulatory-evidence-history',json=history)
        assert stale.status_code==422 and stale.json()['code']=='invalid_state_context'
        fresh=client.get(PREFIX+'/patient-state-v3',params=query).json();assert fresh['execution_enabled'] is False
        history['state_context']=fresh['state_context']
        result=client.post(PREFIX+'/circulatory-evidence-history',json=history)
        assert result.status_code==200 and [r['fact']['revision'] for r in result.json()['revisions']]==['1','2']
        for id,raw in receipts.items():assert client.get(PREFIX+'/circulatory-reviews/'+id).content==raw
    assert rows(database)==before


def verify_retained_evidence(database,receipt):
    # Compare complete retained originals and terminal witnesses with persisted bytes.
    with sqlite3.connect(database) as db:
        db.row_factory=sqlite3.Row
        stored=db.execute('SELECT * FROM circulatory_execution WHERE execution_id=?',(receipt['record']['request']['execution_id'],)).fetchone()
        assert json.loads(stored['payload'])==receipt['record']
        assert hashlib.sha256(stored['payload'].encode()).hexdigest()==stored['payload_digest']
        facts={(r['kind'],r['fact_id'],r['revision']):r for r in db.execute('SELECT * FROM fact_revision')}
        record=receipt['record']
        for fact in record['evidence']['facts']:
            row=facts[(fact['kind'],fact['id'],fact['revision'])]
            assert json.loads(row['payload'])==fact
        assert len(record['final_recheck']['evidence'])==4
        for witness in record['final_recheck']['evidence']:
            for refkey,digestkey in [('consumed','source_digest'),('terminal','terminal_source_digest')]:
                ref=witness[refkey];row=facts[(ref['kind'],ref['id'],ref['version'])]
                assert hashlib.sha256(row['payload'].encode()).hexdigest()==witness[digestkey]
