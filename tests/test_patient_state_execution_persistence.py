from test_persistence import assert_fact_kind_extension_only
"""M4.2 real SQLite envelope, privacy, lifecycle and additive migration tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.persistence import patient_state_executions as store
from app.persistence.patient_state_executions import (
    append_patient_state_temporal_execution as append,
    find_patient_state_temporal_execution as find,
    load_patient_state_temporal_execution as load,
)
from app.persistence.database import create_database
from app.persistence.entities import Base, SCHEMA_REVISION
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch,
    StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown, SchemaMismatch,
)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from test_persistence import ROOT, TARGET, AT, database, registered, migrate, replace, fact, patient, encounter
import test_patient_state_execution as pure

TABLE='patient_state_temporal_execution'


@pytest.fixture
def make(registered,monkeypatch):
    with transaction(registered) as repo: repository_id=repo.capture_cutoff().repository_id
    monkeypatch.setattr(pure,'REPO',repository_id)
    return lambda **kw: pure.artifacts(**kw)[0]


def rows(engine):
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text('SELECT * FROM '+TABLE)).mappings()]


def rewrite(engine,data):
    payload=data if isinstance(data,str) else json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    with engine.begin() as conn:
        conn.execute(text('UPDATE '+TABLE+' SET payload=:p,payload_digest=:d'),{'p':payload,'d':sha256(payload.encode()).hexdigest()})


def private(error):
    rendered=''.join(traceback.format_exception(error))
    for secret in ('PRIVATE_SYNTHETIC','INSERT INTO','SELECT ', 'input_value=', '"patient_id"'):
        assert secret not in rendered
    assert error.__cause__ is None


@pytest.mark.parametrize('withheld',[False,True])
def test_exact_envelope_reopen_and_immutability(make,registered,withheld):
    record=make(**({'actor':'denied'} if withheld else {}))
    saved=append(registered,record,target=TARGET)
    payload=canonical_payload(record)
    assert rows(registered)==[dict(execution_id=str(record.request.execution_id),patient_id=TARGET.patient_id,
        encounter_id=TARGET.encounter_id,payload_version=1,payload=payload,payload_digest=sha256(payload.encode()).hexdigest(),ingested_at=saved.ingested_at.isoformat())]
    assert saved.ingested_at.utcoffset()==timedelta(0)
    assert saved.record.disposition==('completed_withheld' if withheld else 'completed_released')
    registered.dispose(); reopened=create_database(registered.url.database)
    try:
        assert load(reopened,record.request.execution_id,target=TARGET)==saved
        assert append(reopened,record,target=TARGET)==saved
        assert find(reopened,record.request.execution_id,target=TARGET)==saved
    finally: reopened.dispose()
    with pytest.raises(ValidationError): saved.ingested_at=AT
    with pytest.raises(ValidationError): saved.record.request.actor='other'


def test_idempotency_is_full_content_not_request(make,registered,monkeypatch):
    record=make(); assigned=AT.astimezone(timezone.utc)
    monkeypatch.setattr(store,'_now',lambda:assigned)
    saved=append(registered,record,target=TARGET)
    def forbidden(): pytest.fail('retry/load sampled ingestion clock')
    monkeypatch.setattr(store,'_now',forbidden)
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        assert append(registered,record,target=TARGET)==saved
        assert load(registered,record.request.execution_id,target=TARGET)==saved
        other=replace(record,runtime=replace(record.runtime,finalized_at=record.runtime.finalized_at+timedelta(seconds=1)))
        pure.c.require_patient_state_temporal_request_match(record,other.request)
        with pytest.raises(RecordConflict) as caught: append(registered,other,target=TARGET)
        private(caught.value)
    finally: event.remove(registered,'before_cursor_execute',capture)
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for s in statements)
    assert saved.ingested_at==assigned


@pytest.mark.parametrize('scope',['patient','encounter','missing'])
def test_foreign_corruption_excluded_before_decode(make,registered,monkeypatch,scope):
    record=make(); append(registered,record,target=TARGET); rewrite(registered,'PRIVATE_SYNTHETIC')
    target=replace(TARGET,**({'patient_id':'synthetic-p2','encounter_id':'synthetic-e3'} if scope=='patient' else
        {'encounter_id':'synthetic-e2' if scope=='encounter' else 'absent'}))
    def forbidden(*a,**k): pytest.fail('foreign decode')
    monkeypatch.setattr(store,'_decode',forbidden)
    for identity in (record.request.execution_id,uuid4()):
        assert find(registered,identity,target=target) is None
        with pytest.raises(RecordNotFound) as caught: load(registered,identity,target=target)
        assert str(caught.value)=='execution not found in requested context'


def test_foreign_collision_is_bounded(make,registered,monkeypatch):
    record=make(); append(registered,record,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE "+TABLE+" SET patient_id='synthetic-p2',encounter_id='synthetic-e3',payload='PRIVATE_SYNTHETIC'"))
    monkeypatch.setattr(store,'_decode',lambda *a:pytest.fail('foreign decode'))
    with pytest.raises(RecordConflict) as caught: append(registered,record,target=TARGET)
    private(caught.value)


@pytest.mark.parametrize('part',['digest','version','id','patient','encounter','naive','offset','invalid_time','z_time'])
def test_corrupt_envelope(make,registered,part):
    record=make(); append(registered,record,target=TARGET)
    target=TARGET; identity=record.request.execution_id
    field,value={'digest':('payload_digest','0'*64),'version':('payload_version',2),'id':('execution_id',str(uuid4())),
        'patient':('patient_id','synthetic-p2'),'encounter':('encounter_id','synthetic-e2'),
        'naive':('ingested_at','2026-10-08T12:00:00'),'offset':('ingested_at',AT.isoformat()),
        'invalid_time':('ingested_at','PRIVATE_SYNTHETIC'),'z_time':('ingested_at','2026-10-08T12:00:00Z')}[part]
    with registered.begin() as conn:
        conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
        if part=='patient':
            conn.execute(text('UPDATE '+TABLE+" SET patient_id='synthetic-p2',encounter_id='synthetic-e3'"))
            target=replace(TARGET,patient_id='synthetic-p2',encounter_id='synthetic-e3')
        else: conn.execute(text('UPDATE '+TABLE+' SET '+field+'=:v'),{'v':value})
    if part=='id': identity=UUID(value)
    if part=='encounter': target=replace(TARGET,encounter_id=value)
    for op in (find,load):
        with pytest.raises(StorageIntegrityError) as caught: op(registered,identity,target=target)
        private(caught.value)


@pytest.mark.parametrize('part',['json','whitespace','typed','workflow','profile','decision','recheck','context','policy','chronology','dependencies','version'])
def test_rehashed_payload_corruption(make,registered,part):
    record=make(); append(registered,record,target=TARGET); data=json.loads(canonical_payload(record))
    if part=='json': data='PRIVATE_SYNTHETIC'
    elif part=='whitespace': data=json.dumps(data,indent=2)
    elif part=='typed': data['request']['actor']=''
    elif part=='workflow': data['request']['workflow']='PRIVATE_SYNTHETIC'
    elif part=='profile': data['request']['profile']='PRIVATE_SYNTHETIC'
    elif part=='decision': data['decision']['outcome']='withheld'
    elif part=='recheck': data['final_recheck']['inference']['observed_digest']='0'*64
    elif part=='context': data['context_digest']='0'*64
    elif part=='policy': data['decision']['assessment']['policy']['reference']['version']='2'
    elif part=='chronology': data['runtime']['started_at']='2099-01-01T00:00:00+00:00'
    elif part=='dependencies': data['decision']['assessment']['policy']['required_dependencies'].reverse()
    else: data['payload_version']=True
    rewrite(registered,data)
    for op in ('find','load','append'):
        with pytest.raises(StorageIntegrityError) as caught:
            if op=='append': append(registered,record,target=TARGET)
            else: (find if op=='find' else load)(registered,record.request.execution_id,target=TARGET)
        private(caught.value)


def test_load_never_recomputes(make,registered,monkeypatch):
    record=make(); saved=append(registered,record,target=TARGET)
    import app.execution.patient_state_assembly as assembly
    from app.persistence.repository import PatientRepository
    def forbidden(*a,**k): pytest.fail('retained load invoked fresh work')
    monkeypatch.setattr(pure.m3,'build_patient_state_temporal_inference',forbidden)
    monkeypatch.setattr(pure.c,'patient_state_temporal_policy',forbidden)
    for name in dir(pure.g):
        if name.startswith(('build_','evaluate_','validate_patient_','assess_','issue_','render_')) or name=='patient_state_temporal_policy':
            monkeypatch.setattr(pure.g,name,forbidden)
    for name in dir(assembly):
        if name.startswith('assemble_'): monkeypatch.setattr(assembly,name,forbidden)
    for name in ('capture_cutoff','list_history','resolve_lineage','load_fact'):
        if hasattr(PatientRepository,name): monkeypatch.setattr(PatientRepository,name,forbidden)
    monkeypatch.setattr(store,'_now',forbidden)
    assert load(registered,record.request.execution_id,target=TARGET)==saved
    with execution_transaction(registered) as tx:
        assert tx.patient_state_executions.load(record.request.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('op',['append','find','load'])
def test_engine_only(make,registered,op):
    record=make()
    for handle in (Session(registered),registered.connect()):
        try:
            with pytest.raises(PersistenceInputError,match='Engine'):
                (append if op=='append' else find if op=='find' else load)(handle,record if op=='append' else record.request.execution_id,target=TARGET)
        finally: handle.close()


@pytest.mark.parametrize('failure',['body','poison','validation','missing','sql','interrupt'])
def test_shared_rollback_poison_and_no_more_sql(make,registered,failure):
    record=make(); statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        with pytest.raises((TransactionAborted,RuntimeError,KeyboardInterrupt)):
            with execution_transaction(registered) as tx:
                tx.repository.append_fact(fact(id='rollback'),target=TARGET)
                tx.patient_state_executions.append(record,target=TARGET)
                if failure=='body': raise RuntimeError('body')
                if failure=='interrupt': raise KeyboardInterrupt()
                if failure=='poison': tx.patient_state_executions._lifecycle.fail()
                else:
                    try:
                        if failure=='validation': tx.patient_state_executions.append(record.model_copy(update={'context_digest':'bad'}),target=TARGET)
                        elif failure=='missing': tx.patient_state_executions.load(uuid4(),target=TARGET)
                        else:
                            def broken(*a): raise OperationalError('PRIVATE_SYNTHETIC',{},Exception('PRIVATE_SYNTHETIC'))
                            event.listen(registered,'before_cursor_execute',broken)
                            try: tx.patient_state_executions.find(uuid4(),target=TARGET)
                            finally: event.remove(registered,'before_cursor_execute',broken)
                    except (PersistenceInputError,RecordNotFound,TransactionAborted) as error: private(error)
                n=len(statements)
                with pytest.raises(TransactionAborted): tx.patient_state_executions.find(uuid4(),target=TARGET)
                with pytest.raises(TransactionAborted): tx.repository.capture_cutoff()
                assert len(statements)==n
    finally: event.remove(registered,'before_cursor_execute',capture)
    registered.dispose()
    assert rows(registered)==[]
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==0


def test_shared_same_session_one_begin_commit_watermark_and_closed_handles(make,registered):
    record=make(); statements=[]; commits=[]; connections=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement); connections.append(id(conn))
    def commit(conn): commits.append(True)
    event.listen(registered,'before_cursor_execute',capture); event.listen(registered,'commit',commit)
    try:
        with execution_transaction(registered) as tx:
            handle=tx.patient_state_executions
            assert handle._session is tx.repository._session is tx.executions._session is tx.creatinine_executions._session
            assert handle._lifecycle is tx.repository._lifecycle is tx.executions._lifecycle is tx.creatinine_executions._lifecycle
            before=tx.repository.capture_cutoff().fact_watermark
            saved=handle.append(record,target=TARGET)
            assert handle.append(record,target=TARGET)==saved
            assert handle.find(record.request.execution_id,target=TARGET)==handle.load(record.request.execution_id,target=TARGET)==saved
            assert tx.repository.capture_cutoff().fact_watermark==before
            assert not commits
        assert commits==[True] and statements.count('BEGIN IMMEDIATE')==1 and len(set(connections))==1
        n=len(statements)
        for op in (lambda:handle.append(record,target=TARGET),lambda:handle.find(record.request.execution_id,target=TARGET),lambda:handle.load(record.request.execution_id,target=TARGET)):
            with pytest.raises(TransactionAborted): op()
        assert len(statements)==n
    finally:
        event.remove(registered,'before_cursor_execute',capture); event.remove(registered,'commit',commit)
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==before
    assert load(registered,record.request.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('when',['before','after'])
def test_completion_uncertainty_unchanged(make,registered,monkeypatch,when):
    record=make()
    original=registered.dialect.do_commit
    def uncertain(connection):
        if when=='after': original(connection)
        raise OperationalError('PRIVATE_SYNTHETIC',{},Exception('PRIVATE_SYNTHETIC'))
    monkeypatch.setattr(registered.dialect,'do_commit',uncertain)
    with pytest.raises(TransactionCompletionUnknown) as caught:
        with execution_transaction(registered) as tx: tx.patient_state_executions.append(record,target=TARGET)
    private(caught.value)
    monkeypatch.setattr(registered.dialect,'do_commit',original)
    assert (find(registered,record.request.execution_id,target=TARGET) is not None)==(when=='after')


@pytest.mark.parametrize('mode',['same','different','other_id'])
def test_bounded_serialized_concurrency(make,registered,mode):
    first=make(); second=first
    if mode=='different': second=replace(first,runtime=replace(first.runtime,finalized_at=first.runtime.finalized_at+timedelta(seconds=1)))
    if mode=='other_id':
        # Construct a fresh internally bound record with another execution identity.
        evidence,check=pure.fixture()
        evidence=replace(evidence,request=replace(evidence.request,execution_id=uuid4()))
        second=pure.artifacts(evidence,check)[0]
    other=create_database(registered.url.database)
    def zero(dbapi,_): dbapi.execute('PRAGMA busy_timeout=0')
    event.listen(other,'connect',zero)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with execution_transaction(registered) as tx:
                tx.patient_state_executions.append(first,target=TARGET)
                future=pool.submit(append,other,second,target=TARGET)
                with pytest.raises(TransactionAborted): future.result(timeout=10)
        if mode=='different':
            with pytest.raises(RecordConflict): append(other,second,target=TARGET)
        else: append(other,second,target=TARGET)
        assert len(rows(registered))==(2 if mode=='other_id' else 1)
    finally: other.dispose()


def test_process_reopen(make,registered):
    record=make(); saved=append(registered,record,target=TARGET); registered.dispose()
    script='''
import sys
from app.persistence.database import create_database
from app.persistence.patient_state_executions import load_patient_state_temporal_execution
from app.models.clinical.common import ContextTarget
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
try:
 print(canonical_payload(load_patient_state_temporal_execution(engine,sys.argv[2],target=ContextTarget(patient_id='synthetic-p1',encounter_id='synthetic-e1'))))
finally: engine.dispose()
'''
    result=subprocess.run([sys.executable,'-c',script,registered.url.database,str(record.request.execution_id)],capture_output=True,text=True,check=True,timeout=30,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert result.stdout.strip()==canonical_payload(saved)


def test_schema_matches_entity(database):
    with database.connect() as conn:
        schema=inspect(conn)
        assert SCHEMA_REVISION=='m9_0010'
        assert {x['name'] for x in schema.get_columns(TABLE)}=={'execution_id','patient_id','encounter_id','payload_version','payload','payload_digest','ingested_at'}
        assert all(not x['nullable'] for x in schema.get_columns(TABLE))
        assert schema.get_pk_constraint(TABLE)['constrained_columns']==['execution_id']
        assert schema.get_indexes(TABLE)==[]
        assert schema.get_foreign_keys(TABLE)[0]['constrained_columns']==['encounter_id','patient_id']
        assert schema.get_check_constraints(TABLE)==[{'name':'ck_patient_state_execution_payload_version','sqltext':'payload_version = 1'}]
        assert compare_metadata(MigrationContext.configure(conn),Base.metadata)==[]
    scripts=ScriptDirectory.from_config(Config(str(ROOT/'backend/alembic.ini')))
    assert scripts.get_heads()==['m9_0010'] and scripts.get_revision('m4_0005').down_revision=='7b2_0004'


@pytest.mark.parametrize('fail',[False,True])
def test_additive_upgrade_and_failure_rollback(tmp_path,monkeypatch,fail):
    engine=create_database(tmp_path/'old.sqlite3'); config=Config(str(ROOT/'backend/alembic.ini'))
    from app.persistence import database as db
    with engine.begin() as conn:
        config.attributes['connection']=conn; command.upgrade(config,'7b2_0004')
    with monkeypatch.context() as m:
        m.setattr(db,'SCHEMA_REVISION','7b2_0004')
        with transaction(engine) as repo:
            repo.register_patient(patient()); repo.register_encounter(encounter()); repo.append_fact(fact(),target=TARGET)
    def snapshot():
        with engine.connect() as conn:
            names=inspect(conn).get_table_names()
            return {n:conn.execute(text('SELECT * FROM '+n)).all() for n in names},conn.execute(text("SELECT name,sql FROM sqlite_master WHERE name!='alembic_version' ORDER BY name")).all()
    before,ddl=snapshot()
    def broken(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('CREATE TABLE '+TABLE): raise RuntimeError('migration injection')
    try:
        if fail:
            event.listen(engine,'after_cursor_execute',broken)
            with pytest.raises(RuntimeError): migrate(engine)
            assert snapshot()==(before,ddl)
        else:
            migrate(engine); after,newddl=snapshot()
            assert set(after)-set(before)=={TABLE,'micro_antimicrobial_execution','circulatory_execution'}
            assert all(after[n]==value for n,value in before.items() if n!='alembic_version')
            assert_fact_kind_extension_only(ddl, newddl)
            assert after['alembic_version']==[('m9_0010',)]
            migrate(engine); assert snapshot()==(after,newddl)
    finally:
        if fail: event.remove(engine,'after_cursor_execute',broken)
        engine.dispose()


def test_standalone_watermark_and_next_fact_identity(make,registered):
    record=make()
    with transaction(registered) as repo: before=repo.capture_cutoff().fact_watermark
    saved=append(registered,record,target=TARGET)
    assert append(registered,record,target=TARGET)==saved
    with transaction(registered) as repo:
        assert repo.capture_cutoff().fact_watermark==before
        assert repo.append_fact(fact(id='next'),target=TARGET).ingestion.ingestion_sequence==before+1


@pytest.mark.parametrize('part',['raw','malformed','scope','repository'])
def test_invalid_append_bounded_and_empty(make,registered,part):
    record=make(); target=TARGET
    if part=='raw': record=record.model_dump()
    elif part=='malformed': record=record.model_copy(update={'context_digest':'PRIVATE_SYNTHETIC'})
    elif part=='scope': target=replace(TARGET,encounter_id='synthetic-e2')
    else:
        with registered.begin() as conn:
            conn.execute(text('UPDATE repository_identity SET repository_id=:id'),{'id':str(uuid4())})
    with pytest.raises((PersistenceInputError,ScopeMismatch)) as caught: append(registered,record,target=target)
    private(caught.value)
    assert rows(registered)==[]


def test_failure_before_append_and_repository_failure_poison_execution(make,registered):
    record=make()
    with pytest.raises(TransactionAborted):
        with execution_transaction(registered) as tx:
            try: tx.repository.append_fact({},target=TARGET)
            except Exception: pass
            with pytest.raises(TransactionAborted): tx.patient_state_executions.append(record,target=TARGET)
    assert rows(registered)==[]


def test_standalone_sql_failure_rolls_back(make,registered):
    record=make()
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO '+TABLE):
            raise OperationalError('PRIVATE_SYNTHETIC',{},Exception('PRIVATE_SYNTHETIC'))
    event.listen(registered,'after_cursor_execute',fail)
    try:
        with pytest.raises(TransactionAborted) as caught: append(registered,record,target=TARGET)
        private(caught.value)
    finally: event.remove(registered,'after_cursor_execute',fail)
    assert rows(registered)==[]


def test_owner_fk_and_destructive_downgrade_refused(make,registered):
    record=make(); append(registered,record,target=TARGET); before=rows(registered)
    for sql in ('UPDATE '+TABLE+" SET patient_id='synthetic-p2'", "DELETE FROM encounter WHERE encounter_id='synthetic-e1'"):
        with pytest.raises(IntegrityError),registered.begin() as conn: conn.execute(text(sql))
    config=Config(str(ROOT/'backend/alembic.ini'))
    with pytest.raises(RuntimeError,match='destructive downgrade'):
        with registered.begin() as conn:
            config.attributes['connection']=conn; command.downgrade(config,'7b2_0004')
    assert rows(registered)==before


def test_no_workflow_or_existing_store_dependencies():
    tree=ast.parse(Path(store.__file__).read_text())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any('weight' in n or 'creatinine' in n or 'workflow' in n or 'patient_state_release' in n for n in imports)
    adapter=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_PatientStateExecutionAdapter')
    assert {n.name for n in adapter.body if isinstance(n,ast.FunctionDef)}=={'__init__','append','find','load'}
    calls={n.func.id for n in ast.walk(adapter) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
    assert not calls & {'Session','_session','execution_transaction'}
