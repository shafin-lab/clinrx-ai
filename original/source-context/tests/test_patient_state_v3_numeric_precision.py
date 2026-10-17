"""Director R1: exact decimal meaning, including exponent notation."""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.execution import patient_state_v3_execution as c, patient_state_v3_workflow as w
from app.execution.patient_state_v3_inference import CirculatoryInferenceError, build_circulatory_timing_inference
from app.persistence.errors import StorageIntegrityError
from app.persistence.repository import transaction
from test_persistence import database, registered
from test_patient_state_v3 import h, PROV, TARGET, change, code
from test_patient_state_v3_precision import raw_stamp
from test_patient_state_v3_inference import inputs, selected
from test_patient_state_v3_persistence import save
from test_patient_state_v3_workflow import clock, count


def exponent_inputs():
    p,l,v=inputs()
    return change(p,occurred=raw_stamp('1791426600123456.1e-6')),l,change(v,occurred=raw_stamp('1791426600123456.4e-6'))


def test_director_exponents_cannot_be_trusted_or_inferred(registered):
    p,l,v=exponent_inputs();a,r=selected(registered,(p,l,v))
    assert p.occurred.recorded.value==v.occurred.recorded.value
    with pytest.raises(CirculatoryInferenceError,match='untrustworthy_clinical_time'):
        build_circulatory_timing_inference(assembly=a,request=r)


@pytest.mark.parametrize('value,exact',[
    ('1791426600123456.1e-6',False),('1791426600123456.4e-6',False),
    ('1791426600.123456000e+0',True),('1791426600123456.0e-6',True),
    ('1791426600123.456000e0',True),('17914266001234561.0e-7',False),
    ('1.7914266001234561e+9',False),('1.791426600123456e+9',True),
    ('1.7914266001234561e+12',False),('1.791426600123456e+12',True),
    ('2.0e10',True),('20000000000.000001',False),
    ('20000000000.0000001',False),('20000000001',True),
    ('20000000001.000001',False),('20000000001.001',True),
    ('-2.0e10',True),('-20000000000.000001',False),
    ('-20000000000.0000001',False),('-20000000001.001',True),
    ('1.0e-1000000',False),('0.0e-1000000',True),
])
def test_numeric_meaning_compared_exactly_without_decimal_context_rounding(value,exact):
    t=raw_stamp(value)
    assert t.trustworthy is exact
    assert h.ClinicalInstant.model_validate_json(t.model_dump_json()).source_timestamp==value


@pytest.mark.parametrize('where',['alternative','conflicting'])
def test_exponent_support_assertions_preserved_and_unsuitable(where):
    raw='1791426600123456.1e-6';t=raw_stamp('1791426600.123456')
    if where=='alternative':
        t=change(t,alternative_sources=({'recorded':{'status':'known','precision':'instant','value':raw},'source':code(),'clock':'verified','provenance':PROV},))
    else:t=change(t,conflicting=(raw,))
    assert not t.trustworthy and raw in t.model_dump_json()
    assert h.ClinicalInstant.model_validate_json(t.model_dump_json())==t


def test_numeric_evidence_survives_persistence_and_reopen(registered):
    p,l,v=exponent_inputs();save(registered,p,l,v);registered.dispose()
    with transaction(registered) as repo:
        for f in (p,v):
            restored=repo.load_fact(f.reference,target=TARGET).fact
            assert restored.canonical_digest==f.canonical_digest
            assert restored.occurred.source_timestamp==f.occurred.source_timestamp
            assert not restored.occurred.trustworthy


def test_affected_old_preparation_cannot_release_after_precision_fix(registered,monkeypatch):
    # Recreate the reviewed old producer's receipt preparation, then remove it.
    original=h._lossless_microseconds
    monkeypatch.setattr(h,'_lossless_microseconds',lambda v: True)
    a,r=selected(registered,exponent_inputs())
    i=build_circulatory_timing_inference(assembly=a,request=r)
    assert 'Pressure acquisition occurred at the initiation event.' in i.statement
    cutoff=save(registered,i)
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    monkeypatch.setattr(h,'_lossless_microseconds',original)
    with pytest.raises(StorageIntegrityError) as caught:w.execute_circulatory_review(registered,req,clock=clock)
    assert str(caught.value)=='circulatory execution integrity failure'
    assert count(registered)==0
    assert w.reconcile_circulatory_execution(registered,req).status=='absent'


def test_decimal_context_cannot_change_timestamp_trust():
    from decimal import localcontext
    with localcontext() as ctx:
        ctx.prec=1
        assert raw_stamp('1791426600123456.0e-6').trustworthy
        assert not raw_stamp('1791426600123456.1e-6').trustworthy


@pytest.mark.parametrize('raw',['2e10','1791426600123456e-6'])
def test_parser_rejected_exponent_spellings_stay_rejected(raw):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):raw_stamp(raw)


def test_lossless_exponent_preparation_can_release(registered):
    p,l,v=inputs()
    p=change(p,occurred=raw_stamp('1791426600123456.0000e-6'))
    v=change(v,occurred=raw_stamp('1.791426600123456e+9'))
    a,r=selected(registered,(p,l,v));i=build_circulatory_timing_inference(assembly=a,request=r)
    cutoff=save(registered,i)
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    receipt=w.execute_circulatory_review(registered,req,clock=clock)
    assert receipt.record.decision.outcome=='released'
    assert 'Pressure acquisition occurred at the initiation event.' in receipt.record.evidence.inference.statement


def test_global_decimal_parse_traps_do_not_reject_exact_iso_evidence():
    from decimal import localcontext, InvalidOperation
    with localcontext() as ctx:
        ctx.traps[InvalidOperation]=False
        assert raw_stamp('2026-10-08T08:00:00.123456+05:30').trustworthy
        assert raw_stamp('1791426600123456.0e-6').trustworthy
        assert not raw_stamp('1791426600123456.1e-6').trustworthy


@pytest.mark.parametrize('mode',['python','json'])
@pytest.mark.parametrize('where',['primary','alternative'])
@pytest.mark.parametrize('raw,exact',[(1791426600.1234565,False),(1791426600.123456,True),(0.0000001,False)])
def test_native_numeric_inputs_preserve_precision_evidence(mode,where,raw,exact):
    import json
    fields={'recorded':{'status':'known','precision':'instant','value':raw},'clock':'verified','clock_basis':PROV.model_dump(mode='json')}
    if where=='alternative':
        alternative={k:v for k,v in fields.items() if k!='clock_basis'}
        alternative.update(source=code().model_dump(),provenance=PROV.model_dump(mode='json'))
        fields=raw_stamp(str(raw) if 'e' not in str(raw) else '0.0000001').model_dump(mode='json')
        fields['alternative_sources']=[alternative]
    # Floating-point objects/raw JSON floating numbers have no recoverable token
    # precision. The declared B2 boundary now rejects them uniformly.
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        if mode=='python':h.ClinicalInstant.model_validate(fields)
        else:h.ClinicalInstant.model_validate_json(json.dumps(fields))
