"""RF2 reproductive sources through the gateway on disposable repositories."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest

from app.demo.renal_fluid_entry_gateway import RF2
from tests.test_laboratory_contract import report
from tests.test_renal_fluid_entry import pin, post, seed, ws
from tests.test_synthetic_hosting import rows


def stamp(value):
    return {'status': 'known', 'precision': 'instant', 'value': value}


def reproductive(source='preg-status', version='1', **changes):
    record = report().model_dump(mode='json', exclude={
        'source_panel', 'specimen', 'components', 'original_report', 'original_report_digest',
    })
    owner = 'repro-' + sha256(('ward.example\0' + source).encode()).hexdigest()[:32]
    record.update(
        kind='reproductive_record', id=owner, revision=version,
        source_identity={'issuer_namespace': 'ward.example', 'source_report_id': source,
                         'source_version': version, 'accession_id': None},
        category='pregnancy_status', title='Recorded pregnancy status',
        narrative='Pregnancy status is uncertain in the source chart.',
        pregnancy={'phase': 'unknown'}, linked_sources=[],
        times={'occurred': stamp('2026-10-08T09:00:00Z'),
               'reported': stamp('2026-10-08T09:05:00Z'),
               'available': stamp('2026-10-08T09:05:00Z')},
    )
    return {**record, **changes}


def request(client, record):
    return {'repository': client.get(RF2).json()['repository'], 'record': record}


def append(client, body):
    response = post(client, '/reproductive', body)
    assert response.status_code == 200, response.text
    return response.json()


def correction(record):
    revised = deepcopy(record)
    revised.update(
        revision='2', change_state='corrected', report_status='corrected',
        supersedes={'kind': 'reproductive_record', 'id': record['id'], 'version': '1'},
        correction_reason='Corrected dating transcription',
        pregnancy={'phase': 'antepartum', 'gestational_weeks': 32, 'gestational_days': 4,
                   'estimated_due_date': '2026-11-29', 'fetus_count': 1, 'dating_basis': 'Source ultrasound'},
    )
    revised['source_identity']['source_version'] = '2'
    revised['times']['available'] = stamp('2026-10-08T09:30:00.000001Z')
    return revised


def test_reproductive_recovery_is_exact_and_read_only(ws):
    client, db, _ = ws
    body = request(client, reproductive())
    before = rows(db)
    assert post(client, '/reproductive/lookup', body).json() == {'status': 'absent'}
    assert rows(db) == before

    evidence = append(client, body)
    assert evidence['fact']['pregnancy']['phase'] == 'unknown'
    assert evidence['fact']['pregnancy']['gestational_weeks'] is None
    committed = rows(db)
    assert post(client, '/reproductive/lookup', body).json() == {
        'status': 'committed_match', 'evidence': evidence,
    }
    assert append(client, body) == evidence
    changed = deepcopy(body)
    changed['record']['narrative'] = 'Different source under the same revision'
    for route in ('/reproductive', '/reproductive/lookup'):
        assert post(client, route, changed).status_code == 409
    assert rows(db) == committed


def test_reproductive_catalog_and_pins_keep_the_visible_predecessor(ws):
    client, db, _ = ws
    original = reproductive()
    body = request(client, original)
    first = append(client, body)
    latest = append(client, {**body, 'record': correction(original)})
    before = rows(db)

    early = client.get(RF2, params={'review_end': '2026-10-08T09:30:00Z'}).json()
    selected, = early['reproductive_records']
    assert selected['fact']['revision'] == '1'
    assert selected['cutoff'] == first['ingestion']['ingestion_sequence']
    assert selected['terminal_reference']['version'] == '1'
    assert selected['superseded'] is False
    current = client.get(RF2, params={'review_end': '2026-10-08T09:30:00.000001Z'}).json()
    assert current['reproductive_records'][0]['fact']['pregnancy'] == latest['fact']['pregnancy']

    resolved = post(client, '/resolve', {'repository': body['repository'], 'pins': [pin(selected)]})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()['items'] == [selected]
    for source, revisions in ((selected, ['1']), (latest, ['1', '2'])):
        history = post(client, '/history', {'repository': body['repository'], 'pins': [pin(source)]})
        assert history.status_code == 200, history.text
        assert [entry['fact']['revision'] for entry in history.json()['items']] == revisions
    assert rows(db) == before


def test_reproductive_fallback_occurrence_respects_bounded_upper_time(ws):
    client, _, _ = ws
    occurrence = {'status': 'known', 'precision': 'bounded',
                  'lower': '2026-10-08T09:00:00Z', 'upper': '2026-10-08T09:45:00Z'}
    record = reproductive(times={'occurred': occurrence})
    append(client, request(client, record))
    assert client.get(RF2, params={'review_end': '2026-10-08T09:44:59.999999Z'}).json()['reproductive_records'] == []
    assert len(client.get(RF2, params={'review_end': '2026-10-08T09:45:00Z'}).json()['reproductive_records']) == 1


@pytest.mark.parametrize('changes', [
    {'category': 'invented'}, {'id': 'repro-forged'}, {'revision': 'another'},
    {'narrative': '  '}, {'category': 'procedure', 'pregnancy': {'phase': 'unknown'}},
    {'pregnancy': None}, {'pregnancy': {'phase': 'positive'}},
    {'pregnancy': {'phase': 'antepartum', 'gestational_days': 7}},
    {'pregnancy': {'phase': 'antepartum', 'gestational_weeks': True}},
    {'linked_sources': [{'kind': 'observation', 'id': 'missing', 'version': '1'}]},
])
def test_invalid_reproductive_source_leaves_storage_unchanged(ws, changes):
    client, db, _ = ws
    body = request(client, reproductive(**changes))
    before = rows(db)
    assert post(client, '/reproductive', body).status_code in (404, 409, 422)
    assert rows(db) == before


def test_reproductive_safeguards_apply_to_save_and_lookup(ws):
    client, db, _ = ws
    body = request(client, reproductive())
    before = rows(db)
    for route in ('/reproductive', '/reproductive/lookup'):
        assert post(client, route, {**body, 'repository': str(uuid4())}).status_code == 409
        foreign = deepcopy(body)
        foreign['record']['binding']['target']['patient_id'] = 'another-patient'
        assert post(client, route, foreign).status_code == 422
        assert client.post(RF2 + route, json=body, headers={'Origin': 'https://outside.example'}).status_code == 403
        assert client.post(RF2 + route, content='{"repository":0,"repository":1}',
                           headers={'Content-Type': 'application/json'}).status_code == 422
    assert rows(db) == before


def test_reproductive_correction_requires_terminal_predecessor_and_stable_category(ws):
    client, db, _ = ws
    original = reproductive()
    body = request(client, original)
    invalid = correction(original)
    assert post(client, '/reproductive', {**body, 'record': invalid}).status_code == 409
    append(client, body)

    invalid.update(category='maternal_assessment', pregnancy=None)
    before = rows(db)
    assert post(client, '/reproductive', {**body, 'record': invalid}).status_code == 409
    assert rows(db) == before


def test_reproductive_pagination_keeps_first_ingestion_prefix(ws, monkeypatch):
    client, db, app = ws
    repository = client.get(RF2).json()['repository']

    def add(number):
        record = reproductive(f'page-{number}', category='gynecology', pregnancy=None,
                              narrative='Recorded finding é\n' * 800)
        append(client, {'repository': repository, 'record': record})

    for number in range(4):
        add(number)
    original = client.get(RF2)
    assert original.status_code == 200, original.text
    limit = len(original.content) - 25000
    deps = app.core.state.dependencies
    monkeypatch.setattr(app.core.state, 'dependencies', replace(
        deps, config=deps.config.model_copy(update={'max_response_bytes': limit})))
    response = client.get(RF2, params={'paginate': True})
    assert response.status_code == 200, response.text
    first = response.json()
    cursor = first['pagination']['next_cursor']
    assert cursor
    add(4)
    before = rows(db)

    collected = list(first['reproductive_records'])
    while cursor:
        response = client.get(RF2, params={'paginate': True, 'cursor': cursor})
        assert response.status_code == 200, response.text
        assert len(response.content) <= limit
        page = response.json()
        assert page['cutoff'] == first['cutoff']
        collected.extend(page['reproductive_records'])
        cursor = page['pagination']['next_cursor']
    assert collected == original.json()['reproductive_records']
    assert rows(db) == before


def test_m12_upgrade_preserves_revision_links_repository_identity_and_sequence(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from app.demo.authoring import TARGET
    from app.persistence import database as database_module
    from app.persistence.repository import transaction
    from tests.test_persistence import ROOT, encounter, fact, patient

    path = tmp_path / 'm11.sqlite3'
    engine = database_module.create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm11_0012')
    with monkeypatch.context() as patch:
        patch.setattr(database_module, 'SCHEMA_REVISION', 'm11_0012')
        with transaction(engine) as repository:
            repository.register_patient(patient())
            repository.register_encounter(encounter())
            original = repository.append_fact(fact(), target=TARGET)
            successor = fact(revision='2', supersedes=original.fact.reference, correction_reason='Fixture revision')
            repository.append_revision(successor, target=TARGET)
            original_cutoff = repository.capture_cutoff()
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE sqlite_sequence SET seq=80 WHERE name='fact_revision'")

    before = rows(path)
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm12_0013')
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        assert connection.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'").scalar_one() == 80
    after = rows(path)
    assert after.pop('alembic_version') == [('m12_0013',)]
    assert before.pop('alembic_version') == [('m11_0012',)]
    assert after == before
    with monkeypatch.context() as patch:
        patch.setattr(database_module, 'SCHEMA_REVISION', 'm12_0013')
        with transaction(engine) as repository:
            retained_cutoff = repository.capture_cutoff()
            assert retained_cutoff.repository_id == original_cutoff.repository_id
            assert retained_cutoff.fact_watermark == original_cutoff.fact_watermark
            assert repository.load_fact(successor.reference, target=TARGET).fact == successor
            following = repository.append_fact(fact(id='next'), target=TARGET)
            assert following.ingestion.ingestion_sequence == 81
    engine.dispose()
