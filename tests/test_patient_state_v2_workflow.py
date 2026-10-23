"""M6.4 real SQLite protected S/I/U/D tests."""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.execution import patient_state_v2_execution as c
from app.execution import patient_state_v2_workflow as w
from app.execution.patient_state_v2_assembly import AssemblyRequestV2, assemble_patient_state_v2
from app.persistence.repository import transaction
from test_persistence import database, registered
from test_patient_state_v2_inference import selected, request, build
from test_patient_state_v2 import scope, change, TARGET
from test_patient_state_v2_persistence import save, revision

class Clock:
    def __init__(self): self.calls=0
    def __call__(self):
        self.calls+=1
        return c.GRANT_WINDOW.start+timedelta(seconds=self.calls)

def prepare(engine):
    facts=selected()
    cutoff=save(engine,*facts)
    ar=AssemblyRequestV2(scope=change(scope(),repository_cutoff=cutoff),profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2')
    a=assemble_patient_state_v2(engine,request=ar)
    ir=request(a)
    inference=build(a,ir)
    ic=save(engine,inference)
    r=c.MicroAntimicrobialExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=ir,assembly_request=ar,inference_cutoff=ic,expected_inference_digest=c.digest(inference),requested_at=c.GRANT_WINDOW.start)
    return r,facts,inference

def test_release(registered):
    r,f,i=prepare(registered)
    stored=w.execute_micro_antimicrobial_review(registered,r,clock=Clock())
    assert stored.record.decision.outcome=='released'
    assert stored.record.decision.assessment.review.rendering.content==i.statement
    assert stored.record.final_recheck.outcome=='unchanged'

from sqlalchemy import text, event
from app.persistence.errors import StorageIntegrityError, RecordConflict, TransactionAborted, TransactionCompletionUnknown
from app.persistence.shared_transaction import execution_transaction
from app.persistence import micro_antimicrobial_executions as store
from app.persistence.repository import PatientRepository

execute=w.execute_micro_antimicrobial_review
reconcile=w.reconcile_micro_antimicrobial_execution

def count(engine):
    with engine.connect() as conn: return conn.execute(text('SELECT count(*) FROM micro_antimicrobial_execution')).scalar_one()

def forbidden(*a,**k): raise AssertionError('unexpected recomputation')

@pytest.mark.parametrize('role',range(4))
@pytest.mark.parametrize('mode',['same','provenance','value'])
def test_successors_withheld(registered,role,mode):
    r,f,i=prepare(registered)
    edits={}
    if mode=='provenance': edits['provenance']=change(f[role].provenance,actor='revised-source')
    if mode=='value': edits['uncertainty']=('additional recorded uncertainty',)
    successor=revision(f[role],**edits)
    save(registered,successor)
    saved=execute(registered,r,clock=Clock())
    assert saved.record.decision.outcome=='withheld'
    assert saved.record.final_recheck.evidence[role].terminal==successor.reference
    assert saved.record.final_recheck.outcome=='materially_changed'
    assert saved.record.evidence.inference==i
    assert count(registered)==1

@pytest.mark.parametrize('withheld',[False,True])
def test_retry_and_reconciliation_do_not_recompute(registered,monkeypatch,withheld):
    r,f,i=prepare(registered)
    if withheld: save(registered,revision(f[2]))
    saved=execute(registered,r,clock=Clock())
    registered.dispose()
    for name in ('_new_execution','_assemble','build_micro_antimicrobial_timing_inference','_utc_now','assess_release','decide_release'):
        monkeypatch.setattr(w,name,forbidden)
    for name in ('load_fact','list_revisions','load_latest_known','capture_cutoff','list_bounded_history'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    assert execute(registered,r,clock=forbidden)==saved
    assert reconcile(registered,r).stored==saved
    assert count(registered)==1

@pytest.mark.parametrize('field',['actor','requested_at','expected_inference_digest'])
def test_request_conflict(registered,field):
    r,f,i=prepare(registered); execute(registered,r,clock=Clock())
    value={'actor':'different','requested_at':r.requested_at+timedelta(seconds=1),'expected_inference_digest':'0'*64}[field]
    altered=change(r,**{field:value})
    with pytest.raises(RecordConflict): execute(registered,altered,clock=forbidden)
    with pytest.raises(RecordConflict): reconcile(registered,altered)

@pytest.mark.parametrize('role',range(4))
def test_pin_conflicts(registered,role):
    r,f,i=prepare(registered); execute(registered,r,clock=Clock())
    name=('specimen_ref','isolate_ref','susceptibility_ref','administration_ref')[role]
    ir=change(r.inference_request,**{name:change(getattr(r.inference_request,name),expected_digest='0'*64)})
    with pytest.raises(RecordConflict): reconcile(registered,change(r,inference_request=ir))

@pytest.mark.parametrize('field',['statement','applicability','validation_limitations','uncertainty'])
def test_persisted_fidelity_failure(registered,field):
    # A structurally valid persisted record, with a matching request digest, must
    # still match the original M6.3 reconstruction.
    facts=selected(); cutoff=save(registered,*facts)
    ar=AssemblyRequestV2(scope=change(scope(),repository_cutoff=cutoff),profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2')
    a=assemble_patient_state_v2(registered,request=ar); ir=request(a); i=build(a,ir)
    i=change(i,**{field:('changed',) if field=='uncertainty' else 'changed'})
    ic=save(registered,i)
    r=c.MicroAntimicrobialExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=ir,assembly_request=ar,inference_cutoff=ic,expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    with pytest.raises(StorageIntegrityError): execute(registered,r,clock=Clock())
    assert count(registered)==0

@pytest.mark.parametrize('role',[1,2])
def test_binding_correction_withholds(registered,role):
    r,f,i=prepare(registered)
    b=f[role].domain_bindings[0]
    from test_patient_state_v2 import binding
    successor=revision(f[role],domain_bindings=(binding(b.role,'other'),))
    save(registered,successor)
    result=execute(registered,r,clock=Clock())
    assert result.record.decision.outcome=='withheld'
    assert ('specimen_binding_changed' if role==1 else 'isolate_binding_changed') in result.record.final_recheck.reasons

@pytest.mark.parametrize('role',[2,3])
def test_mapping_correction_withholds(registered,role):
    r,f,i=prepare(registered)
    save(registered,revision(f[role],antimicrobial=change(f[role].antimicrobial,canonical_id='different')))
    result=execute(registered,r,clock=Clock())
    assert result.record.decision.outcome=='withheld'
    assert 'antimicrobial_identity_changed' in result.record.final_recheck.reasons

@pytest.mark.parametrize('role',range(4))
def test_unrelated_insert_does_not_withhold(registered,role):
    r,f,i=prepare(registered)
    save(registered,change(f[role],id='unrelated'))
    assert execute(registered,r,clock=Clock()).record.decision.outcome=='released'


def test_inference_successor_withholds(registered):
    r,f,i=prepare(registered)
    save(registered,change(i,revision='2',supersedes=i.reference,correction_reason='same meaning'))
    result=execute(registered,r,clock=Clock())
    assert result.record.decision.outcome=='withheld'
    assert 'inference_superseded' in result.record.final_recheck.reasons


def test_watermark_and_one_transaction(registered):
    r,f,i=prepare(registered)
    with transaction(registered) as repo: before=repo.capture_cutoff()
    sql=[]
    def capture(conn,cursor,statement,parameters,context,executemany): sql.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try: execute(registered,r,clock=Clock())
    finally: event.remove(registered,'before_cursor_execute',capture)
    assert sum(s=='BEGIN IMMEDIATE' for s in sql)==1
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==before.fact_watermark

@pytest.mark.parametrize('stage',['_final_recheck','assess_release','decide_release'])
def test_failure_rolls_back(registered,monkeypatch,stage):
    r,f,i=prepare(registered)
    monkeypatch.setattr(w,stage,forbidden)
    with pytest.raises(TransactionAborted): execute(registered,r,clock=Clock())
    assert count(registered)==0


def test_absent_pure(registered,monkeypatch):
    r,f,i=prepare(registered)
    monkeypatch.setattr(w,'_utc_now',forbidden)
    monkeypatch.setattr(w,'_new_execution',forbidden)
    assert reconcile(registered,r).status=='absent'
    assert count(registered)==0

@pytest.mark.parametrize('field',['patient_id','encounter_id'])
def test_foreign_scope_before_decode(registered,field):
    r,f,i=prepare(registered); execute(registered,r,clock=Clock())
    with registered.begin() as conn: conn.execute(text("UPDATE micro_antimicrobial_execution SET payload='corrupt'"))
    foreign=change(TARGET,**{field:'foreign'})
    assert store.find_micro_antimicrobial_execution(registered,r.execution_id,target=foreign) is None
    with pytest.raises(StorageIntegrityError): reconcile(registered,r)


def test_shared_adapter_poison_and_closed(registered):
    r,f,i=prepare(registered); saved=execute(registered,r,clock=Clock())
    with pytest.raises(TransactionAborted):
        with execution_transaction(registered) as tx:
            try: tx.micro_antimicrobial_executions.append({},target=TARGET)
            except Exception: pass
    with pytest.raises(TransactionAborted): tx.micro_antimicrobial_executions.find(r.execution_id,target=TARGET)
    assert count(registered)==1


def test_commit_unknown_absent(registered):
    r,f,i=prepare(registered)
    def fail(conn): raise RuntimeError('private commit failure')
    event.listen(registered,'commit',fail)
    try:
        with pytest.raises(TransactionCompletionUnknown): execute(registered,r,clock=Clock())
    finally: event.remove(registered,'commit',fail)
    assert reconcile(registered,r).status=='absent'


def test_unknown_after_committed(registered,monkeypatch):
    from contextlib import contextmanager
    original=w.execution_transaction
    @contextmanager
    def uncertain(engine):
        with original(engine) as tx: yield tx
        raise TransactionCompletionUnknown('uncertain')
    r,f,i=prepare(registered)
    monkeypatch.setattr(w,'execution_transaction',uncertain)
    with pytest.raises(TransactionCompletionUnknown): execute(registered,r,clock=Clock())
    assert reconcile(registered,r).status=='committed_match'

@pytest.mark.parametrize('role',[1,2])
def test_withdrawn_terminal_not_predecessor(registered,role):
    r,f,i=prepare(registered)
    save(registered,revision(f[role],report=change(f[role].report,status='withdrawn',change='corrected')))
    assert execute(registered,r,clock=Clock()).record.decision.outcome=='withheld'

@pytest.mark.parametrize('role',range(4))
def test_corrupt_terminal_fails_not_withheld(registered,role):
    r,f,i=prepare(registered); successor=revision(f[role]); save(registered,successor)
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='broken' WHERE kind=:kind AND fact_id=:id AND revision='2'"),{'kind':successor.kind,'id':successor.id})
    with pytest.raises(StorageIntegrityError): execute(registered,r,clock=Clock())
    assert count(registered)==0

@pytest.mark.parametrize('part',['request','terminal','digest','runtime'])
def test_rehashed_invalid_execution_fails(registered,part):
    import json
    from hashlib import sha256
    r,f,i=prepare(registered); execute(registered,r,clock=Clock())
    with registered.begin() as conn:
        data=json.loads(conn.execute(text('SELECT payload FROM micro_antimicrobial_execution')).scalar_one())
        if part=='request': data['request']['expected_inference_digest']='0'*64
        elif part=='terminal': data['final_recheck']['evidence'][0]['terminal']['id']='other'
        elif part=='digest': data['context_digest']='0'*64
        else: data['runtime']['finalized_at']='2000-01-01T00:00:00+00:00'
        from app.persistence.canonical import canonical_payload
        payload=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        conn.execute(text('UPDATE micro_antimicrobial_execution SET payload=:p,payload_digest=:d'),{'p':payload,'d':sha256(payload.encode()).hexdigest()})
    with pytest.raises(StorageIntegrityError): reconcile(registered,r)


def test_immutable_contract_and_roundtrip(registered):
    from pydantic import ValidationError
    r,f,i=prepare(registered)
    result=execute(registered,r,clock=Clock())
    for obj,field in [(r,'actor'),(r.inference_request.specimen_ref,'expected_digest'),(result.record,'request'),(result.record.final_recheck.terminal_facts[0],'id')]:
        with pytest.raises((ValidationError,c.MicroAntimicrobialExecutionError)): setattr(obj,field,None)
    assert c.same(result.record,type(result.record).model_validate_json(c.canonical_payload(result.record)))

@pytest.mark.parametrize('fail',[False,True])
def test_additive_migration_preserves_old_storage(tmp_path,monkeypatch,fail):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect
    from app.persistence.database import create_database
    from app.persistence import database as db
    from test_persistence import ROOT, patient, encounter
    engine=create_database(tmp_path/'upgrade.sqlite3')
    cfg=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        cfg.attributes['connection']=conn; command.upgrade(cfg,'m6_0006')
    with monkeypatch.context() as m:
        m.setattr(db,'SCHEMA_REVISION','m6_0006')
        with transaction(engine) as repo:
            repo.register_patient(patient());repo.register_encounter(encounter())
        save(engine,*selected())
    def snapshot():
        with engine.connect() as conn:
            return {name:conn.execute(text('SELECT * FROM '+name)).all() for name in inspect(conn).get_table_names()}
    before=snapshot()
    def crash(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('CREATE TABLE micro_antimicrobial_execution'): raise RuntimeError('migration interruption')
    if fail: event.listen(engine,'after_cursor_execute',crash)
    try:
        if fail:
            with pytest.raises(RuntimeError),engine.begin() as conn:
                cfg.attributes['connection']=conn;command.upgrade(cfg,'head')
            assert snapshot()==before
        else:
            with engine.begin() as conn:
                cfg.attributes['connection']=conn;command.upgrade(cfg,'head')
            after=snapshot()
            assert set(after)-set(before)=={'micro_antimicrobial_execution','circulatory_execution', 'm10_command', 'm10_attachment'}
            assert all(after[k]==v for k,v in before.items() if k!='alembic_version')
            assert after['alembic_version']==[('m10_0011',)]
    finally:
        if fail:event.remove(engine,'after_cursor_execute',crash)
        engine.dispose()


def test_schema_head_and_metadata(database):
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.persistence.entities import Base
    from test_persistence import ROOT
    scripts=ScriptDirectory.from_config(Config(str(ROOT/'backend/alembic.ini')))
    assert scripts.get_heads()==['m10_0011']
    assert scripts.get_revision('m6_0007').down_revision=='m6_0006'
    with database.connect() as conn: assert compare_metadata(MigrationContext.configure(conn),Base.metadata)==[]

@pytest.mark.parametrize('role',range(4))
def test_future_successor_excluded_at_fixed_final_cutoff(registered,role):
    r,f,i=prepare(registered)
    with execution_transaction(registered) as tx:
        evidence,reconstruction=w._replay(tx.repository,r)
        final=tx.repository.capture_cutoff()
    save(registered,revision(f[role]))
    with execution_transaction(registered) as tx:
        checked=w._final_recheck(tx.repository,evidence,reconstruction,final)
    assert checked.outcome=='unchanged'
    assert checked.evidence[role].terminal==f[role].reference

@pytest.mark.parametrize('withheld',[False,True])
def test_retained_after_later_changes_and_expiry_is_readonly(registered,withheld):
    r,f,i=prepare(registered)
    if withheld: save(registered,revision(f[0]))
    original=execute(registered,r,clock=Clock())
    save(registered,revision(f[2]))
    save(registered,change(i,revision='2',supersedes=i.reference,correction_reason='later inference'))
    statements=[]
    def sql(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
    event.listen(registered,'before_cursor_execute',sql)
    try: recovered=reconcile(registered,r)
    finally:event.remove(registered,'before_cursor_execute',sql)
    assert recovered.stored==original
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for s in statements)
    assert not any('fact_revision' in s for s in statements)
    assert recovered.stored.ingested_at==original.ingested_at
    assert recovered.stored.record.runtime.finalized_at==original.record.runtime.finalized_at


def test_append_then_failure_rolls_back(registered,monkeypatch):
    r,f,i=prepare(registered); original=store._append
    def fail(*a,**k):
        original(*a,**k)
        raise RuntimeError('injected after flush')
    monkeypatch.setattr(store,'_append',fail)
    with pytest.raises(TransactionAborted): execute(registered,r,clock=Clock())
    assert count(registered)==0


def test_same_transaction_idempotency_and_receipt(registered):
    r,f,i=prepare(registered); result=execute(registered,r,clock=Clock())
    with execution_transaction(registered) as tx:
        first=tx.micro_antimicrobial_executions.append(result.record,target=TARGET)
        second=tx.micro_antimicrobial_executions.append(result.record,target=TARGET)
        assert first==second==result
    assert count(registered)==1

@pytest.mark.parametrize('handle',['connection','session'])
def test_standalone_rejects_owned_handles(registered,handle):
    from sqlalchemy.orm import Session
    from app.persistence.errors import PersistenceInputError
    r,f,i=prepare(registered)
    with (registered.connect() if handle=='connection' else Session(registered)) as owned:
        with pytest.raises(PersistenceInputError):store.find_micro_antimicrobial_execution(owned,r.execution_id,target=TARGET)


def test_assembly_digest_tamper_fails(registered):
    r,f,i=prepare(registered)
    altered=change(r,inference_request=change(r.inference_request,expected_assembly_digest='0'*64))
    with pytest.raises(StorageIntegrityError):execute(registered,altered,clock=Clock())
    assert count(registered)==0


def test_process_control_cleanup(registered,monkeypatch):
    r,f,i=prepare(registered)
    def interrupt(*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(w,'_final_recheck',interrupt)
    with pytest.raises(KeyboardInterrupt):execute(registered,r,clock=Clock())
    assert count(registered)==0
