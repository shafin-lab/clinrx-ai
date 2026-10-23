"""Real API/storage tests for the isolated synthetic authoring boundary."""
import copy
import shutil
import sqlite3
from uuid import uuid4
import pytest
from starlette.testclient import TestClient
from app.demo.authoring import SyntheticAuthoringGateway, ENTRY, EvidenceDraft, write_evidence
from app.demo.hosting import SyntheticDemoGateway, PREFIX
from app.demo.icu_flowsheet import bootstrap
from app.persistence.database import create_database
from app.persistence.shared_transaction import execution_transaction
from app.persistence.errors import TransactionCompletionUnknown
from tests.test_synthetic_hosting import rows

ORIGIN='http://127.0.0.1:5185'

@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    root=tmp_path_factory.mktemp('authoring-seed');path=root/'seed.sqlite3'
    engine=create_database(path)
    try:manifest=bootstrap(engine)
    finally:engine.dispose()
    return path,manifest

@pytest.fixture
def workspace(tmp_path,seeded):
    original,manifest=seeded;db=tmp_path/'synthetic.sqlite3';shutil.copyfile(original,db)
    frontend=tmp_path/'dist';(frontend/'assets').mkdir(parents=True);(frontend/'index.html').write_text('local entry')
    app=SyntheticAuthoringGateway(db,frontend,'a7'*32,ORIGIN)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000),headers={'Origin':ORIGIN}) as client:
        state=client.get(PREFIX+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')}).json()
        item=next(i for i in state['assembly']['snapshot']['items'] if i['fact']['id']=='fs-PH-60')
        body={'repository_id':state['assembly']['request']['scope']['repository_cutoff']['repository_id'],
              'fact':copy.deepcopy(item['fact']),'predecessor_digest':item['expected_digest']}
        body['fact'].update(revision='local-correction',supersedes={'kind':item['fact']['kind'],'id':item['fact']['id'],'version':item['fact']['revision']},correction_reason='Synthetic transcription correction')
        body['fact']['result']['quantity']['value']='7.36'
        yield client,db,body,state,app,manifest


def test_reasoned_correction_retry_history_and_receipts(workspace):
    client,db,body,state,app,manifest=workspace;before=rows(db)
    preview=client.post(ENTRY+'/validate',json=body);assert preview.status_code==200
    assert rows(db)==before
    saved=client.post(ENTRY,json=body);assert saved.status_code==200,saved.text
    assert saved.json()['fact']['result']['quantity']['value']=='7.36'
    after=rows(db)
    assert len(after['fact_revision'])==len(before['fact_revision'])+1
    assert after['fact_revision'][:-1]==before['fact_revision']
    for table in before:
        if table not in ('fact_revision','revision_link','sqlite_sequence'):
            assert after[table]==before[table]
    assert client.post(ENTRY,json=body).json()==saved.json()
    assert rows(db)==after
    lookup=client.post(ENTRY+'/lookup',json=body).json()
    assert lookup['status']=='committed_match' and lookup['evidence']==saved.json()
    # Historical context is bounded and still exposes the original revision.
    ref=body['fact']['supersedes']
    history=client.post(PREFIX+'/circulatory-evidence-history',json={'state_context':state['state_context'],'reference':ref}).json()
    assert len(history['revisions'])==1
    assert history['revisions'][0]['fact']['result']['quantity']['value']=='7.35'
    fresh=client.get(PREFIX+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')}).json()
    assert fresh['execution_enabled'] is False
    assert next(i for i in fresh['assembly']['snapshot']['items'] if i['fact']['id']=='fs-PH-60')['fact']['revision']=='local-correction'


def test_stale_conflicting_and_foreign_repository_fail_without_changes(workspace):
    client,db,body,*_=workspace
    assert client.post(ENTRY,json=body).status_code==200
    before=rows(db)
    for change in ('stale','collision','digest','repository','scope'):
        bad=copy.deepcopy(body)
        if change=='stale':bad['fact']['revision']='another'
        if change=='collision':bad['fact']['result']['quantity']['value']='7.40'
        if change=='digest':bad['predecessor_digest']='f'*64
        if change=='repository':bad['repository_id']=str(uuid4())
        if change=='scope':bad['fact']['binding']['target']['patient_id']='foreign'
        assert client.post(ENTRY,json=bad).status_code in (409,422)
        assert rows(db)==before


def test_root_entry_withdrawal_and_retained_retry_after_successor(workspace):
    client,db,body,*_=workspace
    root=copy.deepcopy(body);root['fact'].update(id='local-new-gas',revision='1',supersedes=None,correction_reason=None);root['predecessor_digest']=None
    assert client.post(ENTRY+'/lookup',json=root).json()=={'status':'absent'}
    response=client.post(ENTRY,json=root);assert response.status_code==200,response.text
    withdrawn=copy.deepcopy(root);withdrawn['fact'].update(revision='2',supersedes={'kind':root['fact']['kind'],'id':'local-new-gas','version':'1'},record_status='withdrawn',correction_reason='Fictional sample withdrawn')
    withdrawn['predecessor_digest']=response.json()['expected_digest']
    assert client.post(ENTRY,json=withdrawn).status_code==200
    before=rows(db)
    assert client.post(ENTRY,json=root).json()==response.json()
    assert rows(db)==before

@pytest.mark.parametrize('fault',['float_time','kind','reason','foreign_predecessor','missing_context'])
def test_structured_input_rejection_is_atomic_and_sanitized(workspace,fault):
    client,db,body,*_=workspace;bad=copy.deepcopy(body);before=rows(db)
    if fault=='float_time':bad['fact']['occurred']['source_timestamp']=1791449999.1234567
    if fault=='kind':bad['fact']['kind']='inference'
    if fault=='reason':bad['fact']['correction_reason']=''
    if fault=='foreign_predecessor':bad['fact']['supersedes']['id']='other'
    if fault=='missing_context':bad['fact'].pop('acquisition')
    response=client.post(ENTRY,json=bad)
    assert response.status_code==422,response.text
    assert '7.36' not in response.text
    assert rows(db)==before


def test_gateway_isolation_and_accepted_read_only_surface(workspace):
    client,db,body,state,app,manifest=workspace;before=rows(db)
    for headers in ({'Origin':'https://foreign.example'},{'Origin':''},{'Host':'foreign.example'},{'Sec-Fetch-Site':'cross-site'}):
        assert client.post(ENTRY,json=body,headers=headers).status_code==403
    for path in ('/circulatory-review-preparations','/circulatory-reviews','/circulatory-review-reconciliations'):
        assert client.post(PREFIX+path,json={}).status_code==404
    read_only=SyntheticDemoGateway(db,app.static.directory,'a7'*32)
    with TestClient(read_only) as read_client:
        assert read_client.post(ENTRY,json=body).status_code==404
    with TestClient(app,base_url=ORIGIN,client=('203.0.113.5',50000),headers={'Origin':ORIGIN}) as remote:
        assert remote.post(ENTRY,json=body).status_code==403
    assert rows(db)==before


def test_commit_response_uncertainty_lookup_and_atomic_failure(workspace,monkeypatch):
    client,db,body,*_=workspace
    # Real append succeeds; a lost response is recovered by exact lookup.
    import app.demo.authoring as module
    real=module.write_evidence
    def committed_then_unknown(engine,draft):
        real(engine,draft)
        raise TransactionCompletionUnknown('private driver detail')
    monkeypatch.setattr(module,'write_evidence',committed_then_unknown)
    response=client.post(ENTRY,json=body)
    assert response.status_code==503 and 'private' not in response.text
    assert client.post(ENTRY+'/lookup',json=body).json()['status']=='committed_match'
    before=rows(db)
    engine=create_database(db)
    try:
        draft=EvidenceDraft.model_validate(body)
        new=draft.fact.model_copy(update={'id':'rollback-gas','revision':'1','supersedes':None,'correction_reason':None})
        with pytest.raises(RuntimeError):
            with execution_transaction(engine) as tx:
                tx.repository.append_fact(new,target=module.TARGET)
                raise RuntimeError('abort')
    finally:engine.dispose()
    assert rows(db)==before
