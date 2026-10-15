"""Director R2: validation errors instead of incidental Python exceptions."""
import json
import pytest
from pydantic import ValidationError
from test_patient_state_v3 import h, change
from test_patient_state_v3_precision import raw_stamp


@pytest.mark.parametrize('mode',['python','json'])
def test_null_conflict_container_is_structured_rejection(mode):
    data=raw_stamp('1791426600.123456').model_dump(mode='json')
    data['conflicting']=None
    with pytest.raises(ValidationError):
        if mode=='python':h.ClinicalInstant.model_validate(data)
        else:h.ClinicalInstant.model_validate_json(json.dumps(data))


def test_mixed_iso_and_numeric_conflicting_times_admit():
    with pytest.raises(ValidationError):
        change(raw_stamp('1791426600.123456'),conflicting=('2026-10-08T02:30:00.123456Z',1791426600.123456))

from decimal import Decimal
from datetime import datetime, timezone
from app.persistence.canonical import canonical_payload
from test_patient_state_v3 import PROV, TARGET
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError
from test_patient_state_v3_inference import selected, inputs
from test_persistence import database, registered


@pytest.mark.parametrize('mode',['python','json'])
@pytest.mark.parametrize('bad',[None,12,1.5,True,'private malformed',{'private':'value'},[None],['2026-10-08T02:30:00Z',{}],[True],['not-a-time'],[['nested']]])
def test_malformed_conflicting_shapes_are_structured(mode,bad):
    data=raw_stamp('1791426600.123456').model_dump(mode='json');data['conflicting']=bad
    with pytest.raises(ValidationError) as caught:
        if mode=='python':h.ClinicalInstant.model_validate(data)
        else:h.ClinicalInstant.model_validate_json(json.dumps(data))
    assert caught.value.errors()


@pytest.mark.parametrize('mode',['python','json'])
@pytest.mark.parametrize('bad',[None,12,'not-a-container',[None],[123],{'private':'value'}])
def test_companion_lexeme_shapes_are_structured_before_capture(mode,bad):
    data=raw_stamp('1791426600.123456').model_dump(mode='json')
    data.update(conflicting=['1791426600123456.1e-6'],conflicting_source_timestamps=bad)
    with pytest.raises(ValidationError):
        if mode=='python':h.ClinicalInstant.model_validate(data)
        else:h.ClinicalInstant.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('mode',['python','json'])
def test_mixed_accepted_conflicts_round_trip(mode):
    data=raw_stamp('1791426600').model_dump(mode='json')
    values=['2026-10-08T08:00:00+05:30',1791426600,'1791426600.000e0']
    if mode=='python':values.extend([datetime(2026,10,8,2,30,0,tzinfo=timezone.utc),Decimal('1791426600')])
    data['conflicting']=values
    t=h.ClinicalInstant.model_validate(data) if mode=='python' else h.ClinicalInstant.model_validate_json(json.dumps(data))
    assert t.trustworthy
    assert t.conflicting_source_timestamps[0]==values[0]
    assert h.ClinicalInstant.model_validate_json(t.model_dump_json())==t
    assert canonical_payload(h.ClinicalInstant.model_validate_json(canonical_payload(t)))==canonical_payload(t)


@pytest.mark.parametrize('value',[0.0000001,Decimal('1E-7'),'1791426600123456.1e-6'])
def test_mixed_numeric_precision_not_erased(value):
    # Different instants are already unsuitable; ensure precision evidence also survives.
    if isinstance(value,float):
        with pytest.raises(ValidationError):change(raw_stamp('1791426600.123456'),conflicting=('2026-10-08T02:30:00.123456Z',value))
        return
    t=change(raw_stamp('1791426600.123456'),conflicting=('2026-10-08T02:30:00.123456Z',value))
    assert not t.trustworthy
    assert len(t.conflicting_source_timestamps)==2
    assert not h.ClinicalInstant.model_validate_json(t.model_dump_json()).trustworthy


@pytest.mark.parametrize('container',[list,tuple,iter])
def test_supported_python_containers_remain_supported(container):
    t=change(raw_stamp('1791426600.123456'),conflicting=container(['2026-10-08T02:30:00.123456Z',Decimal('1791426600.123456')]))
    assert t.trustworthy


def test_legacy_conflict_payload_does_not_gain_optional_fields():
    data=raw_stamp('1791426600.123456').model_dump(mode='json')
    data.pop('timestamp_precision',None)  # genuine pre-contract canonical shape
    data['conflicting']=['2026-10-08T02:30:00.123456Z']
    raw=json.dumps(data,sort_keys=True,separators=(',',':'))
    t=h.ClinicalInstant.model_validate_json(raw)
    assert canonical_payload(t)==raw
    assert 'conflicting_source_timestamps' not in t.model_dump()


def test_conflict_cardinality_keeps_exact_existing_cap():
    t=change(raw_stamp('1791426600.123456'),conflicting=('1791426600.123456',)*8)
    assert len(t.conflicting)==8
    with pytest.raises(ValidationError):change(t,conflicting=('1791426600.123456',)*9)


def test_invalid_timestamp_is_sanitized_at_builder_boundary(registered):
    a,r=selected(registered)
    raw=a.model_dump(mode='json');item=next(i for i in raw['snapshot']['items'] if i['fact']['id']=='p')
    item['fact']['occurred']['conflicting']=['PRIVATE_CLINICAL_PAYLOAD',None]
    with pytest.raises(CirculatoryInferenceError) as caught:build_circulatory_timing_inference(assembly=raw,request=r)
    assert str(caught.value)=='invalid_contract'
    assert caught.value.__suppress_context__


def test_stored_malformed_conflict_is_integrity_failure(registered):
    from sqlalchemy import text
    from app.persistence.repository import transaction
    from app.persistence.errors import StorageIntegrityError
    from test_patient_state_v3_persistence import save
    p=inputs()[0];save(registered,p)
    payload=p.model_dump(mode='json');payload['occurred']['conflicting']=None
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET payload=:payload WHERE fact_id='p'"),{'payload':json.dumps(payload)})
    with pytest.raises(StorageIntegrityError) as caught:
        with transaction(registered) as repo:repo.load_fact(p.reference,target=TARGET)
    assert 'PRIVATE' not in str(caught.value) and 'NoneType' not in str(caught.value)
