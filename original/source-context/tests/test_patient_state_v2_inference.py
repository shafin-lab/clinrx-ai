"""Independent M6.3 statement/role assertions, plus durable historical replay."""
import ast
from datetime import timedelta, timezone
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from pydantic import ValidationError
from app.execution import patient_state_v2_inference as n
from app.execution.patient_state_v2_assembly import (AssemblyRequestV2, PatientStateAssemblyResultV2, BindingOutcomeV2, assemble_patient_state_v2)
from app.execution.patient_state_v2 import CoverageV2, MappingIssueV2
from app.models.clinical.common import Reference
from app.persistence.metadata import IngestionMetadata
from app.persistence.canonical import canonical_payload
from test_patient_state_v2 import (facts, all_facts, change, time, binding, item, scope, snapshot, AT, REPO, TARGET, c)
from test_persistence import database, registered
from test_patient_state_v2_persistence import save, revision

FIELDS=('specimen_ref','isolate_ref','susceptibility_ref','administration_ref')


def selected():
    s,i,u,d,_=facts()
    return (s,change(i,identification_state='final'),
            change(u,report=change(u.report,available=time(AT+timedelta(hours=2)))),
            change(d,administered=time(AT+timedelta(hours=1))))


def assembly(records=None, state_scope=None):
    records=selected() if records is None else records
    retained=tuple(item(f,ingestion=IngestionMetadata(repository_id=REPO,ingestion_sequence=index+1,ingested_at=AT+timedelta(hours=3))) for index,f in enumerate(records))
    refs={f.reference for f in records}
    issues=tuple(MappingIssueV2(reference=f.reference,reason='binding_target_unavailable') for f in records if any(b.exact and b.exact not in refs for b in f.domain_bindings))
    coverage=tuple(CoverageV2(domain=domain,mapping_support='partial',retrieval='completed',candidate_count=sum(f.kind.startswith('antimicrobial_')==(domain=='antimicrobial') for f in records),retained_count=sum(f.kind.startswith('antimicrobial_')==(domain=='antimicrobial') for f in records),limitations=('synthetic supplied collection',)) for domain in ('microbiology','antimicrobial'))
    snap=snapshot(retained,coverage=coverage,issues=issues,scope=state_scope or scope())
    outcomes=[]
    for f in records:
        for b in f.domain_bindings:
            status=b.status if b.status!='resolved' or b.exact in refs else 'unresolved'
            disposition='declared_'+b.status if b.status!='resolved' else 'retained_exact' if b.exact in refs else 'unavailable_in_prefix'
            outcomes.append(BindingOutcomeV2(owner=f.reference,role=b.role,declared=b.exact,status=status,disposition=disposition,candidates=b.candidates))
    return PatientStateAssemblyResultV2(request=AssemblyRequestV2(scope=snap.scope,profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2'),snapshot=snap,candidate_rows=len(records),terminal_count=len(records),bindings=tuple(sorted(outcomes,key=lambda b:(b.owner.kind,b.owner.id,b.owner.version,b.role))))


def request(a, records=None, **updates):
    if records is None:
        records=tuple(next(i.fact for i in a.snapshot.items if i.fact.kind==kind) for kind in ('microbiology_specimen','microbiology_isolate','microbiology_susceptibility','antimicrobial_administration'))
    values=dict(scope=a.snapshot.scope,expected_assembly_digest=a.canonical_digest,inference_id='synthetic-SIUD',executed_at=AT+timedelta(hours=3))
    values.update({field:n.MicroAntimicrobialPin(role=role,reference=f.reference,expected_digest=f.canonical_digest) for field,role,f in zip(FIELDS,('S','I','U','D'),records,strict=True)})
    values.update(updates)
    return n.MicroAntimicrobialTimingRequest(**values)


def build(a=None,r=None):
    a=assembly() if a is None else a
    return n.build_micro_antimicrobial_timing_inference(assembly=a,request=request(a) if r is None else r)


def reject(a,r,code,category='unsuitable'):
    with pytest.raises(n.MicroAntimicrobialInferenceError) as caught: build(a,r)
    assert caught.value.code==code
    assert caught.value.category==category
    assert str(caught.value)==code
    assert caught.value.__cause__ is None


def test_exact_statement_and_four_direct_inputs():
    result=build()
    assert result.statement==('The selected antimicrobial administration was recorded at 2026-10-08T09:00:00.123456+05:30. '
        'The selected specimen was collected at 2026-10-08T08:00:00.123456+05:30. '
        'The selected susceptibility revision was recorded as available at 2026-10-08T10:00:00.123456+05:30. '
        'Administration occurred after specimen collection and before susceptibility availability.')
    refs=tuple(f.reference for f in selected())
    assert result.inputs==refs
    assert [(e.relationship,e.target,e.basis) for e in result.provenance.upstream]==[('derived_from',r,()) for r in refs]
    assert result.provenance.dependencies==refs
    assert result.method==Reference(kind='inference_method',id='RecordedAntimicrobialSpecimenSusceptibilityTiming',version='1')
    assert result.origin=='inferred' and result.target is None and result.horizon is None
    for claim in ('treatment appropriateness','infection versus colonization','source authenticity','clinician awareness','causality','complete antimicrobial exposure','clinically actionable','breakpoint validity'):
        assert any(claim in t for t in result.uncertainty)
    for word in ('appropriate','recommend','infection','colonization','cause','escalation','awareness'):
        assert word not in result.statement


@pytest.mark.parametrize('ds', ['before','at','after'])
@pytest.mark.parametrize('du', ['before','at','after'])
def test_all_nine_independent_relations(ds,du):
    s,i,u,d=selected(); center=AT+timedelta(hours=1)
    delta={'before':1,'at':0,'after':-1}
    s=change(s,collected=time(center+timedelta(minutes=delta[ds])))
    u=change(u,report=change(u.report,available=time(center+timedelta(minutes=delta[du]))))
    a=assembly((s,i,u,d))
    assert build(a).statement.endswith(f'Administration occurred {ds} specimen collection and {du} susceptibility availability.')


@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('mutation',['missing','digest','type'])
def test_exact_pin_failures(field,mutation):
    a=assembly(); r=request(a); pin=getattr(r,field)
    if mutation=='missing': pin=change(pin,reference=change(pin.reference,version='absent'))
    elif mutation=='digest': pin=change(pin,expected_digest='0'*64)
    else: pin=change(pin,reference=Reference(kind='observation',id='wrong',version='1'))
    reject(a,change(r,**{field:pin}),{'missing':'selected_reference_missing','digest':'selected_digest_mismatch','type':'selected_role_type'}[mutation],'integrity' if mutation=='digest' else 'unsuitable')


@pytest.mark.parametrize('kind',['antimicrobial_order','antimicrobial_non_delivery','medication_administration'])
def test_administration_role_cannot_be_other_event(kind):
    a=assembly(); r=request(a)
    pin=change(r.administration_ref,reference=Reference(kind=kind,id='other',version='1'))
    reject(a,change(r,administration_ref=pin),'selected_role_type')


@pytest.mark.parametrize('child,role,target',[(1,'specimen','S'),(2,'isolate','I')])
@pytest.mark.parametrize('status',['unresolved','ambiguous','different','old_revision'])
def test_exact_bindings(child,role,target,status):
    records=list(selected()); b=binding(role,target)
    if status in ('unresolved','ambiguous'):
        b=change(b,status=status,stable_target=None,exact=None,limitation='source uncertainty',candidates=(b.exact,change(b.exact,id='other')) if status=='ambiguous' else ())
    elif status=='different': b=binding(role,'other')
    else: b=change(b,exact=change(b.exact,version='old'))
    records[child]=change(records[child],domain_bindings=(b,))
    a=assembly(records)
    reject(a,request(a),'unsupported_binding')


@pytest.mark.parametrize('side',[2,3])
@pytest.mark.parametrize('state',['unknown','unsupported','ambiguous'])
def test_unmapped_agent_unsuitable(side,state):
    records=list(selected()); f=records[side]
    records[side]=change(f,antimicrobial=change(f.antimicrobial,mapping_status=state,canonical_id=None,ingredient_ids=(),limitation='not established'))
    a=assembly(records); reject(a,request(a),'unsupported_antimicrobial_mapping')


@pytest.mark.parametrize('part',['canonical_id','ingredient_ids'])
def test_same_display_different_identity_fails(part):
    s,i,u,d=selected()
    d=change(d,antimicrobial=change(d.antimicrobial,**{part:'other' if part=='canonical_id' else ('other',)}))
    a=assembly((s,i,u,d)); reject(a,request(a),'antimicrobial_identity_mismatch')


def test_different_display_same_explicit_identity_succeeds():
    s,i,u,d=selected(); d=change(d,antimicrobial=change(d.antimicrobial,raw_display='Different source spelling'))
    assert build(assembly((s,i,u,d))).inputs[-1]==d.reference


@pytest.mark.parametrize('role',[0,2,3])
@pytest.mark.parametrize('precision',['missing','approximate','day','uncertain_instant'])
def test_unusable_times_no_fallback(role,precision):
    records=list(selected())
    t=c.RecordedTime(status='missing') if precision=='missing' else c.RecordedTime(status='known',precision='instant' if precision=='uncertain_instant' else precision,value=AT,uncertainty='source uncertain')
    if role==0: records[0]=change(records[0],collected=t)
    elif role==2: records[2]=change(records[2],report=change(records[2].report,available=t))
    else: records[3]=change(records[3],administered=t,infusion_start=time())
    a=assembly(records)
    reject(a,request(a),'missing_required_time' if precision=='missing' else 'insufficient_temporal_precision')


def bounded(lo,hi):
    return c.RecordedTime(status='known',precision='bounded',lower=lo,upper=hi,uncertainty='Approximate within explicit source bounds')


def test_bounded_approximate_order_provable():
    s,i,u,d=selected(); s=change(s,collected=bounded(AT,AT+timedelta(minutes=5)))
    d=change(d,administered=bounded(AT+timedelta(minutes=50),AT+timedelta(minutes=60)))
    u=change(u,report=change(u.report,available=bounded(AT+timedelta(minutes=100),AT+timedelta(minutes=110))))
    result=build(assembly((s,i,u,d)))
    assert result.statement.endswith('Administration occurred after specimen collection and before susceptibility availability.')
    assert 'within [2026-10-08T08:00:00.123456+05:30, 2026-10-08T08:05:00.123456+05:30]' in result.statement
    assert any('Approximate within explicit source bounds' in t for t in result.uncertainty)


@pytest.mark.parametrize('start,end',[(0,60),(30,90),(60,61)])
def test_touching_or_overlapping_intervals_unsuitable(start,end):
    s,i,u,d=selected(); s=change(s,collected=bounded(AT+timedelta(minutes=start),AT+timedelta(minutes=end)))
    a=assembly((s,i,u,d)); reject(a,request(a),'ambiguous_temporal_relation')


def test_offset_equivalent_and_degenerate_bounds_are_at():
    s,i,u,d=selected(); at=d.administered.value
    s=change(s,collected=time(at.astimezone(timezone.utc)))
    u=change(u,report=change(u.report,available=bounded(at,at)))
    result=build(assembly((s,i,u,d)))
    assert result.statement.endswith('Administration occurred at specimen collection and at susceptibility availability.')
    assert '+00:00' in result.statement


@pytest.mark.parametrize('side',[1,2])
@pytest.mark.parametrize('status',['preliminary','interim','withdrawn'])
def test_report_state_policy(side,status):
    records=list(selected()); records[side]=change(records[side],report=change(records[side].report,status=status))
    a=assembly(records); reject(a,request(a),'unsupported_report_state')


@pytest.mark.parametrize('side',[1,2])
def test_superseded_disposition_unsuitable(side):
    records=list(selected()); records[side]=change(records[side],report=change(records[side].report,change='superseded'))
    a=assembly(records); reject(a,request(a),'unsupported_report_state')


@pytest.mark.parametrize('state',['provisional','unresolved'])
def test_isolate_identification_policy(state):
    records=list(selected()); records[1]=change(records[1],identification_state=state)
    a=assembly(records); reject(a,request(a),'unsupported_report_state')


@pytest.mark.parametrize('state',['indeterminate','not_performed'])
def test_susceptibility_must_be_reported(state):
    records=list(selected()); records[2]=change(records[2],result_status=state,mic=None,interpretation=None)
    a=assembly(records); reject(a,request(a),'unsupported_report_state')


def test_corrected_exact_u_is_valid_and_predecessor_not_lineage():
    s,i,u,d=selected(); corrected=revision(u)
    result=build(assembly((s,i,corrected,d)))
    assert result.inputs==(s.reference,i.reference,corrected.reference,d.reference)
    assert u.reference not in result.provenance.dependencies


@pytest.mark.parametrize('role',range(4))
def test_conflict_unsuitable(role):
    records=list(selected()); records[role]=change(records[role],conflict='unresolved')
    a=assembly(records); reject(a,request(a),'unresolved_conflict')


@pytest.mark.parametrize('field',['patient_id','encounter_id','review_start','review_end','repository_cutoff'])
def test_scope_and_cutoff_match(field):
    a=assembly(); r=request(a)
    value='other' if field.endswith('_id') else change(r.scope.repository_cutoff,fact_watermark=99) if field=='repository_cutoff' else AT+timedelta(minutes=1) if field=='review_start' else AT+timedelta(hours=4)
    reject(a,change(r,scope=change(r.scope,**{field:value})),'scope_mismatch','integrity')


@pytest.mark.parametrize('part',['item_digest','time','binding','duplicate','coverage','outcome','profile','ingestion'])
def test_malformed_or_tampered_assembly(part):
    a=assembly(); r=request(a)
    if part=='profile': bad=a.model_copy(update={'request':a.request.model_copy(update={'profile_version':'other'})})
    elif part=='outcome': bad=a.model_copy(update={'bindings':()})
    elif part=='coverage': bad=a.model_copy(update={'snapshot':a.snapshot.model_copy(update={'coverage':()})})
    else:
        items=list(a.snapshot.items); pos=next(k for k,i in enumerate(items) if i.fact.kind=='microbiology_specimen'); item=items[pos]
        if part=='item_digest': items[pos]=item.model_copy(update={'expected_digest':'0'*64})
        elif part=='time': items[pos]=item.model_copy(update={'fact':change(item.fact,collected=time(AT+timedelta(minutes=1)))})
        elif part=='binding': items[pos]=item.model_copy(update={'fact':item.fact.model_copy(update={'binding':item.fact.binding.model_copy(update={'target':change(TARGET,patient_id='other')})})})
        elif part=='duplicate': items.append(item)
        else: items[pos]=item.model_copy(update={'ingestion':None})
        bad=a.model_copy(update={'snapshot':a.snapshot.model_copy(update={'items':tuple(items)})})
    with pytest.raises(n.MicroAntimicrobialInferenceError) as caught: build(bad,r)
    assert caught.value.category=='integrity'


@pytest.mark.parametrize('field',['specimen_ref','isolate_ref','susceptibility_ref','administration_ref'])
def test_named_role_identity_cannot_be_swapped(field):
    a=assembly(); r=request(a); pin=getattr(r,field)
    bad=r.model_copy(update={field:pin.model_copy(update={'role':'D' if pin.role!='D' else 'S'})})
    reject(a,bad,'invalid_request','invalid_input')


def test_complete_collection_pin_rejects_omission():
    records=selected()+(facts()[4],)
    a=assembly(records); r=request(a)
    shorter=assembly(selected())
    reject(shorter,r,'assembly_digest_mismatch','integrity')


def test_selected_payload_change_with_updated_assembly_but_stale_pin():
    a=assembly(); r=request(a); records=list(selected())
    records[3]=change(records[3],administered_dose=change(records[3].administered_dose,amount={'value':'501.00','unit':records[3].administered_dose.amount.unit}))
    b=assembly(records)
    reject(b,change(r,expected_assembly_digest=b.canonical_digest),'selected_digest_mismatch','integrity')
    assert canonical_payload(build(a))!=canonical_payload(build(b))


def test_determinism_permutations_and_deep_immutability():
    a=assembly(); r=request(a); first=build(a,r)
    second=build(a.model_copy(update={'snapshot':a.snapshot.model_copy(update={'items':tuple(reversed(a.snapshot.items))})}),r)
    assert canonical_payload(first)==canonical_payload(second)
    assert sha256(canonical_payload(first).encode()).hexdigest()==sha256(canonical_payload(second).encode()).hexdigest()
    assert canonical_payload(type(first).model_validate_json(canonical_payload(first)))==canonical_payload(first)
    for model,field in [(r,'inference_id'),(r.specimen_ref,'expected_digest'),(first,'statement'),(first.provenance,'upstream')]:
        with pytest.raises(ValidationError): setattr(model,field,None)


def test_unrelated_order_and_other_facts_not_lineage():
    s,i,u,d=selected(); order=facts()[4]
    d=change(d,domain_bindings=(binding('order','O'),))
    result=build(assembly((s,i,u,d,order,all_facts()[5],all_facts()[6])))
    assert result.inputs==(s.reference,i.reference,u.reference,d.reference)
    assert order.reference not in result.provenance.dependencies


@pytest.mark.parametrize('time_value',[AT,AT+timedelta(hours=2,microseconds=-1)])
def test_execution_time_explicit_and_not_before_consumed_times(time_value):
    a=assembly(); reject(a,request(a,executed_at=time_value),'invalid_execution_time')


def test_no_io_or_clock_calls(monkeypatch):
    import app.persistence.repository as repo
    import app.execution.patient_state_v2_assembly as assembler
    def forbidden(*args,**kwargs): pytest.fail('hidden evidence accessed')
    for name in ('load_fact','list_bounded_history','list_latest_known','capture_cutoff','resolve_lineage'):
        monkeypatch.setattr(repo.PatientRepository,name,forbidden)
    monkeypatch.setattr(repo,'_now',forbidden)
    monkeypatch.setattr(assembler,'assemble_patient_state_v2',forbidden)
    assert build().origin=='inferred'
    tree=ast.parse(Path(n.__file__).read_text())
    imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert not any(v and ('repository' in v or 'sqlalchemy' in v or v=='datetime') for v in imports)


def test_persisted_lineage_and_future_historical_replay(registered):
    from app.persistence.repository import transaction
    from app.persistence.lineage import LineageLimits
    records=selected(); old_cutoff=save(registered,*records)
    ar=AssemblyRequestV2(scope=change(scope(),repository_cutoff=old_cutoff),profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2')
    old=assemble_patient_state_v2(registered,request=ar); r=request(old); original=build(old,r)
    with transaction(registered) as repo:
        repo.append_fact(original,target=TARGET)
        output=repo.capture_cutoff()
    with transaction(registered) as repo:
        lineage=repo.resolve_lineage(original.reference,target=TARGET,cutoff=output,limits=LineageLimits())
        assert tuple(x.source for x in lineage.dependencies if x.owner==original.reference)==tuple(f.reference for f in records)
    s,i,u,d=records
    new_i=revision(i,organism=change(i.organism,raw_display='corrected label'))
    new_u=revision(u,provenance=change(u.provenance,actor='corrected source'))
    later=save(registered,new_i,new_u)
    registered.dispose()
    replay=assemble_patient_state_v2(registered,request=ar)
    assert canonical_payload(build(replay,r))==canonical_payload(original)
    current=assemble_patient_state_v2(registered,request=change(ar,scope=change(ar.scope,repository_cutoff=later)))
    reject(current,request(current),'unsupported_binding')
    assert canonical_payload(build(old,r))==canonical_payload(original)


def test_dst_fold_compared_by_actual_instant():
    zone=ZoneInfo('America/New_York')
    first=AT.replace(month=11,day=1,hour=1,minute=30,tzinfo=zone,fold=0)
    second=first.replace(fold=1)
    assert first==second  # Python wall-time equality must not decide the relation.
    s,i,u,d=selected()
    s=change(s,collected=time(first))
    i=change(i,report=change(i.report,available=time(first)))
    u=change(u,report=change(u.report,available=time(second)))
    d=change(d,administered=time(second))
    a=assembly((s,i,u,d),state_scope=change(scope(),review_start=first,review_end=second))
    result=build(a,request(a,executed_at=second+timedelta(hours=1)))
    assert result.statement.endswith('Administration occurred after specimen collection and at susceptibility availability.')
    assert '-04:00' in result.statement and '-05:00' in result.statement


def test_mapping_and_binding_limitations_preserved():
    s,i,u,d=selected()
    i=change(i,domain_bindings=(change(i.domain_bindings[0],provenance=change(i.domain_bindings[0].provenance,limitations=('link source not independently verified',))),))
    u=change(u,antimicrobial=change(u.antimicrobial,mapping_provenance=change(u.antimicrobial.mapping_provenance,limitations=('mapping assertion has limited support',))))
    result=build(assembly((s,i,u,d)))
    assert 'Selected specimen binding limitation: link source not independently verified' in result.uncertainty
    assert 'Selected U identity mapping limitation: mapping assertion has limited support' in result.uncertainty


def test_unrelated_absent_binding_contradiction_is_integrity_failure():
    s,i,u,d=selected(); d=change(d,domain_bindings=(binding('order','missing'),))
    a=assembly((s,i,u,d))
    outcomes=tuple(change(b,status='resolved') if b.role=='order' else b for b in a.bindings)
    bad=change(a,bindings=outcomes)
    reject(bad,request(bad),'invalid_assembly','integrity')


def test_inconsistent_coverage_count_is_integrity_failure():
    a=assembly()
    coverage=tuple(change(c,candidate_count=100) for c in a.snapshot.coverage)
    bad=change(a,snapshot=change(a.snapshot,coverage=coverage))
    reject(bad,request(bad),'invalid_assembly','integrity')


def test_invalid_input_has_no_clinical_text_in_displayed_traceback():
    import traceback
    a=assembly(); r=request(a).model_copy(update={'executed_at':'CONFIDENTIAL_SENTINEL'})
    with pytest.raises(n.MicroAntimicrobialInferenceError) as caught: build(a,r)
    assert 'CONFIDENTIAL_SENTINEL' not in ''.join(traceback.format_exception(caught.value))


def test_source_limitations_over_family_budget_fail_without_truncation():
    records=list(selected()); records[0]=change(records[0],uncertainty=('x'*65536,))
    a=assembly(records)
    reject(a,request(a),'evidence_limits_exceeded')


@pytest.mark.parametrize('field',['profile_id','profile_version','expected_assembly_digest','statement'])
def test_unvalidated_request_copies_rechecked(field):
    a=assembly(); r=request(a).model_copy(update={field:'injected'})
    reject(a,r,'invalid_request','invalid_input')


def test_explicit_same_value_u_successor_is_distinct_evidence():
    s,i,u,d=selected(); newer=revision(u)
    first=build(assembly((s,i,u,d)))
    second=build(assembly((s,i,newer,d)))
    assert first.statement==second.statement
    assert first.inputs[2]==u.reference and second.inputs[2]==newer.reference
    assert canonical_payload(first)!=canonical_payload(second)
