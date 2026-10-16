"""Literal expectations for approved synthetic P/L/V eligibility and exact lineage."""
from datetime import timedelta, timezone
import pytest
from app.execution.patient_state_v3_inference import (CirculatoryTimingRequest, EvidencePin,
    build_circulatory_timing_inference, CirculatoryInferenceError, METHOD, POLICY_VERSION)
from app.execution.patient_state_v3_assembly import assemble_patient_state_v3
from app.persistence.repository import transaction
from app.persistence.lineage import LineageLimits
from test_persistence import database, registered
from test_patient_state_v3 import records, measurement, vaso, change, AT, TARGET, h, stamp, PROV, numeric
from test_patient_state_v3_persistence import save, request as assembly_request, revised


def inputs():
    p=measurement()
    l=change(records()[7],collected=stamp(AT+timedelta(minutes=1)),available=stamp(AT+timedelta(minutes=3)))
    v=change(vaso(),occurred=stamp(AT+timedelta(minutes=2)))
    return p,l,v


def selected(engine, facts=None):
    facts=inputs() if facts is None else facts
    cutoff=save(engine,*facts)
    ar=assembly_request(cutoff)
    ar=change(ar,scope=change(ar.scope,review_end=AT+timedelta(minutes=4)))
    assembly=assemble_patient_state_v3(engine,request=ar)
    pins=[EvidencePin(reference=f.reference,expected_digest=f.canonical_digest) for f in facts[:3]]
    req=CirculatoryTimingRequest(eligibility_policy=POLICY_VERSION,scope=ar.scope,pressure=pins[0],lactate=pins[1],vasopressor=pins[2],
        expected_assembly_digest=assembly.canonical_digest,inference_id='synthetic-m7-i',executed_at=AT+timedelta(minutes=5))
    return assembly,req


def test_exact_statement_and_independent_lineage_expectation(registered):
    assembly,r=selected(registered)
    i=build_circulatory_timing_inference(assembly=assembly,request=r)
    assert i.statement == ('The selected pressure observation was recorded as acquired at 2026-10-08T08:00:00.123456+05:30. '
        'The selected lactate sample was recorded as collected at 2026-10-08T08:01:00.123456+05:30. '
        'The selected vasopressor initiation was documented at 2026-10-08T08:02:00.123456+05:30. '
        'Pressure acquisition occurred before the initiation event. Lactate collection occurred before the initiation event.')
    assert i.origin=='inferred' and i.method==METHOD
    assert [(e.target.id,e.relationship) for e in i.provenance.upstream]==[
        ('p','derived_from'),('l','derived_from'),('v-initiation','derived_from')]
    assert i.target is None and i.horizon is None
    with transaction(registered) as repo:
        stored=repo.append_fact(i,target=TARGET)
        cutoff=repo.capture_cutoff()
        lineage=repo.resolve_lineage(i.reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())
        assert tuple(d.source.id for d in lineage.dependencies if d.owner==i.reference)==('p','l','v-initiation')
    save(registered,revised(inputs()[0]))
    with transaction(registered) as repo:
        assert repo.load_fact(i.reference,target=TARGET).fact.inputs==r.inputs


@pytest.mark.parametrize('method',['invasive_arterial','automated_cuff'])
@pytest.mark.parametrize('concept',['systemic_systolic','systemic_diastolic','systemic_mean'])
def test_allowed_pressure_concepts_methods(registered,method,concept):
    p,l,v=inputs();a=change(p.acquisition,method=method)
    if method=='automated_cuff':a=change(a,zeroing='not_applicable',zeroing_provenance=None,calibration='unknown',calibration_provenance=None,calibration_application=change(a.calibration_application,status='not_required'))
    p=change(p,acquisition=a,concept=concept)
    assembly,r=selected(registered,(p,l,v))
    assert build_circulatory_timing_inference(assembly=assembly,request=r).inputs[0]==p.reference


@pytest.mark.parametrize('failure',['quality_unknown','artifact','zero_unknown','calibration_unknown','method',
    'pressure_unit','pressure_concept','collection_missing','collection_clock','collection_conflict',
    'censored','preliminary','pending','cancelled','withdrawn','unknown','missing_specimen','rate_change',
    'restart','order','preparation','pause','permanent_stop','non_delivery','no_attestation','drug_unknown',
    'future_availability','future_event','missing_pressure','pressure_clock','invalid_terminal'])
def test_inference_boundary_abstentions(registered,failure):
    p,l,v=inputs()
    if failure=='quality_unknown':p=change(p,acquisition=change(p.acquisition,quality=h.EvidenceQuality()))
    elif failure=='artifact':p=change(p,acquisition=change(p.acquisition,quality=change(p.acquisition.quality,artifacts=('damping',))))
    elif failure=='zero_unknown':p=change(p,acquisition=change(p.acquisition,zeroing='unknown',zeroing_provenance=None))
    elif failure=='calibration_unknown':p=change(p,acquisition=change(p.acquisition,calibration='unknown',calibration_provenance=None))
    elif failure=='method':p=change(p,acquisition=change(p.acquisition,method='echo'))
    elif failure=='pressure_unit':p=change(p,result=numeric('65','kPa'))
    elif failure=='pressure_concept':p=change(p,concept='cvp')
    elif failure=='collection_missing':l=change(l,collected=h.ClinicalInstant())
    elif failure=='collection_clock':l=change(l,collected=change(l.collected,clock='unknown'))
    elif failure=='collection_conflict':l=change(l,collected=change(l.collected,conflicting=(AT,)))
    elif failure=='censored':l=change(l,result=change(l.result,comparator='<'))
    elif failure in ('preliminary','pending','cancelled','withdrawn','unknown'):l=change(l,report_status=failure)
    elif failure=='missing_specimen':l=change(l,specimen=None,collection_assertion=None)
    elif failure in ('rate_change','restart','order','preparation','pause','permanent_stop','non_delivery'):v=vaso(failure)
    elif failure=='no_attestation':v=change(v,action=change(v.action,delivery=change(v.action.delivery,attestation=None)))
    elif failure=='drug_unknown':v=change(v,drug=change(v.drug,mapping='unknown',canonical_id=None,limitation='unknown'))
    elif failure=='future_availability':l=change(l,available=stamp(AT+timedelta(hours=1)))
    elif failure=='future_event':p=change(p,occurred=stamp(AT+timedelta(minutes=6)))
    elif failure=='missing_pressure':p=change(p,result=h.MissingResult(status='not_measured',reason='not measured'))
    elif failure=='pressure_clock':p=change(p,occurred=change(p.occurred,clock='unreliable'))
    else:p=change(p,record_status='invalid')
    assembly,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError):build_circulatory_timing_inference(assembly=assembly,request=r)


def test_equivalent_offsets_are_equal_and_original_offsets_preserved(registered):
    p,l,v=inputs()
    v=change(v,occurred=stamp(AT.astimezone(timezone.utc)))
    assembly,r=selected(registered,(p,l,v))
    i=build_circulatory_timing_inference(assembly=assembly,request=r)
    assert 'Pressure acquisition occurred at the initiation event.' in i.statement
    assert 'Lactate collection occurred after the initiation event.' in i.statement
    assert '08:00:00.123456+05:30' in i.statement and '02:30:00.123456+00:00' in i.statement


def test_independent_support_is_explicit_not_hidden(registered):
    p,l,v=inputs();support=records()[11]
    p=change(p,associations=(h.EvidenceBinding(role='calibration',scope=TARGET,status='resolved',exact=support.reference,provenance=PROV),))
    assembly,r=selected(registered,(p,l,v,support))
    with pytest.raises(CirculatoryInferenceError):build_circulatory_timing_inference(assembly=assembly,request=r)
    r=change(r,supporting=(EvidencePin(reference=support.reference,expected_digest=support.canonical_digest),))
    i=build_circulatory_timing_inference(assembly=assembly,request=r)
    assert tuple(x.id for x in i.inputs)==('p','l','v-initiation','cal')
    assert len(i.provenance.upstream)==4


@pytest.mark.parametrize('component',['pressure','lactate','vasopressor'])
def test_tampered_pin_digest_rejected(registered,component):
    assembly,r=selected(registered)
    r=change(r,**{component:change(getattr(r,component),expected_digest='0'*64)})
    with pytest.raises(CirculatoryInferenceError,match='evidence_digest_mismatch'):
        build_circulatory_timing_inference(assembly=assembly,request=r)


@pytest.mark.parametrize('index',range(3))
def test_each_missing_clock_cannot_establish_order(registered,index):
    facts=list(inputs());f=facts[index]
    if index==1:f=change(f,collected=change(f.collected,clock='unknown'))
    else:f=change(f,occurred=change(f.occurred,clock='unknown'))
    facts[index]=f;assembly,r=selected(registered,tuple(facts))
    with pytest.raises(CirculatoryInferenceError,match='untrustworthy_clinical_time'):
        build_circulatory_timing_inference(assembly=assembly,request=r)


def test_final_corrected_lactate_qualifies_without_resurrecting_original(registered):
    assembly,r=selected(registered);l=inputs()[1]
    cutoff=save(registered,revised(l))
    ar=change(assembly.request,scope=change(assembly.request.scope,repository_cutoff=cutoff))
    a=assemble_patient_state_v3(registered,request=ar)
    corrected=next(i for i in a.snapshot.items if i.reference.id=='l')
    r=change(r,scope=ar.scope,expected_assembly_digest=a.canonical_digest,
        lactate=EvidencePin(reference=corrected.reference,expected_digest=corrected.expected_digest))
    assert build_circulatory_timing_inference(assembly=a,request=r).inputs[1].version=='2'


def test_invalid_raw_builder_input_is_sanitized():
    with pytest.raises(CirculatoryInferenceError) as caught:
        build_circulatory_timing_inference(assembly={'private':'payload'},request={})
    assert str(caught.value)=='invalid_contract'


def test_dense_support_graph_is_bounded_and_keeps_exact_dependencies(registered):
    from app.models.clinical.common import LineageEdge
    from test_patient_state_v3 import records
    p,l,v=inputs()
    supports=[change(records()[11],id=f'support-{n:02d}') for n in range(32)]
    for n in range(32):
        supports[n]=change(supports[n],provenance=change(supports[n].provenance,
            upstream=tuple(LineageEdge(target=f.reference,relationship='derived_from') for f in supports[16:] if n < 16)))
    p=change(p,provenance=change(p.provenance,upstream=tuple(LineageEdge(target=f.reference,relationship='derived_from') for f in supports)))
    assembly,r=selected(registered,(p,l,v,*supports))
    r=change(r,supporting=tuple(EvidencePin(reference=f.reference,expected_digest=f.canonical_digest) for f in supports))
    result=build_circulatory_timing_inference(assembly=assembly,request=r)
    assert len(result.inputs)==35
    assert tuple(ref.id for ref in result.inputs[3:])==tuple(f'support-{n:02d}' for n in range(32))


def test_cuff_does_not_require_or_consume_transducer_zeroing(registered):
    p,l,v=inputs();p=change(p,acquisition=change(p.acquisition,method='automated_cuff',zeroing='not_applicable',zeroing_provenance=None),
        associations=(h.EvidenceBinding(role='zeroing',scope=TARGET,status='unresolved',provenance=PROV,limitation='not applicable to cuff'),))
    assembly,r=selected(registered,(p,l,v))
    assert build_circulatory_timing_inference(assembly=assembly,request=r).inputs==r.inputs


def test_invalid_final_lactate_quality_is_unsuitable(registered):
    p,l,v=inputs();l=change(l,acquisition=change(l.acquisition,quality=h.EvidenceQuality(status='invalid',provenance=PROV)))
    assembly,r=selected(registered,(p,l,v))
    with pytest.raises(CirculatoryInferenceError,match='invalid_lactate_quality'):
        build_circulatory_timing_inference(assembly=assembly,request=r)
