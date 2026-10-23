"""Synthetic laboratory report admission and same-cutoff catalog delivery."""
from copy import deepcopy
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path

from app.demo.renal_fluid_entry_gateway import RF2
from app.demo.antibiotic_gateway import ABX, SyntheticAntibioticGateway
from fastapi.testclient import TestClient
from app.models.clinical.laboratory import LaboratoryReport
from app.persistence.canonical import canonical_payload
from tests.test_renal_fluid_entry import ORIGIN, seed, ws
from tests.test_laboratory_contract import report as draft_report


def owned_report(version='1', *, predecessor=None, change_state='original', report_status='final', correction_reason=None):
    owner = 'lab-' + sha256(b'lab.example\0gateway-report').hexdigest()[:32]
    model = draft_report(revision=version, fact_id=owner, source_report='gateway-report',
        supersedes=predecessor, change_state=change_state, report_status=report_status,
        correction_reason=correction_reason)
    data = model.model_dump(mode='python')
    data['source_identity']['source_version'] = version
    data['id'] = owner
    data['revision'] = version
    return LaboratoryReport.model_validate(data)


def test_import_retry_correction_and_overview_share_repository_cutoff(ws):
    client, database, _ = ws
    original = owned_report()
    first = client.post(RF2 + '/laboratory', json=original.model_dump(mode='json'))
    assert first.status_code == 200, first.text
    evidence = first.json()
    assert evidence['fact']['kind'] == 'laboratory_report'
    before_retry = client.get(RF2).json()
    assert len(before_retry['laboratory_reports']) == 1
    assert before_retry['laboratory_reports'][0]['fact'] == evidence['fact']

    retry = client.post(RF2 + '/laboratory', json=original.model_dump(mode='json'))
    assert retry.status_code == 200 and retry.json()['fact'] == evidence['fact']
    assert client.get(RF2).json()['cutoff']['fact_watermark'] == before_retry['cutoff']['fact_watermark']

    corrected = owned_report('2', predecessor={'kind':'laboratory_report','id':original.id,'version':'1'},
        change_state='corrected', report_status='corrected', correction_reason='Issuer corrected source result.')
    revised = client.post(RF2 + '/laboratory', json=corrected.model_dump(mode='json'))
    assert revised.status_code == 200, revised.text
    current = client.get(RF2).json()
    assert current['cutoff']['fact_watermark'] > before_retry['cutoff']['fact_watermark']
    assert len(current['laboratory_reports']) == 1
    assert current['laboratory_reports'][0]['fact']['revision'] == '2'
    assert current['laboratory_reports'][0]['terminal_reference']['version'] == '2'


def test_result_not_yet_available_is_excluded_from_earlier_patient_view(ws):
    client, _, _ = ws
    original = owned_report()
    assert client.post(RF2 + '/laboratory', json=original.model_dump(mode='json')).status_code == 200

    early = client.get(RF2, params={
        'review_start': '2026-10-08T08:00:00+00:00',
        'review_end': '2026-10-08T08:30:00+00:00',
    })
    assert early.status_code == 200, early.text
    assert early.json()['laboratory_reports'] == []


def test_shared_m8_laboratory_records_do_not_break_m6_culture_state(ws):
    client, database, app = ws
    original = owned_report()
    assert client.post(RF2 + '/laboratory', json=original.model_dump(mode='json')).status_code == 200
    abx_app = SyntheticAntibioticGateway(database, Path(app.static.directory), 'ab' * 32, ORIGIN)
    with TestClient(abx_app, base_url=ORIGIN, client=('127.0.0.1', 50000)) as abx_client:
        response = abx_client.get(ABX, params={
            'review_start': '2026-10-08T08:00:00Z',
            'review_end': '2026-10-08T10:00:00Z',
        })
    assert response.status_code == 200, response.text
    assert all(item['fact']['kind'] != 'laboratory_report'
        for item in response.json()['micro']['assembly']['snapshot']['items'])


def test_conflicting_or_cross_source_correction_is_rejected_without_append(ws):
    client, database, _ = ws
    original = owned_report()
    assert client.post(RF2 + '/laboratory', json=original.model_dump(mode='json')).status_code == 200
    before = client.get(RF2).json()['cutoff']['fact_watermark']
    conflicting = deepcopy(original.model_dump(mode='json'))
    conflicting['components'][0]['result']['raw_value'] = '141'
    assert client.post(RF2 + '/laboratory', json=conflicting).status_code == 409
    bad = owned_report('3', predecessor={'kind':'laboratory_report','id':original.id,'version':'2'},
        change_state='corrected', report_status='corrected', correction_reason='Wrong predecessor')
    assert client.post(RF2 + '/laboratory', json=bad.model_dump(mode='json')).status_code == 409
    assert client.get(RF2).json()['cutoff']['fact_watermark'] == before
