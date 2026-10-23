"""Real local SQLite execution recovery; synthetic only, no release orchestration."""
from dataclasses import FrozenInstanceError, replace as dc_replace
from datetime import timedelta, timezone
from hashlib import sha256
import json
import os
import subprocess
import sys
import traceback
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.execution.weight_trend_execution import (
    WeightTrendExecutionIssue, WeightTrendExecutionRecord, WeightTrendInferenceTerminalCheck,
    assess_weight_trend_final_recheck, weight_trend_lineage_witness, weight_trend_selection_manifest,
)
from app.execution.weight_trend_release import (
    build_weight_trend_snapshot, build_weight_trend_candidate, render_weight_trend, GRANT_TARGET,
)
from app.models.clinical.common import ContextTarget, Reference
from app.persistence import executions
from app.persistence.database import create_database
from app.persistence.entities import Base, SCHEMA_REVISION, PAYLOAD_VERSION
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch, SchemaMismatch,
    StorageIntegrityError, TransactionAborted,
)
from app.persistence.executions import append_weight_trend_execution as append, load_weight_trend_execution as load
from app.persistence.lineage import UnresolvedReference, LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import ROOT, TARGET, AT, database, registered, migrate, patient, encounter, fact, replace
from test_revision_chains import revision
from test_weight_trend_execution import EXECUTION, withheld_for_context
from test_weight_trend_release import evidence, NOW, run


@pytest.fixture
def case(registered):
    return evidence(registered)


def make_record(case, variant='released'):
    final = replace(case['selection'],cutoff=case['lineage'].cutoff)
    terminal = WeightTrendInferenceTerminalCheck(target=TARGET,cutoff=final.cutoff,
        consumed=case['inference'].reference,terminal=case['inference'].reference)
    recheck = assess_weight_trend_final_recheck(original=case['selection'],final=final,inference_terminal=terminal)
    actor = 'synthetic-denied' if variant == 'withheld' else 'synthetic-orchestrator'
    return WeightTrendExecutionRecord(execution_id=EXECUTION,target=GRANT_TARGET,actor=actor,
        original=weight_trend_selection_manifest(case['selection']),comparison=case['comparison'],
        inference=case['inference'].reference,lineage=weight_trend_lineage_witness(case['lineage']),
        final_recheck=recheck,decision=None if variant == 'failure' else run(case,actor=actor),
        issue=WeightTrendExecutionIssue(stage='governance',code='internal_failure') if variant == 'failure' else None,
        started_at=NOW-timedelta(seconds=1),finalized_at=NOW+timedelta(seconds=1))


def row(engine):
    with engine.connect() as conn:
        return dict(conn.execute(text('SELECT * FROM weight_trend_execution')).mappings().one())


def mutate_payload(engine, change):
    data = json.loads(row(engine)['payload'])
    change(data)
    payload = json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    with engine.begin() as conn:
        conn.execute(text('UPDATE weight_trend_execution SET payload=:p,payload_digest=:d'),
            {'p':payload,'d':sha256(payload.encode()).hexdigest()})


def assert_private(error):
    formatted = ''.join(traceback.format_exception(error))
    for secret in ('CONFIDENTIAL_SYNTHETIC','SELECT *','INSERT INTO','UPDATE weight_trend_execution',
                   'input_value=', '"earlier_kg"', '"patient_id"'):
        assert secret not in formatted


@pytest.mark.parametrize('variant,disposition', [('released','completed_released'),('withheld','completed_withheld'),('failure','failed_operationally')])
def test_persist_load_reopen_exact_variants(case,registered,variant,disposition):
    original = make_record(case,variant)
    saved = append(registered,original,target=TARGET)
    retained = row(registered)
    assert retained['payload'] == canonical_payload(original)
    assert retained['payload_digest'] == sha256(retained['payload'].encode('utf-8')).hexdigest()
    assert saved.ingested_at.utcoffset() == timedelta(0)
    assert saved.record.disposition == disposition
    assert load(registered,original.execution_id,target=TARGET) == saved
    path = registered.url.database
    registered.dispose()
    reopened = create_database(path)
    try:
        recovered = load(reopened,original.execution_id,target=TARGET)
        assert recovered == saved
        assert recovered.record.model_dump_json() == original.model_dump_json()
        assert append(reopened,original,target=TARGET) == saved
        assert row(reopened) == retained
    finally:
        reopened.dispose()


def test_retry_does_not_refresh_metadata_or_write(case,registered,monkeypatch):
    original = make_record(case)
    assigned = AT.astimezone(timezone.utc)
    monkeypatch.setattr(executions,'_now',lambda:assigned)
    saved = append(registered,original,target=TARGET)
    statements = []
    def capture(conn,cursor,statement,parameters,context,executemany):
        statements.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    def forbidden():
        pytest.fail('retry attempted to assign new ingestion time')
    monkeypatch.setattr(executions,'_now',forbidden)
    try:
        assert append(registered,WeightTrendExecutionRecord.model_validate_json(original.model_dump_json()),target=TARGET) == saved
        assert load(registered,original.execution_id,target=TARGET) == saved
    finally:
        event.remove(registered,'before_cursor_execute',capture)
    assert saved.ingested_at == assigned
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for s in statements)


@pytest.mark.parametrize('part', ['actor','decision','recheck','issue','decimal','offset'])
def test_same_id_changed_canonical_content_conflicts(case,registered,part):
    original = make_record(case,'failure' if part in ('issue','decimal','offset','actor') else 'released')
    append(registered,original,target=TARGET)
    before = row(registered)
    if part == 'actor':
        changed = replace(original,actor='another-synthetic-actor')
    elif part == 'decision':
        changed = replace(original,decision=withheld_for_context(original.decision,material=False))
    elif part == 'recheck':
        cutoff = replace(original.final_recheck.final.cutoff,captured_at=original.final_recheck.final.cutoff.captured_at+timedelta(microseconds=1))
        check = replace(original.final_recheck,final=replace(original.final_recheck.final,cutoff=cutoff),
            inference_terminal=replace(original.final_recheck.inference_terminal,cutoff=cutoff))
        changed = replace(original,final_recheck=check)
    elif part == 'issue':
        changed = replace(original,issue=replace(original.issue,code='storage_failure'))
    elif part == 'decimal':
        from decimal import Decimal
        changed = replace(original,comparison=replace(original.comparison,earlier_kg=Decimal('82.00')))
    else:
        changed = replace(original,comparison=replace(original.comparison,
            earlier_event=original.comparison.earlier_event.astimezone(timezone.utc)))
    assert canonical_payload(changed) != canonical_payload(original)
    with pytest.raises(RecordConflict) as caught:
        append(registered,changed,target=TARGET)
    assert_private(caught.value)
    assert row(registered) == before


@pytest.mark.parametrize('target', [ContextTarget(patient_id='absent',encounter_id='absent'),
    ContextTarget(patient_id='synthetic-p2',encounter_id='synthetic-e3'),
    ContextTarget(patient_id='synthetic-p1',encounter_id='synthetic-e2')])
def test_foreign_or_missing_is_same_not_found_before_decode(case,registered,monkeypatch,target):
    original = make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC_BAD_JSON'"))
    def forbidden(*args):
        pytest.fail('foreign or absent execution payload was decoded')
    monkeypatch.setattr(executions,'_decode',forbidden)
    errors = []
    for identity in (original.execution_id,uuid4()):
        with pytest.raises(RecordNotFound) as caught:
            load(registered,identity,target=target)
        errors.append(str(caught.value))
        assert_private(caught.value)
    assert errors == ['execution not found in requested context']*2


@pytest.mark.parametrize('part', ['digest','json','version','id','patient','encounter','ingested_naive','ingested_offset','ingested_invalid'])
def test_corrupt_envelope_fails_safely(case,registered,part):
    original = make_record(case)
    append(registered,original,target=TARGET)
    target,identity = TARGET,original.execution_id
    fields = {'digest':('payload_digest','0'*64),'json':('payload','CONFIDENTIAL_SYNTHETIC_BAD_JSON'),
        'version':('payload_version',2),'id':('execution_id',str(uuid4())),
        'patient':('patient_id','synthetic-p2'),'encounter':('encounter_id','synthetic-e2'),
        'ingested_naive':('ingested_at','2026-09-25T10:00:00'),
        'ingested_offset':('ingested_at',AT.isoformat()),'ingested_invalid':('ingested_at','CONFIDENTIAL_SYNTHETIC')}
    field,value = fields[part]
    with registered.begin() as conn:
        conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
        if part == 'patient':
            # Valid foreign owner tuple, contradictory retained JSON. Query that scope.
            conn.execute(text("UPDATE weight_trend_execution SET patient_id='synthetic-p2',encounter_id='synthetic-e3'"))
            target = ContextTarget(patient_id='synthetic-p2',encounter_id='synthetic-e3')
        else:
            conn.execute(text(f'UPDATE weight_trend_execution SET {field}=:v'),{'v':value})
        if part == 'json':
            conn.execute(text('UPDATE weight_trend_execution SET payload_digest=:d'),{'d':sha256(value.encode()).hexdigest()})
    if part == 'id':
        identity = UUID(value)
    if part == 'encounter':
        target = replace(TARGET,encounter_id=value)
    with pytest.raises(StorageIntegrityError) as caught:
        load(registered,identity,target=target)
    assert_private(caught.value)


@pytest.mark.parametrize('part', ['decision','lineage','manifest','disposition','uuid','repository','payload_version','execution_version','duplicate_identity','provenance'])
def test_rehashed_but_invalid_contract_is_not_trusted(case,registered,part):
    original = make_record(case)
    append(registered,original,target=TARGET)
    def corrupt(d):
        if part == 'decision': d['decision']['outcome']='CONFIDENTIAL_SYNTHETIC'
        elif part == 'lineage': d['lineage']['coverage']='partial'
        elif part == 'manifest': d['original']['selected']=[]
        elif part == 'disposition': d['disposition']='completed_released'
        elif part == 'uuid': d['execution_id']='CONFIDENTIAL_SYNTHETIC'
        elif part == 'repository':
            # Rewrite every embedded repository ID coherently, isolating active-store validation.
            old = str(original.repository_id)
            def walk(value):
                if isinstance(value,dict):
                    for key,child in value.items():
                        if key == 'repository_id' and child == old: value[key]='00000000-0000-4000-8000-000000000099'
                        else: walk(child)
                elif isinstance(value,list):
                    for child in value: walk(child)
            walk(d)
        elif part == 'payload_version': d['payload_version']=2
        elif part == 'execution_version': d['execution_version']='2'
        elif part == 'duplicate_identity': d['original']['selected'][1]=d['original']['selected'][0]
        else: d['lineage']['nodes'][-1]['limitations']=[]
    mutate_payload(registered,corrupt)
    with pytest.raises(StorageIntegrityError) as caught:
        load(registered,original.execution_id,target=TARGET)
    assert_private(caught.value)


@pytest.mark.parametrize('form', ['whitespace','duplicate_key'])
def test_rehashed_noncanonical_json_rejected(case,registered,form):
    original = make_record(case)
    append(registered,original,target=TARGET)
    before = row(registered)['payload']
    payload = json.dumps(json.loads(before),indent=2) if form=='whitespace' else '{"payload_version":1,'+before[1:]
    with registered.begin() as conn:
        conn.execute(text('UPDATE weight_trend_execution SET payload=:p,payload_digest=:d'),
            {'p':payload,'d':sha256(payload.encode()).hexdigest()})
    with pytest.raises(StorageIntegrityError):
        load(registered,original.execution_id,target=TARGET)


def test_retry_validates_corrupt_existing_row_before_comparing(case,registered):
    original = make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
    for candidate in (original,replace(original,finalized_at=original.finalized_at+timedelta(seconds=1))):
        with pytest.raises(StorageIntegrityError):
            append(registered,candidate,target=TARGET)


def test_repository_identity_append_and_reopen_boundary(case,registered):
    original = make_record(case,'failure')
    original = replace(original,lineage=None,final_recheck=None,
        original=replace(original.original,cutoff=replace(original.original.cutoff,repository_id=uuid4())))
    with pytest.raises(ScopeMismatch):
        append(registered,original,target=TARGET)
    valid = make_record(case)
    append(registered,valid,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text('UPDATE repository_identity SET repository_id=:id'),{'id':str(uuid4())})
    with pytest.raises(StorageIntegrityError):
        load(registered,valid.execution_id,target=TARGET)


@pytest.mark.parametrize('kind', ['raw_dict','forged_contract','scope','uuid'])
def test_invalid_inputs_are_sanitized(case,registered,kind):
    original = make_record(case)
    malformed = original.model_copy(update={'actor':'','issue':'CONFIDENTIAL_SYNTHETIC'})
    invalid_id = 'CONFIDENTIAL_SYNTHETIC'
    with pytest.raises((PersistenceInputError,ScopeMismatch)) as caught:
        if kind == 'raw_dict': append(registered,original.model_dump(),target=TARGET)
        elif kind == 'forged_contract': append(registered,malformed,target=TARGET)
        elif kind == 'scope': append(registered,original,target=replace(TARGET,encounter_id='synthetic-e2'))
        else: load(registered,invalid_id,target=TARGET)
    assert_private(caught.value)
    with registered.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM weight_trend_execution')).scalar_one()==0


def test_distinct_ids_and_immutable_return(case,registered):
    original = make_record(case)
    saved = append(registered,original,target=TARGET)
    second = replace(original,execution_id=uuid4())
    assert append(registered,second,target=TARGET).record.execution_id == second.execution_id
    assert load(registered,original.execution_id,target=TARGET) == saved
    with pytest.raises(FrozenInstanceError): saved.ingested_at = NOW
    with pytest.raises(ValidationError): saved.record.actor = 'changed'
    with pytest.raises(ValidationError): saved.record.decision.assessment.review.candidate.claims[0].action = 'changed'


def test_partial_withheld_evidence_round_trip(case,registered):
    graph=case['lineage']
    missing=case['selection'].selected[0].reference
    graph=dc_replace(graph,nodes=tuple(n for n in graph.nodes if n.stored.fact.reference != missing),
        provenance=tuple(p for p in graph.provenance if p.reference != missing),
        ancestry=tuple(a for a in graph.ancestry if a[0] != missing),coverage='partial',
        unresolved=(UnresolvedReference(graph.reference,missing,'dependency',0,None,'not_resolvable_in_scope_at_cutoff'),))
    snapshot=build_weight_trend_snapshot(selection=case['selection'],inference=case['inference'],lineage=graph,
        patient=patient(),encounter=encounter(),at=NOW,id='snapshot')
    candidate=build_weight_trend_candidate(snapshot=snapshot,comparison=case['comparison'],inference=case['inference'],at=NOW,id='candidate')
    rendering=render_weight_trend(candidate=candidate,comparison=case['comparison'],target=GRANT_TARGET,at=NOW,id='rendering')
    changed={**case,'lineage':graph,'snapshot':snapshot,'candidate':candidate,'rendering':rendering}
    original=make_record(changed)
    assert original.disposition=='completed_withheld'
    saved=append(registered,original,target=TARGET)
    recovered=load(registered,original.execution_id,target=TARGET)
    assert recovered==saved
    assert recovered.record.lineage.coverage=='partial'
    assert recovered.record.lineage.unresolved[0].reference==missing


def test_execution_does_not_change_fact_visibility_or_lineage(case,registered):
    with transaction(registered) as repo:
        cutoff=repo.capture_cutoff()
        history=repo.list_history(target=TARGET,cutoff=cutoff)
        latest=repo.list_latest_known(target=TARGET,cutoff=cutoff)
        graph=repo.resolve_lineage(case['inference'].reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())
    original=make_record(case)
    append(registered,original,target=TARGET)
    with transaction(registered) as repo:
        after=repo.capture_cutoff()
        assert (after.repository_id,after.fact_watermark)==(cutoff.repository_id,cutoff.fact_watermark)
        assert repo.list_history(target=TARGET,cutoff=cutoff)==history
        assert repo.list_latest_known(target=TARGET,cutoff=cutoff)==latest
        assert repo.resolve_lineage(case['inference'].reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())==graph
    with pytest.raises(RecordNotFound),transaction(registered) as repo:
        repo.load_fact(Reference(kind='execution',id=str(original.execution_id),version='1'),target=TARGET)
    fact_id=uuid4()
    with transaction(registered) as repo:
        saved=repo.append_fact(fact(id=str(fact_id)),target=TARGET)
        assert saved.ingestion.ingestion_sequence==cutoff.fact_watermark+1
    with pytest.raises(RecordNotFound): load(registered,fact_id,target=TARGET)


def test_later_correction_never_refreshes_loaded_execution(case,registered,monkeypatch):
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    a=case['selection'].selected[0]
    with transaction(registered) as repo:
        repo.append_revision(revision(a,'later'),target=TARGET)
    import app.execution.weight_trend as weight
    import app.execution.weight_trend_release as release
    import app.execution.weight_trend_execution as execution
    def forbidden(*args,**kwargs): pytest.fail('load recomputed execution')
    for module,name in [(weight,'select_weight_observations'),(release,'release_weight_trend'),
        (release,'assess_weight_trend_context'),(execution,'assess_weight_trend_final_recheck')]:
        monkeypatch.setattr(module,name,forbidden)
    assert load(registered,original.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('seed',['1','8675309'])
def test_process_restart_recovers_exact_payload(case,registered,seed):
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    registered.dispose()
    script='''
import sys
from app.persistence.database import create_database
from app.persistence.executions import load_weight_trend_execution
from app.persistence.mapping import canonical_payload
from app.models.clinical.common import ContextTarget
engine=create_database(sys.argv[1])
try:
    stored=load_weight_trend_execution(engine,sys.argv[2],target=ContextTarget(patient_id='synthetic-p1',encounter_id='synthetic-e1'))
    print(canonical_payload(stored.record))
    print(stored.ingested_at.isoformat())
finally:
    engine.dispose()
'''
    process=subprocess.run([sys.executable,'-c',script,registered.url.database,str(original.execution_id)],
        text=True,capture_output=True,check=True,timeout=30,
        env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert process.stdout.splitlines()==[canonical_payload(original),saved.ingested_at.isoformat()]


def test_sql_failure_is_sanitized_and_insert_rolls_back(case,registered):
    original=make_record(case)
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('INSERT INTO WEIGHT_TREND_EXECUTION'):
            raise OperationalError('CONFIDENTIAL_SYNTHETIC SQL',{'secret':'CONFIDENTIAL_SYNTHETIC'},Exception('CONFIDENTIAL_SYNTHETIC'))
    event.listen(registered,'after_cursor_execute',fail)
    try:
        with pytest.raises(TransactionAborted) as caught: append(registered,original,target=TARGET)
        assert_private(caught.value)
    finally:
        event.remove(registered,'after_cursor_execute',fail)
    with pytest.raises(RecordNotFound): load(registered,original.execution_id,target=TARGET)


def test_unmigrated_store_does_not_auto_create_schema(tmp_path):
    engine=create_database(tmp_path/'empty.sqlite3')
    try:
        with pytest.raises(SchemaMismatch) as caught: load(engine,uuid4(),target=TARGET)
        assert_private(caught.value)
        with engine.connect() as conn: assert inspect(conn).get_table_names()==[]
    finally: engine.dispose()


def test_execution_schema_is_one_table_with_owner_fk(database):
    with database.connect() as conn:
        schema=inspect(conn)
        assert SCHEMA_REVISION=='m10_0011' and PAYLOAD_VERSION==1
        assert {c['name'] for c in schema.get_columns('weight_trend_execution')}=={
            'execution_id','patient_id','encounter_id','payload_version','payload','payload_digest','ingested_at'}
        assert schema.get_indexes('weight_trend_execution')==[]
        fk=schema.get_foreign_keys('weight_trend_execution')
        assert len(fk)==1 and fk[0]['constrained_columns']==['encounter_id','patient_id']
        assert fk[0]['referred_table']=='encounter'
        assert fk[0]['options'].get('ondelete') in (None,'NO ACTION')
        assert compare_metadata(MigrationContext.configure(conn),Base.metadata)==[]


def old_populated(tmp_path,monkeypatch):
    from app.persistence import database as db_module
    engine=create_database(tmp_path/'old.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn
        command.upgrade(config,'7a2_0002')
    with monkeypatch.context() as m:
        m.setattr(db_module,'SCHEMA_REVISION','7a2_0002')
        with transaction(engine) as repo:
            repo.register_patient(patient())
            repo.register_encounter(encounter())
        case=evidence(engine)
        with transaction(engine) as repo:
            repo.append_revision(revision(case['selection'].selected[0],'later'),target=TARGET)
    return engine,case


def clinical_storage(engine):
    with engine.connect() as conn:
        return {name:conn.execute(text(f'SELECT * FROM {name}')).all() for name in
            ('repository_identity','patient','encounter','fact_revision','revision_link','sqlite_sequence')}


def test_populated_upgrade_preserves_all_clinical_bytes_and_prefixes(tmp_path,monkeypatch):
    engine,case=old_populated(tmp_path,monkeypatch)
    try:
        before=clinical_storage(engine)
        with pytest.raises(SchemaMismatch): load(engine,EXECUTION,target=TARGET)
        migrate(engine)
        assert clinical_storage(engine)==before
        migrate(engine)
        assert clinical_storage(engine)==before
        with transaction(engine) as repo:
            assert repo.capture_cutoff().fact_watermark==4
            assert repo.load_fact(case['inference'].reference,target=TARGET).fact==case['inference']
            assert repo.resolve_lineage(case['inference'].reference,target=TARGET,
                cutoff=case['lineage'].cutoff,limits=LineageLimits())==case['lineage']
            old=repo.list_latest_known(target=TARGET,cutoff=case['selection'].cutoff)
            assert {s.fact.reference for s in old.records}=={f.reference for f in case['selection'].selected}
        original=make_record(case)
        assert append(engine,original,target=TARGET).record==original
        assert clinical_storage(engine)==before
    finally: engine.dispose()


def test_execution_migration_failure_rolls_back_table_and_version(tmp_path,monkeypatch):
    engine,_=old_populated(tmp_path,monkeypatch)
    before=clinical_storage(engine)
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('CREATE TABLE weight_trend_execution'):
            raise RuntimeError('injected additive migration failure')
    event.listen(engine,'after_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError,match='injected'): migrate(engine)
        assert clinical_storage(engine)==before
        with engine.connect() as conn:
            assert 'weight_trend_execution' not in inspect(conn).get_table_names()
            assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='7a2_0002'
    finally:
        event.remove(engine,'after_cursor_execute',fail)
        engine.dispose()


def test_destructive_downgrade_refused_with_records(case,registered):
    append(registered,make_record(case),target=TARGET)
    before=row(registered)
    config=Config(str(ROOT/'backend/alembic.ini'))
    with pytest.raises(RuntimeError,match='destructive downgrade'):
        with registered.begin() as conn:
            config.attributes['connection']=conn
            command.downgrade(config,'7a2_0002')
    assert row(registered)==before
    with registered.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='m10_0011'


def test_owner_fk_prevents_delete_or_foreign_owner(case,registered):
    append(registered,make_record(case),target=TARGET)
    for sql in ("DELETE FROM encounter WHERE encounter_id='synthetic-e1'",
                "UPDATE weight_trend_execution SET patient_id='synthetic-p2'"):
        with pytest.raises(IntegrityError),registered.begin() as conn: conn.execute(text(sql))


def test_cross_scope_uuid_collision_never_decodes_foreign_payload(case,registered,monkeypatch):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC_BAD_JSON'"))
    foreign=ContextTarget(patient_id='synthetic-p2',encounter_id='synthetic-e3')
    base=make_record(case,'failure')
    other=replace(base,target=replace(base.target,context=foreign),lineage=None,final_recheck=None,
        original=replace(base.original,target=foreign))
    def forbidden(*args): pytest.fail('cross-scope append decoded foreign content')
    monkeypatch.setattr(executions,'_decode',forbidden)
    with pytest.raises(RecordConflict) as caught: append(registered,other,target=foreign)
    assert str(caught.value)=='execution identity already has different content'
    assert_private(caught.value)
    assert row(registered)['patient_id']==TARGET.patient_id


@pytest.mark.parametrize('target', [ContextTarget(patient_id='absent',encounter_id='absent'),
    ContextTarget(patient_id='synthetic-p2',encounter_id='synthetic-e1')])
def test_append_requires_registered_encounter_ownership(case,registered,target):
    base=make_record(case,'failure')
    other=replace(base,target=replace(base.target,context=target),lineage=None,final_recheck=None,
        original=replace(base.original,target=target))
    with pytest.raises(RecordNotFound): append(registered,other,target=target)
    with registered.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM weight_trend_execution')).scalar_one()==0


@pytest.mark.parametrize('table', ['patient','encounter'])
def test_corrupt_parent_registration_is_not_trusted(case,registered,table):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn:
        conn.execute(text(f"UPDATE {table} SET payload='{{}}'"))
    with pytest.raises(StorageIntegrityError): load(registered,original.execution_id,target=TARGET)
    with pytest.raises(StorageIntegrityError): append(registered,original,target=TARGET)


def test_decimal_scale_and_offset_retained_in_real_storage(registered):
    case=evidence(registered,'82.00','79.000')
    original=make_record(case)
    saved=append(registered,original,target=TARGET)
    recovered=load(registered,original.execution_id,target=TARGET)
    assert recovered==saved
    encoded=canonical_payload(recovered.record)
    assert '"earlier_kg":"82.00"' in encoded and '"later_kg":"79.000"' in encoded
    assert '2026-09-25T15:30:00.123456+05:30' in encoded
    assert row(registered)['payload']==encoded


@pytest.mark.parametrize('sql', ["DELETE FROM repository_identity", "UPDATE repository_identity SET repository_id='invalid'"])
def test_malformed_active_repository_identity_fails_safely(case,registered,sql):
    original=make_record(case)
    append(registered,original,target=TARGET)
    with registered.begin() as conn: conn.execute(text(sql))
    with pytest.raises(StorageIntegrityError): load(registered,original.execution_id,target=TARGET)
    with pytest.raises(StorageIntegrityError): append(registered,original,target=TARGET)


@pytest.mark.parametrize('operation', ['append','load'])
@pytest.mark.parametrize('handle_kind', ['active_connection','idle_connection','session'])
def test_adapter_rejects_caller_owned_transaction_handles(case,registered,operation,handle_kind):
    from contextlib import ExitStack
    from sqlalchemy.orm import Session
    original = make_record(case)
    append(registered,original,target=TARGET)
    with ExitStack() as stack:
        if handle_kind == 'session':
            handle = stack.enter_context(Session(registered))
        else:
            handle = stack.enter_context(registered.connect())
            if handle_kind == 'active_connection': stack.enter_context(handle.begin())
        statements = []
        def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
        event.listen(registered,'before_cursor_execute',capture)
        try:
            with pytest.raises(PersistenceInputError,match='Engine'):
                if operation == 'append': append(handle,original,target=TARGET)
                else: load(handle,original.execution_id,target=TARGET)
            assert statements == []
        finally:
            event.remove(registered,'before_cursor_execute',capture)


@pytest.mark.parametrize('part', ['lineage_metadata','selection_exclusions','selection_policy'])
def test_deep_valid_content_change_cannot_be_an_idempotent_retry(case,registered,part):
    original=make_record(case,'failure')
    append(registered,original,target=TARGET)
    before=row(registered)
    if part=='lineage_metadata':
        nodes=original.lineage.nodes
        metadata=replace(nodes[0].ingestion,ingested_at=nodes[0].ingestion.ingested_at+timedelta(microseconds=1))
        changed=replace(original,lineage=replace(original.lineage,nodes=(replace(nodes[0],ingestion=metadata),*nodes[1:])))
    elif part=='selection_exclusions':
        from app.execution.weight_trend import WeightTrendExclusion
        exclusion=WeightTrendExclusion(reference=Reference(kind='observation',id='outside',version='1'),reason='outside_comparison_window')
        changed=replace(original,original=replace(original.original,exclusions=(exclusion,)))
    else:
        policy=replace(original.original.policy,window_start=original.original.policy.window_start-timedelta(microseconds=1))
        changed=replace(original,original=replace(original.original,policy=policy),
            final_recheck=replace(original.final_recheck,final=replace(original.final_recheck.final,policy=policy)))
    assert canonical_payload(changed)!=before['payload']
    with pytest.raises(RecordConflict) as caught: append(registered,changed,target=TARGET)
    assert_private(caught.value)
    assert row(registered)==before


@pytest.mark.parametrize('part', ['recheck_version','recheck_cutoff','decision_and_failure','unsafe_issue'])
def test_rehashed_invalid_final_recheck_or_failure_is_integrity_error(case,registered,part):
    original=make_record(case,'failure' if part=='unsafe_issue' else 'released')
    append(registered,original,target=TARGET)
    def corrupt(data):
        if part=='recheck_version': data['final_recheck']['policy']['version']='2'
        elif part=='recheck_cutoff': data['final_recheck']['final']['cutoff']['fact_watermark']=0
        elif part=='decision_and_failure': data['issue']={'stage':'governance','code':'internal_failure'}
        else: data['issue']['code']='CONFIDENTIAL_SYNTHETIC'
    mutate_payload(registered,corrupt)
    for operation in ('load','retry'):
        with pytest.raises(StorageIntegrityError) as caught:
            if operation=='load': load(registered,original.execution_id,target=TARGET)
            else: append(registered,original,target=TARGET)
        assert_private(caught.value)
