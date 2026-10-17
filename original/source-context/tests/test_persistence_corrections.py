"""Finding-specific regressions for 7A.1 M1/M2/S1/S2; synthetic data only."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import traceback

import pytest
from sqlalchemy import text

from app.models.clinical.common import ClinicalTime, ClinicalValue, Quantity
from app.models.clinical.facts import ClinicalObservation, MedicationIdentity
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, StorageIntegrityError, UnsupportedOperation,
)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import (
    AT, TARGET, database, registered, encounter, fact, patient, quantity, replace,
)

SENTINEL = 'CONFIDENTIAL_SYNTHETIC_SENTINEL'
ODD = datetime(2026, 9, 26, 10, tzinfo=timezone(timedelta(hours=5, minutes=30, seconds=45)))
KINDS = ['observation', 'medication_order', 'medication_administration', 'inference']


def timestamps(value):
    if isinstance(value, datetime):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from timestamps(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from timestamps(child)


def convert_offsets(value, offset):
    # Test fixture transformation only; production persistence must NOT do this.
    if isinstance(value, datetime):
        return value.astimezone(offset)
    if isinstance(value, dict):
        return {key: convert_offsets(child, offset) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(convert_offsets(child, offset) for child in value)
    return value


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('offset', [timezone.utc, timezone(timedelta(hours=-4)), timezone(timedelta(hours=5, minutes=30))])
def test_m1_accepted_nested_timestamps_preserve_instants_and_offsets(registered, kind, offset):
    original = fact(kind)
    original = type(original).model_validate(convert_offsets(original.model_dump(), offset))
    with transaction(registered) as repo:
        repo.append_fact(original, target=TARGET)
    with transaction(registered) as repo:
        retained = repo.load_fact(original.reference, target=TARGET).fact
    before = list(timestamps(original.model_dump()))
    after = list(timestamps(retained.model_dump()))
    assert before
    assert len(before) == len(after)
    for expected, actual in zip(before, after, strict=True):
        assert expected.isoformat() == actual.isoformat()
        assert expected.astimezone(timezone.utc) == actual.astimezone(timezone.utc)


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('location', ['time', 'binding', 'provenance'])
def test_m1_rejects_nested_lossy_timestamp_and_rolls_back(registered, kind, location):
    original = fact(kind)
    if location == 'time':
        original = replace(original, time=replace(original.time, processed=ODD))
    elif location == 'binding':
        original = replace(original, binding=replace(original.binding,
            verification=replace(original.binding.verification, assessed_at=ODD)))
    else:
        original = replace(original, provenance=replace(original.provenance, recorded_at=ODD))
    with pytest.raises(UnsupportedOperation), transaction(registered) as repo:
        repo.append_fact(fact(id='earlier-write'), target=TARGET)
        repo.append_fact(original, target=TARGET)
    with registered.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 0


@pytest.mark.parametrize('offset', [timedelta(hours=5, minutes=30, seconds=45),
                                  timedelta(hours=-4, microseconds=-1)])
def test_m1_encounter_rejects_seconds_or_fractional_offset_before_insert(database, offset):
    unsupported = datetime(2026, 9, 25, 10, tzinfo=timezone(offset))
    original = replace(encounter(), time=ClinicalTime(event=unsupported, precision='instant'))
    with pytest.raises(UnsupportedOperation), transaction(database) as repo:
        repo.register_patient(patient())
        repo.register_encounter(original)
    with database.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM patient')).scalar_one() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM encounter')).scalar_one() == 0


def test_m1_original_reproduced_event_cannot_change_silently(registered):
    original = fact(time=ClinicalTime(event=ODD.replace(day=25), precision='instant'))
    assert original.time.event.isoformat() == '2026-09-25T10:00:00+05:30:45'
    with pytest.raises(UnsupportedOperation), transaction(registered) as repo:
        repo.append_fact(original, target=TARGET)
    with transaction(registered) as repo:
        assert repo.capture_cutoff().fact_watermark == 0


def corrupt_parent(engine, parent, corruption):
    if corruption == 'malformed':
        payload = '{"synthetic":"invalid registration"}'
    elif parent == 'patient':
        payload = canonical_payload(patient('synthetic-wrong-patient'))
    else:
        payload = canonical_payload(encounter(owner='synthetic-wrong-patient'))
    # Controlled storage corruption, not a supported repository write operation.
    with engine.begin() as connection:
        if parent == 'patient':
            connection.execute(text("UPDATE patient SET payload=:p WHERE patient_id='synthetic-p1'"), {'p': payload})
        else:
            connection.execute(text("UPDATE encounter SET payload=:p WHERE encounter_id='synthetic-e1'"), {'p': payload})


@pytest.mark.parametrize('parent', ['patient', 'encounter'])
@pytest.mark.parametrize('corruption', ['malformed', 'identity_mismatch'])
@pytest.mark.parametrize('operation', ['register_encounter', 'load_encounter', 'append_fact', 'load_fact'])
def test_m2_corrupt_parent_blocks_dependent_operations(registered, parent, corruption, operation):
    original = fact()
    with transaction(registered) as repo:
        repo.append_fact(original, target=TARGET)
    corrupt_parent(registered, parent, corruption)
    with pytest.raises(StorageIntegrityError), transaction(registered) as repo:
        repo.register_patient(patient('synthetic-must-rollback'))
        if operation == 'register_encounter':
            # Existing encounter retry must validate both retained registrations.
            repo.register_encounter(encounter())
        elif operation == 'load_encounter':
            repo.load_encounter(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id)
        elif operation == 'append_fact':
            repo.append_fact(fact(id='must-not-be-inserted'), target=TARGET)
        else:
            repo.load_fact(original.reference, target=TARGET)
    with registered.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM patient WHERE patient_id='synthetic-must-rollback'")).scalar_one() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 1


@pytest.mark.parametrize('corruption', ['malformed', 'identity_mismatch'])
def test_m2_corrupt_patient_blocks_new_encounter(registered, corruption):
    corrupt_parent(registered, 'patient', corruption)
    with pytest.raises(StorageIntegrityError), transaction(registered) as repo:
        repo.register_encounter(encounter('synthetic-new-encounter'))
    with registered.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM encounter WHERE encounter_id='synthetic-new-encounter'")).scalar_one() == 0


def assert_private(exc):
    assert SENTINEL not in str(exc)
    assert SENTINEL not in ''.join(traceback.format_exception(exc))


@pytest.mark.parametrize('operation', ['patient', 'encounter', 'fact', 'target', 'reference', 'serialization'])
def test_s1_invalid_input_does_not_expose_values(registered, operation, monkeypatch):
    if operation == 'serialization':
        from pydantic_core import PydanticSerializationError
        def failed_dump(*args, **kwargs):
            raise PydanticSerializationError(SENTINEL)
        monkeypatch.setattr(ClinicalObservation, 'model_dump', failed_dump)
    with pytest.raises(PersistenceInputError) as caught:
        with transaction(registered) as repo:
            if operation == 'patient':
                repo.register_patient({'patient_id': 'synthetic-new', 'source_identifiers': SENTINEL})
            elif operation == 'encounter':
                repo.register_encounter({'encounter_id': 'synthetic-new', 'patient_id': 'synthetic-p1', 'time': SENTINEL})
            elif operation == 'fact':
                repo.append_fact(fact().model_copy(update={'origin': SENTINEL}), target=TARGET)
            elif operation == 'target':
                repo.append_fact(fact(), target={'patient_id': SENTINEL})
            elif operation == 'reference':
                repo.load_fact({'kind': SENTINEL}, target=TARGET)
            else:
                repo.append_fact(fact(), target=TARGET)
    assert_private(caught.value)


@pytest.mark.parametrize('location', ['patient_payload', 'encounter_payload', 'fact_payload', 'ingested_at', 'repository_identity'])
def test_s1_corrupt_storage_does_not_expose_values(registered, location):
    with transaction(registered) as repo:
        repo.append_fact(fact(), target=TARGET)
    with registered.begin() as connection:
        if location.endswith('_payload'):
            table = {'patient_payload': 'patient', 'encounter_payload': 'encounter', 'fact_payload': 'fact_revision'}[location]
            connection.execute(text(f'UPDATE {table} SET payload=:value'), {'value': '{"private":"'+SENTINEL+'"}'})
        elif location == 'ingested_at':
            connection.execute(text('UPDATE fact_revision SET ingested_at=:value'), {'value': SENTINEL})
        else:
            connection.execute(text('UPDATE repository_identity SET repository_id=:value'), {'value': SENTINEL})
    with pytest.raises(StorageIntegrityError) as caught:
        with transaction(registered) as repo:
            repo.load_fact(fact().reference, target=TARGET)
    assert_private(caught.value)


@pytest.mark.parametrize('variation', ['key_order', 'omitted_defaults', 'pydantic_roundtrip'])
def test_s2_serialization_equivalent_retry_is_idempotent(registered, variation):
    original = fact()
    payload = original.model_dump(mode='json')
    if variation == 'key_order':
        retry = ClinicalObservation.model_validate(dict(reversed(list(payload.items()))))
    elif variation == 'omitted_defaults':
        del payload['supersedes']
        del payload['correction_reason']
        retry = ClinicalObservation.model_validate(payload)
    else:
        retry = ClinicalObservation.model_validate_json(original.model_dump_json())
    with transaction(registered) as repo:
        first = repo.append_fact(original, target=TARGET)
    with transaction(registered) as repo:
        assert repo.append_fact(retry, target=TARGET) == first
        assert repo.capture_cutoff().fact_watermark == first.ingestion.ingestion_sequence


@pytest.mark.parametrize('variation', ['decimal_scale', 'equal_instant_offset', 'ingredient_order'])
def test_s2_representation_conflict_preserves_first_record(registered, variation):
    if variation == 'decimal_scale':
        original = fact(value=ClinicalValue(status='known', value=Quantity(value=Decimal('1.0'), unit=quantity().unit)))
        retry = replace(original, value=ClinicalValue(status='known', value=Quantity(value=Decimal('1.00'), unit=quantity().unit)))
        assert original == retry  # Domain equality does not define storage identity.
    elif variation == 'equal_instant_offset':
        original = fact()
        retry = replace(original, time=replace(original.time, event=AT.astimezone(timezone.utc)))
        assert original == retry
    else:
        original = fact('medication_order', medication=MedicationIdentity(ingredient_ids=('synthetic-a', 'synthetic-b')))
        retry = replace(original, medication=replace(original.medication, ingredient_ids=('synthetic-b', 'synthetic-a')))
    with transaction(registered) as repo:
        first = repo.append_fact(original, target=TARGET)
    with pytest.raises(RecordConflict), transaction(registered) as repo:
        repo.append_fact(retry, target=TARGET)
    with transaction(registered) as repo:
        retained = repo.load_fact(original.reference, target=TARGET)
        assert canonical_payload(retained.fact) == canonical_payload(original)
        assert retained.ingestion == first.ingestion
        assert repo.capture_cutoff().fact_watermark == first.ingestion.ingestion_sequence
