"""Pure M3.1 tests with independent fixture construction and statement expectations."""
import ast
from datetime import timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.execution import patient_state_inference as inference
from app.execution.patient_state import LaboratoryState, MedicationState, PatientStateSnapshot
from app.execution.patient_state_assembly import (
    PatientStateAssemblyResult, DomainSourceCoverage, PatientStateMappingIssue,
)
from app.models.clinical.common import ClinicalValue, LineageEdge, Quantity, Reference, Unit
from app.models.clinical.facts import ClinicalInference
from app.persistence.mapping import canonical_payload
from test_patient_state import AT, DOMAINS, item, replace, scope

DISCLOSURES = (
    'Only the versioned synthetic laboratory source profile and durable medication orders/administrations are mapped.',
    'Unsupported domains may contain real-world evidence; an empty bucket does not establish clinical absence.',
    'Source completeness is unknown, including for completed retrieval.',
    'Availability by clinical time is not established; the repository prefix is not an availability timestamp.',
)
MANDATORY = (
    'Recorded and explicitly selected evidence only; this is not a patient-wide summary.',
    'Source completeness is unknown; additional evidence may exist in unsupported or unmapped domains.',
    'Mapping omissions are not evaluated as evidence of clinical absence.',
    'Availability by review end is not established.',
    'Temporal ordering does not establish clinical significance or cause.',
    'Source authenticity and specimen independence are not independently established.',
)


def with_payload(i, p):
    return replace(i, payload=p, payload_digest=sha256(canonical_payload(p).encode()).hexdigest())


def lab(index=1, value='1.00', at=AT):
    i = item(index=index, at=at)
    source = replace(i.provenance.source, namespace='clinrx.synthetic.serum-creatinine', identifier=f'sample-{index}', version='1', channel='measurement')
    i = replace(i, provenance=replace(i.provenance, source=source))
    return with_payload(i, LaboratoryState(concept_id='synthetic-serum-creatinine', value=ClinicalValue(status='known',
        value=Quantity(value=Decimal(value), unit=Unit(raw='mg/dL', code='mg/dL', system='UCUM', status='assessed')))))


def med(kind='medication_order', at=AT+timedelta(hours=1), index=3):
    i = item('medication', index=index, at=at)
    i = replace(i, reference=replace(i.reference, kind=kind))
    if kind == 'medication_administration':
        i = with_payload(i, replace(i.payload, dose=replace(i.payload.dose, basis='total_administered'), status='administered'))
    return i


def assembly(a=None, b=None, m=None, extras=(), issues=(), state_scope=None):
    a = a or lab()
    b = b or lab(2, '2.00', AT+timedelta(hours=2))
    m = m or med()
    buckets = {'laboratory':(a,b)+tuple(i for i in extras if i.domain=='laboratory'),
               'medication':(m,)+tuple(i for i in extras if i.domain=='medication')}
    coverage = []
    for domain in DOMAINS:
        supported = domain in ('laboratory','medication')
        counts = dict(candidate_count=len(buckets[domain])+sum(i.domain==domain for i in issues),
                      retained_count=len(buckets[domain]), unsuitable_count=sum(i.domain==domain and i.reason in (
                          'structurally_unsuitable_source_shape','missing_required_event_time','unsupported_temporal_precision') for i in issues)) if supported else {}
        coverage.append(DomainSourceCoverage(domain=domain, mapping_support='partial' if domain=='laboratory' else 'supported' if supported else 'unsupported',
            retrieval='completed' if supported else 'not_attempted', limitations=('source_completeness_unknown','availability_by_clinical_time_not_established')+
            (('narrow_laboratory_source_profile',) if domain=='laboratory' else () if supported else ('mapping_unsupported',)), **counts))
    disclosures = DISCLOSURES + (('Some terminal source records were omitted; consult the typed assembly mapping issues.',) if issues else ())
    return PatientStateAssemblyResult(snapshot=PatientStateSnapshot(scope=state_scope or scope(), disclosures=disclosures, **buckets), coverage=tuple(coverage), issues=issues)


def pin(i):
    return inference.PatientStateSelectionPin(reference=i.reference, expected_digest=i.canonical_digest)


def request(s, **changes):
    data = dict(scope=s.snapshot.scope, earlier_laboratory=pin(s.snapshot.laboratory[0]), later_laboratory=pin(s.snapshot.laboratory[1]),
                medication=pin(s.snapshot.medication[0]), inference_id='synthetic-relation', executed_at=AT+timedelta(hours=3))
    data.update(changes)
    return inference.PatientStateTemporalRelationRequest(**data)


def build(s=None, r=None):
    s = s or assembly()
    return inference.build_patient_state_temporal_inference(assembly=s, request=r or request(s))


def rejected(s, r, code):
    with pytest.raises(inference.PatientStateTemporalInferenceError) as exc:
        build(s,r)
    assert exc.value.code == code
    assert str(exc.value) == code
    assert exc.value.__cause__ is None


@pytest.mark.parametrize('kind', ['medication_order','medication_administration'])
@pytest.mark.parametrize('av,bv,clause', [
    ('1.00','2.00','Recorded serum creatinine increased from 1.00 mg/dL to 2.00 mg/dL between the selected laboratory observations at 2026-10-08T08:00:00.123456+05:30 and 2026-10-08T10:00:00.123456+05:30.'),
    ('2.00','1.00','Recorded serum creatinine decreased from 2.00 mg/dL to 1.00 mg/dL between the selected laboratory observations at 2026-10-08T08:00:00.123456+05:30 and 2026-10-08T10:00:00.123456+05:30.'),
    ('1.0','1.00','Recorded serum creatinine was unchanged between the selected laboratory observations at 2026-10-08T08:00:00.123456+05:30 and 2026-10-08T10:00:00.123456+05:30 (1.0 mg/dL then 1.00 mg/dL).'),
])
def test_exact_six_statements(kind,av,bv,clause):
    result=build(assembly(lab(value=av),lab(2,bv,AT+timedelta(hours=2)),med(kind)))
    suffix = ('The selected medication order has a recorded event time of 2026-10-08T09:00:00.123456+05:30, strictly between those observations.' if kind=='medication_order' else
              'The selected medication administration has a recorded administration time of 2026-10-08T09:00:00.123456+05:30, strictly between those observations.')
    assert result.statement == clause+' '+suffix+' Temporal ordering does not establish clinical significance or cause. Synthetic evaluation only.'
    assert 'recorded-ingredient' not in result.statement
    assert result.applicability == 'Descriptive comparison of two explicitly selected recorded serum-creatinine observations and one selected medication event within the supplied patient/encounter snapshot only.'
    assert result.validation_limitations == 'Not clinically validated; no diagnosis, causal attribution, medication-effect assessment or treatment recommendation.'
    assert result.origin=='inferred' and result.target is None and result.horizon is None


@pytest.mark.parametrize('av,bv,word',[('0','-1','decreased'),('-2','0','increased'),('-1.0','-1.00','unchanged'),('0','0.000','unchanged')])
def test_finite_signed_values(av,bv,word):
    assert word in build(assembly(lab(value=av),lab(2,bv,AT+timedelta(hours=2)))).statement


@pytest.mark.parametrize('field',['earlier_laboratory','later_laboratory','medication'])
@pytest.mark.parametrize('mutation',['missing','digest','wrong_domain'])
def test_membership(field,mutation):
    s=assembly(); r=request(s); p=getattr(r,field)
    if mutation=='missing': p=replace(p,reference=replace(p.reference,id='missing'))
    elif mutation=='digest': p=replace(p,expected_digest='0'*64)
    else: p=r.medication if field!='medication' else r.earlier_laboratory
    rejected(s,replace(r,**{field:p}),{'missing':'selected_reference_missing','digest':'selected_content_mismatch','wrong_domain':'selected_domain_mismatch'}[mutation])


@pytest.mark.parametrize('field',['statement','value','event','direction','applicability','limitations','body','medication_name'])
def test_no_injected_request_content(field):
    s=assembly(); r=request(s)
    rejected(s,r.model_copy(update={field:'untrusted'}),'invalid_request')
    with pytest.raises(ValidationError): inference.PatientStateSelectionPin(**{**r.earlier_laboratory.model_dump(),field:'untrusted'})


@pytest.mark.parametrize('field',['patient_id','encounter_id','review_start','review_end','repository_cutoff'])
def test_scope_canonical_mismatch(field):
    s=assembly(); r=request(s)
    value = 'different' if field.endswith('_id') else AT+timedelta(minutes=10) if field=='review_start' else AT+timedelta(hours=7) if field=='review_end' else replace(r.scope.repository_cutoff,captured_at=AT)
    rejected(s,replace(r,scope=replace(r.scope,**{field:value})),'scope_mismatch')


@pytest.mark.parametrize('part',['coverage','profile','disclosures','issue_overlap','wrong_kind','payload_digest','repository','patient','encounter','sequence','ingestion_missing','duplicate_ref','inferred_origin'])
def test_full_assembly_revalidation(part):
    s=assembly(); r=request(s); a=s.snapshot.laboratory[0]
    if part=='coverage': s=s.model_copy(update={'coverage':s.coverage[:-1]})
    elif part=='profile': s=s.model_copy(update={'profile_version':'2'})
    elif part=='disclosures': s=s.model_copy(update={'snapshot':s.snapshot.model_copy(update={'disclosures':()})})
    elif part=='issue_overlap': s=s.model_copy(update={'issues':(PatientStateMappingIssue(reference=a.reference,domain='laboratory',reason='unsupported_source_profile'),)})
    else:
        if part=='wrong_kind': a=a.model_copy(update={'reference':replace(a.reference,kind='condition')})
        elif part=='payload_digest': a=a.model_copy(update={'payload_digest':'0'*64})
        elif part=='repository': a=a.model_copy(update={'ingestion':replace(a.ingestion,repository_id='00000000-0000-4000-8000-000000000099')})
        elif part in ('patient','encounter'): a=a.model_copy(update={'binding':replace(a.binding,target=replace(a.binding.target,**{part+'_id':'foreign'}))})
        elif part=='sequence': a=a.model_copy(update={'ingestion':replace(a.ingestion,ingestion_sequence=101)})
        elif part=='ingestion_missing': a=a.model_copy(update={'ingestion':None})
        elif part=='inferred_origin': a=a.model_copy(update={'origin':'inferred'})
        items=(a,a) if part=='duplicate_ref' else (a,s.snapshot.laboratory[1])
        s=s.model_copy(update={'snapshot':s.snapshot.model_copy(update={'laboratory':items})})
    rejected(s,r,'invalid_assembly')


@pytest.mark.parametrize('part',['concept','namespace','version','channel','text','boolean','missing'])
def test_lab_profile(part):
    a=lab()
    if part=='concept': a=with_payload(a,replace(a.payload,concept_id='other'))
    elif part in ('namespace','version','channel'):
        a=replace(a,provenance=replace(a.provenance,source=replace(a.provenance.source,**{part:'system' if part=='channel' else 'other'})))
    else:
        v=ClinicalValue(status='missing',reason='not measured') if part=='missing' else ClinicalValue(status='known',value='1.00' if part=='text' else True)
        a=with_payload(a,replace(a.payload,value=v))
    s=assembly(a); rejected(s,request(s),'selected_content_mismatch')


@pytest.mark.parametrize('part',['raw','code','system','unresolved'])
def test_units(part):
    a=lab(); q=a.payload.value.value
    unit=Unit(raw='mg/dL',status='unresolved',limitation='unknown') if part=='unresolved' else replace(q.unit,**{part:'other'})
    a=with_payload(a,replace(a.payload,value=replace(a.payload.value,value=replace(q,unit=unit))))
    s=assembly(a); rejected(s,request(s),'unsupported_unit')


def test_normalized_units_and_external_source_accepted():
    a=lab(); q=a.payload.value.value
    a=with_payload(a,replace(a.payload,value=replace(a.payload.value,value=replace(q,unit=replace(q.unit,status='normalized')))))
    a=replace(a,provenance=replace(a.provenance,source=replace(a.provenance.source,channel='external_record')))
    assert build(assembly(a)).origin=='inferred'


@pytest.mark.parametrize('part',['same_pin','same_identity','same_sample'])
def test_distinct_measurements(part):
    s=assembly(); r=request(s)
    if part=='same_pin': r=replace(r,later_laboratory=r.earlier_laboratory)
    else:
        a,b=s.snapshot.laboratory
        b=replace(b,reference=replace(b.reference,id=a.reference.id,version='rev-B')) if part=='same_identity' else replace(b,provenance=replace(b.provenance,source=a.provenance.source))
        s=assembly(a,b); r=request(s)
    rejected(s,r,'duplicate_selected_measurement')


@pytest.mark.parametrize('part',['reversed','equal','offset_equal'])
def test_lab_order(part):
    s=assembly(); r=request(s)
    if part=='reversed': r=replace(r,earlier_laboratory=r.later_laboratory,later_laboratory=r.earlier_laboratory)
    else:
        a,b=s.snapshot.laboratory
        b=replace(b,time=replace(b.time,event=AT if part=='equal' else AT.astimezone(timezone.utc)))
        s=assembly(a,b); r=request(s)
    rejected(s,r,'invalid_laboratory_order')


@pytest.mark.parametrize('offset',[0,2,-1,3])
def test_med_boundary(offset):
    # Interval membership permits an out-of-window event; M3 must still reject it.
    m=med(); m=replace(m,time=replace(m.time,event=AT+timedelta(hours=offset),effective_start=AT),temporal_basis='effective_interval')
    s=assembly(m=m); rejected(s,request(s),'medication_not_strictly_between')


@pytest.mark.parametrize('part',['missing','day','approximate','unknown','uncertain'])
@pytest.mark.parametrize('which',['lab','med'])
def test_explicit_event_required(part,which):
    i=lab() if which=='lab' else med()
    t=replace(i.time,event=None,effective_start=AT) if part=='missing' else replace(i.time,uncertainty='uncertain') if part=='uncertain' else replace(i.time,precision=part)
    i=replace(i,time=t,temporal_basis='effective_interval' if part=='missing' else 'event')
    s=assembly(a=i) if which=='lab' else assembly(m=i)
    rejected(s,request(s),'invalid_event_timing')


@pytest.mark.parametrize('status',['draft','held','cancelled','active','completed'])
def test_order_status_not_reinterpreted(status):
    m=med(); m=with_payload(m,replace(m.payload,status=status))
    m=replace(m,time=replace(m.time,effective_start=AT-timedelta(days=3),effective_end=AT+timedelta(days=10)),temporal_basis='effective_interval')
    assert 'medication order has a recorded event time' in build(assembly(m=m)).statement


@pytest.mark.parametrize('part',['status','dose','basis'])
def test_administration_completed_semantics(part):
    m=med('medication_administration')
    p=replace(m.payload,status='planned') if part=='status' else replace(m.payload,dose=None) if part=='dose' else replace(m.payload,dose=replace(m.payload.dose,basis='per_dose'))
    s=assembly(m=with_payload(m,p)); rejected(s,request(s),'selected_content_mismatch')


def test_exact_dependencies_no_upstream_flattening_or_order_association():
    a=lab(); m=med('medication_administration')
    upstream=Reference(kind='observation',id='upstream',version='1')
    order=Reference(kind='medication_order',id='associated-order',version='1')
    a=replace(a,provenance=replace(a.provenance,upstream=(LineageEdge(target=upstream,relationship='copied_from'),)))
    m=replace(m,provenance=replace(m.provenance,upstream=(LineageEdge(target=order,relationship='fulfills_order'),)))
    s=assembly(a=a,m=m); result=build(s)
    expected=(a.reference,s.snapshot.laboratory[1].reference,m.reference)
    assert result.inputs==expected==result.provenance.dependencies
    assert tuple((e.target,e.relationship,e.basis) for e in result.provenance.upstream)==tuple((ref,'derived_from',()) for ref in expected)
    assert upstream not in result.inputs and order not in result.inputs


def test_valid_extras_and_issues_do_not_change_output():
    original=assembly(); r=request(original)
    extras=(lab(4,'900',AT+timedelta(minutes=10)),med(index=5,at=AT+timedelta(minutes=20)))
    issue=PatientStateMappingIssue(reference=Reference(kind='procedure',id='unmapped',version='1'),domain=None,reason='unsupported_source_profile')
    larger=assembly(extras=extras,issues=(issue,))
    assert canonical_payload(build(original,r))==canonical_payload(build(larger,r))
    assert all(c.source_completeness=='unknown' for c in larger.coverage)


def test_malformed_unselected_content_rejected():
    s=assembly(extras=(lab(4),)); r=request(s)
    bad=s.snapshot.laboratory[-1].model_copy(update={'payload_digest':'bad'})
    s=s.model_copy(update={'snapshot':s.snapshot.model_copy(update={'laboratory':s.snapshot.laboratory[:-1]+(bad,)})})
    rejected(s,r,'invalid_assembly')


def test_revision_pin_and_same_value_correction_material():
    old=assembly(); r=request(old); a,b=old.snapshot.laboratory
    a2=replace(a,reference=replace(a.reference,version='rev-B'))
    new=assembly(a2,b)
    rejected(new,r,'selected_reference_missing')
    original=build(old,r); changed=build(new)
    assert original.inputs[0].version=='rev-A' and changed.inputs[0].version=='rev-B'
    assert original.statement==changed.statement and canonical_payload(original)!=canonical_payload(changed)
    assert build(old,r)==original


def test_uncertainty_exact_order_and_dedup():
    a=replace(lab(),disclosures=(MANDATORY[0],'A disclosure','shared'))
    b=replace(lab(2,'2.00',AT+timedelta(hours=2)),disclosures=('shared','B disclosure'))
    m=replace(med(),disclosures=('M disclosure','shared'))
    result=build(assembly(a,b,m))
    expected=list(MANDATORY)
    for label,disclosures in [('A',('A disclosure','shared')),('B',('B disclosure',)),('M',('M disclosure',))]:
        expected.extend(disclosures)
        if label=='A': expected.append('source evidence only')
        expected.extend((f'Selected {label} verification: unverified.',f'Selected {label} conflict: unknown.',
                         f'Selected {label} provenance completeness: unknown.',f'Selected {label} binding verification: unresolved.'))
    assert result.uncertainty==tuple(expected)


@pytest.mark.parametrize('which',['a','b','m'])
@pytest.mark.parametrize('field',['event','recorded','retrieved','processed','provenance','binding'])
def test_execution_time_bounds(which,field):
    s=assembly(); r=request(s); a,b=s.snapshot.laboratory; m=s.snapshot.medication[0]
    i={'a':a,'b':b,'m':m}[which]; future=r.executed_at+timedelta(microseconds=1)
    if field=='provenance': i=replace(i,provenance=replace(i.provenance,recorded_at=future))
    elif field=='binding': i=replace(i,binding=replace(i.binding,verification=replace(i.binding.verification,assessed_at=future)))
    elif field=='event':
        # Preserve valid ordering and place execution immediately before that event.
        rejected(s,replace(r,executed_at=i.time.event-timedelta(microseconds=1)),'invalid_execution_time'); return
    else: i=replace(i,time=replace(i.time,**{field:future}))
    s=assembly(i if which=='a' else a,i if which=='b' else b,i if which=='m' else m)
    rejected(s,request(s),'invalid_execution_time')


def test_identity_execution_boundary_and_correction():
    s=assembly(); executed=AT+timedelta(hours=2,minutes=15)
    r=request(s,inference_id='I',revision='2',executed_at=executed,supersedes=Reference(kind='inference',id='I',version='1'),correction_reason='recorded correction')
    result=build(s,r)
    assert result.id=='I' and result.revision=='2' and result.supersedes==r.supersedes
    assert result.time.event.isoformat()==executed.isoformat()==result.provenance.recorded_at.isoformat()
    assert result.time.recorded==executed==result.time.processed
    assert r.supersedes not in result.inputs
    assert result.method==Reference(kind='inference_method',id='RecordedPatientStateTemporalRelation',version='1')


@pytest.mark.parametrize('part',['id','revision','naive','half_reason','half_ref','wrong_id','wrong_kind','same_revision'])
def test_invalid_request(part):
    s=assembly(); r=request(s)
    updates={'inference_id':''} if part=='id' else {'revision':''} if part=='revision' else {'executed_at':AT.replace(tzinfo=None)} if part=='naive' else {'correction_reason':'x'}
    if part in ('half_ref','wrong_id','wrong_kind','same_revision'):
        updates={'supersedes':Reference(kind='observation' if part=='wrong_kind' else 'inference',id='other' if part=='wrong_id' else r.inference_id,version='1' if part=='same_revision' else '0')}
        if part!='half_ref': updates['correction_reason']='x'
    rejected(s,r.model_copy(update=updates),'invalid_request')


def test_offsets_dst_actual_order_and_representation():
    zone=ZoneInfo('America/New_York')
    a_at=AT.replace(month=11,day=1,hour=1,minute=10,tzinfo=zone,fold=0)
    m_at=a_at.replace(minute=50)
    b_at=a_at.replace(minute=20,fold=1)
    sscope=replace(scope(),review_start=a_at,review_end=b_at+timedelta(hours=2))
    a,b,m=lab(at=a_at),lab(2,'2.00',b_at),med(at=m_at)
    s=assembly(a,b,m,state_scope=sscope)
    r=request(s,executed_at=b_at+timedelta(hours=3))
    result=build(s,r)
    assert a_at.isoformat() in result.statement and b_at.isoformat() in result.statement
    assert '-04:00' in result.statement and '-05:00' in result.statement


def test_canonical_roundtrip_and_deep_immutability():
    s=assembly(); r=request(s); before=canonical_payload(s); result=build(s,r)
    assert canonical_payload(ClinicalInference.model_validate_json(canonical_payload(result)))==canonical_payload(result)
    assert build(PatientStateAssemblyResult.model_validate_json(before),inference.PatientStateTemporalRelationRequest.model_validate_json(canonical_payload(r)))==result
    for obj,field,value in [(result,'statement','bad'),(result.inputs[0],'version','bad'),(result.provenance,'upstream',()),(r.earlier_laboratory,'expected_digest','0'*64)]:
        with pytest.raises(ValidationError): setattr(obj,field,value)
    assert canonical_payload(s)==before


def test_no_side_effect_calls(monkeypatch):
    import app.persistence.repository as repository
    import app.execution.patient_state_assembly as assembler
    import app.execution.weight_trend as weight
    import app.execution.creatinine_trend as creatinine
    import sqlite3
    import time
    import sqlalchemy
    def forbidden(*args,**kwargs): raise AssertionError('forbidden side effect')
    for obj,name in [(repository,'transaction'),(assembler,'transaction'),(sqlite3,'connect'),(sqlalchemy,'create_engine'),(time,'time'),(time,'monotonic'),
                     (weight,'build_weight_trend_inference'),(creatinine,'build_creatinine_trend_inference')]:
        monkeypatch.setattr(obj,name,forbidden)
    assert build().origin=='inferred'
    tree=ast.parse(Path(inference.__file__).read_text())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert imports==['datetime','typing','pydantic','app.execution.patient_state','app.execution.patient_state_assembly','app.models.clinical.common','app.models.clinical.facts','app.persistence.mapping']
    calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert not any(any(word in call for word in ('now','utcnow','transaction','resolve_lineage','assess_release','decide_release','execute','connect','latest')) for call in calls)


def test_hash_seed_independence():
    code='from test_patient_state_inference import build; from app.persistence.mapping import canonical_payload; print(canonical_payload(build()))'
    outputs=[subprocess.check_output([sys.executable,'-c',code],env={**os.environ,'PYTHONPATH':'backend:tests','PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'},text=True) for seed in ('1','19','109')]
    assert outputs[0]==outputs[1]==outputs[2]


@pytest.mark.parametrize('value',[None,{},'raw',123])
def test_require_typed_assembly(value):
    rejected(value,request(assembly()),'invalid_assembly') if value else None
    with pytest.raises(inference.PatientStateTemporalInferenceError,match='invalid_assembly'):
        inference.build_patient_state_temporal_inference(assembly=value,request=request(assembly()))


def test_sanitized_error_and_process_control(monkeypatch):
    s=assembly(); r=request(s)
    def failure(*args,**kwargs): raise ValueError('SECRET raw payload')
    monkeypatch.setattr(inference,'_build',failure)
    rejected(s,r,'selected_content_mismatch')
    def interrupt(*args,**kwargs): raise KeyboardInterrupt
    monkeypatch.setattr(inference,'_build',interrupt)
    with pytest.raises(KeyboardInterrupt): build(s,r)


@pytest.mark.parametrize('field',['recorded','retrieved','processed'])
def test_absent_optional_recording_times(field):
    a=lab(); a=replace(a,time=replace(a.time,**{field:None}))
    assert build(assembly(a)).origin=='inferred'


@pytest.mark.parametrize('number',['NaN','Infinity','-Infinity'])
def test_nonfinite_bypass_fails_safely(number):
    s=assembly(); r=request(s); a,b=s.snapshot.laboratory
    q=a.payload.value.value.model_copy(update={'value':Decimal(number)})
    p=a.payload.model_copy(update={'value':a.payload.value.model_copy(update={'value':q})})
    a=a.model_copy(update={'payload':p})
    s=s.model_copy(update={'snapshot':s.snapshot.model_copy(update={'laboratory':(a,b)})})
    rejected(s,r,'invalid_assembly')


def test_whole_item_metadata_changes_are_material():
    s=assembly(); r=request(s); a,b=s.snapshot.laboratory
    a=replace(a,disclosures=('new retained disclosure',))
    rejected(assembly(a,b),r,'selected_content_mismatch')


def test_offset_equal_scope_representation_is_material():
    s=assembly(); r=request(s)
    r=replace(r,scope=replace(r.scope,review_start=r.scope.review_start.astimezone(timezone.utc)))
    rejected(s,r,'scope_mismatch')


def test_drug_and_source_text_do_not_enter_statement():
    m=med(); m=with_payload(m,replace(m.payload,medication=replace(m.payload.medication,ingredient_ids=('STOP MEDICATION DUE TO AKI',)),schedule_text='caused renal injury'))
    m=replace(m,provenance=replace(m.provenance,actor='worsening renal function'))
    assert build(assembly(m=m)).statement==build().statement


def test_unrelated_future_metadata_does_not_bound_execution():
    extra=lab(4,at=AT+timedelta(hours=5))
    s=assembly(extras=(extra,)); original=assembly(); r=request(original)
    assert canonical_payload(build(s,r))==canonical_payload(build(original,r))


def test_selected_conflict_and_verification_are_disclosed():
    a=replace(lab(),verification='verified',conflict='unresolved',provenance=replace(lab().provenance,lineage='incomplete'))
    result=build(assembly(a))
    assert 'Selected A verification: verified.' in result.uncertainty
    assert 'Selected A conflict: unresolved.' in result.uncertainty
    assert 'Selected A provenance completeness: incomplete.' in result.uncertainty
