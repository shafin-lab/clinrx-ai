"""Explicit disposable synthetic M7 bootstrap. Never runs on application startup."""
import argparse
import json
from datetime import timedelta
from pathlib import Path
from app.demo.micro_antimicrobial import base, code, concept, BIND, PROV
from app.demo.patient_state import AT, SIMULATION_AT, TARGET, bootstrap as base_bootstrap
from app.models.clinical import hemodynamics as h
from app.models.clinical.common import ClinicalTime, Unit, Reference
from app.models.clinical.recorded_v2 import ExactQuantity
from app.persistence.database import create_database
from app.persistence.repository import transaction

def stamp(at=AT):
    return h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':at.isoformat()},
        timestamp_precision=h.PRECISION_CONTRACT,clock='verified',clock_basis=PROV)
def fields(id):
    return dict(id='m7-'+id,revision='1',binding=BIND,origin='reported',provenance=PROV,
        time=ClinicalTime(precision='unknown'),temporal_status='unknown',occurred=stamp(),available=stamp())
def quantity(value,unit):return ExactQuantity(value=value,unit=Unit(raw=unit,status='unresolved',limitation='Synthetic source unit.'))
def acquisition(method='invasive_arterial',**extra):
    return h.Acquisition(method=method,quality=h.EvidenceQuality(status='acceptable',provenance=PROV),**extra)
def device(technology='PiCCO',platform='PiCCO'):
    return h.DeviceIdentity(manufacturer=code('manufacturer'),platform=platform,product=code('monitor'),technology=technology,sensor=code('sensor'))
def measurement(cls,id,concept,value,unit,**extra):
    return cls(**fields(id),concept=concept,result=h.NumericResult(quantity=quantity(value,unit)),
        acquisition=acquisition(),production='direct_measurement',**extra)

def facts():
    ref=Reference(kind='circulatory_pressure',id='m7-P',version='1')
    application=h.AcquisitionApplicability(acquisition=ref,status='applied',available=stamp(),provenance=PROV)
    p=h.PressureObservation(**fields('P'),concept='systemic_mean',result=h.NumericResult(quantity=quantity('65.00','mmHg')),
        production='direct_measurement',acquisition=acquisition(calibration='adequate',zeroing='adequate',
            calibration_provenance=PROV,zeroing_provenance=PROV,calibration_application=application,zeroing_application=application))
    l=h.LactateResult(**{**fields('L'),'available':stamp(AT+timedelta(minutes=3))},
        collected=stamp(AT+timedelta(minutes=1)),specimen=code('sample'),collection_assertion=PROV,
        result=h.NumericResult(quantity=quantity('2.000','mmol/L')),acquisition=acquisition('laboratory'),production='direct_measurement',report_status='final')
    v=h.VasoactiveEvent(**{**fields('V'),'occurred':stamp(AT+timedelta(minutes=2))},
        drug=h.VasoactiveIdentity(source=code('norepinephrine'),canonical_id='norepinephrine',mapping='mapped',mapping_provenance=PROV),
        action=h.InfusionEvent(event_type='initiation',delivery=h.DeliveryDetails(attestation=PROV)),source_status=concept('Documented initiation'))
    records=(p,
        measurement(h.CardiacPerformance,'CO','co','4.50','L/min'),
        measurement(h.VolumeMeasurement,'GEDV','gedv','700','mL'),
        measurement(h.DynamicMeasurement,'SVV','svv','12.0','%'),
        h.DevicePrediction(**fields('HPI'),result=h.NumericResult(quantity=quantity('30','1')),production='monitor_derived',
            acquisition=acquisition(device=device('AcumenIQ','HemoSphere'),parameter=code('HPI'))),
        measurement(h.PerfusionObservation,'CRT','capillary_refill','2.0','s'),
        measurement(h.OxygenTransport,'SVO2','svo2','65.0','%',sample_type='mixed_venous'),l,
        measurement(h.EchoObservation,'ECHO','tapse','18','mm',study=code('study'),report=code('report'),report_revision='1'),
        measurement(h.ECGObservation,'ECG','qtc','420','ms',interpretation_source='clinician'),v,
        h.MonitoringEvent(**fields('CAL'),device=device(),event_type='configuration',acquisition=acquisition(),finding=concept('Source device configuration')),
        h.DynamicAssessment(**fields('PLR'),test='plr',protocol=code('plr'),baseline=(Reference(kind='circulatory_cardiac',id='m7-CONTEXT-CO',version='1'),),intervention=(),subsequent=()),
        h.CirculatoryEvent(**fields('EVENT'),event_type='position_change',description=concept('Recorded position change')),
        h.SignalManifest(**fields('SIGNAL'),signal='arterial_pressure',device=device(),channel=code('channel'),start=stamp(),
            end=stamp(AT+timedelta(seconds=1)),sample_rate=quantity('125','Hz'),sample_count=125,units=concept('mmHg'),encoding=code('source'),availability='unavailable'),
        h.PressureObservation(**{**fields('UNPLACED'),'occurred':h.ClinicalInstant()},concept='cvp',result=h.MissingResult(status='unknown',reason='Not established'),production='direct_measurement',acquisition=acquisition('unknown')))

    context=h.CardiacPerformance(**{**fields('CONTEXT-CO'),'occurred':stamp(AT-timedelta(hours=2))},concept='co',
        result=h.NumericResult(quantity=quantity('4.500','L/min')),production='direct_measurement',
        acquisition=acquisition('bolus_thermodilution',device=device('SwanGanz','HemoSphere')))
    pac=h.PressureObservation(**fields('PAC'),concept='cvp',result=h.NumericResult(quantity=quantity('8.0','mmHg')),
        production='direct_measurement',acquisition=acquisition('pac',compartment='right_atrial'))
    rhc=h.PressureObservation(**fields('RHC'),concept='pawp',result=h.NumericResult(quantity=quantity('12.0','mmHg')),
        production='direct_measurement',acquisition=acquisition('rhc',compartment='pulmonary_arterial'))
    picco=h.CardiacPerformance(**fields('PICCO-CO'),concept='co',result=h.NumericResult(quantity=quantity('4.60','L/min')),
        production='monitor_derived',acquisition=h.Acquisition(method='pulse_contour',device=device(),quality=h.EvidenceQuality()))
    rhythm=h.ECGObservation(**fields('RHYTHM'),concept='rhythm',result=h.QualitativeResult(finding=concept('Synthetic source-reported rhythm')),
        production='direct_measurement',acquisition=acquisition('ecg_monitor'),interpretation_source='monitor')
    return (*records,context,pac,rhc,picco,rhythm)

def manifest():return dict(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,review_start=AT.isoformat(),review_end=(AT+timedelta(hours=2)).isoformat(),simulation_at=SIMULATION_AT.isoformat(),execution_enabled=False)
def bootstrap(engine):
    base_bootstrap(engine)
    with transaction(engine) as repo:
        for fact in facts():repo.append_fact(fact,target=TARGET)
    return manifest()
def correct(engine):
    p=facts()[0]
    # Corrected exact acquisition requires a new source assertion; old command still consumes revision 1.
    ref=Reference(kind=p.kind,id=p.id,version='2')
    data=p.model_dump();data.update(revision='2',supersedes=p.reference,correction_reason='Explicit synthetic source correction')
    for name in ('calibration_application','zeroing_application'):data['acquisition'][name]['acquisition']=ref
    revised=type(p).model_validate(data)
    with transaction(engine) as repo:repo.append_revision(revised,target=TARGET)
    return dict(consumed=p.reference.model_dump(),corrected=revised.reference.model_dump())
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('bootstrap','correct'));parser.add_argument('--database',type=Path,required=True)
    args=parser.parse_args()
    if not args.database.is_absolute():parser.error('absolute disposable database path required')
    engine=create_database(args.database)
    try:print(json.dumps((bootstrap if args.action=='bootstrap' else correct)(engine)))
    finally:engine.dispose()
if __name__=='__main__':main()
