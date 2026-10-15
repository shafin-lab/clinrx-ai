"""H1-B2 operational limits across all four real SQLite workflows."""
from contextlib import contextmanager
from datetime import datetime,timezone
from uuid import uuid4
import sqlite3
import pytest
from sqlalchemy import text,event
from app.persistence.bounded_history import HistoryBudget,AggregateHistoryBudget
from app.persistence.errors import QueryLimitExceeded,StorageIntegrityError,ScopeMismatch,TransactionAborted,TransactionCompletionUnknown
from app.persistence.repository import PatientRepository,transaction
from app.persistence.mapping import canonical_payload
from app.persistence.database import create_database
from test_persistence import database,registered,TARGET,fact,replace
from test_revision_chains import revision

@pytest.fixture(params=['m4','m6','weight','creatinine'])
def attempt(request,registered):
    name=request.param
    if name=='m4':
        from test_patient_state_workflow import prepare,Clock
        from app.execution import patient_state_workflow as w
        r,fs=prepare(registered);infer=fs[-1];sources=fs[:-1];clock=Clock
        execute=w.execute_patient_state_temporal_review;reconcile=w.reconcile_patient_state_temporal_execution
        table='patient_state_temporal_execution';expected=11
    elif name=='m6':
        from test_patient_state_v2_workflow import prepare,Clock
        from app.execution import patient_state_v2_workflow as w
        r,sources,infer=prepare(registered);clock=Clock
        execute=w.execute_micro_antimicrobial_review;reconcile=w.reconcile_micro_antimicrobial_execution
        table='micro_antimicrobial_execution';expected=14
    elif name=='weight':
        from test_weight_trend_release import evidence
        from test_weight_trend_workflow import request_for,TIME
        from app.execution import weight_trend_workflow as w
        data=evidence(registered);r=request_for(data);sources=data['selection'].selected;infer=data['inference'];clock=lambda:lambda:TIME
        execute=w.execute_weight_trend_review;reconcile=w.reconcile_weight_trend_execution
        table='weight_trend_execution';expected=9
    else:
        from test_creatinine_trend_release import evidence
        from test_creatinine_trend_workflow import request_for,TIME
        from app.execution import creatinine_trend_workflow as w
        data=evidence(registered);r=request_for(data);sources=data['selection'].selected;infer=data['inference'];clock=lambda:lambda:TIME
        execute=w.execute_creatinine_trend_review;reconcile=w.reconcile_creatinine_trend_execution
        table='creatinine_trend_execution';expected=9
    return dict(name=name,engine=registered,request=r,sources=sources,inference=infer,clock=clock,
        execute=execute,reconcile=reconcile,module=w,table=table,expected=expected)

def run(a,**kw):return a['execute'](a['engine'],a['request'],clock=a['clock'](),**kw)
def counts(a):
    with a['engine'].connect() as conn:
        return (conn.execute(text('SELECT count(*) FROM '+a['table'])).scalar_one(),
            conn.execute(text('SELECT max(ingestion_sequence) FROM fact_revision')).scalar_one())
def append(a,f):
    with transaction(a['engine']) as repo:repo.append_revision(f,target=TARGET)
def corrected(f,**changes):
    if hasattr(f,'report'):
        from test_patient_state_v2_persistence import revision as v2revision
        return v2revision(f,revision=str(uuid4()),**changes)
    return replace(revision(f,str(uuid4())),**changes)
def forbidden(*a,**kw):pytest.fail('retained path performed clinical work')

def test_original_replay_exhaustion_is_operational(attempt):
    before=counts(attempt)
    with pytest.raises(QueryLimitExceeded):run(attempt,history_budget=HistoryBudget(max_rows=1))
    assert counts(attempt)==before


def test_large_final_successor_family_exhaustion(attempt):
    f=attempt['sources'][0]
    for _ in range(32):f=corrected(f);append(attempt,f)
    before=counts(attempt)
    with pytest.raises(QueryLimitExceeded):run(attempt,history_budget=HistoryBudget(max_rows=128),family_budget=HistoryBudget(max_rows=2))
    assert counts(attempt)==before


def test_single_account_full_repeated_read_charging(attempt,monkeypatch):
    reads=[];original=PatientRepository.list_bounded_history
    def observed(repo,**kw):
        reads.append(kw);return original(repo,**kw)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',observed)
    result=run(attempt,aggregate_budget=AggregateHistoryBudget(max_rows=attempt['expected']))
    accounts={id(k['accounting']) for k in reads};assert len(accounts)==1
    account=reads[0]['accounting'];assert account.rows==attempt['expected'] and account.payload_bytes>0
    assert result.record.decision.outcome=='released'
    # The same source family appears at original and final cutoffs, not a cache hit.
    assert len(reads)>1


def test_aggregate_exhaustion_across_stages_rolls_back(attempt):
    before=counts(attempt)
    with pytest.raises(QueryLimitExceeded):run(attempt,aggregate_budget=AggregateHistoryBudget(max_rows=attempt['expected']-1))
    assert counts(attempt)==before


def test_aggregate_byte_boundary(attempt,monkeypatch):
    seen=[];original=PatientRepository.list_bounded_history
    def observed(repo,**kw):seen.append(kw['accounting']);return original(repo,**kw)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',observed)
    run(attempt);size=seen[0].payload_bytes
    attempt['request']=replace(attempt['request'],execution_id=uuid4())
    before=counts(attempt)
    with pytest.raises(QueryLimitExceeded):run(attempt,aggregate_budget=AggregateHistoryBudget(max_payload_bytes=size-1))
    assert counts(attempt)==before
    attempt['request']=replace(attempt['request'],execution_id=uuid4())
    assert run(attempt,aggregate_budget=AggregateHistoryBudget(max_payload_bytes=size)).record.decision.outcome=='released'

@pytest.mark.parametrize('mode',['same_value','provenance'])
def test_correction_materiality_unchanged(attempt,mode):
    f=attempt['sources'][0];changes={}
    if mode=='provenance':changes['provenance']=replace(f.provenance,actor='corrected-source')
    append(attempt,corrected(f,**changes));before=counts(attempt)
    result=run(attempt)
    assert result.record.decision.outcome=='withheld' and counts(attempt)[1]==before[1]


def test_admitted_original_corruption_remains_integrity(attempt):
    f=attempt['sources'][0]
    with attempt['engine'].begin() as conn:conn.execute(text('UPDATE fact_revision SET payload=:p WHERE kind=:k AND fact_id=:id'),{'p':'PRIVATE-invalid','k':f.kind,'id':f.id})
    with pytest.raises(StorageIntegrityError) as caught:run(attempt)
    assert 'PRIVATE' not in str(caught.value) and counts(attempt)[0]==0


def test_foreign_selected_successor_fails_without_decode(attempt,monkeypatch):
    f=corrected(attempt['sources'][0]);append(attempt,f)
    with attempt['engine'].begin() as conn:conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2',payload='PRIVATE-invalid' WHERE kind=:k AND fact_id=:id AND revision=:r"),{'k':f.kind,'id':f.id,'r':f.revision})
    from app.persistence import history
    decode=history.load_fact
    def checked(row,*a):
        assert row.encounter_id!= 'synthetic-e2';return decode(row,*a)
    monkeypatch.setattr(history,'load_fact',checked)
    with pytest.raises(ScopeMismatch):run(attempt)
    assert counts(attempt)[0]==0


def test_retry_bypasses_budget_creation_and_reconciliation_is_pure(attempt,monkeypatch):
    saved=run(attempt);append(attempt,corrected(attempt['sources'][0]));append(attempt,corrected(attempt['inference']))
    monkeypatch.setattr(attempt['module'],'HistoryAccounting',forbidden)
    for name in ('list_bounded_history','list_latest_known','load_latest_known','list_revisions','resolve_lineage','capture_cutoff','load_fact'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    recovered=attempt['execute'](attempt['engine'],attempt['request'],clock=forbidden,
        history_budget=HistoryBudget(max_rows=1,max_payload_bytes=1),aggregate_budget=AggregateHistoryBudget(max_rows=1,max_payload_bytes=1))
    assert recovered==saved
    reconciled=attempt['reconcile'](attempt['engine'],attempt['request'])
    assert (reconciled.execution if attempt['name']=='weight' else reconciled.stored)==saved


def test_poison_after_provisional_writes_rolls_back(attempt,monkeypatch):
    original=attempt['module']._new_execution;before=counts(attempt);sql=[]
    def capture(conn,cursor,statement,parameters,context,many):sql.append(statement)
    def exhausted(tx,*a,**kw):
        original(tx,*a,**kw)
        tx.repository.append_fact(fact(id='provisional'),target=TARGET)
        cutoff=tx.repository.capture_cutoff()
        try:tx.repository.list_bounded_history(target=TARGET,cutoff=cutoff,budget=HistoryBudget(max_rows=1))
        except QueryLimitExceeded:
            n=len(sql)
            with pytest.raises(TransactionAborted):tx.repository.capture_cutoff()
            assert len(sql)==n
            raise
        pytest.fail('expected exhaustion')
    monkeypatch.setattr(attempt['module'],'_new_execution',exhausted)
    event.listen(attempt['engine'],'before_cursor_execute',capture)
    try:
        with pytest.raises(QueryLimitExceeded):run(attempt)
    finally:event.remove(attempt['engine'],'before_cursor_execute',capture)
    assert counts(attempt)==before
    assert sum(s=='BEGIN IMMEDIATE' for s in sql)==1

@pytest.mark.parametrize('committed',[False,True])
def test_completion_uncertainty_still_requires_reconciliation(attempt,monkeypatch,committed):
    original=attempt['module'].execution_transaction
    @contextmanager
    def uncertain(engine):
        with original(engine) as tx:
            yield tx
            if not committed:raise TransactionCompletionUnknown('PRIVATE')
        if committed:raise TransactionCompletionUnknown('PRIVATE')
    monkeypatch.setattr(attempt['module'],'execution_transaction',uncertain)
    with pytest.raises(TransactionCompletionUnknown) as caught:run(attempt)
    assert 'PRIVATE' not in str(caught.value)
    result=attempt['reconcile'](attempt['engine'],attempt['request'])
    assert result.status==('committed_match' if committed else 'absent')


def test_under_budget_canonical_record_equals_legacy_retrieval(attempt,monkeypatch,tmp_path):
    # Clone the evidence database so immutable identity, metadata and request agree.
    clone=tmp_path/'legacy.sqlite3'
    with sqlite3.connect(attempt['engine'].url.database) as source,sqlite3.connect(clone) as destination:source.backup(destination)
    from app.persistence import repository,history
    fixed=datetime(2026,10,15,tzinfo=timezone.utc)
    monkeypatch.setattr(repository,'_now',lambda:fixed)
    encoded=canonical_payload(attempt['request'])
    assert canonical_payload(type(attempt['request']).model_validate_json(encoded))==encoded
    bounded=run(attempt)
    def legacy(repo,*,target,cutoff,identity=None,latest=False,clinical_filter=None,ingestion_filter=None,**operational):
        return history.retrieve(repo,target=target,cutoff=cutoff,identity=identity,latest=latest,clinical_filter=clinical_filter,ingestion_filter=ingestion_filter)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',legacy)
    engine=create_database(clone)
    try:old=attempt['execute'](engine,attempt['request'],clock=attempt['clock']())
    finally:engine.dispose()
    assert canonical_payload(bounded.record)==canonical_payload(old.record)
    assert canonical_payload(type(bounded.record).model_validate_json(canonical_payload(bounded.record)))==canonical_payload(bounded.record)


def test_unrelated_final_evidence_preserves_candidate_universe(attempt):
    with transaction(attempt['engine']) as repo:repo.append_fact(fact(id='unrelated-later'),target=TARGET)
    with attempt['engine'].begin() as conn:conn.execute(text("UPDATE fact_revision SET payload='PRIVATE-invalid' WHERE fact_id='unrelated-later'"))
    if attempt['name'] in ('m4','m6'):
        assert run(attempt,aggregate_budget=AggregateHistoryBudget(max_rows=attempt['expected'])).record.decision.outcome=='released'
    else:
        with pytest.raises(StorageIntegrityError):run(attempt)
        assert counts(attempt)[0]==0


def test_future_only_corrections_do_not_consume_fixed_final_budget(attempt,monkeypatch):
    with transaction(attempt['engine']) as repo:visible=repo.capture_cutoff()
    f=attempt['sources'][0]
    for _ in range(8):f=corrected(f);append(attempt,f)
    with attempt['engine'].begin() as conn:conn.execute(text('UPDATE fact_revision SET payload=:p WHERE kind=:k AND fact_id=:id AND revision=:r'),{'p':'PRIVATE-invalid','k':f.kind,'id':f.id,'r':f.revision})
    monkeypatch.setattr(PatientRepository,'capture_cutoff',lambda self:visible)
    assert run(attempt,aggregate_budget=AggregateHistoryBudget(max_rows=attempt['expected'])).record.decision.outcome=='released'


def test_initial_assembly_or_selection_is_bounded_before_execution(attempt):
    before=counts(attempt);r=attempt['request'];kw={'history_budget':HistoryBudget(max_rows=1)}
    with pytest.raises(QueryLimitExceeded):
        if attempt['name']=='m4':
            from app.execution.patient_state_assembly import assemble_patient_state
            assemble_patient_state(attempt['engine'],scope=r.inference_request.scope,**kw)
        elif attempt['name']=='m6':
            from app.execution.patient_state_v2_assembly import assemble_patient_state_v2
            assemble_patient_state_v2(attempt['engine'],request=r.assembly_request,**kw)
        else:
            from app.execution.weight_trend import select_weight_observations
            from app.execution.creatinine_trend import select_creatinine_observations
            with transaction(attempt['engine']) as repo:
                selector=select_weight_observations if attempt['name']=='weight' else select_creatinine_observations
                selector(repo,target=TARGET,cutoff=r.original.cutoff,policy=r.original.policy,**kw)
    assert counts(attempt)==before and before[0]==0


def test_large_inference_successor_chain_exhaustion_is_not_withholding(attempt):
    f=attempt['inference']
    for _ in range(12):f=corrected(f);append(attempt,f)
    before=counts(attempt)
    with pytest.raises(QueryLimitExceeded):run(attempt,history_budget=HistoryBudget(max_rows=64),family_budget=HistoryBudget(max_rows=2))
    assert counts(attempt)==before
