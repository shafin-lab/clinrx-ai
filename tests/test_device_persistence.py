from alembic import command
from alembic.config import Config
import pytest

from app.models.clinical.devices import DeviceEpisode, DeviceHistory, DeviceOutputLink
from app.persistence import database
from app.persistence.database import create_database
from app.persistence.errors import RecordConflict, RecordNotFound
from app.persistence.repository import transaction
from tests.test_persistence import ROOT, SOURCE, TARGET, encounter, fact, migrate, patient


def device(identifier, status, replaces=None):
    return DeviceEpisode(
        reference={'kind': 'device_episode', 'id': identifier, 'version': '1'},
        context=TARGET, source=SOURCE, device_type='chest drain', site='left',
        status=status, replaces=replaces,
    )


def test_replacement_and_output_associations_survive_reload(tmp_path, monkeypatch):
    path = tmp_path / 'devices.sqlite3'
    engine = create_database(path)
    config = Config(str(ROOT / 'backend/alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'm16_0017')
    with monkeypatch.context() as patch:
        patch.setattr(database, 'SCHEMA_REVISION', 'm16_0017')
        with transaction(engine) as repository:
            repository.register_patient(patient())
            repository.register_encounter(encounter())
            outputs = [
                repository.append_fact(fact(id=identifier), target=TARGET)
                for identifier in ('historical', 'unresolved', 'unlinked')
            ]
    migrate(engine)
    old = device('old', 'removed')
    replacement = device('new', 'in_place', old.reference)
    missing = device('missing', 'unknown')
    with transaction(engine) as repository:
        links = tuple(
            DeviceOutputLink(output=output.fact.reference, context=TARGET, device=target)
            for output, target in zip(outputs, (old.reference, missing.reference, None), strict=True)
        )
        repository.append_device_history(DeviceHistory(episodes=(old,), outputs=links), target=TARGET)
    with transaction(engine) as repository:
        increment = DeviceHistory(episodes=(replacement,))
        repository.append_device_history(increment, target=TARGET)
        repository.append_device_history(increment, target=TARGET)
    engine.dispose()

    reopened = create_database(path)
    try:
        with transaction(reopened) as repository:
            history = repository.load_device_history(target=TARGET)
            assert history.episodes == (old, replacement)
            assert history.outputs == links
            assert history.resolve_output(links[0].output) == old
            assert history.resolve_output(links[1].output) is None
            assert history.resolve_output(links[2].output) is None

        with pytest.raises(RecordConflict), transaction(reopened) as repository:
            repository.append_device_history(DeviceHistory(
                episodes=(device('another', 'unknown'), device('old', 'in_place')),
            ), target=TARGET)
        with pytest.raises(RecordNotFound), transaction(reopened) as repository:
            repository.append_device_history(DeviceHistory(outputs=(DeviceOutputLink(
                output={'kind': 'observation', 'id': 'missing-output', 'version': '1'},
                context=TARGET, device=old.reference,
            ),)), target=TARGET)
        with transaction(reopened) as repository:
            assert repository.load_device_history(target=TARGET) == history
    finally:
        reopened.dispose()
