import pytest
from pydantic import ValidationError

from app.models.clinical.common import ContextTarget, Reference, Source
from app.models.clinical.devices import DeviceEpisode, DeviceHistory, DeviceOutputLink


SCOPE = ContextTarget(patient_id='synthetic', encounter_id='encounter-1')
SOURCE = Source(namespace='fixture', identifier='device-register', channel='external_record')


def episode(identifier, **fields):
    return DeviceEpisode(
        reference=Reference(kind='device_episode', id=identifier, version='1'),
        context=SCOPE, source=SOURCE, device_type='chest drain', site='left', **fields
    )


def output(identifier, device=None):
    return DeviceOutputLink(
        output=Reference(kind='observation', id=identifier, version='1'),
        context=SCOPE, device=device,
    )


def test_replacement_preserves_historical_and_unresolved_output_links():
    old = episode('old', status='removed')
    replacement = episode('new', status='in_place', replaces=old.reference)
    historical = output('collection-1', old.reference)
    missing = output('collection-2', Reference(kind='device_episode', id='missing', version='1'))
    unlinked = output('collection-3')
    history = DeviceHistory(episodes=(replacement, old), outputs=(historical, missing, unlinked))

    assert history.resolve_output(historical.output) == old
    assert history.resolve_output(missing.output) is None
    assert history.resolve_output(unlinked.output) is None
    assert history.outputs == (historical, missing, unlinked)


def test_replacement_cannot_reuse_episode_identity():
    with pytest.raises(ValidationError, match='different episode'):
        episode('old', status='in_place', replaces=Reference(
            kind='device_episode', id='old', version='0'
        ))


def test_output_cannot_resolve_across_encounters():
    device = episode('old', status='removed')
    link = DeviceOutputLink(
        output=Reference(kind='observation', id='collection', version='1'),
        context=ContextTarget(patient_id='synthetic', encounter_id='encounter-2'),
        device=device.reference,
    )
    with pytest.raises(ValidationError, match='context'):
        DeviceHistory(episodes=(device,), outputs=(link,))


def test_output_does_not_fall_back_to_a_different_revision():
    device = episode('old', status='removed')
    link = output('collection', Reference(kind='device_episode', id='old', version='0'))
    history = DeviceHistory(episodes=(device,), outputs=(link,))
    assert history.resolve_output(link.output) is None
