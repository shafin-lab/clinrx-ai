"""B1/B2 independent safe-outcome reproductions and precision admission matrix."""
import json
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError
from test_patient_state_v3 import h, PROV, code, change, AT
from test_patient_state_v3_precision import raw_stamp


def json_time(token,where='primary'):
    recorded='{"status":"known","precision":"instant","value":'+token+'}'
    if where=='primary':
        text='{"recorded":'+recorded+',"clock":"verified","clock_basis":'+PROV.model_dump_json()+'}'
    else:
        base=raw_stamp('1791426600.123456').model_dump(mode='json')
        base['alternative_sources']=[]
        text=json.dumps(base)[:-1]+',"alternative_sources":[{"recorded":'+recorded+',"clock":"verified","source":'+code().model_dump_json()+',"provenance":'+PROV.model_dump_json()+'}]}'
    return h.ClinicalInstant.model_validate_json(text)


@pytest.mark.parametrize('case',range(7))
def test_director_seven_precision_assertions(case):
    try:
        if case<4:
            value=(b'2026-10-08T08:00:00.1234561+05:30' if case%2==0 else b'1791426600123456.1e-6')
            if case<2:t=raw_stamp(value)
            else:
                t=change(raw_stamp('1791426600.123456'),alternative_sources=({'recorded':{'status':'known','precision':'instant','value':value},'source':code(),'clock':'verified','provenance':PROV},))
        else:
            token='1791426600.12345601' if case!=5 else '1791426600123456.01e-6'
            t=json_time(token,'alternative' if case==6 else 'primary')
    except ValidationError:
        return
    assert not t.trustworthy


@pytest.mark.parametrize('where',['primary','alternative','conflicting'])
@pytest.mark.parametrize('kind',['iso','bytes_iso','numeric','bytes_numeric','integer','decimal','datetime','float'])
@pytest.mark.parametrize('lossy',[False,True])
def test_python_admitted_matrix(where,kind,lossy):
    iso='2026-10-08T08:00:00.'+('1234561' if lossy else '123456')+'+05:30'
    numeric='1791426600123456.'+('1' if lossy else '0')+'e-6'
    value={'iso':iso,'bytes_iso':iso.encode(),'numeric':numeric,'bytes_numeric':numeric.encode(),
        'integer':1791426600,'decimal':Decimal(numeric),'datetime':AT,'float':1791426600.123456}[kind]
    known=raw_stamp('1791426600' if kind=='integer' else '1791426600.123456')
    fields={'recorded':{'status':'known','precision':'instant','value':value},'clock':'verified','clock_basis':PROV,'timestamp_precision':h.PRECISION_CONTRACT}
    try:
        if where=='primary':t=h.ClinicalInstant(**fields)
        elif where=='alternative':
            fields.pop('clock_basis');fields.update(source=code(),provenance=PROV)
            t=change(known,alternative_sources=(fields,))
        else:t=change(known,conflicting=(value,))
    except ValidationError:
        assert kind=='float'
        return
    expected=not (lossy and kind in ('iso','bytes_iso','numeric','bytes_numeric','decimal'))
    assert t.trustworthy is expected
    restored=h.ClinicalInstant.model_validate_json(t.model_dump_json())
    assert restored==t and restored.trustworthy is expected
    raw=(t.source_timestamp if where=='primary' else t.alternative_sources[0].source_timestamp if where=='alternative' else t.conflicting_source_timestamps[0])
    if kind.startswith('bytes'):assert raw==value.decode()


@pytest.mark.parametrize('where',['primary','alternative','conflicting'])
@pytest.mark.parametrize('token',[json.dumps('2026-10-08T08:00:00.123456+05:30'),json.dumps('2026-10-08T08:00:00.1234561+05:30'),json.dumps('1791426600123456.0e-6'),json.dumps('1791426600123456.1e-6'),'1791426600','1791426600.12345601','1791426600.12345604','1791426600123456.01e-6','1791426600123456.04e-6','1.79142660012345604e9'])
def test_raw_json_token_matrix(where,token):
    template={'recorded':{'status':'known','precision':'instant','value':'TOKEN'},'clock':'verified','clock_basis':PROV.model_dump(mode='json'),'timestamp_precision':h.PRECISION_CONTRACT}
    if where=='primary':data=template
    else:
        data=raw_stamp('1791426600' if token=='1791426600' else '1791426600.123456').model_dump(mode='json')
        if where=='conflicting':data['conflicting']=['TOKEN']
        else:
            template.pop('clock_basis');template.update(source=code().model_dump(),provenance=PROV.model_dump(mode='json'))
            data['alternative_sources']=[template]
    raw=json.dumps(data).replace('"TOKEN"',token)
    floating=not token.startswith('"') and token!='1791426600'
    if floating:
        with pytest.raises(ValidationError):h.ClinicalInstant.model_validate_json(raw)
    else:
        t=h.ClinicalInstant.model_validate_json(raw)
        expected='1234561' not in token and '.1e-6' not in token
        assert t.trustworthy is expected
        assert h.ClinicalInstant.model_validate_json(t.model_dump_json())==t


@pytest.mark.parametrize('where',['primary','alternative','conflicting'])
def test_invalid_bytes_are_structured(where):
    value=b'\xffprivate'
    with pytest.raises(ValidationError):
        if where=='primary':raw_stamp(value)
        elif where=='alternative':change(raw_stamp('1791426600.123456'),alternative_sources=({'recorded':{'status':'known','precision':'instant','value':value},'source':code(),'clock':'verified','provenance':PROV},))
        else:change(raw_stamp('1791426600.123456'),conflicting=(value,))


def test_missing_or_legacy_numeric_precision_never_becomes_new_proof():
    for source in [None,'1791426600.123456']:
        t=h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':AT if source is None else AT.astimezone(timezone.utc)},source_timestamp=source,clock='verified',clock_basis=PROV)
        assert not t.trustworthy
        raw=t.model_dump_json()
        assert h.ClinicalInstant.model_validate_json(raw).model_dump_json()==raw
    # Genuine legacy ISO source evidence is distinguishable from the reviewed
    # producers' rounded numeric source spellings and remains usable.
    t=h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':AT},source_timestamp=AT.isoformat(),clock='verified',clock_basis=PROV)
    assert t.trustworthy and t.timestamp_precision is None

from uuid import uuid4
from app.execution import patient_state_v3_workflow as w, patient_state_v3_execution as c
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError
from app.persistence.repository import transaction
from app.persistence.errors import StorageIntegrityError, RecordConflict
from test_persistence import database, registered
from test_patient_state_v3_inference import inputs, selected
from test_patient_state_v3_persistence import save
from test_patient_state_v3_workflow import clock, count


@pytest.mark.parametrize('where',['primary','alternative','conflicting'])
@pytest.mark.parametrize('exponent',[False,True])
@pytest.mark.parametrize('lossy',[False,True])
def test_bytes_reopen_and_protected_execution(registered,where,exponent,lossy):
    raw=(('1791426600123456.1e-6' if lossy else '1791426600123456.000e-6') if exponent else ('2026-10-08T08:00:00.1234561+05:30' if lossy else AT.isoformat())).encode()
    other=raw.replace(b'1234561',b'1234569').replace(b'.1e-',b'.4e-')
    p,l,v=inputs()
    if where=='primary':p=change(p,occurred=raw_stamp(raw));v=change(v,occurred=raw_stamp(other))
    elif where=='alternative':
        t=change(raw_stamp(AT.isoformat()),alternative_sources=({'recorded':{'status':'known','precision':'instant','value':raw},'timestamp_precision':h.PRECISION_CONTRACT,'source':code(),'clock':'verified','provenance':PROV},))
        p=change(p,occurred=t)
    else:p=change(p,occurred=change(raw_stamp(AT.isoformat()),conflicting=(raw,)))
    a,r=selected(registered,(p,l,v));registered.dispose()
    with transaction(registered) as repo:
        retained=repo.load_fact(p.reference,target=r.scope.target).fact
        assert retained.canonical_digest==p.canonical_digest
        assert raw.decode() in retained.model_dump_json()
    if lossy:
        with pytest.raises(CirculatoryInferenceError):build_circulatory_timing_inference(assembly=a,request=r)
        assert count(registered)==0
    else:
        i=build_circulatory_timing_inference(assembly=a,request=r);cutoff=save(registered,i)
        req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
            inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
            expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
        receipt=w.execute_circulatory_review(registered,req,clock=clock)
        assert receipt.record.decision.outcome=='released'
        assert w.reconcile_circulatory_execution(registered,req).stored==receipt


@pytest.mark.parametrize('where',['primary','alternative','conflicting'])
@pytest.mark.parametrize('token',['1791426600.12345601','1791426600.12345604','1791426600123456.01e-6'])
def test_nested_raw_json_and_persistence_decode_never_float_coerce(registered,where,token):
    from sqlalchemy import text
    p=inputs()[0];save(registered,p)
    data=p.model_dump(mode='json');instant=data['occurred']
    if where=='primary':instant['recorded']['value']='TOKEN'
    elif where=='conflicting':instant['conflicting']=['TOKEN']
    else:instant['alternative_sources']=[{'recorded':{'status':'known','precision':'instant','value':'TOKEN'},'source':code().model_dump(),'clock':'verified','provenance':PROV.model_dump(mode='json')}]
    raw=json.dumps(data).replace('"TOKEN"',token)
    with pytest.raises(ValidationError):h.PressureObservation.model_validate_json(raw)
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET payload=:raw WHERE fact_id='p'"),{'raw':raw})
    with pytest.raises(StorageIntegrityError):
        with transaction(registered) as repo:repo.load_fact(p.reference,target=p.binding.target)
    assert count(registered)==0


def test_precision_declaration_cannot_silently_upgrade_an_exact_revision(registered):
    p=inputs()[0]
    legacy=change(p,occurred=h.ClinicalInstant(
        recorded={'status':'known','precision':'instant','value':AT.astimezone(timezone.utc)},
        source_timestamp='1791426600.123456',clock='verified',clock_basis=PROV))
    save(registered,legacy)
    asserted=change(legacy,occurred=change(legacy.occurred,timestamp_precision=h.PRECISION_CONTRACT))
    assert asserted.canonical_digest!=legacy.canonical_digest
    with pytest.raises(RecordConflict):save(registered,asserted)
    with transaction(registered) as repo:assert repo.load_fact(legacy.reference,target=p.binding.target).fact==legacy


def test_corrupt_receipt_raw_number_is_integrity_failure_not_absence(registered):
    from sqlalchemy import text
    from test_patient_state_v3_workflow import prepare
    req=prepare(registered);w.execute_circulatory_review(registered,req,clock=clock)
    with registered.begin() as conn:
        payload=json.loads(conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one())
        def damage(value):
            if isinstance(value,dict):
                if value.get('kind')=='circulatory_pressure' and 'occurred' in value:
                    value['occurred']['recorded']['value']='TOKEN'
                for item in value.values():damage(item)
            elif isinstance(value,list):
                for item in value:damage(item)
        damage(payload)
        raw=json.dumps(payload).replace('"TOKEN"','1791426600.12345601')
        conn.execute(text('UPDATE circulatory_execution SET payload=:raw'),{'raw':raw})
    with pytest.raises(StorageIntegrityError):w.reconcile_circulatory_execution(registered,req)
