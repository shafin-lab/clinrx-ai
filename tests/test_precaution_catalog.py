"""Exact M20 revisions on a disposable fictional patient repository."""
from copy import deepcopy

from app.demo.patient_state import TARGET
from app.demo.renal_fluid_entry_gateway import RF2
from app.models.clinical.precaution import PrecautionRecord
from app.persistence.repository import transaction
from tests.test_endocrine_gateway import endocrine
from tests.test_renal_fluid_entry import pin, post, seed, ws


def test_precaution_catalog_and_resolve_keep_original_revision(ws):
    client, _, app = ws
    raw = endocrine('m20-precaution')
    for field in ('nutrition', 'category', 'change_state', 'linked_sources'):
        raw.pop(field, None)
    raw.update(kind='precaution_record', status='in_place', precaution='Contact precautions', id='m20-precaution',
               title='Fictional precautions record', narrative='Original documented precaution.')
    original = PrecautionRecord.model_validate(raw)
    with transaction(app.core.state.dependencies.engine) as repo:
        repo.append_fact(original, target=TARGET)
    catalog = client.get(RF2).json()
    evidence, = catalog['precaution_records']

    amended = deepcopy(raw)
    amended.update(revision='2', report_status='corrected', status='discontinued', narrative='Corrected documented precaution.',
                   correction_reason='Fictional precaution source correction',
                   supersedes=original.reference.model_dump(mode='json'))
    amended['source_identity']['source_version'] = '2'
    amended['times']['available']['value'] = '2026-10-08T09:45:00Z'
    with transaction(app.core.state.dependencies.engine) as repo:
        repo.append_revision(PrecautionRecord.model_validate(amended), target=TARGET)
    earlier, = client.get(RF2, params={'review_end': '2026-10-08T09:44:59Z'}).json()['precaution_records']
    assert earlier['fact']['revision'] == '1'
    latest, = client.get(RF2).json()['precaution_records']
    assert latest['fact']['revision'] == '2'
    request = {'repository': catalog['repository'], 'pins': [pin(evidence)]}
    assert post(client, '/resolve', request).json()['items'] == [evidence]
    exact_history = post(client, '/history', request).json()['items']
    assert [item['fact']['revision'] for item in exact_history] == ['1']
    assert earlier['fact']['status'] == 'in_place'
    assert latest['fact']['status'] == 'discontinued'
