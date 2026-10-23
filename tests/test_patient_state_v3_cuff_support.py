"""PR #23 F1: applied cuff adequacy is consumed, exact protected evidence."""
from datetime import timedelta

import pytest

from app.execution.patient_state_v3_inference import (
    CirculatoryInferenceError, build_circulatory_timing_inference as build,
)
from app.models.clinical.common import LineageEdge
from test_persistence import database, registered
from test_patient_state_v3 import AT, PROV, TARGET, change, h, records, stamp
from test_patient_state_v3_inference import inputs, selected
from test_patient_state_v3_persistence import revised, save
from test_patient_state_v3_support import execution
from test_patient_state_v3_workflow import clock, forbidden, w, c, count


def cuff_case(path='adequacy'):
    p, l, v = inputs()
    support = change(records()[11], occurred=stamp(AT-timedelta(days=1)))
    provenance = change(PROV, upstream=(LineageEdge(target=support.reference, relationship='derived_from'),))
    acquisition = change(p.acquisition, method='automated_cuff', zeroing='not_applicable',
                         zeroing_provenance=None, zeroing_application=None)
    if path == 'adequacy':
        acquisition = change(acquisition, calibration_provenance=provenance)
    else:
        p = change(p, associations=(h.EvidenceBinding(role='calibration', scope=TARGET,
            status='resolved', exact=support.reference, provenance=PROV),))
    return change(p, acquisition=acquisition), l, v, support


@pytest.mark.parametrize('path', ['adequacy', 'association'])
def test_applied_cuff_missing_exact_support_pin_rejects(registered, path):
    facts = cuff_case(path)
    assembly, request = selected(registered, facts)
    item = next(i for i in assembly.snapshot.items if i.reference == facts[-1].reference)
    assert item.inclusion == 'contextual'
    with pytest.raises(CirculatoryInferenceError, match='supporting_dependency_mismatch'):
        build(assembly=assembly, request=request)


@pytest.mark.parametrize('path', ['adequacy', 'association'])
@pytest.mark.parametrize('correction', [None, 'same_value', 'provenance', 'withdrawn'])
def test_applied_cuff_support_is_in_lineage_and_final_witnesses(registered, path, correction):
    facts = cuff_case(path)
    support = facts[-1]
    request = execution(registered, facts)
    if correction is not None:
        fields = ({'provenance': change(support.provenance, actor='corrected source')}
                  if correction == 'provenance' else {'record_status': 'withdrawn'}
                  if correction == 'withdrawn' else {})
        save(registered, revised(support, **fields))
    receipt = w.execute_circulatory_review(registered, request, clock=clock)
    assert receipt.record.decision.outcome == ('released' if correction is None else 'withheld')
    assert receipt.record.evidence.inference.inputs[-1] == support.reference
    assert receipt.record.evidence.inference.provenance.upstream[-1].target == support.reference
    assert receipt.record.evidence.facts[-1] == support
    witness = receipt.record.final_recheck.evidence[-1]
    assert witness.consumed == support.reference
    assert witness.terminal == (support.reference if correction is None else revised(support).reference)
    assert w.reconcile_circulatory_execution(registered, request).stored == receipt
    assert w.execute_circulatory_review(registered, request, clock=forbidden) == receipt


def test_applied_cuff_future_adequacy_provenance_abstains(registered):
    p, l, v = inputs()
    p = change(p, acquisition=change(p.acquisition, method='automated_cuff',
        calibration_provenance=change(PROV, recorded_at=AT+timedelta(hours=1))))
    assembly, request = selected(registered, (p, l, v))
    with pytest.raises(CirculatoryInferenceError, match='future_recording'):
        build(assembly=assembly, request=request)


def test_cuff_not_required_does_not_consume_adequacy_or_transducer_zeroing(registered):
    p, l, v, support = cuff_case()
    future = change(PROV, recorded_at=AT+timedelta(hours=1),
        upstream=(LineageEdge(target=support.reference, relationship='derived_from'),))
    p = change(p, acquisition=change(p.acquisition, calibration='unknown',
        calibration_provenance=future,
        calibration_application=change(p.acquisition.calibration_application, status='not_required'),
        zeroing_provenance=future),
        associations=(h.EvidenceBinding(role='zeroing', scope=TARGET, status='unresolved',
            provenance=future, limitation='not applicable to cuff'),
            h.EvidenceBinding(role='calibration', scope=TARGET, status='unresolved',
            provenance=future, limitation='not required for this acquisition')))
    assembly, request = selected(registered, (p, l, v, support))
    assert build(assembly=assembly, request=request).inputs == tuple(f.reference for f in (p, l, v))


@pytest.mark.parametrize('committed', [False, True])
def test_prior_cuff_selection_cannot_gain_new_release_but_receipts_stay_retained(registered, monkeypatch, committed):
    # Recreate the prior omitted-cuff rule only while producing the old request.
    from uuid import uuid4
    from sqlalchemy import text
    from app.execution import patient_state_v3_support as support_rules
    from app.persistence.errors import StorageIntegrityError
    original = support_rules._applied_cuff_calibration
    monkeypatch.setattr(support_rules, '_applied_cuff_calibration', lambda fact: False)
    assembly, timing = selected(registered, cuff_case())
    inference = build(assembly=assembly, request=timing)
    cutoff = save(registered, inference)
    request = c.CirculatoryExecutionRequest(execution_id=uuid4(), target=c.GRANT_TARGET,
        actor=c.GRANT_ACTOR, inference_request=timing, assembly_request=assembly.request,
        inference_cutoff=cutoff, expected_inference_digest=c.digest(inference), requested_at=c.GRANT_WINDOW.start)
    if committed:
        receipt = w.execute_circulatory_review(registered, request, clock=clock)
        with registered.connect() as conn:
            payload = conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one()
    monkeypatch.setattr(support_rules, '_applied_cuff_calibration', original)
    if committed:
        monkeypatch.setattr(w, '_new_execution', forbidden)
        assert w.execute_circulatory_review(registered, request, clock=forbidden) == receipt
        assert w.reconcile_circulatory_execution(registered, request).stored == receipt
        with registered.connect() as conn:
            assert conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one() == payload
    else:
        with pytest.raises(StorageIntegrityError):
            w.execute_circulatory_review(registered, request, clock=clock)
        assert count(registered) == 0
        assert w.reconcile_circulatory_execution(registered, request).status == 'absent'
