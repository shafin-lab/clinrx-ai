"""Independent M7 adversarial cases and comprehensive synthetic recorded scenarios."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from datetime import datetime
import pytest
from pydantic import ValidationError
from sqlalchemy import event, text, inspect
from alembic import command
from alembic.config import Config
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.canonical import canonical_payload
from app.persistence.errors import StorageIntegrityError, ScopeMismatch
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError, EvidencePin
from app.execution.patient_state_v3_assembly import assemble_patient_state_v3
from test_persistence import database, registered, ROOT, patient, encounter, fact as legacy_fact
from test_patient_state_v3 import h, records, measurement, acquisition, numeric, device, code, stamp, change, PROV, AT, TARGET
from test_patient_state_v3_inference import inputs, selected
from test_patient_state_v3_persistence import save, revised, request


# Explicit source examples, not a universal manufacturer capability matrix.
DEVICE_EXAMPLES = [
    ('HemoSphere','FloTrac',h.CardiacPerformance,'co','L/min'),
    ('HemoSphere','FloTrac',h.CardiacPerformance,'ci','L/min/m2'),
    ('HemoSphere','AcumenIQ',h.DynamicMeasurement,'dynamic_arterial_elastance','1'),
    ('HemoSphere','AcumenIQ',h.DynamicMeasurement,'dp_dt','mmHg/s'),
    ('HemoSphere','AcumenIQ',h.DevicePrediction,'hpi','1'),
    ('EV1000','VolumeView',h.VolumeMeasurement,'gedv','mL'),
    ('EV1000','VolumeView',h.VolumeMeasurement,'evlw','mL'),
    ('HemoSphere','SwanGanz',h.CardiacPerformance,'co','L/min'),
] + [('PiCCO','PiCCO',cls,metric,unit) for cls,metric,unit in [
    (h.CardiacPerformance,'co','L/min'),(h.CardiacPerformance,'ci','L/min/m2'),
    (h.CardiacPerformance,'sv','mL'),(h.CardiacPerformance,'svi','mL/m2'),
    (h.VolumeMeasurement,'gedv','mL'),(h.VolumeMeasurement,'gedvi','mL/m2'),
    (h.VolumeMeasurement,'itbv','mL'),(h.VolumeMeasurement,'itbvi','mL/m2'),
    (h.VolumeMeasurement,'evlw','mL'),(h.VolumeMeasurement,'evlwi','mL/kg'),
    (h.VolumeMeasurement,'pvpi','1'),(h.CardiacPerformance,'svr','dyn.s/cm5'),
    (h.CardiacPerformance,'svri','dyn.s.m2/cm5'),(h.DynamicMeasurement,'ppv','%'),
    (h.DynamicMeasurement,'svv','%'),(h.VolumeMeasurement,'gef','%'),(h.VolumeMeasurement,'cfi','1/min')]]


@pytest.mark.parametrize('platform,technology,cls,metric,unit',DEVICE_EXAMPLES)
def test_source_monitor_metrics_durable(registered,platform,technology,cls,metric,unit):
    method='transpulmonary_thermodilution' if cls is h.VolumeMeasurement else 'pulse_contour'
    if technology=='SwanGanz':method='continuous_thermodilution'
    a=acquisition(method,device=device(technology,platform),parameter=code(metric),parameter_concept=metric,
        parameter_support='source_documented',support_provenance=PROV,algorithm=code('recorded-source-version'))
    f=measurement(cls,'metric',concept=metric,result=numeric('2.00',unit),acquisition=a,production='monitor_derived')
    cutoff=save(registered,f)
    actual=assemble_patient_state_v3(registered,request=request(cutoff)).snapshot.items[0].fact
    assert actual.acquisition.device.technology==technology
    assert actual.acquisition.method==method
    assert actual.acquisition.parameter.code==metric
    assert actual.result.quantity.unit.raw==unit and str(actual.result.quantity.value)=='2.00'
    assert canonical_payload(actual)==canonical_payload(f)


def test_wrong_source_parameter_mapping_rejected():
    a=acquisition(parameter=code('CO'),parameter_concept='co',parameter_support='source_documented',support_provenance=PROV)
    with pytest.raises(ValidationError):measurement(acquisition=a)


def test_known_wrong_pressure_compartment_is_unsuitable(registered):
    p,l,v=inputs();p=change(p,acquisition=change(p.acquisition,compartment='right_atrial'))
    assembly,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError,match='pressure_site_mismatch'):
        build_circulatory_timing_inference(assembly=assembly,request=r)


def test_unverified_binding_is_unsuitable(registered):
    p,l,v=inputs();p=change(p,binding=change(p.binding,verification=change(p.binding.verification,
        status='unresolved',ambiguity='source ambiguity')))
    assembly,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError,match='unverified_binding'):
        build_circulatory_timing_inference(assembly=assembly,request=r)


def test_monitor_reported_map_and_no_conversion(registered):
    p,l,v=inputs();p=change(p,production='monitor_derived',acquisition=change(p.acquisition,
        device=device('AcumenIQ','HemoSphere'),parameter=code('MAP'),parameter_concept='systemic_mean',
        parameter_support='source_documented',support_provenance=PROV))
    assembly,r=selected(registered,(p,l,v))
    assert build_circulatory_timing_inference(assembly=assembly,request=r).inputs[0]==p.reference


def test_pure_builder_performs_no_sql(registered):
    assembly,r=selected(registered);sql=[]
    def observed(*args):sql.append(args)
    event.listen(registered,'before_cursor_execute',observed)
    try:build_circulatory_timing_inference(assembly=assembly,request=r)
    finally:event.remove(registered,'before_cursor_execute',observed)
    assert sql==[]


def test_dst_fold_ordering():
    zone=ZoneInfo('America/New_York')
    early=datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
    late=datetime(2026,11,1,1,30,tzinfo=zone,fold=1)
    from app.models.clinical.recorded_v2 import instant
    assert instant(late)-instant(early)==3600_000_000
    assert early.isoformat().endswith('-04:00') and late.isoformat().endswith('-05:00')


@pytest.mark.parametrize('fail',[False,True])
def test_m7_migration_preserves_bytes_allocator_links_and_rollback(tmp_path,monkeypatch,fail):
    engine=create_database(tmp_path/'m7.sqlite3');cfg=Config(str(ROOT/'backend/alembic.ini'))
    with engine.begin() as conn:
        cfg.attributes['connection']=conn;command.upgrade(cfg,'m6_0007')
    from app.persistence import database as db
    with monkeypatch.context() as m:
        m.setattr(db,'SCHEMA_REVISION','m6_0007')
        with transaction(engine) as repo:
            repo.register_patient(patient());repo.register_encounter(encounter())
            f=legacy_fact();repo.append_fact(f,target=TARGET);repo.append_revision(revised(f),target=TARGET)
        with engine.begin() as conn:conn.execute(text("UPDATE sqlite_sequence SET seq=999 WHERE name='fact_revision'"))
    def snapshot():
        with engine.connect() as conn:
            result={name:conn.execute(text('SELECT * FROM '+name)).all() for name in inspect(conn).get_table_names()}
            result['allocator']=conn.execute(text('SELECT * FROM sqlite_sequence')).all()
            return result
    before=snapshot()
    def broken(conn,cursor,statement,*args):
        if statement.lstrip().startswith('CREATE TABLE circulatory_execution'):raise RuntimeError('bounded injection')
    if fail:event.listen(engine,'after_cursor_execute',broken)
    try:
        with engine.begin() as conn:
            cfg.attributes['connection']=conn
            if fail:
                with pytest.raises(RuntimeError):command.upgrade(cfg,'head')
                raise RuntimeError('rollback owner')
            command.upgrade(cfg,'head')
    except RuntimeError:
        if not fail:raise
    finally:
        if fail:event.remove(engine,'after_cursor_execute',broken)
    after=snapshot()
    if fail:assert after==before
    else:
        assert set(after)-set(before)=={'circulatory_execution', 'm10_command', 'm10_attachment'}
        assert all(after[k]==v for k,v in before.items() if k!='alembic_version')
        assert save(engine,measurement()).fact_watermark==1000
    engine.dispose()


@pytest.mark.parametrize('scenario', ['vasodilatory_recorded','low_output_recorded','pulmonary_rv_recorded',
    'post_transplant','simultaneous_vasopressors','edwards','picco','pac','echo','arrhythmia',
    'lactate_perfusion','fluid_challenge','calibration_quality'])
def test_complex_synthetic_evidence_has_no_generated_diagnosis(registered,scenario):
    p,l,v=inputs(); extra=[]
    if scenario=='low_output_recorded':extra=[measurement(h.CardiacPerformance,'co',concept='co',result=numeric('2.0','L/min'))]
    elif scenario=='pulmonary_rv_recorded':extra=[measurement(concept='mpap',name='pap',result=numeric('40','mmHg')),change(records()[8],concept='rv_function',result=h.QualitativeResult(finding=code_as_concept('source-reported reduced RV function')))]
    elif scenario=='post_transplant':extra=[records()[13]]
    elif scenario=='simultaneous_vasopressors':extra=[change(v,id='v-epinephrine',drug=change(v.drug,canonical_id='epinephrine'))]
    elif scenario in ('edwards','picco'):extra=[measurement(h.CardiacPerformance,'co',concept='co',result=numeric('4.0','L/min'),acquisition=acquisition('pulse_contour',device=device('FloTrac','HemoSphere') if scenario=='edwards' else device()),production='monitor_derived')]
    elif scenario=='pac':extra=[measurement(name='pawp',concept='pawp',acquisition=acquisition('pac'))]
    elif scenario=='echo':extra=[records()[8]]
    elif scenario=='arrhythmia':extra=[change(records()[9],concept='rhythm',result=h.QualitativeResult(finding=code_as_concept('source-documented arrhythmia')))]
    elif scenario=='lactate_perfusion':extra=[records()[5]]
    elif scenario=='fluid_challenge':extra=[change(records()[12],test='fluid_challenge')]
    elif scenario=='calibration_quality':extra=[records()[11],change(p,id='artifact-pressure',acquisition=change(p.acquisition,quality=h.EvidenceQuality(artifacts=('damped',))))]
    cutoff=save(registered,p,l,v,*extra)
    view=assemble_patient_state_v3(registered,request=change(request(cutoff),scope=change(request(cutoff).scope,review_end=AT+timedelta(minutes=4))))
    assert len(view.snapshot.items)==3+len(extra)
    assert 'diagnosis' not in type(view.snapshot).model_fields
    assert view.snapshot.coverage.continuity=='not_established'


def code_as_concept(label):
    return h.RecordedConcept(raw_display=label)
