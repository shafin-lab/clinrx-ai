"""D3 explicit third handle: real mixed writes and independent SQLite visibility."""
from dataclasses import FrozenInstanceError, fields
from datetime import timedelta
import ast
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from pydantic_core import PydanticSerializationError
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.execution.creatinine_trend import compare_recorded_creatinine
from app.persistence import creatinine_executions as creatinine_store
from app.persistence import shared_transaction as shared
from app.persistence.creatinine_executions import (
    append_creatinine_trend_execution as append, load_creatinine_trend_execution as load,
    find_creatinine_trend_execution as find,
)
from app.persistence.database import create_database
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch,
    StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown,
)
from app.persistence.executions import append_weight_trend_execution, load_weight_trend_execution
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from test_persistence import AT, TARGET, database, registered, fact, patient, encounter, replace
from test_weight_trend_shared_transaction import trace, private, SECRET
from test_weight_trend_execution_persistence import make_record as weight_record
from test_weight_trend_release import evidence as weight_evidence
from test_creatinine_trend import creatinine, save, select
from test_creatinine_trend_inference import build, persist, resolve
from test_creatinine_trend_release import compose, GRANT_TARGET
from test_creatinine_trend_execution_persistence import make_record, mutate_payload


@pytest.fixture
def mixed(registered):
    # Both capabilities have actual retained facts in this repository, with distinct IDs.
    weight=weight_record(weight_evidence(registered))
    a=creatinine('creatinine-a','1.00')
    b=creatinine('creatinine-b','1.200',AT+timedelta(hours=1))
    selection=select(registered,save(registered,b,a))
    inference=build(selection)
    _,cutoff=persist(registered,inference)
    case=compose(dict(selection=selection,comparison=compare_recorded_creatinine(selection),
        inference=inference,lineage=resolve(registered,inference.reference,cutoff),
        patient=patient(),encounter=encounter(),target=GRANT_TARGET))
    return weight,make_record(case),case


def counts(engine):
    connection=sqlite3.connect(f'file:{engine.url.database}?mode=ro',uri=True,timeout=0)
    try:
        return tuple(connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
            for table in ('fact_revision','weight_trend_execution','creatinine_trend_execution'))
    finally: connection.close()


def blocked(tx,events):
    before=list(events['sql'])
    with pytest.raises(TransactionAborted): tx.repository.capture_cutoff()
    with pytest.raises(TransactionAborted): tx.executions.find(uuid4(),target=TARGET)
    with pytest.raises(TransactionAborted): tx.creatinine_executions.find(uuid4(),target=TARGET)
    # Even missing arguments must hit the lifecycle check first.
    with pytest.raises(TransactionAborted): tx.creatinine_executions.append()
    with pytest.raises(TransactionAborted): tx.creatinine_executions.load()
    assert events['sql']==before


@pytest.mark.parametrize('variant',['released','withheld'])
def test_one_owner_and_atomic_visibility(mixed,registered,monkeypatch,variant):
    weight,original,case=mixed
    original=make_record(case,variant)
    before=counts(registered)
    sessions=[]
    checkouts=[]
    real_session=shared.Session
    def session(*args,**kwargs):
        value=real_session(*args,**kwargs)
        sessions.append(value)
        return value
    def checkout(*args): checkouts.append(True)
    def forbidden(*args,**kwargs): pytest.fail('bound adapter opened a standalone transaction')
    monkeypatch.setattr(shared,'Session',session)
    monkeypatch.setattr(creatinine_store,'_session',forbidden)
    event.listen(registered,'checkout',checkout)
    try:
        with trace(registered) as events:
            with execution_transaction(registered) as tx:
                assert {f.name for f in fields(tx)}=={'repository','executions','creatinine_executions'}
                for handle in (tx,tx.repository,tx.executions,tx.creatinine_executions):
                    assert not any(hasattr(handle,name) for name in ('session','connection','commit','rollback','reset'))
                assert not any(isinstance(v,Session) for v in vars(tx).values())
                with pytest.raises(FrozenInstanceError): tx.creatinine_executions=None
                assert tx.repository._session is tx.executions._session is tx.creatinine_executions._session is sessions[0]
                assert tx.repository._lifecycle is tx.executions._lifecycle is tx.creatinine_executions._lifecycle
                saved_fact=tx.repository.append_fact(fact(id='D3-mixed'),target=TARGET)
                saved_weight=tx.executions.append(weight,target=TARGET)
                saved=tx.creatinine_executions.append(original,target=TARGET)
                assert tx.creatinine_executions.load(original.execution_id,target=TARGET)==saved
                assert tx.creatinine_executions.find(original.execution_id,target=TARGET)==saved
                assert tx.executions.load(weight.execution_id,target=TARGET)==saved_weight
                assert tx.repository.load_fact(saved_fact.fact.reference,target=TARGET)==saved_fact
                assert counts(registered)==before
                assert events['commits']==0 and events['rollbacks']==0
                assert events['sql'].count('BEGIN IMMEDIATE')==1
                assert len(events['connections'])==len(sessions)==len(checkouts)==1
            assert events['commits']==1 and events['rollbacks']==0
            blocked(tx,events)
    finally: event.remove(registered,'checkout',checkout)
    assert counts(registered)==(before[0]+1,before[1]+1,before[2]+1)
    # _session spy applies only to the duration under test.
    monkeypatch.undo()
    assert load(registered,original.execution_id,target=TARGET)==saved
    assert load_weight_trend_execution(registered,weight.execution_id,target=TARGET)==saved_weight


@pytest.mark.parametrize('failure,category',[
    ('creatinine_validation',PersistenceInputError),('weight_validation',PersistenceInputError),
    ('repository_validation',PersistenceInputError),('creatinine_missing',RecordNotFound),
    ('weight_missing',RecordNotFound),('repository_missing',RecordNotFound),
    ('creatinine_conflict',RecordConflict),('weight_conflict',RecordConflict),('repository_conflict',RecordConflict),
    ('creatinine_scope',ScopeMismatch),('creatinine_arguments',TransactionAborted),
])
@pytest.mark.parametrize('caught',[False,True])
def test_failure_any_handle_rolls_back_all(mixed,registered,failure,category,caught):
    weight,original,_=mixed
    before=counts(registered)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted if caught else category):
            with execution_transaction(registered) as tx:
                tx.repository.append_fact(fact(id='D3-prior'),target=TARGET)
                tx.executions.append(weight,target=TARGET)
                tx.creatinine_executions.append(original,target=TARGET)
                def fail():
                    if failure=='creatinine_validation': tx.creatinine_executions.append(original.model_copy(update={'actor':''}),target=TARGET)
                    elif failure=='weight_validation': tx.executions.append(weight.model_copy(update={'actor':''}),target=TARGET)
                    elif failure=='repository_validation': tx.repository.append_fact(fact().model_copy(update={'origin':SECRET}),target=TARGET)
                    elif failure=='creatinine_missing': tx.creatinine_executions.load(uuid4(),target=TARGET)
                    elif failure=='weight_missing': tx.executions.load(uuid4(),target=TARGET)
                    elif failure=='repository_missing': tx.repository.load_patient('missing')
                    elif failure=='creatinine_conflict': tx.creatinine_executions.append(replace(original,finalized_at=original.finalized_at+timedelta(seconds=1)),target=TARGET)
                    elif failure=='weight_conflict': tx.executions.append(replace(weight,finalized_at=weight.finalized_at+timedelta(seconds=1)),target=TARGET)
                    elif failure=='repository_conflict': tx.repository.append_fact(fact(id='D3-prior',concept_id='changed'),target=TARGET)
                    elif failure=='creatinine_scope': tx.creatinine_executions.append(original,target=replace(TARGET,encounter_id='foreign'))
                    else: tx.creatinine_executions.append(unexpected=SECRET)
                if caught:
                    with pytest.raises(category) as error: fail()
                    private(error.value)
                    blocked(tx,events)
                else: fail()
        assert events['commits']==0
        blocked(tx,events)
    assert counts(registered)==before


@pytest.mark.parametrize('operation',['append','load','find','serialization'])
def test_creatinine_failure_before_sql_still_poisons(mixed,registered,monkeypatch,operation):
    _,original,_=mixed
    def fail(*args): raise PydanticSerializationError(SECRET)
    if operation=='serialization': monkeypatch.setattr(creatinine_store,'canonical_payload',fail)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
            before=list(events['sql'])
            with pytest.raises(PersistenceInputError) as error:
                if operation=='append': tx.creatinine_executions.append(original.model_copy(update={'payload_version':True}),target=TARGET)
                elif operation=='serialization': tx.creatinine_executions.append(original,target=TARGET)
                else: getattr(tx.creatinine_executions,operation)(SECRET,target=TARGET)
            private(error.value)
            assert events['sql']==before
            blocked(tx,events)


@pytest.mark.parametrize('foreign',[False,True])
def test_find_absence_is_normal_and_foreign_payload_undecoded(mixed,registered,monkeypatch,foreign):
    weight,original,_=mixed
    if foreign:
        append(registered,original,target=TARGET)
        with registered.begin() as conn:
            conn.execute(text("UPDATE creatinine_trend_execution SET patient_id='synthetic-p2',encounter_id='synthetic-e3',payload='CONFIDENTIAL_SYNTHETIC'"))
    def forbidden(*args): pytest.fail('foreign payload decoded')
    with execution_transaction(registered) as tx:
        with monkeypatch.context() as m:
            m.setattr(creatinine_store,'_decode',forbidden)
            assert tx.creatinine_executions.find(original.execution_id,target=TARGET) is None
        assert tx.repository.load_patient(TARGET.patient_id)==patient()
        assert tx.executions.append(weight,target=TARGET).record==weight
        different=replace(original,execution_id=uuid4())
        assert tx.creatinine_executions.append(different,target=TARGET).record==different
    assert load(registered,different.execution_id,target=TARGET).record==different


@pytest.mark.parametrize('kind',['digest','json','typed','scope'])
@pytest.mark.parametrize('operation',['load','find','append'])
def test_visible_corruption_poisoning(mixed,registered,kind,operation):
    weight,original,_=mixed
    append(registered,original,target=TARGET)
    if kind=='typed': mutate_payload(registered,lambda d:d.update(started_at='2099-01-01T00:00:00+00:00'))
    elif kind=='scope': mutate_payload(registered,lambda d:d['target']['context'].update(patient_id='foreign'))
    else:
        with registered.begin() as conn:
            field='payload_digest' if kind=='digest' else 'payload'
            conn.execute(text(f'UPDATE creatinine_trend_execution SET {field}=:v'),{'v':SECRET})
    before=counts(registered)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
            tx.repository.append_fact(fact(id='D3-rollback'),target=TARGET)
            tx.executions.append(weight,target=TARGET)
            with pytest.raises(StorageIntegrityError) as error:
                if operation=='append': tx.creatinine_executions.append(original,target=TARGET)
                else: getattr(tx.creatinine_executions,operation)(original.execution_id,target=TARGET)
            private(error.value)
            blocked(tx,events)
        blocked(tx,events)
    assert counts(registered)==before


@pytest.mark.parametrize('committed',[False,True])
def test_retry_same_transaction_preserves_metadata_and_watermark(mixed,registered,monkeypatch,committed):
    _,original,_=mixed
    saved=append(registered,original,target=TARGET) if committed else None
    with trace(registered) as events:
        with execution_transaction(registered) as tx:
            before=tx.repository.capture_cutoff()
            history=tx.repository.list_history(target=TARGET,cutoff=before)
            if saved is None: saved=tx.creatinine_executions.append(original,target=TARGET)
            def forbidden(): pytest.fail('retry refreshed metadata')
            monkeypatch.setattr(creatinine_store,'_now',forbidden)
            index=len(events['sql'])
            assert tx.creatinine_executions.append(original,target=TARGET)==saved
            assert tx.creatinine_executions.load(original.execution_id,target=TARGET)==saved
            assert tx.creatinine_executions.find(original.execution_id,target=TARGET)==saved
            assert not any(s.startswith(('INSERT','UPDATE','DELETE')) for s in events['sql'][index:])
            assert tx.repository.capture_cutoff().fact_watermark==before.fact_watermark
            assert tx.repository.list_history(target=TARGET,cutoff=before)==history
    assert load(registered,original.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('kind',['sql','internal'])
@pytest.mark.parametrize('operation',['append','find'])
def test_creatinine_driver_and_internal_errors_sanitized(mixed,registered,kind,operation):
    weight,original,_=mixed
    before=counts(registered)
    def fail(conn,cursor,statement,parameters,context,executemany):
        wanted='INSERT INTO creatinine_trend_execution' if operation=='append' else 'SELECT'
        if statement.startswith(wanted):
            if kind=='sql': raise OperationalError('SELECT * '+SECRET,{},Exception('driver detail'))
            raise RuntimeError(SECRET)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
            tx.repository.append_fact(fact(id='D3-before-error'),target=TARGET)
            tx.executions.append(weight,target=TARGET)
            event.listen(registered,'after_cursor_execute',fail)
            try:
                with pytest.raises(TransactionAborted) as error:
                    if operation=='append': tx.creatinine_executions.append(original,target=TARGET)
                    else: tx.creatinine_executions.find(original.execution_id,target=TARGET)
                private(error.value)
                blocked(tx,events)
            finally: event.remove(registered,'after_cursor_execute',fail)
    assert counts(registered)==before


class ProcessControl(BaseException):
    pass


@pytest.mark.parametrize('category',[KeyboardInterrupt,SystemExit,ProcessControl])
@pytest.mark.parametrize('caught',[False,True])
def test_process_control_preserved_and_all_handles_invalidated(mixed,registered,category,caught):
    weight,original,_=mixed
    before=counts(registered)
    signal=category(SECRET)
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO creatinine_trend_execution'): raise signal
    event.listen(registered,'after_cursor_execute',fail)
    try:
        with trace(registered) as events:
            with pytest.raises(TransactionAborted if caught else category) as outer:
                with execution_transaction(registered) as tx:
                    tx.repository.append_fact(fact(id='D3-control'),target=TARGET)
                    tx.executions.append(weight,target=TARGET)
                    if caught:
                        with pytest.raises(category) as error: tx.creatinine_executions.append(original,target=TARGET)
                        assert error.value is signal
                        blocked(tx,events)
                    else: tx.creatinine_executions.append(original,target=TARGET)
            if not caught: assert outer.value is signal
            blocked(tx,events)
            assert events['commits']==0
    finally: event.remove(registered,'after_cursor_execute',fail)
    assert counts(registered)==before


@pytest.mark.parametrize('committed',[False,True])
def test_completion_uncertainty_closes_third_handle_without_outcome_claim(mixed,registered,monkeypatch,committed):
    weight,original,_=mixed
    before=counts(registered)
    do_commit=registered.dialect.do_commit
    def fail(connection):
        if committed: do_commit(connection)
        raise RuntimeError(SECRET)
    with monkeypatch.context() as m:
        m.setattr(registered.dialect,'do_commit',fail)
        with trace(registered) as events:
            with pytest.raises(TransactionCompletionUnknown) as error:
                with execution_transaction(registered) as tx:
                    tx.repository.append_fact(fact(id='D3-completion'),target=TARGET)
                    tx.executions.append(weight,target=TARGET)
                    tx.creatinine_executions.append(original,target=TARGET)
            assert str(error.value)=='transaction completion could not be confirmed'
            private(error.value)
            blocked(tx,events)
    expected=tuple(n+1 for n in before) if committed else before
    assert counts(registered)==expected
    # Fault-injection observation only, not a new reconciliation API.
    assert (find(registered,original.execution_id,target=TARGET) is not None)==committed


def test_new_ownership_registrations_visible_to_both_adapters(mixed,registered):
    weight,original,_=mixed
    # Isolate ownership visibility; D3 storage does not replay historical evidence.
    with registered.begin() as conn:
        for table in ('revision_link','fact_revision','encounter','patient'):
            conn.execute(text('DELETE FROM '+table))
    with execution_transaction(registered) as tx:
        tx.repository.register_patient(patient())
        tx.repository.register_encounter(encounter())
        assert tx.executions.append(weight,target=TARGET).record==weight
        assert tx.creatinine_executions.append(original,target=TARGET).record==original
    assert load(registered,original.execution_id,target=TARGET).record==original


@pytest.mark.parametrize('inner_kind',['shared','standalone'])
def test_independent_nested_writer_contends_without_poisoning_outer(mixed,registered,inner_kind):
    weight,original,_=mixed
    contender=create_database(registered.url.database)
    def no_wait(connection,record): connection.execute('PRAGMA busy_timeout=0')
    event.listen(contender,'connect',no_wait)
    try:
        with execution_transaction(registered) as tx:
            tx.repository.append_fact(fact(id='D3-outer'),target=TARGET)
            with trace(contender) as events:
                with pytest.raises(TransactionAborted):
                    if inner_kind=='shared':
                        with execution_transaction(contender): pytest.fail('nested writer acquired lock')
                    else: append(contender,original,target=TARGET)
                assert events['sql']==['BEGIN IMMEDIATE']
                assert events['commits']==0
            assert tx.creatinine_executions.append(original,target=TARGET).record==original
            assert tx.executions.append(weight,target=TARGET).record==weight
    finally: contender.dispose()
    assert load(registered,original.execution_id,target=TARGET).record==original


def test_bound_adapter_surface_has_no_transaction_or_workflow_owner():
    source=Path(creatinine_store.__file__).read_text()
    tree=ast.parse(source)
    adapter=next(n for n in tree.body if isinstance(n,ast.ClassDef))
    assert adapter.name=='_CreatinineExecutionAdapter'
    assert {n.name for n in adapter.body if isinstance(n,ast.FunctionDef)}=={'__init__','append','load','find'}
    for method in adapter.body:
        if isinstance(method,ast.FunctionDef) and method.name!='__init__':
            assert [ast.unparse(d) for d in method.decorator_list]==['_operation']
    calls=[ast.unparse(n.func) for n in ast.walk(adapter) if isinstance(n,ast.Call)]
    assert not any(c.endswith(('.commit','.rollback','.begin','.close','.connect')) for c in calls)
    assert not any(c in ('Session','_session','append_creatinine_trend_execution','load_creatinine_trend_execution','find_creatinine_trend_execution') for c in calls)
    assert not any(word in source for word in ('reconcile_','capture_cutoff','TransactionCompletionUnknown','execute_creatinine'))
