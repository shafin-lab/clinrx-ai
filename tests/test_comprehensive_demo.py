"""Read-only demo uses full evidence and real retained receipts with the API gate closed."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.demo.comprehensive import bootstrap, RELEASED_ID, WITHHELD_ID
from app.demo.circulatory import SIMULATION_AT
from app.api.config import APIConfig
from app.main import create_app
from app.models.clinical.hemodynamics import M7_FACTS
from app.persistence.database import create_database
from app.persistence.repository import transaction

P='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'

def test_comprehensive_fixture_browses_all_families_and_retained_examples_while_gated(tmp_path):
    path=tmp_path/'demo.sqlite3';engine=create_database(path)
    try:
        manifest=bootstrap(engine)
        config=APIConfig(database_path=path,environment='test',envelope_signing_key='b7'*32,
            clock_mode='historical_simulation',simulation_at=SIMULATION_AT)
        with TestClient(create_app(config,engine=engine)) as client:
            state=client.get(P+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')}).json()
            assert state['execution_enabled'] is False
            items=state['assembly']['snapshot']['items'];assert len(items)==41
            assert {i['fact']['kind'] for i in items}==set(M7_FACTS)-{'circulatory_device_prediction'}
            by_id={i['fact']['id']:i for i in items}
            assert 'm7-HPI' not in by_id
            assert manifest['recorded_families']==14 and manifest['optional_hpi_included'] is False
            assert by_id['m7-CO']['fact']['result']['quantity']['value']=='4.50'
            assert by_id['m7-CO']['fact']['acquisition']['method']=='bolus_thermodilution'
            assert all(by_id[id]['fact']['acquisition']['method']=='echo' for id in ('m7-ECHO','m7-EF','m7-VTI'))
            assert by_id['m7-FLOTRAC']['fact']['acquisition']['device']['technology']=='FloTrac'
            assert by_id['m7-VOLUMEVIEW']['fact']['acquisition']['device']['platform']=='EV1000'
            assert by_id['m7-PICCO-CO']['fact']['acquisition']['quality']['status']=='unknown'
            assert by_id['m7-UNPLACED']['inclusion']=='unplaced'
            for id,outcome in ((RELEASED_ID,'released'),(WITHHELD_ID,'withheld')):
                response=client.get(P+'/circulatory-reviews/'+str(id));assert response.status_code==200
                receipt=response.json();record=receipt['record'];assert record['decision']['outcome']==outcome
                assert record['evidence']['facts'][-1]['id']=='m7-CAL' and record['evidence']['facts'][-1]['revision']=='1'
                assert record['final_recheck']['evidence'][-1]['terminal']['version']==('1' if outcome=='released' else '2')
                assert (receipt['statement'] is None)==(outcome=='withheld')
                assert client.get(P+'/circulatory-reviews/'+str(id)).content==response.content
            support=by_id['m7-CAL'];ref={'kind':support['fact']['kind'],'id':'m7-CAL','version':'2'}
            history=client.post(P+'/circulatory-evidence-history',json={'state_context':state['state_context'],'reference':ref})
            assert history.status_code==200 and [i['fact']['revision'] for i in history.json()['revisions']]==['1','2']
            body={'execution_id':'00000000-0000-4000-8000-00000000c903','state_context':state['state_context']}
            for role,id in (('pressure','m7-P'),('lactate','m7-L'),('vasopressor','m7-V')):
                item=by_id[id];body[role]={'reference':{'kind':item['fact']['kind'],'id':id,'version':'1'},'expected_digest':item['expected_digest']}
            with transaction(engine) as repo:before=repo.capture_cutoff().fact_watermark
            assert client.post(P+'/circulatory-review-preparations',json=body).status_code==422
            with transaction(engine) as repo:assert repo.capture_cutoff().fact_watermark==before
    finally:engine.dispose()

def test_comprehensive_bootstrap_refuses_to_replace_existing_data(tmp_path):
    engine=create_database(tmp_path/'demo.sqlite3')
    try:
        bootstrap(engine)
        with transaction(engine) as repo:before=repo.capture_cutoff().fact_watermark
        with pytest.raises(ValueError,match='fresh disposable'):bootstrap(engine)
        with transaction(engine) as repo:assert repo.capture_cutoff().fact_watermark==before
    finally:engine.dispose()


def test_expanded_abg_echo_records_survive_canonical_roundtrip_and_old_oxygen_is_unchanged():
    from app.demo.comprehensive import demo_facts, replace
    from app.demo.circulatory import facts
    from app.models.clinical import hemodynamics as h
    from app.persistence.canonical import canonical_payload
    from pydantic import ValidationError
    by_id={f.id:f for f in demo_facts()}
    expected={'PH':('ph','7.31'),'PACO2':('paco2','48.0'),'PAO2':('pao2','78.0'),
        'HCO3':('bicarbonate','23.0'),'BE':('base_excess','-2.0'),
        'SAO2':('sao2','95.0'),'HB':('hemoglobin','10.2')}
    for suffix,(analyte,value) in expected.items():
        fact=by_id['m7-ABG-'+suffix]
        decoded=h.OxygenTransport.model_validate_json(fact.model_dump_json())
        assert canonical_payload(decoded)==canonical_payload(fact)
        assert decoded.concept==analyte and str(decoded.result.quantity.value)==value
        assert decoded.sample_type=='arterial'
        assert decoded.blood_gas_context.collected==decoded.occurred
        assert str(decoded.blood_gas_context.fio2.value)=='40'
        assert str(decoded.blood_gas_context.peep.value)=='5'
        assert decoded.specimen.code=='synthetic-arterial-sample-1'
    old=next(f for f in facts() if f.id=='m7-SVO2')
    assert 'blood_gas_context' not in old.model_dump(mode='json')
    assert canonical_payload(h.OxygenTransport.model_validate_json(old.model_dump_json()))==canonical_payload(old)
    with pytest.raises(ValidationError):replace(by_id['m7-ABG-PACO2'],sample_type='mixed_venous')
    with pytest.raises(ValidationError):replace(by_id['m7-ABG-PH'],sample_type='noninvasive')
    with pytest.raises(ValidationError):
        h.BloodGasContext.model_validate({**by_id['m7-ABG-PH'].blood_gas_context.model_dump(),
            'fio2':{'value':0.4,'unit':{'raw':'1','status':'unresolved','limitation':'test'}}})
    for id in ('m7-RVSP','m7-PASP','m7-TRV','m7-RVD','m7-RVFUNCTION','m7-SEPTUM','m7-VALVE','m7-EFFUSION','m7-PH','m7-VTI'):
        fact=by_id[id]
        assert canonical_payload(h.EchoObservation.model_validate_json(fact.model_dump_json()))==canonical_payload(fact)
    assert by_id['m7-RVSP'].production=='source_calculated'
    assert 'no invasive confirmation or PAH subtype' in by_id['m7-PH'].result.finding.raw_display
    with_hpi=demo_facts(include_hpi=True)
    assert len(with_hpi)==42 and len({f.kind for f in with_hpi})==15
    assert next(f for f in with_hpi if f.id=='m7-HPI').acquisition.device.technology=='AcumenIQ'


def test_bootstrap_with_optional_hpi_keeps_gate_closed_and_receipts_available(tmp_path):
    engine=create_database(tmp_path/'hpi.sqlite3')
    try:
        result=bootstrap(engine,include_hpi=True)
        assert result['recorded_families']==15 and result['optional_hpi_included'] is True
        assert result['execution_enabled'] is False
    finally:engine.dispose()
