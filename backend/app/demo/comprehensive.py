"""Explicit disposable demo data and retained examples; never seeds on API startup."""
import argparse
import json
from pathlib import Path
from uuid import UUID
from sqlalchemy import inspect
from app.demo.patient_state import bootstrap as patient_bootstrap
from app.demo.circulatory import facts, manifest, TARGET, SIMULATION_AT, PROV, device, quantity, code, concept, stamp
from app.models.clinical.common import LineageEdge
from app.models.clinical import hemodynamics as h
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.execution.patient_state_v3 import PatientStateScopeV3
from app.execution.patient_state_v3_assembly import AssemblyRequestV3, assemble_patient_state_v3
from app.execution.patient_state_v3_inference import CirculatoryTimingRequest, EvidencePin, build_circulatory_timing_inference
from app.execution.patient_state_v3_execution import CirculatoryExecutionRequest, GRANT_ACTOR, GRANT_TARGET, digest
from app.execution.patient_state_v3_workflow import execute_circulatory_review

RELEASED_ID=UUID('00000000-0000-4000-8000-00000000c901')
WITHHELD_ID=UUID('00000000-0000-4000-8000-00000000c902')

def replace(model,**fields):return type(model).model_validate({**model.model_dump(),**fields})

def demo_facts(*, include_hpi=False):
    original=list(facts());support=original[11]
    methods={'circulatory_cardiac':'bolus_thermodilution','circulatory_volume':'transpulmonary_thermodilution',
        'circulatory_dynamic':'pulse_contour','circulatory_perfusion':'bedside_examination',
        'circulatory_oxygen':'blood_gas','circulatory_echo':'echo','circulatory_ecg':'ecg_12_lead',
        'circulatory_monitoring':'source_other'}
    for n,fact in enumerate(original):
        acq=getattr(fact,'acquisition',None)
        if acq is not None and acq.method=='invasive_arterial' and fact.kind in methods:
            fields={'method':methods[fact.kind]}
            if fact.kind=='circulatory_cardiac':fields['device']=device('SwanGanz','HemoSphere')
            if fact.kind in ('circulatory_volume','circulatory_dynamic'):fields['device']=device()
            original[n]=replace(fact,acquisition=replace(acq,**fields))
    if not include_hpi:original=[f for f in original if f.kind!='circulatory_device_prediction']
    p=original[0]
    original[0]=replace(p,acquisition=replace(p.acquisition,calibration_provenance=replace(PROV,
        upstream=(LineageEdge(target=support.reference,relationship='derived_from'),))))
    echo=next(f for f in original if f.id=='m7-ECHO');co=next(f for f in original if f.id=='m7-CO')
    def numeric(template,id,concept,value,unit,**extra):
        result=replace(template.result,quantity=replace(template.result.quantity,value=value,
            unit=replace(template.result.quantity.unit,raw=unit)))
        return replace(template,id=id,concept=concept,result=result,**extra)
    oxygen=next(f for f in original if f.id=='m7-SVO2')
    abg_context=h.BloodGasContext(collected=stamp(),fio2=quantity('40','%'),
        oxygen_device=concept('Synthetic invasive ventilation'),ventilator_mode=concept('Volume assist-control'),
        peep=quantity('5','cmH2O'),provenance=PROV,
        limitations=('Synthetic sample-time settings, not current ventilator settings.',))
    abg=[]
    for id,analyte,v,u in (
        ('PH','ph','7.31','1'),('PACO2','paco2','48.0','mmHg'),('PAO2','pao2','78.0','mmHg'),
        ('HCO3','bicarbonate','23.0','mmol/L'),('BE','base_excess','-2.0','mmol/L'),
        ('SAO2','sao2','95.0','%'),('HB','hemoglobin','10.2','g/dL')):
        acq=replace(oxygen.acquisition,quality=h.EvidenceQuality(status='acceptable',provenance=PROV),
            limitations=(('Source-reported analyzer calculation; not calculated by ClinRx.',)
                if analyte in ('bicarbonate','base_excess') else ()))
        abg.append(numeric(oxygen,'m7-ABG-'+id,analyte,v,u,sample_type='arterial',
            specimen=code('synthetic-arterial-sample-1'),blood_gas_context=abg_context,acquisition=acq,
            production='source_calculated' if analyte in ('bicarbonate','base_excess') else 'direct_measurement',
            calculation_method=code('source-analyzer-calculation') if analyte in ('bicarbonate','base_excess') else None))
    def finding(id,analyte,text):
        return replace(echo,id=id,concept=analyte,result=h.QualitativeResult(finding=concept(text)))
    return (*original,*abg,
        numeric(echo,'m7-RVSP','estimated_rvsp','45.0','mmHg',production='source_calculated',
            calculation_method=code('echo-report-rvsp-estimate'),
            disclosures=('Source-reported estimate using TR velocity and estimated RAP 5 mmHg; not recalculated by ClinRx. RVOT obstruction not documented.',)),
        numeric(echo,'m7-PASP','estimated_pasp','45.0','mmHg',production='source_calculated',
            calculation_method=code('echo-report-pasp-estimate'),
            disclosures=('Source-reported PASP estimate; equivalence to RVSP is not established by ClinRx. RVOT obstruction not documented.',)),
        numeric(echo,'m7-TRV','tr_measurement','3.16','m/s',
            disclosures=('Source-reported peak TR velocity; envelope adequacy reported acceptable in the synthetic study.',)),
        numeric(echo,'m7-RVD','rv_dimension','4.3','cm',
            disclosures=('Source-reported RV basal end-diastolic dimension, apical four-chamber view.',)),
        finding('m7-RVFUNCTION','rv_function','Synthetic report: mildly reduced RV systolic function.'),
        finding('m7-SEPTUM','septal_configuration','Synthetic report: systolic septal flattening.'),
        finding('m7-VALVE','valve_finding','Synthetic report: moderate tricuspid regurgitation.'),
        finding('m7-EFFUSION','pericardial_effusion','Synthetic report: no pericardial effusion visualized.'),
        finding('m7-PH','structural_finding','Synthetic report: findings suggest pulmonary hypertension; no invasive confirmation or PAH subtype established.'),
        numeric(echo,'m7-EF','lv_ef','55.0','%'),
        numeric(echo,'m7-VTI','lvot_vti','17.5','cm'),
        numeric(co,'m7-CI','ci','2.60','L/min/m2'),
        numeric(co,'m7-FLOTRAC','co','4.40','L/min',production='monitor_derived',
            acquisition=replace(co.acquisition,method='pulse_contour',device=device('FloTrac','HemoSphere'))),
        numeric(co,'m7-VOLUMEVIEW','co','4.60','L/min',
            acquisition=replace(co.acquisition,method='transpulmonary_thermodilution',device=device('VolumeView','EV1000'))))

def prepare_example(engine,execution_id):
    window=manifest()
    with transaction(engine) as repo:cutoff=repo.capture_cutoff()
    scope=PatientStateScopeV3(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,
        review_start=window['review_start'],review_end=window['review_end'],repository_cutoff=cutoff)
    ar=AssemblyRequestV3(scope=scope,profile_id='RecordedCirculatoryEvidence',profile_version='1')
    assembly=assemble_patient_state_v3(engine,request=ar)
    def pin(id):
        item=next(i for i in assembly.snapshot.items if i.fact.id==id)
        return EvidencePin(reference=item.reference,expected_digest=item.expected_digest)
    request=CirculatoryTimingRequest(eligibility_policy='SyntheticPLVEligibility/1',scope=scope,
        pressure=pin('m7-P'),lactate=pin('m7-L'),vasopressor=pin('m7-V'),supporting=(pin('m7-CAL'),),
        expected_assembly_digest=assembly.canonical_digest,inference_id=str(execution_id)+'-inference',executed_at=SIMULATION_AT)
    inference=build_circulatory_timing_inference(assembly=assembly,request=request)
    with transaction(engine) as repo:
        repo.append_fact(inference,target=TARGET);cutoff=repo.capture_cutoff()
    return CirculatoryExecutionRequest(execution_id=execution_id,target=GRANT_TARGET,actor=GRANT_ACTOR,
        inference_request=request,assembly_request=ar,inference_cutoff=cutoff,
        expected_inference_digest=digest(inference),requested_at=SIMULATION_AT)

def bootstrap(engine, *, include_hpi=False):
    if inspect(engine).has_table('fact_revision'):raise ValueError('choose a fresh disposable database')
    patient_bootstrap(engine)
    seeded=demo_facts(include_hpi=include_hpi)
    with transaction(engine) as repo:
        for fact in seeded:repo.append_fact(fact,target=TARGET)
    released=execute_circulatory_review(engine,prepare_example(engine,RELEASED_ID),clock=lambda:SIMULATION_AT)
    pending=prepare_example(engine,WITHHELD_ID)
    support=next(f for f in seeded if f.id=='m7-CAL')
    corrected=replace(support,revision='2',supersedes=support.reference,
        correction_reason='Synthetic provenance-only calibration-support correction',
        provenance=replace(support.provenance,actor='synthetic corrected calibration assertion'))
    with transaction(engine) as repo:repo.append_revision(corrected,target=TARGET)
    withheld=execute_circulatory_review(engine,pending,clock=lambda:SIMULATION_AT)
    assert released.record.decision.outcome=='released' and withheld.record.decision.outcome=='withheld'
    return {**manifest(),'released_example':str(RELEASED_ID),'withheld_example':str(WITHHELD_ID),
        'dataset':'comprehensive-synthetic-demo/2','recorded_families':len({f.kind for f in seeded}),
        'optional_hpi_included':include_hpi,'execution_enabled':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--flowsheet',action='store_true',help='build the expanded ICU fixture offline and exit; never seed on runtime startup')
    args=parser.parse_args()
    if not args.database.is_absolute():parser.error('provide a new absolute disposable database path')
    # Reserve exclusively, including empty files and symlinks: never replace existing bytes.
    try:
        with args.database.open('xb'):pass
    except OSError:parser.error('provide a new absolute disposable database path in an existing writable directory')
    engine=create_database(args.database)
    try:
        if args.flowsheet:
            from app.demo.icu_flowsheet import bootstrap as flowsheet_bootstrap
            result=flowsheet_bootstrap(engine)
        else:result=bootstrap(engine)
        print(json.dumps(result,indent=2))
    finally:engine.dispose()
if __name__=='__main__':main()
