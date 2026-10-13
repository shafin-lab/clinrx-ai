"""M6.2 durable identities, migration atomicity and prefix privacy."""
from datetime import timedelta
import json
import pytest
from sqlalchemy import text, event, inspect
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.mapping import canonical_payload, SUPPORTED_FACTS
from app.persistence.history import FactIdentity
from app.persistence.errors import RecordConflict, ScopeMismatch, StorageIntegrityError, QueryLimitExceeded
from app.persistence.bounded_history import HistoryBudget
from test_persistence import database, registered, ROOT, migrate, patient, encounter, fact as old_fact
from test_patient_state_v2 import all_facts, facts, change, report, time, AT, TARGET, c, m, quantity


def save(engine, *records):
    with transaction(engine) as repo:
        for fact in records:
            (repo.append_revision if fact.supersedes else repo.append_fact)(fact, target=TARGET)
        return repo.capture_cutoff()


def revision(fact, **changes):
    fields = dict(revision='2', supersedes=fact.reference, correction_reason='explicit synthetic correction')
    if hasattr(fact, 'report'):
        fields['report'] = change(fact.report, change='corrected')
    fields.update(changes)
    return change(fact, **fields)


@pytest.mark.parametrize('index', range(12))
def test_every_kind_roundtrip_retry_revision_reopen(registered, index):
    original = all_facts()[index]
    before = save(registered, original)
    corrected = revision(original)
    after = save(registered, corrected)
    registered.dispose()
    with transaction(registered) as repo:
        retained = repo.load_fact(original.reference, target=TARGET)
        assert type(retained.fact) is type(original)
        assert canonical_payload(retained.fact) == canonical_payload(original)
        assert retained.fact.canonical_digest == original.canonical_digest
        assert repo.append_fact(original, target=TARGET) == retained
        identity = FactIdentity(kind=original.kind, id=original.id)
        assert repo.load_latest_known(identity,target=TARGET,cutoff=before).records[0].fact.reference == original.reference
        assert repo.load_latest_known(identity,target=TARGET,cutoff=after).records[0].fact.reference == corrected.reference
        assert repo.append_revision(corrected,target=TARGET).fact == corrected
    with pytest.raises(RecordConflict), transaction(registered) as repo:
        repo.append_revision(change(corrected, provenance=change(corrected.provenance, actor='different')),target=TARGET)


@pytest.mark.parametrize('index', range(12))
@pytest.mark.parametrize('scope', ['patient', 'encounter'])
def test_foreign_payload_never_decoded(registered, index, scope, monkeypatch):
    original = all_facts()[index]
    cutoff = save(registered, original)
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET patient_id=:p, encounter_id=:e, payload='broken'"),
            dict(p='synthetic-p2' if scope=='patient' else 'synthetic-p1',e='synthetic-e3' if scope=='patient' else 'synthetic-e2'))
    import app.persistence.history as history
    monkeypatch.setattr(history,'load_fact',lambda *a: pytest.fail('foreign payload decoded'))
    with pytest.raises(ScopeMismatch), transaction(registered) as repo:
        repo.load_latest_known(FactIdentity(kind=original.kind,id=original.id),target=TARGET,cutoff=cutoff)


@pytest.mark.parametrize('index', range(12))
def test_future_mixed_scope_corruption_irrelevant_until_visible(registered, index, monkeypatch):
    original = all_facts()[index]
    cutoff = save(registered, original)
    current = save(registered, revision(original))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2', payload='private-invalid' WHERE revision='2'"))
    with transaction(registered) as repo:
        old = repo.list_bounded_history(target=TARGET,cutoff=cutoff,budget=HistoryBudget())
        assert old.records[0].fact.reference == original.reference
    import app.persistence.history as history
    monkeypatch.setattr(history,'load_fact',lambda *a: pytest.fail('mixed chain decoded'))
    with pytest.raises(ScopeMismatch), transaction(registered) as repo:
        repo.list_bounded_history(target=TARGET,cutoff=current,budget=HistoryBudget())


@pytest.mark.parametrize('damage', ['json', 'envelope', 'noncanonical', 'kind'])
def test_visible_corruption_is_integrity_failure(registered, damage):
    original = facts()[0]
    cutoff = save(registered, original)
    with registered.begin() as conn:
        if damage == 'json': conn.execute(text("UPDATE fact_revision SET payload='private-invalid'"))
        elif damage == 'envelope': conn.execute(text("UPDATE fact_revision SET fact_id='other'"))
        elif damage == 'noncanonical': conn.execute(text("UPDATE fact_revision SET payload=payload || ' '"))
        else: conn.execute(text("UPDATE fact_revision SET kind='microbiology_isolate'"))
    with pytest.raises(StorageIntegrityError), transaction(registered) as repo:
        repo.list_bounded_history(target=TARGET,cutoff=cutoff,budget=HistoryBudget())


def test_admission_is_exact_closed_mapping(registered):
    assert len(SUPPORTED_FACTS)==16
    for fact in all_facts(): assert SUPPORTED_FACTS[fact.kind] is type(fact)
    save(registered, facts()[0])
    with pytest.raises(IntegrityError), registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET kind='unknown'"))


def test_migration_preserves_populated_bytes_links_and_high_water(tmp_path):
    engine=create_database(tmp_path/'old.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn
        command.upgrade(config,'m4_0005')
        for table, model, identity in [('patient',patient(),'patient_id'),('encounter',encounter(),'encounter_id')]:
            values={identity:getattr(model,identity),'payload':canonical_payload(model),'at':AT.isoformat()}
            columns=f'{identity},payload_version,payload,ingested_at'
            placeholders=f':{identity},1,:payload,:at'
            if table=='encounter':
                columns+=',patient_id'; placeholders+=',:patient'; values['patient']=TARGET.patient_id
            conn.execute(text(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'),values)
        for seq,fact in [(7,old_fact()),(9,revision(old_fact()))]:
            conn.execute(text('INSERT INTO fact_revision VALUES (:seq,:kind,:id,:rev,:p,:e,1,:payload,:at)'),
                dict(seq=seq,kind=fact.kind,id=fact.id,rev=fact.revision,p=TARGET.patient_id,e=TARGET.encounter_id,payload=canonical_payload(fact),at=AT.isoformat()))
        conn.execute(text('INSERT INTO revision_link VALUES (9,7)'))
        conn.execute(text("UPDATE sqlite_sequence SET seq=99 WHERE name='fact_revision'"))
    def stored():
        with engine.connect() as conn:
            return {t:conn.execute(text(f'SELECT * FROM {t}')).all() for t in ('patient','encounter','fact_revision','revision_link','sqlite_sequence','repository_identity')}
    before=stored()
    migrate(engine)
    assert stored()==before
    with transaction(engine) as repo:
        assert repo.load_fact(old_fact().reference,target=TARGET).ingestion.ingestion_sequence==7
        assert repo.append_fact(facts()[0],target=TARGET).ingestion.ingestion_sequence==100
    engine.dispose()


def test_migration_head_and_refused_downgrade(database):
    scripts=ScriptDirectory.from_config(Config(str(ROOT/'backend/alembic.ini')))
    assert scripts.get_heads()==['m6_0006']
    assert scripts.get_revision('m6_0006').down_revision=='m4_0005'
    config=Config(str(ROOT/'backend/alembic.ini'))
    with pytest.raises(RuntimeError), database.begin() as conn:
        config.attributes['connection']=conn
        command.downgrade(config,'m4_0005')
    with database.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='m6_0006'


def test_migration_failure_rolls_back_table_copy(tmp_path):
    engine=create_database(tmp_path/'fail.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn; command.upgrade(config,'m4_0005')
    def fail(conn,cursor,statement,params,context,many):
        if statement.startswith('INSERT INTO revision_link SELECT'): raise RuntimeError('synthetic failure')
    event.listen(engine,'before_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError): migrate(engine)
    finally: event.remove(engine,'before_cursor_execute',fail)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='m4_0005'
        assert 'revision_link' in inspect(conn).get_table_names()
    migrate(engine)
    engine.dispose()


@pytest.mark.parametrize('operation',['load','retry','revision'])
def test_exact_operations_check_chain_scope_before_decode(registered,monkeypatch,operation):
    original=facts()[0]
    save(registered,original,revision(original))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2',payload='private-invalid' WHERE revision='2'"))
    import app.persistence.repository as module
    monkeypatch.setattr(module,'load_fact',lambda *a: pytest.fail('mixed chain decoded'))
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:
        if operation=='load': repo.load_fact(original.reference,target=TARGET)
        elif operation=='retry': repo.append_fact(original,target=TARGET)
        else: repo.append_revision(revision(original),target=TARGET)


@pytest.mark.parametrize('case',['mic','interpretation','provenance','same_value','identification'])
def test_clinical_corrections_preserve_original(registered,case):
    original=facts()[1 if case=='identification' else 2]
    updates={}
    if case=='mic': updates['mic']=change(original.mic,quantity=quantity('2.000'))
    if case=='interpretation': updates['interpretation']=change(original.interpretation,raw=' R ',category='resistant')
    if case=='provenance': updates['provenance']=change(original.provenance,actor='corrected source')
    if case=='identification': updates['identification_state']='final'
    corrected=revision(original,**updates)
    before=save(registered,original); after=save(registered,corrected)
    with transaction(registered) as repo:
        identity=FactIdentity(kind=original.kind,id=original.id)
        assert canonical_payload(repo.load_latest_known(identity,target=TARGET,cutoff=before).records[0].fact)==canonical_payload(original)
        assert canonical_payload(repo.load_latest_known(identity,target=TARGET,cutoff=after).records[0].fact)==canonical_payload(corrected)
        assert corrected.supersedes==original.reference


def test_shared_transaction_admits_new_facts_and_rolls_back(registered):
    from app.persistence.shared_transaction import execution_transaction
    from app.persistence.errors import TransactionAborted
    original=facts()[0]
    with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
        tx.repository.append_fact(original,target=TARGET)
        try: tx.repository.append_fact(change(original,collector='different'),target=TARGET)
        except RecordConflict: pass
    with registered.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM fact_revision')).scalar_one()==0


def test_migration_failure_preserves_populated_store(tmp_path,monkeypatch):
    from test_revision_chains import legacy_database,snapshot_storage
    engine,original=legacy_database(tmp_path,monkeypatch)
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn; command.upgrade(config,'m4_0005')
    before=snapshot_storage(engine)
    def fail(conn,cursor,statement,params,context,many):
        if statement.startswith('INSERT INTO revision_link SELECT'): raise RuntimeError('synthetic failure')
    event.listen(engine,'before_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError): migrate(engine)
    finally: event.remove(engine,'before_cursor_execute',fail)
    assert snapshot_storage(engine)==before
    migrate(engine)
    assert snapshot_storage(engine)==before
    engine.dispose()


@pytest.mark.parametrize('allocator',[None,99])
def test_empty_migration_preserves_allocator_presence(tmp_path,allocator):
    engine=create_database(tmp_path/'empty.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        config.attributes['connection']=conn; command.upgrade(config,'m4_0005')
        if allocator is not None:
            conn.execute(text("INSERT INTO sqlite_sequence(name,seq) VALUES ('fact_revision',:value)"),{'value':allocator})
    migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'")).scalar_one_or_none()==allocator
    engine.dispose()
