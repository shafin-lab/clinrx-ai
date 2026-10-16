"""User-approved synthetic policy boundaries; broad evidence admission is separate."""
from datetime import timedelta
import pytest
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference as build, CirculatoryInferenceError, EvidencePin
from app.execution.patient_state_v3_workflow import execute_circulatory_review, reconcile_circulatory_execution
from app.models.clinical.common import LineageEdge
from test_persistence import database, registered
from test_patient_state_v3 import change, stamp, records, PROV, AT, TARGET
from test_patient_state_v3_inference import inputs, selected
from test_patient_state_v3_workflow import prepare, clock, forbidden
from test_patient_state_v3_persistence import save, revised

@pytest.mark.parametrize('quality',['acceptable','unknown','suspect','invalid'])
def test_lactate_quality_preserved_but_only_acceptable_eligible(registered,quality):
    p,l,v=inputs();l=change(l,acquisition=change(l.acquisition,quality=change(l.acquisition.quality,status=quality)))
    a,r=selected(registered,(p,l,v));assert l.reference in a.input_references
    if quality=='acceptable':assert build(assembly=a,request=r).inputs==r.inputs
    else:
        with pytest.raises(CirculatoryInferenceError,match='invalid_lactate_quality'):build(assembly=a,request=r)

@pytest.mark.parametrize('name',['calibration','zeroing'])
@pytest.mark.parametrize('case',['missing','unknown','not_applied','not_required','wrong_revision','wrong_measurement','future_available','future_recorded'])
def test_acquisition_applicability_boundary(registered,name,case):
    p,l,v=inputs();application=getattr(p.acquisition,name+'_application')
    if case=='missing':application=None
    elif case in ('unknown','not_applied','not_required'):application=change(application,status=case)
    elif case=='wrong_revision':application=change(application,acquisition=change(p.reference,version='2'))
    elif case=='wrong_measurement':application=change(application,acquisition=change(p.reference,id='another'))
    elif case=='future_available':application=change(application,available=stamp(AT+timedelta(hours=1)))
    else:application=change(application,provenance=change(PROV,recorded_at=AT+timedelta(hours=1)))
    p=change(p,acquisition=change(p.acquisition,**{name+'_application':application}))
    a,r=selected(registered,(p,l,v));assert p.reference in a.input_references
    with pytest.raises(CirculatoryInferenceError):build(assembly=a,request=r)

@pytest.mark.parametrize('offset',[0,4,5,6])
def test_retrospective_application_has_no_invented_freshness(registered,offset):
    p,l,v=inputs();at=AT+timedelta(minutes=offset)
    application=change(p.acquisition.calibration_application,available=stamp(at),provenance=change(PROV,recorded_at=at))
    p=change(p,acquisition=change(p.acquisition,calibration_application=application))
    a,r=selected(registered,(p,l,v))
    if offset<=5:assert build(assembly=a,request=r).inputs[0]==p.reference
    else:
        with pytest.raises(CirculatoryInferenceError):build(assembly=a,request=r)

@pytest.mark.parametrize('agent',['norepinephrine','epinephrine','vasopressin','phenylephrine','dopamine','dobutamine'])
def test_five_drug_scope_does_not_narrow_state(registered,agent):
    p,l,v=inputs();v=change(v,drug=change(v.drug,canonical_id=agent))
    a,r=selected(registered,(p,l,v));assert v.reference in a.input_references
    if agent=='dobutamine':
        with pytest.raises(CirculatoryInferenceError,match='unsupported_vasopressor_identity'):build(assembly=a,request=r)
    else:assert build(assembly=a,request=r).inputs==r.inputs

@pytest.mark.parametrize('withheld',[False,True])
def test_applicability_support_is_exact_and_successors_material(registered,withheld):
    from test_patient_state_v3_workflow import c
    from uuid import uuid4
    p,l,v=inputs();support=records()[11]
    application=change(p.acquisition.calibration_application,provenance=change(PROV,
        upstream=(LineageEdge(target=support.reference,relationship='derived_from'),)))
    p=change(p,acquisition=change(p.acquisition,calibration_application=application))
    a,r=selected(registered,(p,l,v,support))
    with pytest.raises(CirculatoryInferenceError,match='supporting_dependency_mismatch'):build(assembly=a,request=r)
    r=change(r,supporting=(EvidencePin(reference=support.reference,expected_digest=support.canonical_digest),))
    i=build(assembly=a,request=r);assert i.inputs[-1]==support.reference
    cutoff=save(registered,i)
    req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    if withheld:save(registered,revised(support))
    stored=execute_circulatory_review(registered,req,clock=clock)
    assert stored.record.decision.outcome==('withheld' if withheld else 'released')
    assert reconcile_circulatory_execution(registered,req).stored==stored
    assert execute_circulatory_review(registered,req,clock=forbidden)==stored


def test_pre_policy_request_cannot_be_new_execution(registered):
    from app.persistence.errors import StorageIntegrityError
    req=prepare(registered);req=change(req,inference_request=change(req.inference_request,eligibility_policy=None))
    with pytest.raises(StorageIntegrityError):execute_circulatory_review(registered,req,clock=clock)
    assert reconcile_circulatory_execution(registered,req).status=='absent'

@pytest.mark.parametrize('blood,compartment',[('arterial','central_venous'),('central_venous','systemic_arterial'),('mixed_venous','systemic_arterial')])
def test_explicit_lactate_compartment_contradiction_is_retained_but_ineligible(registered,blood,compartment):
    p,l,v=inputs();l=change(l,blood_source=blood,acquisition=change(l.acquisition,compartment=compartment))
    a,r=selected(registered,(p,l,v));assert l.reference in a.input_references
    with pytest.raises(CirculatoryInferenceError,match='lactate_site_mismatch'):build(assembly=a,request=r)

@pytest.mark.parametrize('axis',['measured','reported'])
@pytest.mark.parametrize('minutes',[2,5,6])
def test_reporting_after_collection_is_valid_only_by_evaluation_cutoff(registered,axis,minutes):
    p,l,v=inputs();l=change(l,**{axis:stamp(AT+timedelta(minutes=minutes))})
    a,r=selected(registered,(p,l,v))
    if minutes<=5:assert build(assembly=a,request=r).inputs[1]==l.reference
    else:
        with pytest.raises(CirculatoryInferenceError):build(assembly=a,request=r)


def test_lossy_attestation_availability_cannot_collapse_to_cutoff(registered):
    p,l,v=inputs();at=AT+timedelta(minutes=5)
    raw=at.isoformat().replace('.123456','.1234569')
    available=stamp(at).model_dump();available.update(recorded={'status':'known','precision':'instant','value':raw},source_timestamp=raw)
    application=change(p.acquisition.calibration_application,available=available)
    p=change(p,acquisition=change(p.acquisition,calibration_application=application))
    a,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError):build(assembly=a,request=r)


@pytest.mark.parametrize('role',['pressure_quality','calibration_adequacy','lactate_quality','delivery','clock_basis'])
def test_all_actually_consumed_future_attestations_are_unsuitable(registered,role):
    p,l,v=inputs();future=change(PROV,recorded_at=AT+timedelta(hours=1))
    if role=='pressure_quality':p=change(p,acquisition=change(p.acquisition,quality=change(p.acquisition.quality,provenance=future)))
    elif role=='calibration_adequacy':p=change(p,acquisition=change(p.acquisition,calibration_provenance=future))
    elif role=='lactate_quality':l=change(l,acquisition=change(l.acquisition,quality=change(l.acquisition.quality,provenance=future)))
    elif role=='delivery':v=change(v,action=change(v.action,delivery=change(v.action.delivery,attestation=future)))
    else:p=change(p,occurred=change(p.occurred,clock_basis=future))
    a,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError,match='future_recording'):build(assembly=a,request=r)
