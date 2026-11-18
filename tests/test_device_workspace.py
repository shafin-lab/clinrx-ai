from alembic import command
from alembic.config import Config
from starlette.testclient import TestClient

from app.demo.authoring import TARGET
from app.demo.renal_fluid_entry_gateway import RF2, SyntheticRF2Gateway
from app.models.clinical.devices import DeviceEpisode, DeviceHistory, DeviceOutputLink, ProcedureRecord
from app.persistence import database
from app.persistence.database import create_database
from app.persistence.repository import transaction
from tests.test_persistence import ROOT, SOURCE, encounter, fact, migrate, patient



def test_procedure_device_and_output_history_reloads_through_workspace_api(tmp_path, monkeypatch):
    path = tmp_path / 'patient.sqlite3'
    engine = create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm19_0018')
    old = DeviceEpisode(reference={'kind': 'device_episode', 'id': 'removed-drain', 'version': '1'},
                        context=TARGET, source=SOURCE, device_type='Chest drain', status='removed')
    new = DeviceEpisode(reference={'kind': 'device_episode', 'id': 'replacement-drain', 'version': '1'},
                        context=TARGET, source=SOURCE, device_type='Chest drain', status='in_place',
                        replaces=old.reference)
    procedure = ProcedureRecord(
        reference={'kind': 'procedure_record', 'id': 'replace-drain', 'version': '1'},
        context=TARGET, source=SOURCE, title='Chest drain replacement', status='performed',
        devices=(old.reference, new.reference),
    )
    with monkeypatch.context() as patch:
        patch.setattr(database, 'SCHEMA_REVISION', 'm19_0018')
        with transaction(engine) as repo:
            repo.register_patient(patient())
            repo.register_encounter(encounter())
            output = repo.append_fact(fact(id='historical-output'), target=TARGET).fact
            link = DeviceOutputLink(output=output.reference, context=TARGET, device=old.reference)
            missing_output = repo.append_fact(fact(id='unresolved-output'), target=TARGET).fact
            unresolved = DeviceOutputLink(
                output=missing_output.reference, context=TARGET,
                device={'kind': 'device_episode', 'id': 'missing-drain', 'version': '1'},
            )
            repo.append_device_history(DeviceHistory(episodes=(old,), outputs=(link, unresolved)), target=TARGET)
            repository = str(repo.capture_cutoff().repository_id)
    migrate(engine)
    engine.dispose()

    frontend = tmp_path / 'dist'
    (frontend / 'assets').mkdir(parents=True)
    (frontend / 'index.html').write_text('Synthetic patient')
    origin = 'http://127.0.0.1:5197'

    def open_workspace():
        return TestClient(SyntheticRF2Gateway(path, frontend, 'ab' * 32, origin), base_url=origin,
                          client=('127.0.0.1', 50000), headers={'Origin': origin})

    route = RF2 + '/devices'
    with open_workspace() as client:
        payload = DeviceHistory(episodes=(new,), procedures=(procedure,)).model_dump(mode='json')
        response = client.post(route, json={'repository': repository, 'history': payload})
        assert response.status_code == 200, response.text
        assert client.post(route, json={'repository': repository, 'history': payload}).status_code == 200
        wrong_repository = '00000000-0000-4000-8000-000000000001'
        assert client.post(route, json={'repository': wrong_repository, 'history': payload}).status_code == 409
    with open_workspace() as client:
        response = client.get(route)
        assert response.status_code == 200, response.text
        assert 'no-store' in response.headers['cache-control'].split(', ')
        history = DeviceHistory.model_validate(response.json())
        assert history.procedures == (procedure,)
        assert history.episodes == (old, new)
        assert history.resolve_output(link.output) == old
        assert history.outputs == (link, unresolved)
        assert history.resolve_output(unresolved.output) is None
        assert client.get(route, headers={'sec-fetch-site': 'cross-site'}).status_code == 403
