"""Source-preserving M14 catalog and admission checks on disposable databases."""
from copy import deepcopy
from hashlib import sha256

from app.demo.renal_fluid_entry_gateway import RF2
from tests.test_renal_fluid_entry import pin, post, seed, ws
from tests.test_reproductive_gateway import reproductive, stamp
from tests.test_synthetic_hosting import rows


def endocrine(source='feed-0900', **changes):
    record = reproductive(source)
    del record['pregnancy']
    record.update(
        kind='endocrine_record',
        id='endo-' + sha256(('ward.example\0' + source).encode()).hexdigest()[:32],
        category='nutrition',
        title='Enteral nutrition',
        narrative='Nursing chart records a feed pause.',
        nutrition={'status': 'paused', 'route': 'Enteral tube'},
    )
    return {**record, **changes}


def test_feed_correction_keeps_review_cutoff_and_exact_source(ws):
    client, db, _ = ws
    repository = client.get(RF2).json()['repository']
    original = endocrine()
    request = {'repository': repository, 'record': original}
    assert post(client, '/endocrine/lookup', request).json() == {'status': 'absent'}
    response = post(client, '/endocrine', request)
    assert response.status_code == 200, response.text
    first = response.json()
    assert first['fact']['nutrition'] == original['nutrition']
    assert post(client, '/endocrine/lookup', request).json() == {
        'status': 'committed_match', 'evidence': first,
    }

    corrected = deepcopy(original)
    corrected.update(revision='2', change_state='corrected', report_status='corrected',
                     supersedes={'kind': 'endocrine_record', 'id': original['id'], 'version': '1'},
                     correction_reason='Corrected the source status',
                     nutrition={'status': 'stopped', 'route': 'Enteral tube'})
    corrected['source_identity']['source_version'] = '2'
    corrected['times']['available'] = stamp('2026-10-08T09:30:00.000001Z')
    response = post(client, '/endocrine', {**request, 'record': corrected})
    assert response.status_code == 200, response.text
    before = rows(db)

    for end, version, history in (
        ('2026-10-08T09:30:00Z', '1', ['1']),
        ('2026-10-08T09:30:00.000001Z', '2', ['1', '2']),
    ):
        catalog = client.get(RF2, params={'review_end': end, 'paginate': True}).json()
        evidence, = catalog['endocrine_records']
        assert evidence['fact']['revision'] == version
        assert not evidence['superseded']
        query = {'repository': repository, 'pins': [pin(evidence)]}
        assert post(client, '/resolve', query).json()['items'] == [evidence]
        assert [item['fact']['revision'] for item in post(client, '/history', query).json()['items']] == history
    assert rows(db) == before


def test_insulin_not_delivered_is_not_a_completed_administration(ws):
    client, db, _ = ws
    repository = client.get(RF2).json()['repository']
    record = endocrine('mar-hold', category='insulin_non_delivery', nutrition=None,
                       insulin={'name': 'Insulin lispro', 'status': 'held', 'reason': 'Feed paused'})
    before = rows(db)
    invalid = {**record, 'insulin': {**record['insulin'], 'status': 'given'}}
    assert post(client, '/endocrine', {'repository': repository, 'record': invalid}).status_code == 422
    assert rows(db) == before
    response = post(client, '/endocrine', {'repository': repository, 'record': record})
    assert response.status_code == 200, response.text
    catalog = client.get(RF2).json()
    assert catalog['endocrine_records'][0]['fact']['insulin'] == record['insulin']
    assert catalog['medication_administrations'] == []


def test_order_retrieval_preserves_source_time_and_distinguishes_delivery(ws):
    from app.demo.authoring import TARGET
    from app.models.clinical.facts import MedicationOrder
    from app.persistence.repository import transaction

    client, db, app = ws
    base = endocrine()
    occurrence = '2026-10-08T09:00:00Z'
    available = '2026-10-08T09:15:00Z'
    order = MedicationOrder.model_validate({
        **{key: base[key] for key in ('binding', 'provenance', 'temporal_status', 'origin')},
        'id': 'm14-insulin-order', 'revision': '1',
        'time': {'event': occurrence, 'recorded': available, 'precision': 'instant'},
        'medication': {'ingredient_ids': ['insulin-lispro']},
        'prescribed_dose': {'amount': {'value': '2', 'unit': {'raw': 'units', 'status': 'unresolved',
                            'limitation': 'Original source unit'}}, 'basis': 'per_dose'},
        'route': 'Subcutaneous', 'schedule_text': 'Recorded schedule', 'order_status': 'active',
    })
    with transaction(app.core.state.dependencies.engine) as repo:
        repo.append_fact(order, target=TARGET)

    before = rows(db)
    early = client.get(RF2, params={'review_end': '2026-10-08T09:14:59.999999Z'}).json()
    assert all(item['fact']['id'] != order.id for item in early['medication_orders'])
    catalog = client.get(RF2, params={'review_end': available, 'paginate': True}).json()
    evidence, = [item for item in catalog['medication_orders'] if item['fact']['id'] == order.id]
    assert all(item['fact']['order'] != order.reference.model_dump(mode='json')
               for item in catalog['medication_administrations'])
    assert evidence['fact'] == order.model_dump(mode='json')
    query = {'repository': catalog['repository'], 'pins': [pin(evidence)]}
    assert post(client, '/resolve', query).json()['items'] == [evidence]
    assert post(client, '/history', query).json()['items'] == [evidence]
    assert rows(db) == before


def test_m14_upgrade_preserves_original_neurology_revision_chain(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from app.demo.authoring import TARGET
    from app.models.clinical.endocrine import EndocrineRecord
    from app.models.clinical.neurological import NeurologicalRecord
    from app.persistence import database as database_module
    from app.persistence.repository import transaction
    from tests.test_neurological_gateway import neurological
    from tests.test_persistence import ROOT, encounter, patient

    path = tmp_path / 'm13.sqlite3'
    engine = database_module.create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm13_0014')

    original = NeurologicalRecord.model_validate(neurological())
    successor = NeurologicalRecord.model_validate({
        **original.model_dump(mode='json'), 'revision': '2', 'supersedes': original.reference,
        'correction_reason': 'Corrected prior source wording', 'change_state': 'corrected',
        'report_status': 'corrected', 'narrative': 'Corrected bedside source wording',
        'source_identity': {**original.source_identity.model_dump(mode='json'), 'source_version': '2'},
    })
    with monkeypatch.context() as patch:
        patch.setattr(database_module, 'SCHEMA_REVISION', 'm13_0014')
        with transaction(engine) as repo:
            repo.register_patient(patient())
            repo.register_encounter(encounter())
            repo.append_fact(original, target=TARGET)
            repo.append_revision(successor, target=TARGET)
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
    assert after.pop('alembic_version') == [('m15_0016',)]
    assert before.pop('alembic_version') == [('m13_0014',)]
    assert after == before
    with transaction(engine) as repo:
        cutoff = repo.capture_cutoff()
        assert cutoff.repository_id == retained_cutoff.repository_id
        assert cutoff.fact_watermark == retained_cutoff.fact_watermark
        assert repo.load_fact(successor.reference, target=TARGET).fact == successor
        added = repo.append_fact(EndocrineRecord.model_validate(endocrine()), target=TARGET)
        assert added.ingestion.ingestion_sequence == 81
    engine.dispose()
