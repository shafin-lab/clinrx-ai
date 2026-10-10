"""Synthetic persistence cases; none asserts clinical validity or production readiness."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models.clinical.common import (
    Binding, ClinicalTime, ClinicalValue, ContextTarget, IdentityVerification,
    LineageEdge, Provenance, Quantity, Reference, Source, Unit,
)
from app.models.clinical.facts import (
    ClinicalCondition, ClinicalInference, ClinicalObservation, Dose, EncounterContext,
    MedicationAdministration, MedicationIdentity, MedicationOrder, PatientContext,
)
from app.persistence.database import create_database, create_sqlite_engine
from app.persistence.entities import Base, SCHEMA_REVISION
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, SchemaMismatch, ScopeMismatch, StorageIntegrityError,
    TransactionAborted, UnsupportedOperation,
)
from app.persistence.mapping import canonical_payload
from app.persistence.metadata import ReconstructionMetadata
from app.persistence.repository import transaction

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 9, 25, 15, 30, 0, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))
SOURCE = Source(namespace='synthetic-only', identifier='device-1', version='1', channel='measurement')
TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')


def replace(model, **updates):
    return type(model).model_validate({**model.model_dump(), **updates})


def patient(id='synthetic-p1'):
    return PatientContext(patient_id=id, source_identifiers=(SOURCE,))


def encounter(id='synthetic-e1', owner='synthetic-p1'):
    return EncounterContext(encounter_id=id, patient_id=owner,
                            time=ClinicalTime(event=AT, precision='instant'), source=SOURCE)


def quantity():
    return Quantity(value=Decimal('1234567890.123456789012345678900'),
                    unit=Unit(raw=' mg/L ', status='assessed', system='UCUM', code='mg/L'))


def fact(kind='observation', **updates):
    binding = Binding(target=TARGET, verification=IdentityVerification(status='verified',
        method='synthetic-fixture', verifier='synthetic-system', assessed_at=AT, source=SOURCE))
    provenance = Provenance(source=SOURCE, actor='synthetic-author', recorded_at=AT,
                            lineage='unknown', limitations=('synthetic, not a clinical feed',))
    common = dict(id=kind+'-1', revision='1', binding=binding, origin='reported',
        provenance=provenance, time=ClinicalTime(event=AT, recorded=AT, retrieved=AT,
        processed=AT, precision='approximate', uncertainty='synthetic timing'),
        verification='clinician_confirmed', conflict='unresolved', temporal_status='unknown',
        uncertainty=('synthetic uncertainty',))
    medication = MedicationIdentity(product_id='synthetic-product', ingredient_ids=('synthetic-ingredient',),
                                    formulation='synthetic formulation')
    if kind == 'observation':
        model = ClinicalObservation
        common.update(concept_id='synthetic-measurement', value=ClinicalValue(status='known', value=quantity()))
    elif kind == 'medication_order':
        model = MedicationOrder
        common.update(medication=medication, prescribed_dose=Dose(amount=quantity(), basis='per_dose'),
                      route='synthetic route', schedule_text='synthetic schedule', order_status='active')
    elif kind == 'medication_administration':
        model = MedicationAdministration
        common.update(medication=medication, administered_dose=Dose(amount=quantity(), basis='total_administered'),
                      route='synthetic route', administered_at=AT,
                      order=Reference(kind='medication_order', id='medication_order-1', version='1'))
    elif kind == 'inference':
        model = ClinicalInference
        dependency = Reference(kind='observation', id='observation-1', version='1')
        common.update(origin='inferred', statement='Synthetic hypothesis', inputs=(dependency,),
            provenance=replace(provenance, upstream=(LineageEdge(target=dependency, relationship='derived_from'),)),
            method=Reference(kind='model', id='synthetic-model', version='1'),
            applicability='synthetic only', validation_limitations='no clinical validation',
            target='synthetic outcome', horizon='synthetic horizon')
    else:
        raise AssertionError(kind)
    common.update(updates)
    return model(**common)


def migrate(engine):
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')


@pytest.fixture
def database(tmp_path):
    engine = create_database(tmp_path / 'synthetic.sqlite3')
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def registered(database):
    with transaction(database) as repository:
        repository.register_patient(patient())
        repository.register_patient(patient('synthetic-p2'))
        repository.register_encounter(encounter())
        repository.register_encounter(encounter('synthetic-e2'))
        repository.register_encounter(encounter('synthetic-e3', 'synthetic-p2'))
    return database


def test_migration_empty_database_and_repeat(database):
    expected = {'repository_identity', 'patient', 'encounter', 'fact_revision', 'revision_link', 'weight_trend_execution', 'creatinine_trend_execution', 'patient_state_temporal_execution', 'alembic_version'}
    with database.connect() as connection:
        assert set(inspect(connection).get_table_names()) == expected
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == SCHEMA_REVISION
        identity = connection.execute(text('SELECT repository_id FROM repository_identity')).scalar_one()
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    migrate(database)
    with database.connect() as connection:
        assert connection.execute(text('SELECT repository_id FROM repository_identity')).scalar_one() == identity


def test_migration_cli(tmp_path):
    path = tmp_path / 'cli.sqlite3'
    result = subprocess.run([sys.executable, '-m', 'alembic', '-c', str(ROOT / 'backend/alembic.ini'), 'upgrade', 'head'],
        cwd=tmp_path, env={**os.environ, 'CLINRX_DATABASE_PATH': str(path)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    engine = create_database(path)
    try:
        with transaction(engine) as repository:
            assert repository.capture_cutoff().fact_watermark == 0
    finally:
        engine.dispose()


def test_schema_must_be_migrated(tmp_path):
    engine = create_database(tmp_path / 'unmigrated.sqlite3')
    try:
        with pytest.raises(SchemaMismatch), transaction(engine):
            pass
    finally:
        engine.dispose()


def test_wrong_schema_rejected(database):
    with database.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'future'"))
    with pytest.raises(SchemaMismatch), transaction(database):
        pass


@pytest.mark.parametrize('url', ['sqlite+pysqlite:///:memory:', 'postgresql://localhost/test',
                                'sqlite+pysqlite:///file.db?uri=true'])
def test_only_supported_database_configuration(url):
    with pytest.raises(UnsupportedOperation):
        create_sqlite_engine(url)


def test_foreign_keys_on_every_new_connection(database):
    for _ in range(2):
        database.dispose()
        with database.connect() as connection:
            assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar_one() == 1
        with pytest.raises(IntegrityError), database.begin() as connection:
            connection.execute(text("INSERT INTO encounter VALUES ('e', 'absent', 1, '{}', 'test')"))


def test_database_enforces_composite_encounter_ownership(registered):
    with pytest.raises(IntegrityError), registered.begin() as connection:
        connection.execute(text("""INSERT INTO fact_revision
            (kind, fact_id, revision, patient_id, encounter_id, payload_version, payload, ingested_at)
            VALUES ('observation', 'bad', '1', 'synthetic-p2', 'synthetic-e1', 1, '{}', 'test')"""))


def test_registration_roundtrip_retry_and_ownership(registered):
    with transaction(registered) as repository:
        assert repository.register_patient(patient()) == patient()
        assert repository.load_patient('synthetic-p1') == patient()
        assert repository.register_encounter(encounter()) == encounter()
        assert repository.load_encounter(patient_id='synthetic-p1', encounter_id='synthetic-e1') == encounter()
    with pytest.raises(ScopeMismatch), transaction(registered) as repository:
        repository.register_encounter(encounter(owner='synthetic-p2'))
    with pytest.raises(ScopeMismatch), transaction(registered) as repository:
        repository.load_encounter(patient_id='synthetic-p2', encounter_id='synthetic-e1')


@pytest.mark.parametrize('which', ['patient', 'encounter'])
def test_registration_cannot_silently_change(registered, which):
    with pytest.raises(RecordConflict), transaction(registered) as repository:
        if which == 'patient':
            repository.register_patient(replace(patient(), source_identifiers=()))
        else:
            repository.register_encounter(replace(encounter(), source=replace(SOURCE, identifier='other')))


def test_encounter_requires_registered_patient(database):
    with pytest.raises(RecordNotFound), transaction(database) as repository:
        repository.register_encounter(encounter())


@pytest.mark.parametrize('kind', ['observation', 'medication_order', 'medication_administration', 'inference'])
def test_all_supported_facts_roundtrip(registered, kind):
    original = fact(kind)
    with transaction(registered) as repository:
        stored = repository.append_fact(original, target=TARGET)
    with transaction(registered) as repository:
        loaded = repository.load_fact(original.reference, target=TARGET)
    assert loaded == stored
    assert type(loaded.fact) is type(original)
    assert canonical_payload(loaded.fact) == canonical_payload(original)
    assert loaded.fact.time.event.isoformat() == AT.isoformat()
    assert loaded.fact.provenance == original.provenance
    assert loaded.fact.binding == original.binding
    assert loaded.fact.verification == 'clinician_confirmed'
    assert loaded.fact.conflict == 'unresolved'
    assert loaded.ingestion.ingested_at.utcoffset() == timedelta(0)
    assert loaded.ingestion.ingested_at != AT
    if kind == 'observation':
        assert loaded.fact.value.value.value.as_tuple() == quantity().value.as_tuple()
        assert loaded.fact.value.value.unit.raw == ' mg/L '
    if kind == 'inference':
        assert loaded.fact.origin == 'inferred'
        assert loaded.fact.inputs == original.inputs
        assert loaded.fact.provenance.upstream == original.provenance.upstream


@pytest.mark.parametrize('status', ['unknown', 'missing', 'not_measured', 'not_applicable'])
def test_missingness_preserved(registered, status):
    original = fact(value=ClinicalValue(status=status, reason='synthetic absence'))
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with transaction(registered) as repository:
        result = repository.load_fact(original.reference, target=TARGET).fact
    assert result.value.status == status
    assert result.value.value is None
    assert result.value.reason == 'synthetic absence'


def test_unresolved_unit_and_identity_are_not_promoted(registered):
    original = fact()
    original = replace(original, value=ClinicalValue(status='known', value=Quantity(value='1.00',
        unit=Unit(raw='unknown unit', status='unresolved', limitation='synthetic ambiguity'))),
        binding=replace(original.binding, verification=replace(original.binding.verification,
            status='unresolved', ambiguity='synthetic ambiguous matching')))
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with transaction(registered) as repository:
        result = repository.load_fact(original.reference, target=TARGET).fact
    assert result == original
    assert result.binding.verification.status == 'unresolved'
    assert result.value.value.unit.status == 'unresolved'


def test_order_is_not_administration_and_inference_is_not_observation(registered):
    with transaction(registered) as repository:
        repository.append_fact(fact('medication_order'), target=TARGET)
        repository.append_fact(fact('inference'), target=TARGET)
    for reference in [Reference(kind='medication_administration', id='medication_order-1', version='1'),
                      Reference(kind='observation', id='inference-1', version='1')]:
        with pytest.raises(RecordNotFound), transaction(registered) as repository:
            repository.load_fact(reference, target=TARGET)


def test_retry_equivalent_canonical_content_preserves_ingestion(registered):
    original = fact()
    # Alternate JSON key order and omitted explicit default normalize identically.
    payload = original.model_dump(mode='json')
    del payload['supersedes']
    reordered = ClinicalObservation.model_validate(dict(reversed(list(payload.items()))))
    with transaction(registered) as repository:
        first = repository.append_fact(original, target=TARGET)
    with transaction(registered) as repository:
        second = repository.append_fact(reordered, target=TARGET)
        assert repository.capture_cutoff().fact_watermark == first.ingestion.ingestion_sequence
    assert first == second


@pytest.mark.parametrize('field,value', [('concept_id', 'different'), ('verification', 'unverified'),
                                        ('uncertainty', ('different uncertainty',))])
def test_same_reference_changed_clinical_content_fails(registered, field, value):
    original = fact()
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with pytest.raises(RecordConflict), transaction(registered) as repository:
        repository.append_fact(replace(original, **{field: value}), target=TARGET)
    with transaction(registered) as repository:
        assert repository.load_fact(original.reference, target=TARGET).fact == original


@pytest.mark.parametrize('target', [ContextTarget(patient_id='synthetic-p2', encounter_id='synthetic-e3'),
                                    ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e2'),
                                    ContextTarget(patient_id='synthetic-p2', encounter_id='synthetic-e1')])
def test_wrong_patient_or_encounter_append_and_load_rejected(registered, target):
    original = fact()
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with pytest.raises(ScopeMismatch), transaction(registered) as repository:
        repository.append_fact(original, target=target)
    with pytest.raises(ScopeMismatch), transaction(registered) as repository:
        repository.load_fact(original.reference, target=target)


def test_exact_reference_cannot_move_context(registered):
    original = fact()
    other = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e2')
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with pytest.raises(ScopeMismatch), transaction(registered) as repository:
        repository.append_fact(replace(original, binding=replace(original.binding, target=other)), target=other)


def test_rollback_has_no_partial_registrations_or_facts(database):
    with pytest.raises(RuntimeError), transaction(database) as repository:
        repository.register_patient(patient())
        repository.register_encounter(encounter())
        repository.append_fact(fact(), target=TARGET)
        raise RuntimeError('injected failure')
    with database.connect() as connection:
        for table in ['patient', 'encounter', 'fact_revision']:
            assert connection.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one() == 0


def test_caught_repository_failure_still_aborts_all_writes(registered):
    with pytest.raises(TransactionAborted), transaction(registered) as repository:
        repository.append_fact(fact(), target=TARGET)
        try:
            repository.append_fact(fact(concept_id='changed'), target=TARGET)
        except RecordConflict:
            pass
    with transaction(registered) as repository:
        assert repository.capture_cutoff().fact_watermark == 0


def test_closed_transaction_cannot_be_reused(database):
    with transaction(database) as repository:
        repository.register_patient(patient())
    with pytest.raises(TransactionAborted):
        repository.register_patient(patient('other'))


def test_revalidate_untrusted_model_copy(registered):
    forged = fact().model_copy(update={'origin': 'inferred'})
    with pytest.raises(PersistenceInputError), transaction(registered) as repository:
        repository.append_fact(forged, target=TARGET)


def test_deferred_operations_rejected_explicitly(registered):
    original = fact()
    condition = ClinicalCondition(**{key: value for key, value in original.model_dump().items()
        if key not in ('kind', 'value')}, diagnostic_status='provisional')
    with pytest.raises(UnsupportedOperation), transaction(registered) as repository:
        repository.append_fact(condition, target=TARGET)
    longitudinal = ContextTarget(patient_id='synthetic-p1', longitudinal_context_id='synthetic-longitudinal')
    with pytest.raises(UnsupportedOperation), transaction(registered) as repository:
        repository.append_fact(replace(original, binding=replace(original.binding, target=longitudinal)), target=longitudinal)
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    for revision in [replace(original, revision='2'), replace(original, revision='2',
                        supersedes=original.reference, correction_reason='synthetic correction')]:
        with pytest.raises(UnsupportedOperation), transaction(registered) as repository:
            repository.append_fact(revision, target=TARGET)


@pytest.mark.parametrize('mutation', ["payload = '{}'", "fact_id = 'mismatched'", "ingested_at = 'not-a-time'"])
def test_corrupt_storage_never_becomes_valid_domain_record(registered, mutation):
    with transaction(registered) as repository:
        repository.append_fact(fact(), target=TARGET)
    with registered.begin() as connection:
        connection.execute(text(f'UPDATE fact_revision SET {mutation}'))
    reference = fact().reference
    if 'fact_id' in mutation:
        reference = replace(reference, id='mismatched')
    with pytest.raises(StorageIntegrityError), transaction(registered) as repository:
        repository.load_fact(reference, target=TARGET)


def test_watermark_and_reserved_reconstruction_metadata(registered):
    with transaction(registered) as repository:
        before = repository.capture_cutoff()
        stored = repository.append_fact(fact(), target=TARGET)
        after = repository.capture_cutoff()
    assert before.fact_watermark == 0
    assert after.fact_watermark == stored.ingestion.ingestion_sequence
    metadata = ReconstructionMetadata(reconstruction_policy=Reference(kind='reconstruction_policy',
        id='future-synthetic-policy', version='1'), repository_cutoff=after, knowledge_cutoff=after.captured_at)
    assert ReconstructionMetadata.model_validate_json(metadata.model_dump_json()) == metadata


def test_concurrent_identical_retry_is_one_record(registered):
    def write():
        with transaction(registered) as repository:
            return repository.append_fact(fact(), target=TARGET)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: write(), range(2)))
    assert results[0] == results[1]
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 1


def test_close_reopen_and_separate_process_durability(registered):
    with transaction(registered) as repository:
        stored = repository.append_fact(fact(), target=TARGET)
    path = registered.url.database
    registered.dispose()
    script = '''
import json, sys
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.models.clinical.common import ContextTarget, Reference
engine = create_database(sys.argv[1])
with transaction(engine) as repo:
    stored = repo.load_fact(Reference(kind='observation', id='observation-1', version='1'),
        target=ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1'))
    print(json.dumps({'fact': stored.fact.model_dump(mode='json'),
                      'ingestion': stored.ingestion.model_dump(mode='json')}))
engine.dispose()
'''
    result = subprocess.run([sys.executable, '-c', script, path], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'backend'), 'PYTHONDONTWRITEBYTECODE': '1'},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert loaded['fact'] == stored.fact.model_dump(mode='json')
    assert loaded['ingestion'] == stored.ingestion.model_dump(mode='json')


def test_exact_reference_uniqueness_enforced_by_database(registered):
    with transaction(registered) as repository:
        repository.append_fact(fact(), target=TARGET)
    with pytest.raises(IntegrityError), registered.begin() as connection:
        connection.execute(text('''INSERT INTO fact_revision
            (kind, fact_id, revision, patient_id, encounter_id, payload_version, payload, ingested_at)
            SELECT kind, fact_id, revision, patient_id, encounter_id, payload_version, payload, ingested_at
            FROM fact_revision'''))


@pytest.mark.parametrize('value', [False, True, 'synthetic text'])
def test_boolean_and_text_values_keep_their_types(registered, value):
    original = fact(value=ClinicalValue(status='known', value=value))
    with transaction(registered) as repository:
        repository.append_fact(original, target=TARGET)
    with transaction(registered) as repository:
        loaded = repository.load_fact(original.reference, target=TARGET).fact
    assert type(loaded.value.value) is type(value)
    assert loaded.value.value == value


def test_unknown_clinical_time_does_not_gain_ingestion_time(registered):
    original = fact(time=ClinicalTime(precision='unknown', uncertainty='no source time'))
    with transaction(registered) as repository:
        stored = repository.append_fact(original, target=TARGET)
    assert stored.fact.time.event is None
    assert stored.fact.time.recorded is None
    assert stored.ingestion.ingested_at is not None


def test_unsupported_payload_version_is_rejected():
    from app.persistence.entities import FactRow
    from app.persistence.mapping import load_fact

    row = FactRow(payload_version=2, kind='observation', payload=canonical_payload(fact()))
    with pytest.raises(StorageIntegrityError):
        load_fact(row, '00000000-0000-0000-0000-000000000001')


def test_exact_lookup_never_substitutes_latest_revision(registered):
    with transaction(registered) as repository:
        repository.append_fact(fact(), target=TARGET)
    with pytest.raises(RecordNotFound), transaction(registered) as repository:
        repository.load_fact(replace(fact().reference, version='missing'), target=TARGET)


def test_schema_changes_roll_back_with_explicit_transactions(database):
    with pytest.raises(RuntimeError), database.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE synthetic_rollback_test (id INTEGER)')
        raise RuntimeError('injected migration failure')
    with database.connect() as connection:
        assert 'synthetic_rollback_test' not in inspect(connection).get_table_names()


def test_concurrent_conflicting_retry_preserves_one_revision(registered):
    def write(concept):
        try:
            with transaction(registered) as repository:
                repository.append_fact(fact(concept_id=concept), target=TARGET)
            return 'stored'
        except RecordConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, ['synthetic-a', 'synthetic-b']))
    assert sorted(outcomes) == ['conflict', 'stored']
    with transaction(registered) as repository:
        assert repository.load_fact(fact().reference, target=TARGET).fact.concept_id in ('synthetic-a', 'synthetic-b')
