"""Pure M4.1 synthetic contracts and adversarial governance checks; no database."""
import ast
from datetime import timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.execution import patient_state_execution as c
from app.execution import patient_state_release as g
from app.execution import patient_state_inference as m3
from app.execution.patient_state import LaboratoryState, MedicationState, PatientStateScope, RetainedStateItem
from app.models.clinical.common import LineageEdge, Reference
from app.models.clinical.decisions import RecommendationReview
from app.models.clinical.governance import RuntimeState, ValidityWindow, required_payload
from app.persistence.errors import RecordConflict
from app.persistence.mapping import StoredFact, canonical_payload
from app.persistence.metadata import RepositoryCutoff, IngestionMetadata
from app.services.governance_service import assess_release, decide_release
from test_persistence import AT, patient, encounter, replace
from test_patient_state_assembly import lab, med
from test_patient_state_inference import assembly

REPO=UUID('00000000-0000-4000-8000-000000000001')
START=c.GRANT_WINDOW.start


def mapped(f,index):
    if f.kind=='observation':
        p=LaboratoryState(concept_id=f.concept_id,value=f.value)
    else:
        dose=f.prescribed_dose if f.kind=='medication_order' else f.administered_dose
        p=MedicationState(medication=f.medication,dose=dose,route=f.route,frequency=dose.frequency,
            schedule_text=f.schedule_text if f.kind=='medication_order' else None,
            status=f.order_status if f.kind=='medication_order' else 'administered')
    disclosures=tuple('Source uncertainty: '+x for x in f.uncertainty)
    if f.kind=='observation': disclosures+=('Dedicated specimen identity and result status are not represented by this durable observation model.',)
    return RetainedStateItem(reference=f.reference,binding=f.binding,origin=f.origin,time=f.time,provenance=f.provenance,
        ingestion=IngestionMetadata(repository_id=REPO,ingestion_sequence=index,ingested_at=AT+timedelta(days=1)),
        payload=p,payload_digest=c.digest(p),verification=f.verification,conflict=f.conflict,temporal_status=f.temporal_status,disclosures=disclosures)


def fixture(kind='medication_order',av='1.00',bv='2.00'):
    a=lab('A',av,AT); b=lab('B',bv,AT+timedelta(hours=2)); m=med(kind,at=AT+timedelta(hours=1))
    b=replace(b,provenance=replace(b.provenance,source=replace(b.provenance.source,identifier='sample-B')))
    facts=(a,b,m); items=tuple(mapped(f,n+1) for n,f in enumerate(facts))
    cutoff=RepositoryCutoff(repository_id=REPO,fact_watermark=3,captured_at=AT+timedelta(days=1))
    scope=PatientStateScope(patient_id='synthetic-p1',encounter_id='synthetic-e1',review_start=AT,review_end=AT+timedelta(hours=2),repository_cutoff=cutoff)
    assembled=assembly(*items,state_scope=scope)
    pins=tuple(m3.PatientStateSelectionPin(reference=x.reference,expected_digest=x.canonical_digest) for x in items)
    ir=m3.PatientStateTemporalRelationRequest(scope=scope,earlier_laboratory=pins[0],later_laboratory=pins[1],medication=pins[2],
        inference_id='I',executed_at=AT+timedelta(days=2))
    inference=m3.build_patient_state_temporal_inference(assembly=assembled,request=ir)
    request=c.PatientStateTemporalExecutionRequest(execution_id=UUID('10000000-0000-4000-8000-000000000001'),target=c.GRANT_TARGET,
        actor=c.GRANT_ACTOR,inference_request=ir,inference_cutoff=replace(cutoff,fact_watermark=4),expected_inference_digest=c.digest(inference),requested_at=START)
    ingestion=IngestionMetadata(repository_id=REPO,ingestion_sequence=4,ingested_at=AT+timedelta(days=2))
    evidence=c.PatientStateTemporalEvidence(request=request,items=items,facts=facts,inference=inference,inference_ingestion=ingestion)
    check=recheck(evidence)
    return evidence,check


def recheck(evidence):
    witnesses=tuple(c.PatientStateEvidenceWitness(role=role,consumed=i.reference,item_digest=i.canonical_digest,source_digest=c.digest(f),
        original_ingestion=i.ingestion,terminal=i.reference,terminal_source_digest=c.digest(f),terminal_ingestion=i.ingestion,suitability='established')
        for role,i,f in zip(('A','B','M'),evidence.items,evidence.facts,strict=True))
    inf=evidence.inference
    iw=c.PatientStateInferenceWitness(reference=inf.reference,expected_digest=c.digest(inf),observed_digest=c.digest(inf),
        ingestion=evidence.inference_ingestion,terminal=inf.reference,terminal_digest=c.digest(inf),terminal_ingestion=evidence.inference_ingestion,
        method=inf.method,inputs=inf.inputs,dependencies=inf.provenance.dependencies,declarations=inf.provenance.upstream,reconstruction_digest=c.digest(inf))
    return c.PatientStateTemporalFinalRecheck(scope=evidence.request.inference_request.scope,inference_cutoff=evidence.request.inference_cutoff,
        final_cutoff=evidence.request.inference_cutoff,evidence=witnesses,inference=iw)


def artifacts(evidence=None,check=None,*,actor=None,rendered=None):
    if evidence is None: evidence,check=fixture()
    if actor: evidence=replace(evidence,request=replace(evidence.request,actor=actor))
    request=evidence.request
    at=START+timedelta(seconds=1)
    validity=ValidityWindow(start=at,end=at+timedelta(seconds=30))
    snapshot=g.build_patient_state_temporal_context(evidence=evidence,patient=patient(),encounter=encounter(),at=at,id='context')
    candidate=g.build_patient_state_temporal_candidate(evidence=evidence,snapshot=snapshot,at=at,id='candidate')
    rendering=g.render_patient_state_temporal(candidate=candidate,target=request.target,at=at,id='rendering')
    if rendered is not None: rendering=replace(rendering,content=rendered)
    evaluation=g.evaluate_patient_state_temporal(evidence=evidence,recheck=check,snapshot=snapshot,candidate=candidate,rendering=rendering,target=request.target,at=at,id='safety')
    review=RecommendationReview(candidate=candidate,rendering=rendering,evaluations=(evaluation,))
    payload=required_payload(review,(),c.LIMITATIONS)
    validation=g.validate_patient_state_temporal_content(evidence=evidence,recheck=check,snapshot=snapshot,review=review,payload=payload,target=request.target,at=at,validity=validity,id='fidelity')
    freshness=g.assess_patient_state_temporal_context(evidence=evidence,recheck=check,snapshot=snapshot,at=at,validity=validity,id='freshness')
    dependencies=g.assess_patient_state_temporal_dependencies(evidence=evidence,recheck=check,snapshot=snapshot,validity=validity)
    policy=c.patient_state_temporal_policy(snapshot)
    decision_at=at+timedelta(seconds=1)
    authority=g.issue_synthetic_patient_state_temporal_authority(request=request,review=review,payload=payload,policy=policy,at=decision_at,id='authority')
    state=RuntimeState(target=request.target,identity=snapshot.binding.verification,request_state='active',output_state='current',
        observed_at=at,authorization=authority,freshness=freshness,dependencies=dependencies)
    assessment=assess_release(reference=c.ref('release_eligibility','assessment'),review=review,payload=payload,target=request.target,policy=policy,
        content_validation=validation,state=state,assessor=c.WORKFLOW,at=decision_at,validity=validity)
    decision=decide_release(reference=c.ref('release_decision','decision'),assessment=assessment,actor=request.actor,at=decision_at)
    record=c.PatientStateTemporalExecutionRecord(request=request,final_recheck=check,context_digest=c.digest(snapshot),decision=decision,
        runtime=c.PatientStateTemporalRuntime(started_at=START,observed_at=at,decision_at=decision_at,finalized_at=decision_at+timedelta(seconds=1)))
    return record,evidence


def changed(check,role):
    if role=='I':
        iw=check.inference
        iw=replace(iw,terminal=replace(iw.reference,version='2'),terminal_ingestion=replace(iw.ingestion,ingestion_sequence=5))
        return replace(check,inference=iw,final_cutoff=replace(check.final_cutoff,fact_watermark=5))
    n=('A','B','M').index(role); ws=list(check.evidence); w=ws[n]
    ws[n]=replace(w,terminal=replace(w.consumed,version='2'),terminal_ingestion=replace(w.original_ingestion,ingestion_sequence=5))
    return replace(check,evidence=tuple(ws),final_cutoff=replace(check.final_cutoff,fact_watermark=5))


def test_valid_release_and_preparation():
    record,evidence=artifacts()
    assert record.decision.outcome=='released' and record.decision.reasons==()
    assert evidence.request.inference_reference==Reference(kind='inference',id='I',version='1')
    assert record.final_recheck.outcome=='unchanged' and record.final_recheck.reasons==()
    assert len(record.decision.assessment.review.candidate.snapshot.facts)==4
    assert record.disposition=='completed_released'


@pytest.mark.parametrize('field,value',[('execution_id','bad'),('expected_inference_digest','bad'),('requested_at',AT.replace(tzinfo=None)),
    ('workflow','other'),('profile','other'),('final_cutoff',None),('final_recheck',None),('decision',None),('finalized_at',START),('ingested_at',START),
    ('runtime',{}),('inference',{}),('facts',()),('expected_inference_digest','A'*64)])
def test_bad_request_fields(field,value):
    e,_=fixture()
    with pytest.raises(c.PatientStateExecutionError): replace(e.request,**{field:value})


@pytest.mark.parametrize('part',['scope','repo','equal_prefix','earlier_prefix','requested_before_inference','duplicate_lab','wrong_med_kind','half_correction'])
def test_request_cross_bindings(part):
    e,_=fixture(); r=e.request
    if part=='scope': changes={'target':replace(r.target,context=replace(r.target.context,patient_id='foreign'))}
    elif part=='repo': changes={'inference_cutoff':replace(r.inference_cutoff,repository_id='00000000-0000-4000-8000-000000000002')}
    elif part in ('equal_prefix','earlier_prefix'): changes={'inference_cutoff':replace(r.inference_cutoff,fact_watermark=3 if part=='equal_prefix' else 2)}
    elif part=='requested_before_inference': changes={'requested_at':AT}
    elif part=='duplicate_lab': changes={'inference_request':replace(r.inference_request,later_laboratory=r.inference_request.earlier_laboratory)}
    elif part=='half_correction': changes={'inference_request':r.inference_request.model_copy(update={'correction_reason':'reason'})}
    else: changes={'inference_request':replace(r.inference_request,medication=replace(r.inference_request.medication,reference=r.inputs[0]))}
    with pytest.raises(c.PatientStateExecutionError): replace(r,**changes)


@pytest.mark.parametrize('part',['execution_id','actor','target_request','destination','recipient','pin_digest','pin_revision','inference_digest','requested_at','inference_cutoff','scope_time','executed_at','inference_id','revision','correction'])
def test_every_immutable_request_change_conflicts(part):
    e,_=fixture(); r=e.request; ir=r.inference_request
    if part=='execution_id': changes={'execution_id':UUID('20000000-0000-4000-8000-000000000001')}
    elif part=='actor': changes={'actor':'other'}
    elif part in ('target_request','destination','recipient'): changes={'target':replace(r.target,**{('request_id' if part=='target_request' else part):'other'})}
    elif part=='pin_digest': changes={'inference_request':replace(ir,earlier_laboratory=replace(ir.earlier_laboratory,expected_digest='0'*64))}
    elif part=='pin_revision': changes={'inference_request':replace(ir,earlier_laboratory=replace(ir.earlier_laboratory,reference=replace(ir.earlier_laboratory.reference,version='2')))}
    elif part=='inference_digest': changes={'expected_inference_digest':'0'*64}
    elif part=='requested_at': changes={'requested_at':r.requested_at+timedelta(seconds=1)}
    elif part=='inference_cutoff': changes={'inference_cutoff':replace(r.inference_cutoff,captured_at=START)}
    elif part=='scope_time': changes={'inference_request':replace(ir,scope=replace(ir.scope,review_start=AT-timedelta(seconds=1)))}
    elif part=='executed_at': changes={'inference_request':replace(ir,executed_at=ir.executed_at+timedelta(seconds=1))}
    elif part=='correction': changes={'inference_request':replace(ir,supersedes=Reference(kind='inference',id='I',version='0'),correction_reason='corrected')}
    else: changes={'inference_request':replace(ir,**{part:'other'})}
    other=replace(r,**changes)
    with pytest.raises(RecordConflict): c.require_patient_state_temporal_request_match(r,other)


def test_matcher_equal_objects_and_runtime_exclusion():
    record,_=artifacts(); r=record.request
    restored=c.PatientStateTemporalExecutionRequest.model_validate_json(canonical_payload(r))
    assert restored is not r
    c.require_patient_state_temporal_request_match(record,restored)
    changed_record=replace(record,runtime=replace(record.runtime,finalized_at=record.runtime.finalized_at+timedelta(seconds=1)))
    assert c.patient_state_temporal_request_projection(changed_record)==canonical_payload(r)


@pytest.mark.parametrize('role',['A','B','M','I'])
def test_same_displayed_content_successor_is_material(role):
    evidence,check=fixture(); final=changed(check,role)
    assert final.outcome=='materially_changed'
    assert final.reasons==(('inference' if role=='I' else role)+'_superseded',)
    record,_=artifacts(evidence,final)
    assert record.decision.outcome=='withheld'
    assert record.decision.assessment.review.candidate.snapshot.facts[-1].reference.version=='1'


@pytest.mark.parametrize('part',['digest','metadata','wrong_terminal_family','missing_terminal','backward_successor','duplicate_sequence','wrong_order','wrong_consumed','inference_digest','inference_method','inference_dependency','inference_missing'])
def test_witness_contradictions(part):
    e,ch=fixture(); w=ch.evidence[0]
    with pytest.raises(c.PatientStateExecutionError):
        if part=='digest': replace(w,terminal_source_digest='0'*64)
        elif part=='metadata': replace(w,terminal_ingestion=replace(w.original_ingestion,ingested_at=START))
        elif part=='wrong_terminal_family': replace(w,terminal=replace(w.terminal,id='other'))
        elif part=='missing_terminal': replace(w,terminal=None)
        elif part=='backward_successor': replace(w,terminal=replace(w.terminal,version='2'))
        elif part=='duplicate_sequence': replace(ch,evidence=(w,replace(ch.evidence[1],original_ingestion=w.original_ingestion,terminal_ingestion=w.original_ingestion),ch.evidence[2]))
        elif part=='wrong_order': replace(ch,evidence=(ch.evidence[1],w,ch.evidence[2]))
        elif part=='wrong_consumed': replace(ch,evidence=(replace(w,consumed=replace(w.consumed,version='0')),ch.evidence[1],ch.evidence[2]))
        elif part=='inference_digest': replace(ch.inference,terminal_digest='0'*64)
        elif part=='inference_method': replace(ch.inference,method=replace(ch.inference.method,version='2'))
        elif part=='inference_dependency': replace(ch.inference,dependencies=tuple(reversed(ch.inference.dependencies)))
        else: replace(ch.inference,terminal=None)


@pytest.mark.parametrize('part',['unavailable','failed','reconstruction_unavailable','reconstruction_mismatch'])
def test_final_assessment_outcomes(part):
    e,ch=fixture()
    if part.startswith('reconstruction'):
        ch=replace(ch,inference=replace(ch.inference,reconstruction_digest=None if part.endswith('unavailable') else '0'*64))
    else: ch=replace(ch,evidence=(replace(ch.evidence[0],suitability=part),*ch.evidence[1:]))
    assert ch.outcome==('unavailable' if part.endswith('unavailable') else 'materially_changed')
    assert artifacts(e,ch)[0].decision.outcome=='withheld'


@pytest.mark.parametrize('field',['outcome','reasons','unrelated_laboratory','unrelated_medication','unsupported_domain','mapping_issues','coverage','snapshot'])
def test_no_unrelated_state_or_success_flags(field):
    _,ch=fixture()
    with pytest.raises(c.PatientStateExecutionError): replace(ch,**{field:()})


@pytest.mark.parametrize('which',[0,1,2,3])
def test_unverified_admission_never_promoted(which):
    e,_=fixture(); facts=list(e.facts); items=list(e.items)
    fact=e.inference if which==3 else facts[which]
    bad=replace(fact,binding=replace(fact.binding,verification=replace(fact.binding.verification,status='unresolved',ambiguity='not authenticated')))
    if which==3:
        r=replace(e.request,expected_inference_digest=c.digest(bad))
        updates={'inference':bad,'request':r}
    else:
        facts[which]=bad; items[which]=replace(items[which],binding=bad.binding)
        updates={'facts':tuple(facts),'items':tuple(items)}
    before=canonical_payload(e)
    with pytest.raises(c.PatientStateExecutionError): replace(e,**updates)
    assert canonical_payload(e)==before


@pytest.mark.parametrize('part',['method','identity','digest','metadata','extra_dependency','reordered_dependencies','association','supersedes_dependency'])
def test_original_inference_binding(part):
    e,_=fixture(); i=e.inference
    with pytest.raises((c.PatientStateExecutionError,ValidationError)):
        if part=='method': i=replace(i,method=replace(i.method,version='2'))
        elif part=='identity': i=replace(i,id='other')
        elif part=='metadata': replace(e,inference_ingestion=replace(e.inference_ingestion,ingestion_sequence=3)); return
        elif part=='digest': replace(e,request=replace(e.request,expected_inference_digest='0'*64)); return
        else:
            extra=Reference(kind='medication_order' if part=='association' else 'inference' if part=='supersedes_dependency' else 'policy',id='extra',version='1')
            edges=tuple(reversed(i.provenance.upstream)) if part=='reordered_dependencies' else (*i.provenance.upstream,LineageEdge(target=extra,relationship='fulfills_order' if part=='association' else 'derived_from'))
            i=replace(i,provenance=replace(i.provenance,upstream=edges))
        replace(e,inference=i,request=replace(e.request,expected_inference_digest=c.digest(i)))


@pytest.mark.parametrize('kind',['medication_order','medication_administration'])
@pytest.mark.parametrize('av,bv,word',[('1.00','2.00','increased'),('2.00','1.00','decreased'),('-1.0','-1.00','was unchanged')])
def test_independent_six_grammar_families(kind,av,bv,word):
    e,ch=fixture(kind,av,bv); record,_=artifacts(e,ch)
    text=record.decision.assessment.review.rendering.content
    assert word in text
    ta='2026-09-25T15:30:00.123456+05:30'; tb='2026-09-25T17:30:00.123456+05:30'; tm='2026-09-25T16:30:00.123456+05:30'
    first=(f'Recorded serum creatinine was unchanged between the selected laboratory observations at {ta} and {tb} ({av} mg/dL then {bv} mg/dL).' if word=='was unchanged' else
        f'Recorded serum creatinine {word} from {av} mg/dL to {bv} mg/dL between the selected laboratory observations at {ta} and {tb}.')
    clause=(f'The selected medication order has a recorded event time of {tm}, strictly between those observations.' if kind=='medication_order' else
        f'The selected medication administration has a recorded administration time of {tm}, strictly between those observations.')
    assert text==first+' '+clause+' Temporal ordering does not establish clinical significance or cause. Synthetic evaluation only.'
    assert record.decision.outcome=='released'


@pytest.mark.parametrize('part',['causal','diagnosis','treatment','no_disclaimer','timestamp','scale','medication_kind','applicability','uncertainty','validation_limitation'])
def test_independent_fidelity_rejects_tampered_inference(part):
    e,_=fixture(); i=e.inference
    text={'causal':'Creatinine increased due to medication.','diagnosis':'AKI diagnosed.','treatment':'Stop medication.','no_disclaimer':i.statement.split(' Temporal ordering')[0],
          'timestamp':i.statement.replace('17:30','18:30'),'scale':i.statement.replace('1.00','1.0'),'medication_kind':i.statement.replace('medication order','medication administration')}.get(part)
    updates={'statement':text} if text else {'applicability':'patient wide'} if part=='applicability' else {'uncertainty':('missing source limitations',)} if part=='uncertainty' else {'validation_limitations':'validated'}
    i=replace(i,**updates); e=replace(e,inference=i,request=replace(e.request,expected_inference_digest=c.digest(i)))
    ch=recheck(e); record,_=artifacts(e,ch)
    assert record.decision.outcome=='withheld'
    assert record.decision.assessment.content_validation.outcome=='failed'
    assert record.decision.assessment.review.evaluations[0].outcome=='hard_failure'


def test_presentation_mismatch_and_authority_deny():
    assert artifacts(rendered='Changed presentation')[0].decision.outcome=='withheld'
    record,_=artifacts(actor='not-granted')
    assert record.decision.outcome=='withheld' and record.decision.assessment.state.authorization.outcome=='deny'


def test_roundtrip_deep_immutability_and_no_builder_during_decode(monkeypatch):
    record,_=artifacts(); raw=canonical_payload(record)
    def forbidden(*args,**kwargs): raise AssertionError('clinical producer called during decoding')
    monkeypatch.setattr(m3,'build_patient_state_temporal_inference',forbidden)
    monkeypatch.setattr(c,'patient_state_temporal_policy',forbidden)
    monkeypatch.setattr(g,'patient_state_temporal_policy',forbidden)
    for name in ('evaluate_patient_state_temporal','validate_patient_state_temporal_content','issue_synthetic_patient_state_temporal_authority','build_patient_state_temporal_context'):
        monkeypatch.setattr(g,name,forbidden)
    restored=c.PatientStateTemporalExecutionRecord.model_validate_json(raw)
    assert canonical_payload(restored)==raw
    c.require_patient_state_temporal_request_match(restored,record.request)
    for obj,field,value in ((restored,'context_digest','0'*64),(restored.request,'actor','other'),(restored.final_recheck.evidence[0],'suitability','failed')):
        with pytest.raises(ValidationError): setattr(obj,field,value)


@pytest.mark.parametrize('part',['context_digest','implementation','payload_version','actor','scope_pin','cutoff','inference_digest','chronology','workflow','final_recheck'])
def test_record_mutations(part):
    record,_=artifacts()
    with pytest.raises((c.PatientStateExecutionError,ValidationError)):
        if part=='context_digest': replace(record,context_digest='0'*64)
        elif part=='implementation': replace(record,implementation=replace(record.implementation,version='2'))
        elif part=='payload_version': replace(record,payload_version=True)
        elif part=='actor': replace(record,request=replace(record.request,actor='other'))
        elif part=='scope_pin': replace(record,request=replace(record.request,inference_request=replace(record.request.inference_request,earlier_laboratory=replace(record.request.inference_request.earlier_laboratory,expected_digest='0'*64))))
        elif part=='cutoff': replace(record,request=replace(record.request,inference_cutoff=replace(record.request.inference_cutoff,captured_at=START)))
        elif part=='inference_digest': replace(record,request=replace(record.request,expected_inference_digest='0'*64))
        elif part=='chronology': replace(record,runtime=replace(record.runtime,started_at=START+timedelta(days=1)))
        elif part=='workflow': replace(record,request=record.request.model_copy(update={'workflow':'other'}))
        else: replace(record,final_recheck=changed(record.final_recheck,'A'))


@pytest.mark.parametrize('field',['started_at','observed_at','decision_at','finalized_at'])
def test_runtime_invalid(field):
    record,_=artifacts()
    with pytest.raises(c.PatientStateExecutionError): replace(record.runtime,**{field:START.replace(tzinfo=None)})


def test_no_io_or_clock_in_production_modules():
    for module in (c,g):
        tree=ast.parse(Path(module.__file__).read_text())
        imports=[x.module for x in ast.walk(tree) if isinstance(x,ast.ImportFrom)]
        assert not any(any(s in (x or '') for s in ('repository','sqlalchemy','shared_transaction','workflow','creatinine','weight','patient_state_assembly')) for x in imports)
        calls=[ast.unparse(x.func) for x in ast.walk(tree) if isinstance(x,ast.Call)]
        assert not any(any(s in x for s in ('now','utcnow','capture_cutoff','transaction','connect','build_patient_state_temporal_inference','assemble_patient_state')) for x in calls)


def test_hash_seed_independence():
    code='from test_patient_state_execution import artifacts; from app.persistence.mapping import canonical_payload; print(canonical_payload(artifacts()[0]))'
    outputs=[subprocess.check_output([sys.executable,'-c',code],env={**os.environ,'PYTHONPATH':'backend:tests','PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'},text=True) for seed in ('1','17')]
    assert outputs[0]==outputs[1]


def test_mapping_correspondence_matches_existing_m2_pure_mapping():
    from app.execution.patient_state_assembly import _map
    e,_=fixture()
    for fact,item in zip(e.facts,e.items,strict=True):
        domain,mapped_item,issue=_map(StoredFact(fact,item.ingestion),e.request.inference_request.scope)
        assert issue is None and canonical_payload(mapped_item)==canonical_payload(item)


def rebuild_decision(record,assessment):
    decision=decide_release(reference=record.decision.reference,assessment=assessment,actor=record.request.actor,at=record.runtime.decision_at)
    return replace(record,decision=decision)


@pytest.mark.parametrize('part',['context_scope','fidelity_method','fidelity_assessor','freshness_digest','freshness_outcome','freshness_refs','policy','authority_issuer','authority_role','authority_window','runtime_identity','dependency_order','safety_rules','safety_override','observation_time'])
def test_retained_structural_assertion_tampering(part):
    record,_=artifacts(); a=record.decision.assessment
    with pytest.raises((c.PatientStateExecutionError,ValidationError)):
        if part=='context_scope':
            snap=replace(a.review.candidate.snapshot,completeness_scope='wrong')
            candidate=replace(a.review.candidate,snapshot=snap)
            a=replace(a,review=replace(a.review,candidate=candidate))
        elif part in ('fidelity_method','fidelity_assessor'):
            v=replace(a.content_validation,method=c.ref('content_validation_method','other')) if part=='fidelity_method' else replace(a.content_validation,assessor='other')
            a=replace(a,content_validation=v)
        elif part.startswith('freshness'):
            f=a.state.freshness
            if part=='freshness_digest': f=replace(f,rationale='different')
            elif part=='freshness_outcome': f=replace(f,adequate=False)
            else: f=replace(f,items=tuple(reversed(f.items)))
            a=replace(a,state=replace(a.state,freshness=f))
        elif part=='policy': a=replace(a,policy=replace(a.policy,max_assessment_age=timedelta(seconds=31)))
        elif part.startswith('authority'):
            auth=a.state.authorization
            auth=replace(auth,**({'issuer':'other'} if part=='authority_issuer' else {'role':'other'} if part=='authority_role' else {'validity':replace(auth.validity,end=auth.validity.end+timedelta(seconds=1))}))
            a=replace(a,state=replace(a.state,authorization=auth))
        elif part=='runtime_identity': a=replace(a,state=replace(a.state,identity=replace(a.state.identity,verifier='other')))
        elif part=='dependency_order': a=replace(a,state=replace(a.state,dependencies=tuple(reversed(a.state.dependencies))))
        elif part in ('safety_rules','safety_override'):
            ev=a.review.evaluations[0]; checks=list(ev.checks)
            checks[0]=replace(checks[0],rule=c.ref('safety_rule','other')) if part=='safety_rules' else replace(checks[0],outcome='warning',overrideable=True)
            a=replace(a,review=replace(a.review,evaluations=(replace(ev,checks=tuple(checks)),)))
        else: a=replace(a,state=replace(a.state,observed_at=a.state.observed_at+timedelta(seconds=1)))
        rebuild_decision(record,a)


def test_record_refuses_unbound_context_scope_even_when_digest_is_updated():
    record,_=artifacts(); a=record.decision.assessment
    snap=replace(a.review.candidate.snapshot,completeness_scope='arbitrary')
    review=replace(a.review,candidate=replace(a.review.candidate,snapshot=snap))
    a=replace(a,review=review)
    decision=decide_release(reference=record.decision.reference,assessment=a,actor=record.request.actor,at=record.runtime.decision_at)
    with pytest.raises(c.PatientStateExecutionError,match='context_mismatch'):
        replace(record,decision=decision,context_digest=c.digest(snap))


def test_record_refuses_forged_released_presentation_without_semantic_reconstruction():
    record,_=artifacts(); a=record.decision.assessment
    # Coherently rebind generic attestations to altered prose; M4 structural binding
    # must still prohibit a released claim differing from the retained inference.
    candidate=replace(a.review.candidate,claims=(replace(a.review.candidate.claims[0],action='unrelated output'),))
    rendering=replace(a.review.rendering,content='unrelated output')
    review=replace(a.review,candidate=candidate,rendering=rendering)
    payload=required_payload(review,(),c.LIMITATIONS)
    validation=replace(a.content_validation,content_digest=c.digest(review),payload_digest=c.digest(payload))
    auth=replace(a.state.authorization,content_digest=c.digest(review),payload_digest=c.digest(payload))
    a=replace(a,review=review,payload=payload,content_validation=validation,state=replace(a.state,authorization=auth))
    decision=decide_release(reference=record.decision.reference,assessment=a,actor=record.request.actor,at=record.runtime.decision_at)
    assert decision.outcome=='released'
    with pytest.raises(c.PatientStateExecutionError,match='released_content_mismatch'): replace(record,decision=decision)


@pytest.mark.parametrize('part',['A','B','M'])
@pytest.mark.parametrize('change',['provenance','event','status','value'])
def test_revision_change_always_material_without_successor_substitution(part,change):
    _,ch=fixture(); final=changed(ch,part)
    ws=list(final.evidence); n=('A','B','M').index(part)
    # The representation digest is opaque to the classifier; no value-based escape.
    ws[n]=replace(ws[n],terminal_source_digest={'provenance':'1','event':'2','status':'3','value':'4'}[change]*64)
    final=replace(final,evidence=tuple(ws))
    assert final.outcome=='materially_changed' and final.evidence[n].consumed.version=='1'


@pytest.mark.parametrize('part',['repo','future_original','future_terminal','cutoff_repo','cutoff_before_inference','method','policy','implementation'])
def test_recheck_prefix_and_marker_tampering(part):
    _,ch=fixture()
    with pytest.raises(c.PatientStateExecutionError):
        if part=='repo':
            w=ch.evidence[0]; meta=replace(w.original_ingestion,repository_id='00000000-0000-4000-8000-000000000099')
            replace(ch,evidence=(replace(w,original_ingestion=meta,terminal_ingestion=meta),*ch.evidence[1:]))
        elif part=='future_original':
            w=ch.evidence[0]; meta=replace(w.original_ingestion,ingestion_sequence=9)
            replace(ch,evidence=(replace(w,original_ingestion=meta,terminal_ingestion=meta),*ch.evidence[1:]))
        elif part=='future_terminal': replace(changed(ch,'A'),final_cutoff=ch.final_cutoff)
        elif part=='cutoff_repo': replace(ch,final_cutoff=replace(ch.final_cutoff,repository_id='00000000-0000-4000-8000-000000000099'))
        elif part=='cutoff_before_inference': replace(ch,final_cutoff=replace(ch.final_cutoff,fact_watermark=3))
        elif part=='method': replace(ch,inference=replace(ch.inference,method=c.ref('inference_method','other')))
        else: replace(ch,**{part:replace(getattr(ch,part),version='2')})


def test_metadata_model_copy_escape_hatch_revalidated():
    _,ch=fixture()
    bad=ch.evidence[0].original_ingestion.model_copy(update={'payload_version':True})
    with pytest.raises(c.PatientStateExecutionError): replace(ch.evidence[0],original_ingestion=bad,terminal_ingestion=bad)
    bad_cutoff=ch.final_cutoff.model_copy(update={'fact_watermark':True})
    with pytest.raises(c.PatientStateExecutionError): replace(ch,final_cutoff=bad_cutoff)


@pytest.mark.parametrize('part',['statement','applicability','uncertainty','conditions','warnings','basis','rationale','classification','extra_claim','knowledge_shape','destination'])
def test_candidate_and_presentation_fidelity_failures(part):
    record,e=artifacts(); a=record.decision.assessment; review=a.review; candidate=review.candidate
    claim=candidate.claims[0]
    if part=='destination': review=replace(review,rendering=replace(review.rendering,destination='other'))
    elif part=='extra_claim': review=replace(review,candidate=replace(candidate,claims=(claim,replace(claim,id='second'))))
    elif part=='knowledge_shape': review=replace(review,candidate=replace(candidate,monitoring=('treatment monitoring',)))
    else:
        updates={'statement':{'action':'other'},'applicability':{'conditions':('other',)},'uncertainty':{'uncertainty':()},
                 'conditions':{'conditions':()},'warnings':{'warnings':()},'basis':{'basis':(e.request.inputs[0],)},
                 'rationale':{'rationale':'cause'},'classification':{'classifications':('ai_inferred',)}}[part]
        review=replace(review,candidate=replace(candidate,claims=(replace(claim,**updates),)))
    result=g.validate_patient_state_temporal_content(evidence=e,recheck=record.final_recheck,snapshot=a.review.candidate.snapshot,
        review=review,payload=required_payload(review,(),c.LIMITATIONS),target=e.request.target,at=record.runtime.observed_at,
        validity=a.validity,id='new-fidelity')
    assert result.outcome=='failed'


def test_payload_disclosure_removed_fails():
    record,e=artifacts(); a=record.decision.assessment
    result=g.validate_patient_state_temporal_content(evidence=e,recheck=record.final_recheck,snapshot=a.review.candidate.snapshot,
        review=a.review,payload=replace(a.payload,limitations=()),target=e.request.target,at=record.runtime.observed_at,validity=a.validity,id='new')
    assert result.outcome=='failed'


def test_authority_expiry_pure_and_assessment_expiry_withholds():
    record,e=artifacts(); a=record.decision.assessment
    auth=g.issue_synthetic_patient_state_temporal_authority(request=e.request,review=a.review,payload=a.payload,policy=a.policy,at=c.GRANT_WINDOW.end,id='expired')
    assert auth.outcome=='deny'
    decision=decide_release(reference=c.ref('release_decision','late'),assessment=a,actor=e.request.actor,at=a.validity.end)
    assert decision.outcome=='withheld'


def test_record_validation_has_no_io_dynamic(monkeypatch):
    import app.persistence.repository as repository
    import app.execution.patient_state_assembly as assembler
    import sqlite3
    import time
    record,_=artifacts(); raw=canonical_payload(record)
    def forbidden(*args,**kwargs): raise AssertionError('forbidden runtime access')
    for obj,name in ((repository,'transaction'),(repository.PatientRepository,'load_latest_known'),(assembler,'assemble_patient_state'),
                     (m3,'build_patient_state_temporal_inference'),(sqlite3,'connect'),(time,'time'),(time,'monotonic')):
        monkeypatch.setattr(obj,name,forbidden)
    assert canonical_payload(c.PatientStateTemporalExecutionRecord.model_validate_json(raw))==raw


def test_errors_bounded_and_unknown_failures_not_withheld(monkeypatch):
    e,ch=fixture()
    with pytest.raises(c.PatientStateExecutionError) as err:
        c.PatientStateTemporalExecutionRequest.model_validate({'actor':'SECRET patient payload'})
    assert str(err.value)=='invalid_contract' and 'SECRET' not in str(err.value) and err.value.__cause__ is None
    def failure(*args,**kwargs): raise RuntimeError('programmer failure')
    monkeypatch.setattr(g,'_meaning',failure)
    with pytest.raises(RuntimeError): artifacts(e,ch)


def test_offsets_and_decimal_scale_preserved_in_retained_contract():
    record,e=artifacts(*fixture(av='-1.0000',bv='0.00'))
    raw=canonical_payload(record)
    assert '-1.0000' in raw and '+05:30' in raw
    assert canonical_payload(c.PatientStateTemporalExecutionRecord.model_validate_json(raw))==raw


def test_correction_metadata_stays_outside_dependencies():
    e,_=fixture(); i=e.inference
    prior=Reference(kind='inference',id=i.id,version='0')
    ir=replace(e.request.inference_request,supersedes=prior,correction_reason='recorded correction')
    i=replace(i,supersedes=prior,correction_reason='recorded correction')
    e=replace(e,inference=i,request=replace(e.request,inference_request=ir,expected_inference_digest=c.digest(i)))
    record,_=artifacts(e,recheck(e))
    assert record.decision.outcome=='released' and prior not in e.inference.provenance.dependencies


def test_released_payload_preserves_all_selected_disclosures():
    record,evidence=artifacts()
    payload=record.decision.released_payload
    assert payload is not None
    for text in (*evidence.inference.uncertainty,evidence.inference.applicability,evidence.inference.validation_limitations,*evidence.inference.provenance.limitations):
        assert text in payload.limitations
    assert len(payload.limitations)==len(set(payload.limitations))


def test_coherent_disclosure_removal_rejected_by_retained_validation():
    record,_=artifacts(); a=record.decision.assessment
    evaluation=replace(a.review.evaluations[0],limitations=c.LIMITATIONS)
    review=replace(a.review,evaluations=(evaluation,))
    payload=required_payload(review,(),c.LIMITATIONS)
    validation=replace(a.content_validation,limitations=c.LIMITATIONS,content_digest=c.digest(review),payload_digest=c.digest(payload))
    authority=replace(a.state.authorization,content_digest=c.digest(review),payload_digest=c.digest(payload))
    a=replace(a,review=review,payload=payload,content_validation=validation,state=replace(a.state,authorization=authority))
    with pytest.raises(c.PatientStateExecutionError,match='invalid_assertions'): rebuild_decision(record,a)
