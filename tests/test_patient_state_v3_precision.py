"""Director regressions: independently specified correction boundaries."""
import pytest
from app.models.clinical.common import LineageEdge
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError, EvidencePin
from test_persistence import database, registered
from test_patient_state_v3 import h, PROV, TARGET, change, records
from test_patient_state_v3_inference import inputs, selected


def raw_stamp(value):
    return h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':value},clock='verified',clock_basis=PROV)


def test_f1_material_fractional_precision_abstains(registered):
    p,l,v=inputs()
    p=change(p,occurred=raw_stamp('2026-10-08T08:00:00.1234561+05:30'))
    v=change(v,occurred=raw_stamp('2026-10-08T08:00:00.1234569+05:30'))
    a,r=selected(registered,(p,l,v))
    assert next(i.fact for i in a.snapshot.items if i.reference==p.reference).occurred.source_timestamp.endswith('1234561+05:30')
    with pytest.raises(CirculatoryInferenceError,match='untrustworthy_clinical_time'):
        build_circulatory_timing_inference(assembly=a,request=r)



@pytest.mark.parametrize('fraction,trustworthy', [('123456',True),('1234560',True),('123456000000',True),('1234561',False),('123456000001',False)])
def test_fractional_boundaries_preserve_source(fraction,trustworthy):
    value='2026-10-08T08:00:00.'+fraction+'+05:30'
    t=raw_stamp(value)
    assert t.trustworthy is trustworthy
    assert h.ClinicalInstant.model_validate_json(t.model_dump_json()).source_timestamp==value


@pytest.mark.parametrize('field',['alternative_sources','conflicting'])
def test_lossy_supporting_time_assertions_abstain(field):
    t=raw_stamp('2026-10-08T08:00:00.123456+05:30')
    value='2026-10-08T08:00:00.1234569+05:30'
    if field=='alternative_sources':
        from test_patient_state_v3 import code
        values=({'recorded':{'status':'known','precision':'instant','value':value},'source':code(),'clock':'verified','provenance':PROV},)
    else: values=(value,)
    t=change(t,**{field:values})
    assert not t.trustworthy
    assert value in t.model_dump_json()


def test_old_timestamp_serialization_unchanged():
    from test_patient_state_v3 import stamp
    t=stamp()
    assert 'conflicting_source_timestamps' not in t.model_dump()
    assert 'source_timestamp' not in h.SourceTimeAssertion(recorded=t.recorded,source={'namespace':'synthetic','code':'clock','raw_display':'clock'},clock='verified',provenance=PROV).model_dump()

@pytest.mark.parametrize('component',['primary','alternative','conflicting'])
def test_explicit_empty_lexeme_cannot_hide_lost_precision(component):
    from test_patient_state_v3 import code
    value='2026-10-08T08:00:00.1234569+05:30'
    raw={'recorded':{'status':'known','precision':'instant','value':value},'source_timestamp':None,'clock':'verified','clock_basis':PROV}
    if component=='primary':t=h.ClinicalInstant.model_validate(raw)
    elif component=='alternative':
        alt={k:v for k,v in raw.items() if k!='clock_basis'}
        alt.update(source=code(),provenance=PROV)
        t=change(raw_stamp('2026-10-08T08:00:00.123456+05:30'),alternative_sources=(alt,))
    else:t=change(raw_stamp('2026-10-08T08:00:00.123456+05:30'),conflicting=(value,),conflicting_source_timestamps=())
    assert not t.trustworthy
    assert value in t.model_dump_json()


def test_alternative_time_malformed_recorded_is_validation_error():
    from pydantic import ValidationError
    from test_patient_state_v3 import code
    import json
    data={'recorded':'private invalid','source':code().model_dump(),'provenance':PROV.model_dump(mode='json')}
    with pytest.raises(ValidationError):h.SourceTimeAssertion.model_validate_json(json.dumps(data))


def test_precision_lexemes_survive_reopen_and_canonical_projection(registered):
    from test_patient_state_v3_persistence import save
    from app.persistence.repository import transaction
    from app.persistence.canonical import canonical_payload
    p=change(inputs()[0],occurred=raw_stamp('2026-10-08T08:00:00.123456100+05:30'))
    save(registered,p);registered.dispose()
    with transaction(registered) as repo:f=repo.load_fact(p.reference,target=TARGET).fact
    assert canonical_payload(f)==canonical_payload(p)
    assert '2026-10-08T08:00:00.123456100+05:30' in f.model_dump_json()
    assert not f.occurred.trustworthy

@pytest.mark.parametrize('value,trustworthy',[
    ('2026-10-08_08:00:00.1234561+05:30',False),
    ('2026-10-08_08:00:00.123456000+05:30',True),
    ('1791417600.1234561',False),('1791417600.12345600000000000000000000000001',False),('1791417600.123456000',True),
    ('1791417600123.4561',False),('1791417600123.456000',True)])
def test_all_parser_accepted_source_forms_check_precision(value,trustworthy):
    t=raw_stamp(value)
    assert t.trustworthy is trustworthy
    assert h.ClinicalInstant.model_validate_json(t.model_dump_json()).source_timestamp==value
