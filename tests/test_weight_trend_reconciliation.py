"""Explicit recovery against durable SQLite; no provisional-result cache."""
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from decimal import Decimal
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.execution import weight_trend_workflow as workflow
from app.persistence import executions
from app.persistence.database import create_database
from app.persistence.errors import (PersistenceInputError, RecordConflict, SchemaMismatch,
    StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository
from app.persistence.shared_transaction import execution_transaction
from test_persistence import ROOT, TARGET, database, registered, replace
from test_weight_trend_release import case
from test_weight_trend_workflow import request_for, run, change_evidence, TIME
from test_weight_trend_execution_persistence import make_record, mutate_payload, row
from test_weight_trend_shared_transaction import counts, trace, private, SECRET

reconcile = workflow.reconcile_weight_trend_execution


def forbid_work(monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('reconciliation executed clinical work')
    for name in ('capture_cutoff', 'resolve_lineage', 'list_history', 'list_latest_known', 'load_latest_known'):
        monkeypatch.setattr(PatientRepository, name, forbidden)
    for name in ('_new_execution', '_tick', '_utc_now', 'select_weight_observations',
        'assess_weight_trend_final_recheck', 'build_weight_trend_snapshot', 'build_weight_trend_candidate',
        'evaluate_weight_trend', 'validate_weight_trend_content', 'assess_weight_trend_final_context',
        'assess_weight_trend_dependencies', 'issue_synthetic_weight_release', 'assemble_weight_trend_runtime',
        'assess_release', 'decide_release'):
        monkeypatch.setattr(workflow, name, forbidden)


@pytest.mark.parametrize('actor,outcome', [('synthetic-orchestrator','released'), ('synthetic-denied','withheld')])
def test_committed_exact_read_only(case, registered, monkeypatch, actor, outcome):
    request = request_for(case, actor=actor)
    saved = run(registered, request)
    before = row(registered)
    forbid_work(monkeypatch)
    with trace(registered) as events:
        result = reconcile(registered, request)
    assert result.status == 'committed_match'
    assert result.execution == saved and result.execution.record.decision.outcome == outcome
    assert result.execution.ingested_at == saved.ingested_at
    assert not any(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'DROP')) for s in events['sql'])
    assert events['sql'].count('BEGIN IMMEDIATE') == 1
    assert len(events['connections']) == 1
    assert counts(registered) == (3, 1) and row(registered) == before
    with registered.connect() as conn:
        assert conn.execute(text('SELECT MAX(ingestion_sequence) FROM fact_revision')).scalar_one() == 3
    with pytest.raises(FrozenInstanceError): result.status = 'absent'
    with pytest.raises(FrozenInstanceError): result.execution.ingested_at = TIME


@pytest.mark.parametrize('status,value', [('committed_match',None), ('committed_match',object()), ('absent',object()), ('unknown',None)])
def test_result_rejects_invalid_pairs(status, value):
    with pytest.raises(ValueError): workflow.WeightTrendReconciliationResult(status, value)


@pytest.mark.parametrize('committed', [False, True])
def test_uncertain_completion_then_explicit_reconcile(case, registered, monkeypatch, committed):
    request = request_for(case)
    commit = registered.dialect.do_commit
    def fail(conn):
        if committed: commit(conn)
        raise RuntimeError(SECRET)
    with monkeypatch.context() as patch:
        patch.setattr(registered.dialect, 'do_commit', fail)
        with pytest.raises(TransactionAborted) as error: run(registered, request)
    assert type(error.value) is TransactionCompletionUnknown
    assert str(error.value) == 'transaction completion could not be confirmed'
    private(error.value)
    retained = executions.load_weight_trend_execution(registered,request.execution_id,target=TARGET) if committed else None
    forbid_work(monkeypatch)
    result = reconcile(registered,request)
    assert result.status == ('committed_match' if committed else 'absent')
    assert result.execution == retained
    assert counts(registered) == (3, int(committed))


@pytest.mark.parametrize('scope', ['patient','encounter'])
@pytest.mark.parametrize('corrupt', ['none','json','digest','version','nested'])
def test_foreign_is_identical_to_missing_without_decode(case, registered, monkeypatch, scope, corrupt):
    foreign = replace(TARGET, **{scope+'_id':'foreign'})
    stored_request = request_for(case)
    run(registered,stored_request)
    if corrupt in ('json','digest','version'):
        sql = {'json':"UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC'",
               'digest':"UPDATE weight_trend_execution SET payload_digest='bad'",
               'version':'UPDATE weight_trend_execution SET payload_version=99'}[corrupt]
        with registered.begin() as conn:
            conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            conn.execute(text(sql))
    elif corrupt == 'nested': mutate_payload(registered,lambda data:data.update(comparison={'invalid':SECRET}))
    request = replace(stored_request,target=replace(stored_request.target,context=foreign),
        original=replace(stored_request.original,target=foreign),lineage=replace(stored_request.lineage,target=foreign))
    def forbidden(*args): pytest.fail('foreign execution decoded')
    monkeypatch.setattr(executions,'_decode',forbidden)
    assert reconcile(registered,request) == reconcile(registered,replace(request,execution_id=uuid4()))
    assert reconcile(registered,request) == workflow.WeightTrendReconciliationResult('absent',None)


@pytest.mark.parametrize('part', ['target','actor','manifest','comparison','decimal','offset','inference','lineage','requested_at','requested_offset'])
def test_request_differences_conflict(case, registered, monkeypatch, part):
    request = request_for(case)
    run(registered,request)
    if part == 'target': changed = replace(request,target=replace(request.target,recipient='different'))
    elif part == 'actor': changed = replace(request,actor='different')
    elif part == 'manifest': changed = replace(request,original=replace(request.original,selected_payload_digests=('0'*64,request.original.selected_payload_digests[1])))
    elif part in ('comparison','decimal'): changed = replace(request,comparison=replace(request.comparison,earlier_kg=Decimal('83' if part=='comparison' else '82.00')))
    elif part == 'offset': changed = replace(request,comparison=replace(request.comparison,earlier_event=request.comparison.earlier_event.astimezone(timezone.utc)))
    elif part == 'lineage': changed = replace(request,lineage=replace(request.lineage,cutoff=replace(request.lineage.cutoff,captured_at=TIME)))
    elif part == 'inference':
        data = request.model_dump(mode='json')
        old = request.inference.model_dump(mode='json')
        def walk(value):
            if isinstance(value,dict):
                if value == old: value['version'] = 'different'
                else:
                    for child in value.values(): walk(child)
            elif isinstance(value,list):
                for child in value: walk(child)
        walk(data)
        changed = workflow.WeightTrendReviewRequest.model_validate(data)
    else:
        t = request.requested_at
        changed = replace(request,requested_at=t-timedelta(seconds=1) if part=='requested_at' else t.astimezone(timezone(timedelta(hours=5,minutes=30))))
    assert canonical_payload(changed) != canonical_payload(request)
    forbid_work(monkeypatch)
    with pytest.raises(RecordConflict) as error: reconcile(registered,changed)
    private(error.value)
    assert counts(registered) == (3,1)


@pytest.mark.parametrize('marker', ['legacy','SyntheticWeightProtectedExecution/v2','',{'bad':SECRET}])
def test_assessor_classification(case, registered, marker):
    request=request_for(case)
    run(registered,request)
    mutate_payload(registered,lambda d:d['decision']['assessment'].update(assessor=marker))
    with pytest.raises(RecordConflict if isinstance(marker,str) and marker else StorageIntegrityError):
        reconcile(registered,request)


@pytest.mark.parametrize('variant', ['released','failure'])
def test_standalone_is_not_protected(case,registered,variant):
    request=request_for(case)
    record=replace(make_record(case,variant),execution_id=request.execution_id,started_at=request.requested_at)
    executions.append_weight_trend_execution(registered,record,target=TARGET)
    with pytest.raises(RecordConflict): reconcile(registered,request)


@pytest.mark.parametrize('part', ['json','digest','version','envelope','decision','lineage','assessor','ingestion'])
def test_corruption_precedes_request_matching(case, registered, part):
    request=request_for(case)
    run(registered,request)
    if part in ('json','digest','version','ingestion'):
        sql={'json':"UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC'",
             'digest':"UPDATE weight_trend_execution SET payload_digest='bad'",
             'version':'UPDATE weight_trend_execution SET payload_version=99',
             'ingestion':"UPDATE weight_trend_execution SET ingested_at='bad'"}[part]
        with registered.begin() as conn:
            conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            conn.execute(text(sql))
    else:
        def corrupt(d):
            if part=='envelope': d['execution_id']=str(uuid4())
            elif part=='assessor': d['decision']['assessment']['assessor']={'bad':SECRET}
            else: d[part]={'bad':SECRET}
        mutate_payload(registered,corrupt)
    with pytest.raises(StorageIntegrityError) as error: reconcile(registered,replace(request,actor='different'))
    private(error.value)


@pytest.mark.parametrize('kind',['correction','third','inference','unrelated','expiry','execution'])
def test_current_state_independent(case,registered,monkeypatch,kind):
    request=request_for(case)
    saved=run(registered,request)
    if kind=='execution': run(registered,request_for(case))
    elif kind!='expiry': change_evidence(registered,case,kind)
    forbid_work(monkeypatch)
    assert reconcile(registered,request).execution == saved


@pytest.mark.parametrize('change',[False,True])
def test_absent_then_explicit_retry(case,registered,change):
    request=request_for(case)
    assert reconcile(registered,request).status=='absent'
    if change: change_evidence(registered,case,'correction')
    saved=run(registered,request)
    assert saved.record.decision.outcome==('withheld' if change else 'released')
    assert reconcile(registered,request).execution==saved


@pytest.mark.parametrize('different',[False,True])
def test_row_appearing_after_absence(case,registered,monkeypatch,different):
    request=request_for(case)
    assert reconcile(registered,request).status=='absent'
    saved=run(registered,replace(request,actor='synthetic-denied') if different else request)
    forbid_work(monkeypatch)
    if different:
        with pytest.raises(RecordConflict): run(registered,request)
    else: assert run(registered,request)==saved


@pytest.mark.parametrize('seed',['1','8675309'])
def test_reopen_and_process(case,registered,seed):
    request=request_for(case)
    saved=run(registered,request)
    path=registered.url.database
    registered.dispose()
    reopened=create_database(path)
    try: assert reconcile(reopened,request).execution==saved
    finally: reopened.dispose()
    script='''
import sys
from app.execution.weight_trend_workflow import WeightTrendReviewRequest, reconcile_weight_trend_execution
from app.persistence.database import create_database
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
try:
    result=reconcile_weight_trend_execution(engine,WeightTrendReviewRequest.model_validate_json(sys.argv[2]))
    print(result.status)
    print(canonical_payload(result.execution.record))
    print(result.execution.ingested_at.isoformat())
finally: engine.dispose()
'''
    proc=subprocess.run([sys.executable,'-c',script,path,request.model_dump_json()],check=True,
        capture_output=True,text=True,timeout=30,cwd=ROOT,
        env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert proc.stdout.splitlines()==['committed_match',canonical_payload(saved.record),saved.ingested_at.isoformat()]


@pytest.mark.parametrize('kind',['sql','internal','completion','not_found_message'])
def test_errors_never_become_absence(case,registered,monkeypatch,kind):
    request=request_for(case)
    run(registered,request)
    if kind=='sql':
        def fail(*args): raise OperationalError(SECRET,{'secret':SECRET},RuntimeError(SECRET))
        event.listen(registered,'before_cursor_execute',fail)
    elif kind=='completion':
        def fail(*args): raise RuntimeError(SECRET)
        monkeypatch.setattr(registered.dialect,'do_commit',fail)
    else:
        def fail(*args,**kwargs): raise RuntimeError('execution not found in requested context' if kind=='not_found_message' else SECRET)
        monkeypatch.setattr(workflow,'load_weight_trend_execution',fail)
    try:
        with pytest.raises(TransactionAborted) as error: reconcile(registered,request)
        assert type(error.value) is TransactionAborted
        private(error.value)
    finally:
        if kind=='sql': event.remove(registered,'before_cursor_execute',fail)


@pytest.mark.parametrize('category',[KeyboardInterrupt,SystemExit])
def test_process_control_preserved(case,registered,monkeypatch,category):
    request=request_for(case)
    error=category('interruption')
    def fail(*args,**kwargs): raise error
    monkeypatch.setattr(workflow,'load_weight_trend_execution',fail)
    with pytest.raises(category) as caught: reconcile(registered,request)
    assert caught.value is error


@pytest.mark.parametrize('kind',['dict','forged','session','connection'])
def test_invalid_input(case,registered,kind):
    request=request_for(case)
    if kind=='dict': request=request.model_dump()
    elif kind=='forged': request=request.model_copy(update={'actor':{'bad':SECRET}})
    if kind in ('session','connection'):
        with (Session(registered) if kind=='session' else registered.connect()) as handle:
            with pytest.raises(PersistenceInputError): reconcile(handle,request)
    else:
        with pytest.raises(PersistenceInputError) as error: reconcile(registered,request)
        private(error.value)


def test_schema_failure(case,tmp_path):
    engine=create_database(tmp_path/'unmigrated.sqlite3')
    try:
        with pytest.raises(SchemaMismatch) as error: reconcile(engine,request_for(case))
        private(error.value)
    finally: engine.dispose()


def test_ordinary_abort_not_completion_unknown(case,registered,monkeypatch):
    request=request_for(case)
    def fail(*args,**kwargs): raise RuntimeError(SECRET)
    monkeypatch.setattr(workflow,'build_weight_trend_candidate',fail)
    with pytest.raises(TransactionAborted) as error: run(registered,request)
    assert type(error.value) is TransactionAborted
    assert reconcile(registered,request).status=='absent'


def test_shared_boundary_subtype(case,registered):
    def fail(conn): raise RuntimeError(SECRET)
    event.listen(registered,'commit',fail)
    try:
        with pytest.raises(TransactionCompletionUnknown):
            with execution_transaction(registered): pass
    finally: event.remove(registered,'commit',fail)


def test_generated_fields_do_not_enter_identity(case,registered,monkeypatch):
    request=request_for(case)
    change_evidence(registered,case,'unrelated')
    ticks=iter(TIME+timedelta(seconds=i) for i in range(4))
    saved=run(registered,request,clock=lambda:next(ticks))
    assert saved.record.final_recheck.final.cutoff.fact_watermark==4
    assert saved.record.finalized_at==TIME+timedelta(seconds=3)
    assert saved.record.finalized_at!=request.requested_at
    forbid_work(monkeypatch)
    assert reconcile(registered,request).execution==saved


def test_both_entry_points_share_matcher(case,registered,monkeypatch):
    request=request_for(case)
    saved=run(registered,request)
    original=workflow._require_request_match
    calls=[]
    def observed(stored, candidate):
        calls.append(candidate.execution_id)
        return original(stored,candidate)
    monkeypatch.setattr(workflow,'_require_request_match',observed)
    assert reconcile(registered,request).execution==saved
    assert run(registered,request)==saved
    assert calls==[request.execution_id,request.execution_id]


def test_message_alone_cannot_claim_uncertainty(case,registered,monkeypatch):
    def fail(*args,**kwargs): raise TransactionAborted('transaction completion could not be confirmed')
    monkeypatch.setattr(workflow,'build_weight_trend_candidate',fail)
    with pytest.raises(TransactionAborted) as error: run(registered,request_for(case))
    assert type(error.value) is TransactionAborted
    assert str(error.value)=='protected weight execution failed'


def test_lock_contention_is_error_not_absence(case,registered):
    request=request_for(case)
    contender=create_database(registered.url.database)
    def zero(conn,record): conn.execute('PRAGMA busy_timeout=0')
    event.listen(contender,'connect',zero)
    try:
        with execution_transaction(registered):
            with pytest.raises(TransactionAborted) as error: reconcile(contender,request)
            private(error.value)
        assert reconcile(contender,request).status=='absent'
    finally: contender.dispose()


@pytest.mark.parametrize('category',[KeyboardInterrupt,SystemExit])
def test_process_control_during_actual_read_cleans_up(case,registered,category):
    request=request_for(case)
    error=category('interruption')
    def fail(conn,cursor,statement,parameters,context,many):
        if 'FROM weight_trend_execution' in statement: raise error
    event.listen(registered,'before_cursor_execute',fail)
    try:
        with pytest.raises(category) as caught: reconcile(registered,request)
        assert caught.value is error
    finally: event.remove(registered,'before_cursor_execute',fail)
    assert reconcile(registered,request).status=='absent'
