"""Closed explicit admission and the approved raw-unit boundary."""
import pytest
from app.persistence import mapping as m
from app.models.clinical import hemodynamics as h
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError
from test_persistence import database, registered
from test_patient_state_v3 import change, numeric
from test_patient_state_v3_inference import inputs, selected


def test_complete_admission_registry_is_exact_original_16_plus_explicit_15():
    assert m.SUPPORTED_FACTS == {
        'observation':m.ClinicalObservation,'medication_order':m.MedicationOrder,
        'medication_administration':m.MedicationAdministration,'inference':m.ClinicalInference,
        'microbiology_specimen':m.Specimen,'microbiology_direct_examination':m.DirectExamination,
        'microbiology_culture':m.CultureFinding,'microbiology_isolate':m.IsolateIdentification,
        'microbiology_susceptibility':m.SusceptibilityResult,'microbiology_resistance':m.ResistanceFinding,
        'microbiology_molecular':m.MolecularResult,'blood_culture_set':m.BloodCultureSet,
        'blood_culture_bottle':m.BloodCultureBottle,'antimicrobial_order':m.AntimicrobialOrder,
        'antimicrobial_administration':m.CompletedAntimicrobialAdministration,'antimicrobial_non_delivery':m.AntimicrobialNonDelivery,
        'circulatory_pressure':h.PressureObservation,'circulatory_cardiac':h.CardiacPerformance,
        'circulatory_volume':h.VolumeMeasurement,'circulatory_dynamic':h.DynamicMeasurement,
        'circulatory_device_prediction':h.DevicePrediction,'circulatory_perfusion':h.PerfusionObservation,
        'circulatory_oxygen':h.OxygenTransport,'circulatory_lactate':h.LactateResult,
        'circulatory_echo':h.EchoObservation,'circulatory_ecg':h.ECGObservation,
        'circulatory_vasoactive':h.VasoactiveEvent,'circulatory_monitoring':h.MonitoringEvent,
        'circulatory_assessment':h.DynamicAssessment,'circulatory_event':h.CirculatoryEvent,
        'circulatory_signal':h.SignalManifest,
        'laboratory_report':__import__('app.models.clinical.laboratory',fromlist=['LaboratoryReport']).LaboratoryReport,
    }


@pytest.mark.parametrize('raw,status,system,code,eligible',[
    ('mmHg','unresolved',None,None,True),('mmHg','assessed','UCUM','mm[Hg]',True),
    ('mm[Hg]','assessed','UCUM','mm[Hg]',False),('mm[Hg]','unresolved',None,None,False),
    ('mmHg','assessed','UCUM','kPa',False),('kPa','unresolved',None,None,False)])
def test_pressure_unit_matrix_never_converts(registered,raw,status,system,code,eligible):
    p,l,v=inputs();result=numeric('65.00',raw)
    unit=change(result.quantity.unit,status=status,system=system,code=code)
    p=change(p,result=change(result,quantity=change(result.quantity,unit=unit)))
    a,r=selected(registered,(p,l,v))
    if eligible:
        assert build_circulatory_timing_inference(assembly=a,request=r).inputs[0]==p.reference
    else:
        with pytest.raises(CirculatoryInferenceError,match='unsupported_unit'):
            build_circulatory_timing_inference(assembly=a,request=r)
