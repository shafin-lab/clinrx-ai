"""Synthetic immutable revision chains; no historical query or lineage resolver."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
from threading import Event
import traceback

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import event, inspect, text

from app.persistence.database import create_database
from app.persistence.errors import (PersistenceInputError, RecordConflict, RecordNotFound,
    ScopeMismatch, StorageIntegrityError, TransactionAborted, UnsupportedOperation)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import ROOT, TARGET, database, registered, fact, replace, migrate


def revision(previous, label='second', **updates):
    return replace(previous, revision=label, supersedes=previous.reference,
                   correction_reason='synthetic source correction', **updates)


def seed(engine):
    original = fact(revision='z-root')
    with transaction(engine) as repo:
        first = repo.append_fact(original, target=TARGET)
    return first


def test_chain_opaque_labels_retries_and_immutable_reads(registered):
    first = seed(registered)
    second = revision(first.fact, '10')
    third = revision(second, '2')
    with transaction(registered) as repo:
        saved2 = repo.append_revision(second, target=TARGET)
        assert repo.append_revision(second, target=TARGET) == saved2
        saved3 = repo.append_revision(third, target=TARGET)
    with transaction(registered) as repo:
        assert repo.append_revision(second, target=TARGET) == saved2
        assert repo.append_fact(first.fact, target=TARGET) == first
        for stored in (first, saved2, saved3):
            assert repo.load_fact(stored.fact.reference, target=TARGET) == stored
        assert repo.capture_cutoff().fact_watermark == saved3.ingestion.ingestion_sequence


@pytest.mark.parametrize('case', ['changed', 'branch', 'missing', 'self', 'kind', 'id', 'patient', 'encounter', 'root', 'no_predecessor'])
def test_invalid_revision_attempts(registered, case):
    first = seed(registered).fact
    second = revision(first)
    with transaction(registered) as repo:
        repo.append_revision(second, target=TARGET)
    target = TARGET
    candidate = revision(first, 'branch')
    error = RecordConflict
    if case == 'changed':
        candidate = replace(second, concept_id='changed')
    elif case == 'missing':
        candidate = replace(candidate, supersedes=replace(first.reference, version='absent'))
        error = RecordNotFound
    elif case in ('self', 'kind', 'id'):
        ref = candidate.reference if case == 'self' else replace(first.reference, **{case: 'wrong'})
        candidate = candidate.model_copy(update={'supersedes': ref})
        error = PersistenceInputError
    elif case in ('patient', 'encounter'):
        target = replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3') if case == 'patient' else replace(TARGET, encounter_id='synthetic-e2')
        candidate = replace(candidate, binding=replace(candidate.binding, target=target))
        error = ScopeMismatch
    elif case == 'root':
        candidate = replace(first, revision='second-root')
        error = UnsupportedOperation
    elif case == 'no_predecessor':
        candidate = first
        error = PersistenceInputError
    with pytest.raises(error), transaction(registered) as repo:
        (repo.append_fact if case == 'root' else repo.append_revision)(candidate, target=target)
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 2
        assert connection.execute(text('SELECT COUNT(*) FROM revision_link')).scalar_one() == 1


@pytest.mark.parametrize('corruption', ['missing_link', 'foreign_link', 'payload', 'cycle', 'second_root'])
@pytest.mark.parametrize('operation', ['read', 'retry', 'append'])
def test_corrupt_chains_fail_closed(registered, corruption, operation):
    first = seed(registered).fact
    second = revision(first)
    with transaction(registered) as repo:
        repo.append_revision(second, target=TARGET)
        other = repo.append_fact(fact(id='other'), target=TARGET)
    with registered.begin() as connection:
        if corruption == 'missing_link':
            connection.execute(text('DELETE FROM revision_link'))
        elif corruption == 'foreign_link':
            connection.execute(text('INSERT INTO revision_link VALUES (:s, 2)'), {'s': other.ingestion.ingestion_sequence})
        elif corruption == 'payload':
            connection.execute(text('UPDATE fact_revision SET payload=:p WHERE ingestion_sequence=2'),
                               {'p': canonical_payload(replace(second, supersedes=replace(first.reference, version='absent')))})
        elif corruption == 'cycle':
            connection.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            connection.execute(text('INSERT INTO revision_link VALUES (1, 2)'))
        else:
            root = replace(first, revision='illegal-root')
            connection.execute(text('''INSERT INTO fact_revision
                (kind,fact_id,revision,patient_id,encounter_id,payload_version,payload,ingested_at)
                SELECT kind,fact_id,'illegal-root',patient_id,encounter_id,payload_version,:p,ingested_at
                FROM fact_revision WHERE ingestion_sequence=1'''), {'p': canonical_payload(root)})
    with pytest.raises(StorageIntegrityError), transaction(registered) as repo:
        if operation == 'read':
            repo.load_fact(first.reference, target=TARGET)
        elif operation == 'retry':
            repo.append_revision(second, target=TARGET)
        else:
            repo.append_revision(revision(second, 'third'), target=TARGET)


@pytest.mark.parametrize('caught', [False, True])
def test_revision_and_link_rollback(registered, caught):
    first = seed(registered).fact
    with pytest.raises((RecordConflict, TransactionAborted)), transaction(registered) as repo:
        repo.append_revision(revision(first), target=TARGET)
        if caught:
            try:
                repo.append_revision(revision(first, 'branch'), target=TARGET)
            except RecordConflict:
                pass
        else:
            repo.append_revision(revision(first, 'branch'), target=TARGET)
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 1
        assert connection.execute(text('SELECT COUNT(*) FROM revision_link')).scalar_one() == 0


def test_revision_error_traceback_is_private(registered):
    first = seed(registered).fact
    sentinel = 'CONFIDENTIAL_SYNTHETIC_REVISION'
    bad = revision(first).model_copy(update={'supersedes': sentinel})
    with pytest.raises(PersistenceInputError) as caught, transaction(registered) as repo:
        repo.append_revision(bad, target=TARGET)
    assert sentinel not in ''.join(traceback.format_exception(caught.value))


def test_competing_successors_overlap_at_database_lock(registered):
    first = seed(registered).fact
    attempted, completed = Event(), Event()
    contender = create_database(registered.url.database)
    def before_begin(connection, cursor, statement, parameters, context, executemany):
        if statement == 'BEGIN IMMEDIATE':
            attempted.set()
    event.listen(contender, 'before_cursor_execute', before_begin)
    def compete():
        try:
            with transaction(contender) as repo:
                repo.append_revision(revision(first, 'loser'), target=TARGET)
        except RecordConflict:
            return 'conflict'
        finally:
            completed.set()
        return 'unexpected-success'
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction(registered) as repo:
                repo.append_revision(revision(first, 'winner'), target=TARGET)
                future = pool.submit(compete)
                assert attempted.wait(2), 'contender never attempted BEGIN IMMEDIATE'
                assert not completed.wait(0.1), 'contender did not block behind writer'
            assert future.result(timeout=3) == 'conflict'
    finally:
        contender.dispose()
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM revision_link')).scalar_one() == 1


def test_restart_exact_revision_retry(registered):
    first = seed(registered).fact
    with transaction(registered) as repo:
        second = repo.append_revision(revision(first), target=TARGET)
        repo.append_revision(revision(second.fact, 'third'), target=TARGET)
    script = '''
import json, sys
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.models.clinical.facts import ClinicalObservation
from app.models.clinical.common import ContextTarget
fact=ClinicalObservation.model_validate_json(sys.argv[2])
engine=create_database(sys.argv[1])
with transaction(engine) as repo:
    stored=repo.append_revision(fact,target=fact.binding.target)
    print(stored.ingestion.model_dump_json())
engine.dispose()
'''
    result = subprocess.run([sys.executable, '-c', script, registered.url.database, second.fact.model_dump_json()],
        env={**os.environ, 'PYTHONPATH':str(ROOT/'backend'), 'PYTHONDONTWRITEBYTECODE':'1'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == second.ingestion.model_dump(mode='json')


def legacy_database(tmp_path, monkeypatch):
    from app.persistence import database as database_module
    engine = create_database(tmp_path / 'legacy.sqlite3')
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '7a1_0001')
    # Seed through the unchanged 7A.1 mapping/registration contracts. Root insert
    # uses explicit old-schema SQL because the new repository validates links.
    from test_persistence import patient, encounter, AT
    with engine.begin() as connection:
        for table, key, model in [('patient', 'patient_id', patient()), ('encounter', 'encounter_id', encounter())]:
            fields = {key:getattr(model,key), 'payload_version':1, 'payload':canonical_payload(model), 'ingested_at':AT.isoformat()}
            if table == 'encounter':
                fields['patient_id']=TARGET.patient_id
            connection.execute(text(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(':'+k for k in fields)})"), fields)
        original=fact()
        connection.execute(text('''INSERT INTO fact_revision
            (ingestion_sequence,kind,fact_id,revision,patient_id,encounter_id,payload_version,payload,ingested_at)
            VALUES (7,:kind,:id,:revision,:patient,:encounter,1,:payload,:at)'''),
            {'kind':original.kind,'id':original.id,'revision':original.revision,'patient':TARGET.patient_id,
             'encounter':TARGET.encounter_id,'payload':canonical_payload(original),'at':AT.isoformat()})
        # Preserve the allocator, not only MAX(sequence).
        connection.execute(text("UPDATE sqlite_sequence SET seq=20 WHERE name='fact_revision'"))
    return engine, original


def snapshot_storage(engine):
    with engine.connect() as connection:
        return {table:connection.execute(text(f'SELECT * FROM {table}')).all()
                for table in ('repository_identity','patient','encounter','fact_revision','sqlite_sequence')}


def test_populated_upgrade_preserves_bytes_identity_metadata_allocator(tmp_path, monkeypatch):
    engine, original = legacy_database(tmp_path, monkeypatch)
    try:
        before=snapshot_storage(engine)
        migrate(engine)
        assert snapshot_storage(engine) == before
        migrate(engine)
        assert snapshot_storage(engine) == before
        with transaction(engine) as repo:
            root=repo.load_fact(original.reference,target=TARGET)
            assert root.ingestion.ingestion_sequence == 7
            assert repo.capture_cutoff().fact_watermark == 7
            result=repo.append_revision(revision(original),target=TARGET)
            assert result.ingestion.ingestion_sequence == 21
            assert result.ingestion.repository_id == root.ingestion.repository_id
    finally:
        engine.dispose()


@pytest.mark.parametrize('corruption', ['duplicate_stable','correction','bad_json','owner','naive_time','allocator'])
def test_legacy_migration_rejects_ambiguous_state_atomically(tmp_path, monkeypatch, corruption):
    engine, original=legacy_database(tmp_path, monkeypatch)
    try:
        with engine.begin() as connection:
            if corruption == 'duplicate_stable':
                connection.execute(text('''INSERT INTO fact_revision
                    (kind,fact_id,revision,patient_id,encounter_id,payload_version,payload,ingested_at)
                    SELECT kind,fact_id,'other',patient_id,encounter_id,payload_version,:p,ingested_at FROM fact_revision'''),
                    {'p':canonical_payload(replace(original,revision='other'))})
            elif corruption in ('correction','bad_json','owner'):
                payload = canonical_payload(revision(original)) if corruption == 'correction' else '{CONFIDENTIAL_SYNTHETIC_BAD_JSON'
                if corruption == 'correction':
                    connection.execute(text("UPDATE fact_revision SET revision='second'"))
                if corruption == 'owner':
                    payload=canonical_payload(replace(original,binding=replace(original.binding,target=replace(TARGET,patient_id='wrong'))))
                connection.execute(text('UPDATE fact_revision SET payload=:p'),{'p':payload})
            elif corruption == 'naive_time':
                connection.execute(text("UPDATE fact_revision SET ingested_at='2026-09-25T10:00:00'"))
            else:
                connection.execute(text("UPDATE sqlite_sequence SET seq=1 WHERE name='fact_revision'"))
        before=snapshot_storage(engine)
        with pytest.raises(RuntimeError) as caught:
            migrate(engine)
        assert 'CONFIDENTIAL_SYNTHETIC' not in ''.join(traceback.format_exception(caught.value))
        assert snapshot_storage(engine)==before
        with engine.connect() as connection:
            assert 'revision_link' not in inspect(connection).get_table_names()
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='7a1_0001'
    finally:
        engine.dispose()


@pytest.mark.parametrize('variation', ['decimal_scale','offset','ingredient_order'])
def test_revision_canonical_representation_conflicts(registered, variation):
    from datetime import timezone
    from app.models.clinical.common import ClinicalValue, Quantity
    from app.models.clinical.facts import MedicationIdentity
    from test_persistence import quantity
    original=fact('medication_order',medication=MedicationIdentity(ingredient_ids=('a','b'))) if variation=='ingredient_order' else fact()
    second=revision(original)
    if variation=='decimal_scale':
        second=replace(second,value=ClinicalValue(status='known',value=Quantity(value='1.0',unit=quantity().unit)))
        retry=replace(second,value=ClinicalValue(status='known',value=Quantity(value='1.00',unit=quantity().unit)))
    elif variation=='offset':
        retry=replace(second,time=replace(second.time,event=second.time.event.astimezone(timezone.utc)))
    else:
        retry=replace(second,medication=replace(second.medication,ingredient_ids=('b','a')))
    with transaction(registered) as repo:
        repo.append_fact(original,target=TARGET)
        saved=repo.append_revision(second,target=TARGET)
    with pytest.raises(RecordConflict),transaction(registered) as repo:
        repo.append_revision(retry,target=TARGET)
    with transaction(registered) as repo:
        assert repo.load_fact(second.reference,target=TARGET)==saved


def test_revision_nested_lossy_timestamp_rolls_back(registered):
    from test_persistence_corrections import ODD
    first=seed(registered).fact
    second=revision(first)
    bad=revision(second,'third',provenance=replace(second.provenance,recorded_at=ODD))
    with pytest.raises(UnsupportedOperation),transaction(registered) as repo:
        repo.append_revision(second,target=TARGET)
        repo.append_revision(bad,target=TARGET)
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one()==1
        assert connection.execute(text('SELECT COUNT(*) FROM revision_link')).scalar_one()==0


def test_link_insert_failure_rolls_back_revision(registered):
    first=seed(registered).fact
    def fail(connection,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO revision_link'):
            raise RuntimeError('synthetic link failure')
    event.listen(registered,'before_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError),transaction(registered) as repo:
            repo.append_revision(revision(first),target=TARGET)
    finally:
        event.remove(registered,'before_cursor_execute',fail)
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one()==1
        assert connection.execute(text('SELECT COUNT(*) FROM revision_link')).scalar_one()==0


@pytest.mark.parametrize('sql', ['INSERT INTO revision_link VALUES (1,1)',
    'INSERT INTO revision_link VALUES (1,2)', 'INSERT INTO revision_link VALUES (3,1)',
    'INSERT INTO revision_link VALUES (99,2)', 'INSERT INTO revision_link VALUES (2,1)'])
def test_revision_link_database_constraints(registered,sql):
    from sqlalchemy.exc import IntegrityError
    first=seed(registered).fact
    with transaction(registered) as repo:
        repo.append_revision(revision(first),target=TARGET)
        repo.append_fact(fact(id='another'),target=TARGET)
    with pytest.raises(IntegrityError),registered.begin() as connection:
        connection.execute(text(sql))


def test_migration_ddl_failure_rolls_back(tmp_path,monkeypatch):
    engine,_=legacy_database(tmp_path,monkeypatch)
    def fail(connection,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('CREATE TABLE revision_link'):
            raise RuntimeError('synthetic migration failure')
    event.listen(engine,'after_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError):
            migrate(engine)
        with engine.connect() as connection:
            assert 'revision_link' not in inspect(connection).get_table_names()
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='7a1_0001'
    finally:
        event.remove(engine,'after_cursor_execute',fail)
        engine.dispose()


@pytest.mark.parametrize('kind',['observation','medication_order','medication_administration','inference'])
def test_all_supported_categories_accept_revisions(registered,kind):
    original=fact(kind)
    with transaction(registered) as repo:
        root=repo.append_fact(original,target=TARGET)
        saved=repo.append_revision(revision(original),target=TARGET)
    with transaction(registered) as repo:
        assert repo.load_fact(original.reference,target=TARGET)==root
        assert repo.load_fact(saved.fact.reference,target=TARGET)==saved


@pytest.mark.parametrize('parent',['patient','encounter'])
def test_revision_revalidates_corrupt_parents(registered,parent):
    from test_persistence_corrections import corrupt_parent
    first=seed(registered).fact
    corrupt_parent(registered,parent,'identity_mismatch')
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:
        repo.append_revision(revision(first),target=TARGET)


def test_corrupt_revision_payload_traceback_is_private(registered):
    first=seed(registered).fact
    with transaction(registered) as repo:
        repo.append_revision(revision(first),target=TARGET)
    sentinel='CONFIDENTIAL_SYNTHETIC_STORED_REVISION'
    with registered.begin() as connection:
        connection.execute(text('UPDATE fact_revision SET payload=:p WHERE ingestion_sequence=2'),{'p':json.dumps({'private':sentinel})})
    with pytest.raises(StorageIntegrityError) as caught,transaction(registered) as repo:
        repo.load_fact(first.reference,target=TARGET)
    assert sentinel not in ''.join(traceback.format_exception(caught.value))


def test_corrupt_chain_owner_is_rejected(registered):
    first=seed(registered).fact
    second=revision(first)
    with transaction(registered) as repo:
        repo.append_revision(second,target=TARGET)
    changed=replace(second,binding=replace(second.binding,target=replace(TARGET,encounter_id='synthetic-e2')))
    with registered.begin() as connection:
        connection.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2',payload=:p WHERE ingestion_sequence=2"),{'p':canonical_payload(changed)})
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:
        repo.load_fact(first.reference,target=TARGET)
