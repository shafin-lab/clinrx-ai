"""The hosted surface reads real synthetic APIs and rejects all other operations."""
import sqlite3
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


@pytest.fixture
def hosted(tmp_path):
    database=tmp_path/'synthetic.sqlite3';engine=create_database(database)
    try:manifest=bootstrap(engine)
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
        assert len(items)==41 and len({i['fact']['kind'] for i in items})==14
        for id,outcome in ((RELEASED_ID,'released'),(WITHHELD_ID,'withheld')):
            result=client.get(PREFIX+'/circulatory-reviews/'+str(id))
            assert result.status_code==200 and result.json()['record']['decision']['outcome']==outcome
        support=next(i for i in items if i['fact']['id']=='m7-CAL')
        history=client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':data['state_context'],
            'reference':{'kind':support['fact']['kind'],'id':'m7-CAL','version':'2'}})
        assert history.status_code==200
        assert [r['fact']['revision'] for r in history.json()['revisions']]==['1','2']
        assert client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':'invalid','reference':{}}).status_code==422
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
