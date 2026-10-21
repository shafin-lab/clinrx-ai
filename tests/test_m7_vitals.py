"""Recorded vital sources round-trip through the real scoped M7 API."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.api.config import APIConfig
from app.demo.circulatory import bootstrap, fields, acquisition, quantity, SIMULATION_AT, TARGET
from app.main import create_app
from app.models.clinical import hemodynamics as h
from app.persistence.database import create_database
from app.persistence.repository import transaction


def vital(cls, id, concept, amount, unit, method='unknown', **extra):
    return cls(**fields(id), concept=concept, result=h.NumericResult(quantity=quantity(amount, unit)),
               acquisition=acquisition(method), production='direct_measurement', **extra)


def test_recorded_vitals_api_and_exact_respiratory_history(tmp_path):
    path=tmp_path/'vitals.sqlite3';engine=create_database(path);bootstrap(engine)
    records=[vital(h.CardiacPerformance,'VITAL-HR','heart_rate','88.00','/min','ecg_monitor'),
             vital(h.PressureObservation,'VITAL-SBP','systemic_systolic','104.00','mmHg','invasive_arterial'),
             vital(h.PressureObservation,'VITAL-DBP','systemic_diastolic','58.0','mmHg','invasive_arterial'),
             vital(h.OxygenTransport,'VITAL-SPO2','spo2','97.0','%','source_other',sample_type='noninvasive'),
             vital(h.OxygenTransport,'VITAL-RR','respiratory_rate','22.00','/min',sample_type='noninvasive')]
    with transaction(engine) as repo:
        for fact in records: repo.append_fact(fact,target=TARGET)
        before=repo.capture_cutoff().fact_watermark
    config=APIConfig(database_path=path,environment='test',envelope_signing_key='a9'*32,
        clock_mode='historical_simulation',simulation_at=SIMULATION_AT,circulatory_execution_enabled=False)
    prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
    try:
        with TestClient(create_app(config,engine=engine)) as client:
            response=client.get(prefix+'/patient-state-v3',params={'review_start':'2026-10-08T08:00:00Z','review_end':'2026-10-08T10:00:00Z'})
            assert response.status_code==200,response.text
            state=response.json();assert state['execution_enabled'] is False
            for fact in records:
                item=next(i for i in state['assembly']['snapshot']['items'] if i['fact']['id']==fact.id)
                assert item['fact']['result']['quantity']['value']==str(fact.result.quantity.value)
                assert item['inclusion']=='in_window'
            history=client.post(prefix+'/circulatory-evidence-history',json={'state_context':state['state_context'],'reference':records[-1].reference.model_dump()})
            assert history.status_code==200,history.text
            assert history.json()['revisions'][0]['fact']['result']['quantity']['value']=='22.00'
        with transaction(engine) as repo: assert repo.capture_cutoff().fact_watermark==before
    finally:engine.dispose()


@pytest.mark.parametrize('extra', [dict(sample_type='arterial'),dict(sample_type='mixed_venous'),dict(sample_type='noninvasive',method='blood_gas')])
def test_respiratory_rate_does_not_claim_a_blood_sample(extra):
    with pytest.raises(ValidationError):
        vital(h.OxygenTransport,'RR','respiratory_rate','22.00','/min',**extra)
