"""M15 wound source linkage and exact revision history on disposable databases."""
from copy import deepcopy
from hashlib import sha256

from app.demo.renal_fluid_entry_gateway import RF2
from tests.test_endocrine_gateway import endocrine
from tests.test_renal_fluid_entry import pin, post, seed, ws
from tests.test_reproductive_gateway import stamp


def wound(source='wound-assessment', **changes):
    record = endocrine(source)
    del record['nutrition']
    record.update(
        kind='wound_record',
        id='wound-' + sha256(('ward.example\0' + source).encode()).hexdigest()[:32],
        category='assessment', wound_id='W-01', site='Sacrum', stage='Stage 2',
        length_cm='2.2', width_cm='1.4', dressing='Silicone foam',
        title='Sacral wound assessment', narrative='Recorded wound assessment.',
    )
    return {**record, **changes}


def test_wound_assessments_and_pressure_care_share_the_encounter(ws):
    client, _, _ = ws
    repository = client.get(RF2).json()['repository']
    for record in (wound(), wound('repositioning', category='pressure_care', wound_id=None,
                                 site=None, stage=None, length_cm=None, width_cm=None,
                                 dressing=None, action='Right lateral repositioning')):
        response = post(client, '/wound', {'repository': repository, 'record': record})
        assert response.status_code == 200, response.text
    catalog = client.get(RF2, params={'paginate': True}).json()
    rows = {e['fact']['category']: e['fact'] for e in catalog['wound_records']}
    assert rows['assessment']['wound_id'] == 'W-01'
    assert rows['assessment']['length_cm'] == '2.2'
    assert rows['pressure_care']['action'] == 'Right lateral repositioning'
    assert rows['pressure_care']['wound_id'] is None


def test_wound_correction_retains_the_original_at_the_old_cutoff(ws):
    client, _, _ = ws
    repository = client.get(RF2).json()['repository']
    record = wound()
    request = {'repository': repository, 'record': record}
    assert post(client, '/wound/lookup', request).json() == {'status': 'absent'}
    response = post(client, '/wound', request)
    assert response.status_code == 200, response.text
    assert post(client, '/wound/lookup', request).json()['status'] == 'committed_match'
    corrected = deepcopy(record)
    corrected.update(
        revision='2', change_state='corrected', report_status='corrected', length_cm='2.0',
        supersedes={'kind': 'wound_record', 'id': record['id'], 'version': '1'},
        correction_reason='Original measurement transcription corrected.',
    )
    corrected['source_identity']['source_version'] = '2'
    corrected['times']['available'] = stamp('2026-10-08T09:30:00.000001Z')
    response = post(client, '/wound', {**request, 'record': corrected})
    assert response.status_code == 200, response.text
    for end, length, versions in (
        ('2026-10-08T09:30:00Z', '2.2', ['1']),
        ('2026-10-08T09:30:00.000001Z', '2.0', ['1', '2']),
    ):
        catalog = client.get(RF2, params={'review_end': end, 'paginate': True}).json()
        source, = catalog['wound_records']
        assert source['fact']['length_cm'] == length
        exact = {'repository': repository, 'pins': [pin(source)]}
        assert post(client, '/resolve', exact).json()['items'] == [source]
        assert [e['fact']['revision'] for e in post(client, '/history', exact).json()['items']] == versions


def test_m15_upgrade_preserves_the_m14_endocrine_revision_chain(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from app.demo.authoring import TARGET
    from app.models.clinical.endocrine import EndocrineRecord
    from app.models.clinical.wound import WoundRecord
    from app.persistence import database as database_module
    from app.persistence.repository import transaction
    from tests.test_persistence import ROOT, encounter, patient
    from tests.test_synthetic_hosting import rows

    path = tmp_path / 'm14.sqlite3'
    engine = database_module.create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'm14_0015')
        original_data = endocrine()
        original = EndocrineRecord.model_validate(original_data)
        corrected_data = deepcopy(original_data)
        corrected_data.update(
            revision='2', supersedes=original.reference,
            correction_reason='Corrected prior source wording', change_state='corrected',
            report_status='corrected', narrative='Corrected nutrition chart wording',
        )
        corrected_data['source_identity']['source_version'] = '2'
        corrected = EndocrineRecord.model_validate(corrected_data)
        with monkeypatch.context() as patch:
            patch.setattr(database_module, 'SCHEMA_REVISION', 'm14_0015')
            with transaction(engine) as repo:
                repo.register_patient(patient())
                repo.register_encounter(encounter())
                repo.append_fact(original, target=TARGET)
                repo.append_revision(corrected, target=TARGET)
                previous_cutoff = repo.capture_cutoff()
        with engine.begin() as connection:
            connection.exec_driver_sql("UPDATE sqlite_sequence SET seq=80 WHERE name='fact_revision'")

        before = rows(path)
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
            assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        after = rows(path)
        assert after.pop('alembic_version') == [('m15_0016',)]
        assert before.pop('alembic_version') == [('m14_0015',)]
        assert after == before
        with transaction(engine) as repo:
            cutoff = repo.capture_cutoff()
            assert cutoff.repository_id == previous_cutoff.repository_id
            assert cutoff.fact_watermark == previous_cutoff.fact_watermark
            assert repo.load_fact(corrected.reference, target=TARGET).fact == corrected
            saved = repo.append_fact(WoundRecord.model_validate(wound()), target=TARGET)
            assert saved.ingestion.ingestion_sequence == 81
    finally:
        engine.dispose()
