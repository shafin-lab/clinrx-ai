"""Opt-in synthetic flowsheet uses real persisted evidence with execution gated."""
import pytest
from fastapi.testclient import TestClient
from app.demo.icu_flowsheet import bootstrap,flowsheet_facts
from app.demo.comprehensive import demo_facts,RELEASED_ID,WITHHELD_ID
from app.demo.circulatory import SIMULATION_AT
from app.api.config import APIConfig
from app.main import create_app
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.canonical import canonical_payload
P='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'

def test_sequence_has_distinct_observations_and_documented_events_with_canonical_roundtrips():
    facts=flowsheet_facts();assert len(facts)==115 and len({f.id for f in facts})==115
    for fact in facts:assert canonical_payload(type(fact).model_validate_json(fact.model_dump_json()))==canonical_payload(fact)
    events=[f for f in facts if f.kind=='circulatory_vasoactive']
    assert {f.drug.canonical_id for f in events}=={'norepinephrine','vasopressin','dobutamine'}
    assert {f.action.event_type for f in events}=={'order','initiation','rate_change','pause','restart','permanent_stop'}
    assert all(f.source_identifiers[0].namespace=='clinrx.synthetic.infusion-series/v1' for f in events)
    assert all(f.revision=='1' and f.supersedes is None for f in facts)
    assert all(f.action.delivery.dosing_weight.id=='fs-WEIGHT' for f in events if hasattr(f.action,'delivery'))
    assert next(f for f in facts if f.id=='fs-CO-60').acquisition.quality.status=='suspect'
    assert all(f.production=='source_calculated' and f.calculation_method is not None for f in facts if f.id.startswith('fs-CI-'))

def test_gated_real_api_preserves_original_evidence_and_exact_infusion_history(tmp_path):
    path=tmp_path/'flowsheet.sqlite3';engine=create_database(path)
    try:
        manifest=bootstrap(engine);assert manifest['execution_enabled'] is False
        config=APIConfig(database_path=path,environment='test',envelope_signing_key='b7'*32,clock_mode='historical_simulation',simulation_at=SIMULATION_AT)
        with TestClient(create_app(config,engine=engine)) as client:
            response=client.get(P+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')});assert response.status_code==200
            state=response.json();assert state['execution_enabled'] is False
            items=state['assembly']['snapshot']['items'];assert len(items)==156
            by_id={i['fact']['id']:i for i in items}
            for fact in demo_facts():
                if fact.id!='m7-CAL':assert by_id[fact.id]['fact']==fact.model_dump(mode='json')
            event=by_id['fs-D-CHANGE']
            assert event['fact']['action']['delivery']['rate']['value']=='3.0'
            assert event['fact']['action']['delivery']['rate']['unit']['raw']=='mcg/kg/min'
            ref={'kind':'circulatory_vasoactive','id':'fs-D-CHANGE','version':'1'}
            history=client.post(P+'/circulatory-evidence-history',json={'state_context':state['state_context'],'reference':ref})
            assert history.status_code==200 and history.json()['revisions'][0]['fact']==event['fact']
            for id,outcome in [(RELEASED_ID,'released'),(WITHHELD_ID,'withheld')]:
                a=client.get(P+'/circulatory-reviews/'+str(id));assert a.status_code==200
                assert a.json()['record']['decision']['outcome']==outcome
                assert client.get(P+'/circulatory-reviews/'+str(id)).content==a.content
            with transaction(engine) as repo:before=repo.capture_cutoff().fact_watermark
            body={'execution_id':'00000000-0000-4000-8000-00000000c903','state_context':state['state_context']}
            for role,id in [('pressure','m7-P'),('lactate','m7-L'),('vasopressor','fs-D-CHANGE')]:
                i=by_id[id];body[role]={'reference':{'kind':i['fact']['kind'],'id':id,'version':'1'},'expected_digest':i['expected_digest']}
            assert client.post(P+'/circulatory-review-preparations',json=body).status_code==422
            with transaction(engine) as repo:assert repo.capture_cutoff().fact_watermark==before
        with pytest.raises(ValueError,match='fresh disposable'):bootstrap(engine)
    finally:engine.dispose()


def test_recorded_interval_is_optional_and_preserves_existing_event_payloads_and_exact_lexemes():
    from app.demo.circulatory import facts
    from app.models.clinical import hemodynamics as h
    from app.demo.icu_chart_entries import context_facts
    old=next(f for f in facts() if f.id=='m7-EVENT')
    assert 'recorded_interval' not in old.model_dump(mode='json')
    assert canonical_payload(type(old).model_validate_json(old.model_dump_json()))==canonical_payload(old)
    interval=next(f for f in context_facts() if f.id=='fs-IO-output_urine-15').recorded_interval
    assert interval.start.source_timestamp=='2026-10-08T08:00:00+00:00'
    assert interval.end.source_timestamp=='2026-10-08T08:15:00+00:00'
    raw=interval.model_dump(mode='json');raw['start']['source_timestamp']='2026-10-08T08:00:00.0000001Z'
    restored=h.RecordedCirculatoryInterval.model_validate(raw)
    assert restored.start.source_timestamp=='2026-10-08T08:00:00.0000001Z'
    # Interval boundaries are source assertions, not a new order/duration inference.
    raw=interval.model_dump(mode='json');raw['start'],raw['end']=raw['end'],raw['start']
    assert h.RecordedCirculatoryInterval.model_validate(raw).start==interval.end


def test_chart_context_has_explicit_intervals_source_totals_and_exact_infusion_support():
    facts=flowsheet_facts();by_id={f.id:f for f in facts}
    urine=by_id['fs-IO-output_urine-15'];assert str(urine.recorded_amount.value)=='35'
    assert urine.recorded_interval is not None
    balance=by_id['fs-BALANCE-TOTAL'];assert str(balance.recorded_amount.value)=='285'
    assert balance.description.coding.code=='balance_total_reported'
    for event in [f for f in facts if f.kind=='circulatory_vasoactive' and hasattr(f.action,'delivery')]:
        assert event.action.delivery.dosing_weight==by_id['fs-WEIGHT'].reference
        assert event.associations[0].role=='delivery'
        assert event.associations[0].exact.id in by_id
    assert by_id['fs-SCVO2-30'].sample_type=='central_venous'
    assert by_id['fs-SVO2-30'].sample_type=='mixed_venous'
    assert by_id['fs-FLUID-ASSESSMENT'].reported_interpretation is None
