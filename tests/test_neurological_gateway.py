"""Source revision, admission and M12 upgrade checks on disposable repositories."""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import pytest

from app.demo.renal_fluid_entry_gateway import RF2
from tests.test_renal_fluid_entry import pin, post, seed, ws
from tests.test_reproductive_gateway import reproductive, stamp
from tests.test_synthetic_hosting import rows


def neurological(source='recorded-exam', **changes):
    record = reproductive(source)
    del record['pregnancy']
    record.update(
        kind='neurological_record',
        id='neuro-' + sha256(('ward.example\0' + source).encode()).hexdigest()[:32],
        category='exam', title='Recorded bedside examination',
        narrative='Verbal response was untestable due to an endotracheal tube.',
        exam={'eye': 3, 'verbal': 'untestable', 'motor': 6,
              'verbal_reason': 'Endotracheal tube', 'rass': -2, 'pupils': 'Equal'},
        medication=None,
    )
    record['provenance']['actor'] = 'Recorded examiner'
    return {**record, **changes}


def save(client, body):
    response = post(client, '/neurological', body)
    assert response.status_code == 200, response.text
    return response.json()


def test_neurological_correction_and_lookup_preserve_exact_history_at_availability(ws):
    client, db, _ = ws
    catalog = client.get(RF2).json()
    repository = catalog['repository']
    assert catalog['neurological_records'] == []
    original = neurological()
    body = {'repository': repository, 'record': original}
    before = rows(db)
    assert post(client, '/neurological/lookup', body).json() == {'status': 'absent'}
    assert rows(db) == before

    first = save(client, body)
    assert first['fact']['exam'] == original['exam']
    assert first['fact']['provenance']['actor'] == 'Recorded examiner'
    assert post(client, '/neurological/lookup', body).json() == {
        'status': 'committed_match', 'evidence': first,
    }
    assert save(client, body) == first

    correction = deepcopy(original)
    correction.update(
        revision='2', change_state='corrected', report_status='corrected',
        supersedes={'kind': 'neurological_record', 'id': original['id'], 'version': '1'},
        correction_reason='Corrected source transcription',
    )
    correction['exam']['eye'] = 4
    correction['source_identity']['source_version'] = '2'
    correction['times']['available'] = stamp('2026-10-08T09:30:00.000001Z')
    revised = save(client, {**body, 'record': correction})
    before = rows(db)
    different = {**original, 'narrative': 'Different payload with the same version'}
    for route in ('/neurological', '/neurological/lookup'):
        assert post(client, route, {**body, 'record': different}).status_code == 409
    for end, version in (('2026-10-08T09:30:00Z', '1'), ('2026-10-08T09:30:00.000001Z', '2')):
        catalog = client.get(RF2, params={'review_end': end}).json()
        selected, = catalog['neurological_records']
        assert selected['fact']['revision'] == version
        assert selected['terminal_reference']['version'] == version
        assert selected['superseded'] is False
        assert selected['cutoff'] == (first if version == '1' else revised)['ingestion']['ingestion_sequence']
        selection = {'repository': repository, 'pins': [pin(selected)]}
        assert post(client, '/resolve', selection).json()['items'] == [selected]
        assert [row['fact']['revision'] for row in post(client, '/history', selection).json()['items']] == (
            ['1'] if version == '1' else ['1', '2']
        )
    assert rows(db) == before


@pytest.mark.parametrize(('category', 'field', 'value'), [
    ('exam', 'exam', None),
    ('exam', 'exam', {'eye': 5}),
    ('exam', 'exam', {'verbal': True}),
    ('exam', 'exam', {'motor': 0}),
    ('exam', 'exam', {'rass': -6}),
    ('exam', 'medication', {'name': 'Recorded sedative', 'status': 'paused'}),
    ('imaging', 'exam', {'eye': 2}),
    ('medication_status', 'medication', {'name': 'Recorded sedative', 'status': 'suggested'}),
    ('medication_status', 'medication', None),
])
def test_neurological_structured_fields_are_category_bound_and_range_checked(ws, category, field, value):
    client, db, _ = ws
    record = neurological(category=category, exam=None) if category != 'exam' else neurological()
    record[field] = value
    before = rows(db)
    response = post(client, '/neurological', {'repository': client.get(RF2).json()['repository'], 'record': record})
    assert response.status_code == 422
    assert rows(db) == before


def test_neurological_routes_inherit_local_and_repository_safeguards(ws):
    client, db, _ = ws
    record = neurological(category='imaging', exam=None)
    body = {'repository': client.get(RF2).json()['repository'], 'record': record}
    before = rows(db)
    for route in ('/neurological', '/neurological/lookup'):
        assert post(client, route, {**body, 'repository': str(uuid4())}).status_code == 409
        assert post(client, route, {**body, 'record': {**record, 'id': 'neuro-forged'}}).status_code == 422
        assert client.post(RF2 + route, json=body, headers={'Origin': 'https://outside.example'}).status_code == 403
        assert client.post(RF2 + route, content='{"repository":0,"repository":1}',
                           headers={'Content-Type': 'application/json'}).status_code == 422
    assert rows(db) == before
    assert save(client, body)['fact']['category'] == 'imaging'
    medication = neurological('sedation-source', category='medication_status', exam=None,
                              medication={'name': 'Recorded sedative', 'status': 'paused'})
    assert save(client, {**body, 'record': medication})['fact']['medication'] == medication['medication']


def test_m13_upgrade_preserves_m12_reproductive_revisions_and_sequence(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from app.demo.authoring import TARGET
    from app.models.clinical.reproductive import ReproductiveRecord
    from app.persistence import database as database_module
    from app.persistence.repository import transaction
    from tests.test_persistence import ROOT, encounter, patient
    from tests.test_reproductive_gateway import correction

    path = tmp_path / 'm12.sqlite3'
    engine = database_module.create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm12_0013')

    original = reproductive()
    revised = ReproductiveRecord.model_validate(correction(original))
    with monkeypatch.context() as patch:
        patch.setattr(database_module, 'SCHEMA_REVISION', 'm12_0013')
        with transaction(engine) as repo:
            repo.register_patient(patient())
            repo.register_encounter(encounter())
            repo.append_fact(ReproductiveRecord.model_validate(original), target=TARGET)
            repo.append_revision(revised, target=TARGET)
            retained_cutoff = repo.capture_cutoff()
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE sqlite_sequence SET seq=80 WHERE name='fact_revision'")

    before = rows(path)
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        assert connection.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'").scalar_one() == 80
    after = rows(path)
    assert after.pop('alembic_version') == [('m13_0014',)]
    assert before.pop('alembic_version') == [('m12_0013',)]
    assert after == before

    from app.models.clinical.neurological import NeurologicalRecord
    with transaction(engine) as repo:
        cutoff = repo.capture_cutoff()
        assert cutoff.repository_id == retained_cutoff.repository_id
        assert cutoff.fact_watermark == retained_cutoff.fact_watermark
        assert repo.load_fact(revised.reference, target=TARGET).fact == revised
        added = repo.append_fact(NeurologicalRecord.model_validate(neurological()), target=TARGET)
        assert added.ingestion.ingestion_sequence == 81
    engine.dispose()


def test_catalog_preserves_generic_completed_administration_at_source_cutoff(ws):
    from app.demo.authoring import TARGET
    from app.models.clinical.facts import MedicationAdministration
    from app.persistence.repository import transaction

    client, db, app = ws
    base = neurological()
    occurrence = '2026-10-08T09:00:00Z'
    original = MedicationAdministration.model_validate({
        **{key: base[key] for key in ('binding', 'provenance', 'temporal_status', 'origin')},
        'id': 'completed-m13-administration', 'revision': '1',
        'time': {'event': occurrence, 'recorded': '2026-10-08T09:10:00Z', 'precision': 'instant'},
        'medication': {'product_id': 'example-recorded-product'},
        'administered_dose': {'amount': {'value': '2.00', 'unit': {'raw': 'mg', 'status': 'unresolved',
                              'limitation': 'Exact source unit'}}, 'basis': 'total_administered'},
        'route': 'Recorded intravenous', 'administered_at': occurrence,
    })
    revised = MedicationAdministration.model_validate({
        **original.model_dump(mode='json'), 'revision': '2', 'supersedes': original.reference,
        'correction_reason': 'Source retracted the completed claim', 'conflict': 'unresolved',
        'uncertainty': ['The corrected chart no longer verifies completed delivery.'],
        'provenance': {**original.provenance.model_dump(mode='json'), 'recorded_at': '2026-10-08T09:30:00.000001Z'},
    })
    with transaction(app.core.state.dependencies.engine) as repo:
        repo.append_fact(original, target=TARGET)
        repo.append_revision(revised, target=TARGET)

    before = rows(db)
    absent = client.get(RF2, params={'review_end': '2026-10-08T09:09:59.999999Z'}).json()
    assert absent['medication_administrations'] == []
    for end, item in (('2026-10-08T09:30:00Z', original), ('2026-10-08T09:30:00.000001Z', revised)):
        catalog = client.get(RF2, params={'review_end': end, 'paginate': True}).json()
        selected, = catalog['medication_administrations']
        assert selected['fact'] == item.model_dump(mode='json')
        assert selected['terminal_reference'] == item.reference.model_dump(mode='json')
        assert selected['superseded'] is False
        request = {'repository': catalog['repository'], 'pins': [pin(selected)]}
        assert post(client, '/resolve', request).json()['items'] == [selected]
        assert [row['fact']['revision'] for row in post(client, '/history', request).json()['items']] == (
            ['1'] if item is original else ['1', '2']
        )
    assert rows(db) == before


def test_blood_glucose_and_urine_glucose_keep_distinct_exact_mappings(ws):
    from tests.test_laboratory_contract import component, report

    client, _, _ = ws
    source = 'm13-glucose-source'
    blood = component('blood-c1', test='Blood glucose', unit='mg/dL', value='112.00').model_dump(mode='json')
    blood['mapped_concept'] = 'glucose'
    urine = component('urine-c1', test='Urine glucose', mapping='urine_glucose').model_dump(mode='json')
    for source_id, payload in (('blood', blood), ('urine', urine)):
        report_id = source + '-' + source_id
        exact_owner = 'lab-' + sha256(('lab.example\0' + report_id).encode()).hexdigest()[:32]
        fact = report(source_report=report_id, fact_id=exact_owner).model_dump(mode='json')
        fact['components'] = [payload]
        response = post(client, '/laboratory', fact)
        assert response.status_code == 200, response.text
    catalog = client.get(RF2).json()
    assert [(item['fact']['components'][0]['mapped_concept'], item['fact']['components'][0]['result']['raw_value'])
            for item in catalog['laboratory_reports']] == [('glucose', '112.00'), ('urine_glucose', '138.00')]
