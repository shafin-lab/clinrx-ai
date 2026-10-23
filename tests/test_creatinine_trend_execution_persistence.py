from test_persistence import assert_fact_kind_extension_only
"""D2 real SQLite durability and additive schema evidence; synthetic only."""
from contextlib import ExitStack
from dataclasses import replace as dc_replace
from datetime import timedelta, timezone
from decimal import Decimal
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

from app.execution.creatinine_trend import compare_recorded_creatinine, CreatinineTrendExclusion
from app.execution.creatinine_trend_execution import (
    CreatinineTrendExecutionRecord, CreatinineTrendInferenceTerminalCheck,
    assess_creatinine_trend_final_recheck, creatinine_trend_lineage_witness,
)
from app.persistence import creatinine_executions as adapter
from app.persistence.creatinine_executions import (
    append_creatinine_trend_execution as append, load_creatinine_trend_execution as load,
    find_creatinine_trend_execution as find,
)
from app.persistence.database import create_database
from app.persistence.entities import Base, SCHEMA_REVISION, PAYLOAD_VERSION
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch, SchemaMismatch,
    StorageIntegrityError, TransactionAborted, UnsupportedOperation,
)
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import ROOT, TARGET, AT, database, registered, migrate, patient, encounter, fact, replace
from test_revision_chains import revision
from test_creatinine_trend_execution import record
from test_creatinine_trend_inference import build
from test_creatinine_trend_release import evidence, compose, NOW

TABLE = 'creatinine_trend_execution'


@pytest.fixture
def case(registered):
    return evidence(registered, '1.00', '1.200')


def make_record(case, variant='released'):
    witness = creatinine_trend_lineage_witness(case['lineage'])
    digest = next(n.payload_digest for n in witness.nodes if n.reference == witness.root)
    cutoff = case['lineage'].cutoff
    terminal = CreatinineTrendInferenceTerminalCheck(target=TARGET, historical_cutoff=cutoff, cutoff=cutoff,
        consumed=witness.root, consumed_payload_digest=digest, terminal=witness.root, terminal_payload_digest=digest)
    final = replace(case['selection'], cutoff=cutoff)
    check = assess_creatinine_trend_final_recheck(original=case['selection'], final=final, inference_terminal=terminal)
    return record(case, check=check, **({'actor':'synthetic-denied'} if variant == 'withheld' else {}))


def changed_measurement_case(case):
    a, b = case['selection'].selected
    a = replace(a, value=replace(a.value, value=replace(a.value.value, value=Decimal('1.000'))))
    selection = replace(case['selection'], selected=(a, b))
    inference = build(selection)
    by_ref = {f.reference:f for f in (a,b,inference)}
    graph = dc_replace(case['lineage'], nodes=tuple(dc_replace(n, stored=dc_replace(n.stored,
        fact=by_ref[n.stored.fact.reference])) for n in case['lineage'].nodes))
    return compose({**case, 'selection':selection, 'comparison':compare_recorded_creatinine(selection),
        'inference':inference, 'lineage':graph})


def row(engine):
    with engine.connect() as conn:
        return dict(conn.execute(text(f'SELECT * FROM {TABLE}')).mappings().one())


def write_payload(engine, payload):
    with engine.begin() as conn:
        conn.execute(text(f'UPDATE {TABLE} SET payload=:p,payload_digest=:d'),
            {'p':payload,'d':sha256(payload.encode('utf-8')).hexdigest()})


def mutate_payload(engine, change):
    data = json.loads(row(engine)['payload'])
    change(data)
    write_payload(engine, json.dumps(data, sort_keys=True, separators=(',',':'), ensure_ascii=False))


def assert_private(error):
    formatted = ''.join(traceback.format_exception(error))
    for secret in ('CONFIDENTIAL_SYNTHETIC', 'SELECT ', 'INSERT INTO', 'UPDATE creatinine',
                   'input_value=', '"earlier_value"', '"patient_id"'):
        assert secret not in formatted
    assert error.__cause__ is None


@pytest.mark.parametrize('variant', ['released','withheld'])
def test_append_load_find_reopen_exact_record(case, registered, variant):
    original = make_record(case,variant)
    saved = append(registered,original,target=TARGET)
    retained = row(registered)
    assert retained == dict(execution_id=str(original.execution_id), patient_id=TARGET.patient_id,
        encounter_id=TARGET.encounter_id, payload_version=1, payload=canonical_payload(original),
        payload_digest=sha256(canonical_payload(original).encode()).hexdigest(), ingested_at=saved.ingested_at.isoformat())
    assert saved.record.disposition == 'completed_'+variant
    assert saved.ingested_at.utcoffset() == timedelta(0)
    assert load(registered,original.execution_id,target=TARGET) == find(registered,original.execution_id,target=TARGET) == saved
    registered.dispose()
    reopened = create_database(registered.url.database)
    try:
        recovered = load(reopened,original.execution_id,target=TARGET)
        assert canonical_payload(recovered) == canonical_payload(saved)
        assert append(reopened,original,target=TARGET) == saved
        assert row(reopened) == retained
        assert str(recovered.record.comparison.earlier_value) == '1.00'
        assert str(recovered.record.comparison.later_value) == '1.200'
        assert recovered.record.comparison.earlier_sample_time.isoformat() == AT.isoformat()
        assert [s.identifier for s in recovered.record.original.selected_samples] == ['sample-a','sample-b']
        assert [n.reference.id for n in recovered.record.lineage.nodes] == ['b','a','creatinine-i1']
        assert recovered.record.decision.assessment.assessor == 'SyntheticCreatinineProtectedExecution/v1'
    finally:
        reopened.dispose()


def test_retry_preserves_assigned_metadata_and_performs_no_dml(case,registered,monkeypatch):
    original = make_record(case)
    assigned = AT.astimezone(timezone.utc)
    monkeypatch.setattr(adapter,'_now',lambda:assigned)
    saved = append(registered,original,target=TARGET)
    statements = []
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    def forbidden(): pytest.fail('retry assigned a new ingestion time')
    monkeypatch.setattr(adapter,'_now',forbidden)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        equivalent = CreatinineTrendExecutionRecord.model_validate_json(canonical_payload(original))
        assert append(registered,original,target=TARGET) == append(registered,equivalent,target=TARGET) == saved
        assert load(registered,original.execution_id,target=TARGET) == saved
        assert find(registered,original.execution_id,target=TARGET) == saved
    finally: event.remove(registered,'before_cursor_execute',capture)
    assert saved.ingested_at == assigned
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for s in statements)


@pytest.mark.parametrize('part', ['actor','decision','manifest','comparison','lineage','recheck','finalized','requested'])
def test_valid_changed_full_content_conflicts(case,registered,part):
    original = make_record(case)
    append(registered,original,target=TARGET)
    before = row(registered)
    if part in ('actor','decision'): changed = make_record(case,'withheld')
    elif part == 'comparison': changed = make_record(changed_measurement_case(case))
    elif part == 'lineage':
        nodes = original.lineage.nodes
        node = replace(nodes[0], ingestion=replace(nodes[0].ingestion, ingested_at=NOW))
        changed = replace(original,lineage=replace(original.lineage,nodes=(node,*nodes[1:])))
    elif part == 'manifest':
        exclusion = CreatinineTrendExclusion(reference=replace(original.original.selected[0],id='outside'), reason='outside_sample_window')
        manifest = replace(original.original, exclusions=(exclusion,))
        changed = replace(original, original=manifest, final_recheck=replace(original.final_recheck,original=manifest))
    elif part == 'recheck':
        check = original.final_recheck
        cutoff = replace(check.final.cutoff,captured_at=NOW)
        changed = replace(original,final_recheck=replace(check,final=replace(check.final,cutoff=cutoff),
            inference_terminal=replace(check.inference_terminal,cutoff=cutoff)))
    elif part == 'finalized': changed = replace(original,finalized_at=original.finalized_at+timedelta(seconds=1))
    else: changed = replace(original,requested_at=original.requested_at-timedelta(seconds=1))
    assert canonical_payload(changed) != before['payload']
    with pytest.raises(RecordConflict) as caught: append(registered,changed,target=TARGET)
    assert_private(caught.value)
    assert row(registered) == before


@pytest.mark.parametrize('scope', ['missing','patient','encounter'])
def test_foreign_corruption_never_decoded(case,registered,monkeypatch,scope):
    original=make_record(case)
    append(registered,original,target=TARGET)
    write_payload(registered,'CONFIDENTIAL_SYNTHETIC_BAD_JSON')
    target = {'missing':replace(TARGET,patient_id='absent',encounter_id='absent'),
        'patient':replace(TARGET,patient_id='synthetic-p2',encounter_id='synthetic-e3'),
        'encounter':replace(TARGET,encounter_id='synthetic-e2')}[scope]
    def forbidden(*args): pytest.fail('foreign payload decoded')
    monkeypatch.setattr(adapter,'_decode',forbidden)
    for identity in (original.execution_id,uuid4()):
        assert find(registered,identity,target=target) is None
        with pytest.raises(RecordNotFound) as caught: load(registered,identity,target=target)
        assert str(caught.value) == 'execution not found in requested context'
        assert_private(caught.value)


def test_cross_scope_collision_does_not_decode_foreign_row(case,registered,monkeypatch):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text(f"UPDATE {TABLE} SET patient_id='synthetic-p2',encounter_id='synthetic-e3',payload='CONFIDENTIAL_SYNTHETIC'"))
    def forbidden(*args): pytest.fail('foreign payload decoded')
    monkeypatch.setattr(adapter,'_decode',forbidden)
    with pytest.raises(RecordConflict) as caught: append(registered,original,target=TARGET)
    assert_private(caught.value)
    assert row(registered)['patient_id'] == 'synthetic-p2'


@pytest.mark.parametrize('part', ['digest','json','truncated','version','id','patient','encounter',
    'ingested_naive','ingested_offset','ingested_invalid','ingested_z'])
def test_corrupt_envelope_fails_safely(case,registered,part):
    original=make_record(case)
    append(registered,original,target=TARGET)
    target, identity = TARGET, original.execution_id
    fields = {'digest':('payload_digest','0'*64), 'json':('payload','CONFIDENTIAL_SYNTHETIC'),
        'truncated':('payload',row(registered)['payload'][:-10]), 'version':('payload_version',2),
        'id':('execution_id',str(uuid4())), 'patient':('patient_id','synthetic-p2'),
        'encounter':('encounter_id','synthetic-e2'), 'ingested_naive':('ingested_at','2026-10-04T12:00:00'),
        'ingested_offset':('ingested_at',AT.isoformat()), 'ingested_invalid':('ingested_at','CONFIDENTIAL_SYNTHETIC'),
        'ingested_z':('ingested_at','2026-10-04T12:00:00Z')}
    field,value=fields[part]
    with registered.begin() as conn:
        conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
        if part=='patient':
            conn.execute(text(f"UPDATE {TABLE} SET patient_id='synthetic-p2',encounter_id='synthetic-e3'"))
            target=replace(TARGET,patient_id='synthetic-p2',encounter_id='synthetic-e3')
        else: conn.execute(text(f'UPDATE {TABLE} SET {field}=:v'),{'v':value})
        if part in ('json','truncated'):
            conn.execute(text(f'UPDATE {TABLE} SET payload_digest=:d'),{'d':sha256(value.encode()).hexdigest()})
    if part=='id': identity=UUID(value)
    if part=='encounter': target=replace(TARGET,encounter_id=value)
    for lookup in (load,find):
        with pytest.raises(StorageIntegrityError) as caught: lookup(registered,identity,target=target)
        assert_private(caught.value)


@pytest.mark.parametrize('part', ['typed','workflow','chronology','bool_version','version','uuid','repository',
    'decimal','offset','lineage','sample','recheck','decision','ordinal'])
def test_rehashed_contract_corruption_rejected(case,registered,part):
    original=make_record(case)
    append(registered,original,target=TARGET)
    def corrupt(d):
        if part=='typed': d['actor']=''
        elif part=='workflow': d['decision']['assessment']['assessor']='CONFIDENTIAL_SYNTHETIC'
        elif part=='chronology': d['started_at']='2099-01-01T00:00:00+00:00'
        elif part=='bool_version': d['payload_version']=True
        elif part=='version': d['payload_version']=2
        elif part=='uuid': d['execution_id']='CONFIDENTIAL_SYNTHETIC'
        elif part=='repository':
            def walk(v):
                if isinstance(v,dict):
                    for k,c in v.items():
                        if k=='repository_id': v[k]='00000000-0000-4000-8000-000000000099'
                        else: walk(c)
                elif isinstance(v,list):
                    for c in v: walk(c)
            walk(d)
        elif part=='decimal': d['comparison']['earlier_value']='1.0'
        elif part=='offset': d['comparison']['earlier_sample_time']=AT.astimezone(timezone.utc).isoformat()
        elif part=='lineage': d['lineage']['nodes'].reverse()
        elif part=='sample': d['original']['selected_samples'][0]['identifier']='another'
        elif part=='recheck': d['final_recheck']['policy']['version']='2'
        elif part=='decision': d['decision']['outcome']='withheld'
        else: d['lineage']['nodes'][0]['ingestion']['ingestion_sequence']=False
    mutate_payload(registered,corrupt)
    for operation in ('load','find','retry'):
        with pytest.raises(StorageIntegrityError) as caught:
            if operation=='retry': append(registered,original,target=TARGET)
            else: (load if operation=='load' else find)(registered,original.execution_id,target=TARGET)
        assert_private(caught.value)


@pytest.mark.parametrize('form', ['whitespace','duplicate','numeric_decimal'])
def test_noncanonical_payload_rejected_even_with_matching_digest(case,registered,form):
    original=make_record(case)
    append(registered,original,target=TARGET)
    payload=row(registered)['payload']
    if form=='whitespace': payload=json.dumps(json.loads(payload),indent=2)
    elif form=='duplicate': payload='{"payload_version":1,'+payload[1:]
    else: payload=payload.replace('"1.00"','1.00')
    write_payload(registered,payload)
    with pytest.raises(StorageIntegrityError): load(registered,original.execution_id,target=TARGET)


@pytest.mark.parametrize('part',['raw_dict','forged','bool_version','scope','uuid','target'])
def test_invalid_inputs_are_bounded_and_write_nothing(case,registered,part):
    original=make_record(case)
    malformed=original.model_copy(update={'actor':'','decision':'CONFIDENTIAL_SYNTHETIC'})
    invalid_id='CONFIDENTIAL_SYNTHETIC'
    with pytest.raises((PersistenceInputError,ScopeMismatch)) as caught:
        if part=='raw_dict': append(registered,original.model_dump(),target=TARGET)
        elif part=='forged': append(registered,malformed,target=TARGET)
        elif part=='bool_version': append(registered,original.model_copy(update={'payload_version':True}),target=TARGET)
        elif part=='scope': append(registered,original,target=replace(TARGET,encounter_id='synthetic-e2'))
        elif part=='uuid': load(registered,invalid_id,target=TARGET)
        else: find(registered,original.execution_id,target={'patient_id':''})
    assert_private(caught.value)
    with registered.connect() as conn: assert conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar_one()==0


@pytest.mark.parametrize('part',['patient','encounter','wrong_owner'])
def test_append_requires_registered_owner(case,registered,part):
    original=make_record(case)
    with registered.begin() as conn:
        conn.execute(text('DELETE FROM revision_link'))
        conn.execute(text('DELETE FROM fact_revision'))
        if part=='wrong_owner': conn.execute(text("UPDATE encounter SET patient_id='synthetic-p2' WHERE encounter_id='synthetic-e1'"))
        else:
            conn.execute(text("DELETE FROM encounter WHERE patient_id='synthetic-p1'"))
            if part=='patient': conn.execute(text("DELETE FROM patient WHERE patient_id='synthetic-p1'"))
    with pytest.raises(RecordNotFound): append(registered,original,target=TARGET)


@pytest.mark.parametrize('table',['patient','encounter'])
def test_malformed_parent_registration_is_integrity_error(case,registered,table):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn: conn.execute(text(f"UPDATE {table} SET payload='{{}}'"))
    for operation in ('append','load'):
        with pytest.raises(StorageIntegrityError) as caught:
            if operation=='append': append(registered,original,target=TARGET)
            else: load(registered,original.execution_id,target=TARGET)
        assert_private(caught.value)


@pytest.mark.parametrize('sql',["DELETE FROM repository_identity", "UPDATE repository_identity SET repository_id='invalid'", "UPDATE repository_identity SET repository_id='00000000-0000-4000-8000-000000000099'"])
def test_repository_ownership(case,registered,sql):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn: conn.execute(text(sql))
    with pytest.raises(StorageIntegrityError): load(registered,original.execution_id,target=TARGET)
    with pytest.raises((StorageIntegrityError,ScopeMismatch)): append(registered,original,target=TARGET)


@pytest.mark.parametrize('operation',['append','load','find'])
@pytest.mark.parametrize('handle_kind',['active_connection','idle_connection','session'])
def test_engine_only_boundary(case,registered,operation,handle_kind):
    original=make_record(case)
    with ExitStack() as stack:
        handle=stack.enter_context(Session(registered) if handle_kind=='session' else registered.connect())
        if handle_kind=='active_connection': stack.enter_context(handle.begin())
        statements=[]
        def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
        event.listen(registered,'before_cursor_execute',capture)
        try:
            with pytest.raises(PersistenceInputError,match='Engine'):
                if operation=='append': append(handle,original,target=TARGET)
                else: (load if operation=='load' else find)(handle,original.execution_id,target=TARGET)
            assert statements==[]
        finally: event.remove(registered,'before_cursor_execute',capture)


def test_fact_history_lineage_and_allocator_isolation(case,registered):
    original=make_record(case)
    with transaction(registered) as repo:
        cutoff=repo.capture_cutoff()
        history=repo.list_history(target=TARGET,cutoff=cutoff)
        graph=repo.resolve_lineage(original.inference,target=TARGET,cutoff=cutoff,limits=LineageLimits())
    append(registered,original,target=TARGET)
    append(registered,original,target=TARGET)
    load(registered,original.execution_id,target=TARGET)
    find(registered,original.execution_id,target=TARGET)
    with pytest.raises(RecordConflict): append(registered,replace(original,finalized_at=NOW+timedelta(seconds=2)),target=TARGET)
    with transaction(registered) as repo:
        assert repo.capture_cutoff().fact_watermark==cutoff.fact_watermark
        assert repo.list_history(target=TARGET,cutoff=cutoff)==history
        assert repo.resolve_lineage(original.inference,target=TARGET,cutoff=cutoff,limits=LineageLimits())==graph
        next_fact=repo.append_fact(fact(id='after-execution'),target=TARGET)
        assert next_fact.ingestion.ingestion_sequence==cutoff.fact_watermark+1


def test_later_revision_does_not_refresh_recovery(case,registered,monkeypatch):
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    with transaction(registered) as repo: repo.append_revision(revision(case['selection'].selected[0],'later'),target=TARGET)
    import app.execution.creatinine_trend as trend
    import app.execution.creatinine_trend_release as release
    import app.execution.creatinine_trend_execution as execution
    def forbidden(*args,**kwargs): pytest.fail('load ran current clinical work')
    for module,name in [(trend,'select_creatinine_observations'),(release,'release_creatinine_trend'),
                        (release,'assess_creatinine_trend_context'),(execution,'assess_creatinine_trend_final_recheck')]:
        monkeypatch.setattr(module,name,forbidden)
    assert load(registered,original.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('seed',['1','8675309'])
def test_separate_process_reopen_after_retry(case,registered,seed):
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    assert append(registered,original,target=TARGET)==saved
    registered.dispose()
    script='''
import sys
from app.persistence.database import create_database
from app.persistence.creatinine_executions import load_creatinine_trend_execution
from app.persistence.mapping import canonical_payload
from app.models.clinical.common import ContextTarget
engine=create_database(sys.argv[1])
try:
    stored=load_creatinine_trend_execution(engine,sys.argv[2],target=ContextTarget(patient_id='synthetic-p1',encounter_id='synthetic-e1'))
    print(canonical_payload(stored))
finally:
    engine.dispose()
'''
    result=subprocess.run([sys.executable,'-c',script,registered.url.database,str(original.execution_id)],
        text=True,capture_output=True,check=True,timeout=30,
        env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert result.stdout.strip()==canonical_payload(saved)


def test_immutable_return(case,registered):
    stored=append(registered,make_record(case),target=TARGET)
    with pytest.raises(ValidationError): stored.ingested_at=NOW
    with pytest.raises(ValidationError): stored.record.actor='other'
    with pytest.raises(ValidationError): stored.record.original.selected_samples[0].identifier='other'


def test_sql_failure_rolls_back_and_sanitizes(case,registered):
    original=make_record(case)
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('INSERT INTO CREATININE_TREND_EXECUTION'):
            raise OperationalError('CONFIDENTIAL_SYNTHETIC SQL',{},Exception('CONFIDENTIAL_SYNTHETIC'))
    event.listen(registered,'after_cursor_execute',fail)
    try:
        with pytest.raises(TransactionAborted) as caught: append(registered,original,target=TARGET)
        assert_private(caught.value)
    finally: event.remove(registered,'after_cursor_execute',fail)
    assert find(registered,original.execution_id,target=TARGET) is None


def test_unmigrated_store_rejected(tmp_path):
    engine=create_database(tmp_path/'unmigrated.sqlite3')
    try:
        with pytest.raises(SchemaMismatch) as caught: find(engine,uuid4(),target=TARGET)
        assert_private(caught.value)
        with engine.connect() as conn: assert inspect(conn).get_table_names()==[]
    finally: engine.dispose()


def test_schema_exact(database):
    with database.connect() as conn:
        schema=inspect(conn)
        assert SCHEMA_REVISION=='m9_0010' and PAYLOAD_VERSION==1
        assert {c['name'] for c in schema.get_columns(TABLE)}=={
            'execution_id','patient_id','encounter_id','payload_version','payload','payload_digest','ingested_at'}
        assert all(not c['nullable'] for c in schema.get_columns(TABLE))
        assert schema.get_pk_constraint(TABLE)['constrained_columns']==['execution_id']
        assert schema.get_unique_constraints(TABLE)==[] and schema.get_indexes(TABLE)==[]
        assert schema.get_check_constraints(TABLE)==[{'sqltext':'payload_version = 1','name':'ck_creatinine_execution_payload_version'}]
        fk=schema.get_foreign_keys(TABLE)
        assert len(fk)==1 and fk[0]['name']=='fk_creatinine_execution_encounter_owner'
        assert fk[0]['constrained_columns']==['encounter_id','patient_id']
        assert fk[0]['referred_table']=='encounter' and fk[0]['referred_columns']==['encounter_id','patient_id']
        assert fk[0]['options'].get('ondelete') in (None,'NO ACTION')
        assert compare_metadata(MigrationContext.configure(conn),Base.metadata)==[]
    scripts=ScriptDirectory.from_config(Config(str(ROOT/'backend/alembic.ini')))
    assert scripts.get_heads()==['m9_0010']
    assert scripts.get_revision('7b2_0004').down_revision=='7b1_0003'


def prior_database(tmp_path,monkeypatch,populated):
    from app.persistence import database as db_module
    engine=create_database(tmp_path/'prior.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn
        command.upgrade(config,'7b1_0003')
    saved=None
    if populated:
        from test_weight_trend_execution_persistence import make_record as weight_record
        from test_weight_trend_release import evidence as weight_evidence
        from app.persistence.executions import append_weight_trend_execution
        with monkeypatch.context() as m:
            m.setattr(db_module,'SCHEMA_REVISION','7b1_0003')
            with transaction(engine) as repo:
                repo.register_patient(patient())
                repo.register_encounter(encounter())
            weight=weight_evidence(engine)
            saved=append_weight_trend_execution(engine,weight_record(weight),target=TARGET)
            with transaction(engine) as repo: repo.append_revision(revision(weight['selection'].selected[0],'later'),target=TARGET)
    return engine,saved


def retained_storage(engine):
    with engine.connect() as conn:
        names=('repository_identity','patient','encounter','fact_revision','revision_link','sqlite_sequence','weight_trend_execution')
        rows={name:conn.execute(text(f'SELECT * FROM {name}')).all() for name in names}
        ddl=conn.execute(text("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') AND name != 'alembic_version' ORDER BY name")).all()
        return rows,ddl


@pytest.mark.parametrize('populated',[False,True])
def test_upgrade_preserves_existing_schema_payloads_and_watermark(tmp_path,monkeypatch,populated):
    engine,saved=prior_database(tmp_path,monkeypatch,populated)
    try:
        before,ddl=retained_storage(engine)
        with pytest.raises(SchemaMismatch): find(engine,uuid4(),target=TARGET)
        migrate(engine)
        after,newddl=retained_storage(engine)
        assert after==before
        assert_fact_kind_extension_only(ddl, newddl)
        assert {entry[0] for entry in newddl}-{entry[0] for entry in ddl}=={TABLE,'sqlite_autoindex_'+TABLE+'_1','patient_state_temporal_execution','sqlite_autoindex_patient_state_temporal_execution_1','micro_antimicrobial_execution','sqlite_autoindex_micro_antimicrobial_execution_1','circulatory_execution','sqlite_autoindex_circulatory_execution_1'}
        migrate(engine)
        assert retained_storage(engine)==(after,newddl)
        with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==(4 if populated else 0)
        with engine.connect() as conn: assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='m9_0010'
        if saved is not None:
            from app.persistence.executions import load_weight_trend_execution
            assert load_weight_trend_execution(engine,saved.record.execution_id,target=TARGET)==saved
    finally: engine.dispose()


def test_migration_failure_rolls_back_new_table_and_head(tmp_path,monkeypatch):
    engine,_=prior_database(tmp_path,monkeypatch,True)
    before=retained_storage(engine)
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('CREATE TABLE '+TABLE): raise RuntimeError('injected D2 migration failure')
    event.listen(engine,'after_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError,match='injected'): migrate(engine)
        assert retained_storage(engine)==before
        with engine.connect() as conn:
            assert TABLE not in inspect(conn).get_table_names()
            assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='7b1_0003'
    finally:
        event.remove(engine,'after_cursor_execute',fail)
        engine.dispose()


def test_downgrade_refused_and_owner_fk_enforced(case,registered):
    original=make_record(case)
    append(registered,original,target=TARGET)
    before=row(registered)
    config=Config(str(ROOT/'backend/alembic.ini'))
    with pytest.raises(RuntimeError,match='destructive downgrade'):
        with registered.begin() as conn:
            config.attributes['connection']=conn
            command.downgrade(config,'7b1_0003')
    assert row(registered)==before
    for sql in (f"UPDATE {TABLE} SET patient_id='synthetic-p2'", "DELETE FROM encounter WHERE encounter_id='synthetic-e1'"):
        with pytest.raises(IntegrityError),registered.begin() as conn: conn.execute(text(sql))


def test_no_workflow_or_weight_dependency():
    source=Path(adapter.__file__).read_text()
    imports=[n.module for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ImportFrom)]
    assert not any('weight' in name or 'workflow' in name for name in imports)
    assert not any(word in source for word in ('TransactionCompletionUnknown','reconcile_', 'capture_cutoff'))
    assert {n.name for n in ast.parse(source).body if isinstance(n,ast.ClassDef)}=={'_CreatinineExecutionAdapter'}



def test_different_output_target_conflicts(case,registered):
    from app.execution.creatinine_trend_execution import WORKFLOW_ASSESSOR, FINAL_CONTEXT_ASSESSOR
    from app.services.governance_service import decide_release
    from test_creatinine_trend_release import run
    original=make_record(case)
    append(registered,original,target=TARGET)
    target=replace(original.target,recipient='different-synthetic-recipient')
    changed_case=compose({**case,'target':target})
    decision=run(changed_case,active_request=target)
    assessment=decision.assessment
    assessment=replace(assessment,assessor=WORKFLOW_ASSESSOR,state=replace(assessment.state,
        freshness=replace(assessment.state.freshness,assessor=FINAL_CONTEXT_ASSESSOR)))
    decision=decide_release(reference=decision.reference,assessment=assessment,actor=original.actor,at=NOW)
    changed=replace(original,target=target,decision=decision)
    with pytest.raises(RecordConflict): append(registered,changed,target=TARGET)
    assert load(registered,original.execution_id,target=TARGET).record==original


def test_large_valid_payload_and_utf8_digest(case,registered):
    original=make_record(case)
    exclusions=tuple(CreatinineTrendExclusion(reference=replace(original.original.selected[0],
        id='outside-µmol-'+str(i)),reason='outside_sample_window') for i in range(400))
    manifest=replace(original.original,exclusions=exclusions)
    larger=replace(original,original=manifest,final_recheck=replace(original.final_recheck,original=manifest))
    saved=append(registered,larger,target=TARGET)
    payload=canonical_payload(larger)
    assert len(payload.encode('utf-8'))>100000
    assert row(registered)['payload_digest']==sha256(payload.encode('utf-8')).hexdigest()
    assert canonical_payload(load(registered,larger.execution_id,target=TARGET))==canonical_payload(saved)


@pytest.mark.parametrize('value',[True,1.0,'1',2])
def test_envelope_payload_version_is_exact_integer(case,registered,value):
    from types import SimpleNamespace
    original=make_record(case)
    append(registered,original,target=TARGET)
    envelope=SimpleNamespace(**{**row(registered),'payload_version':value})
    with pytest.raises(StorageIntegrityError,match='unsupported execution payload version'):
        adapter._decode(envelope,original.repository_id)


def test_one_owned_transaction_per_call(case,registered):
    original=make_record(case)
    statements=[]
    commits=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    def committed(conn): commits.append(True)
    event.listen(registered,'before_cursor_execute',capture)
    event.listen(registered,'commit',committed)
    try:
        for operation in (lambda:append(registered,original,target=TARGET),
                          lambda:load(registered,original.execution_id,target=TARGET),
                          lambda:find(registered,original.execution_id,target=TARGET)):
            statements.clear()
            commits.clear()
            operation()
            assert statements.count('BEGIN IMMEDIATE')==1
            assert commits==[True]
    finally:
        event.remove(registered,'before_cursor_execute',capture)
        event.remove(registered,'commit',committed)


def test_same_uuid_is_capability_qualified(case,registered):
    from test_weight_trend_execution_persistence import make_record as weight_record
    from test_weight_trend_release import evidence as weight_evidence
    from app.persistence.executions import append_weight_trend_execution,load_weight_trend_execution
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    # Separate stable observation families avoid replacing creatinine inputs.
    # The weight fixture uses a/b IDs, so produce its valid record in a separate store
    # and map only repository metadata before importing that supplied contract.
    from app.persistence.database import create_database
    other=create_database(str(registered.url.database)+'.weight')
    try:
        migrate(other)
        with transaction(other) as repo:
            repo.register_patient(patient())
            repo.register_encounter(encounter())
        weight=weight_record(weight_evidence(other))
        data=json.loads(canonical_payload(weight))
        def remap(v):
            if isinstance(v,dict):
                for k,c in v.items():
                    if k=='repository_id': v[k]=str(original.repository_id)
                    else: remap(c)
            elif isinstance(v,list):
                for c in v: remap(c)
        remap(data)
        data['execution_id']=str(original.execution_id)
        weight=type(weight).model_validate(data)
        kept=append_weight_trend_execution(registered,weight,target=TARGET)
        assert load_weight_trend_execution(registered,weight.execution_id,target=TARGET)==kept
        assert load(registered,original.execution_id,target=TARGET)==saved
    finally: other.dispose()
