"""M4.3 synthetic end-to-end protected workflow; real file-backed SQLite."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace as dc_replace
from datetime import timedelta, timezone
import ast
import json
from pathlib import Path
import traceback
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from app.execution import patient_state_workflow as w
from app.execution import patient_state_execution as c
from app.execution import patient_state_release as g
from app.execution.patient_state import PatientStateScope
from app.execution.patient_state_assembly import _assemble
from app.execution.patient_state_inference import PatientStateSelectionPin, PatientStateTemporalRelationRequest, build_patient_state_temporal_inference
from app.models.clinical.common import LineageEdge
from app.persistence.database import create_database
from app.persistence.errors import PersistenceInputError, RecordConflict, ScopeMismatch, StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown
from app.persistence.history import FactIdentity
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository, transaction
from app.persistence import patient_state_executions as store
from test_persistence import TARGET, AT, database, registered, replace, fact
from test_patient_state_assembly import lab, med
from test_revision_chains import revision

execute=w.execute_patient_state_temporal_review
reconcile=w.reconcile_patient_state_temporal_execution
TABLE='patient_state_temporal_execution'
START=c.GRANT_WINDOW.start


class Clock:
    def __init__(self,values=None):
        self.values=iter(values or [START+timedelta(seconds=n) for n in range(4)])
        self.calls=[]
    def __call__(self):
        value=next(self.values); self.calls.append(value); return value


def prepare(engine, *, kind='medication_order', extra=False, transform=None, actor=c.GRANT_ACTOR):
    a=lab('A','1.00',AT); b=lab('B','2.000',AT+timedelta(hours=2)); m=med(kind,at=AT+timedelta(hours=1))
    b=replace(b,provenance=replace(b.provenance,source=replace(b.provenance.source,identifier='sample-B')))
    with transaction(engine) as repo:
        for f in (a,b,m): repo.append_fact(f,target=TARGET)
        if extra: repo.append_fact(lab('unrelated-before','5.00',AT),target=TARGET)
        cutoff=repo.capture_cutoff()
        scope=PatientStateScope(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,review_start=AT,
            review_end=AT+timedelta(hours=2),repository_cutoff=cutoff)
        assembly=_assemble(repo,scope)
        items={i.reference:i for i in assembly.snapshot.ordered_items}
        pins=[PatientStateSelectionPin(reference=f.reference,expected_digest=items[f.reference].canonical_digest) for f in (a,b,m)]
        ir=PatientStateTemporalRelationRequest(scope=scope,earlier_laboratory=pins[0],later_laboratory=pins[1],medication=pins[2],
            inference_id='I',executed_at=AT+timedelta(days=1))
        inference=build_patient_state_temporal_inference(assembly=assembly,request=ir)
        if transform: inference=transform(inference)
        repo.append_fact(inference,target=TARGET)
        ic=repo.capture_cutoff()
    request=c.PatientStateTemporalExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=actor,
        inference_request=ir,inference_cutoff=ic,expected_inference_digest=c.digest(inference),requested_at=START)
    return request,(a,b,m,inference)


@pytest.fixture
def case(registered): return prepare(registered)


def count(engine):
    with engine.connect() as conn: return conn.execute(text('SELECT COUNT(*) FROM '+TABLE)).scalar_one()


def bounded(error):
    output=''.join(traceback.format_exception(error))
    assert error.__cause__ is None
    for secret in ('PRIVATE_SYNTHETIC','input_value=','SELECT ','INSERT INTO','"patient_id"'):
        assert secret not in output


@pytest.mark.parametrize('kind',['medication_order','medication_administration'])
@pytest.mark.parametrize('denied',[False,True])
def test_fresh_durable_minimal_exact_outcome(registered,kind,denied):
    request,facts=prepare(registered,kind=kind,actor='denied' if denied else c.GRANT_ACTOR)
    clock=Clock(); commits=[]
    def commit(conn): commits.append(True)
    event.listen(registered,'commit',commit)
    try: saved=execute(registered,request,clock=clock)
    finally: event.remove(registered,'commit',commit)
    assert commits==[True] and len(clock.calls)==4
    assert saved.record.decision.outcome==('withheld' if denied else 'released')
    assert saved.record.final_recheck.outcome=='unchanged'
    assert tuple(f.reference for f in saved.record.decision.assessment.review.candidate.snapshot.facts)==tuple(f.reference for f in facts)
    assert saved.record.decision.assessment.review.candidate.snapshot.completeness=='partial'
    assert saved.record.final_recheck.inference.inputs==request.inputs
    assert count(registered)==1
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==4
    registered.dispose(); reopened=create_database(registered.url.database)
    try:
        assert reconcile(reopened,request).stored==saved
        assert execute(reopened,request,clock=lambda:pytest.fail('retry clock'))==saved
    finally: reopened.dispose()
    with pytest.raises(ValidationError): saved.record.request.actor='other'


def forbid_fresh(monkeypatch):
    def forbidden(*a,**k): pytest.fail('retained path invoked fresh work')
    for name in ('_utc_now','_assemble','build_patient_state_temporal_inference','_final_recheck','_new_execution'):
        monkeypatch.setattr(w,name,forbidden)
    monkeypatch.setattr(c,'patient_state_temporal_policy',forbidden)
    for name in dir(g):
        if name.startswith(('build_','render_','evaluate_','validate_patient_','assess_','issue_')) or name=='patient_state_temporal_policy':
            monkeypatch.setattr(g,name,forbidden)
    for name in ('capture_cutoff','list_revisions','load_latest_known','list_latest_known','list_bounded_history','load_fact','resolve_lineage'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    monkeypatch.setattr(store,'_now',forbidden)
    return forbidden


@pytest.mark.parametrize('denied',[False,True])
def test_retry_and_reconciliation_no_recomputation_after_corrections(case,registered,monkeypatch,denied):
    request,facts=case
    if denied: request=replace(request,actor='denied')
    saved=execute(registered,request,clock=Clock())
    with transaction(registered) as repo:
        for f in facts: repo.append_revision(revision(f,'later'),target=TARGET)
    forbid_fresh(monkeypatch)
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        assert execute(registered,request)==saved
        result=reconcile(registered,request)
        assert result.status=='committed_match' and result.stored==saved
    finally: event.remove(registered,'before_cursor_execute',capture)
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) or 'FROM fact_revision' in s for s in statements)
    assert result.stored.record.runtime.finalized_at==saved.record.runtime.finalized_at
    assert result.stored.ingested_at==saved.ingested_at


@pytest.mark.parametrize('part',['actor','recipient','destination','request_id','requested_at','inference_digest','inference_cutoff_time',
    'input_cutoff_time','review_start','review_end','executed_at','inference_id','revision','correction','A_digest','B_digest','M_digest','A_ref','B_ref','M_ref'])
def test_exact_request_conflicts_before_work(case,registered,monkeypatch,part):
    request,_=case; execute(registered,request,clock=Clock()); ir=request.inference_request
    if part=='actor': changed=replace(request,actor='other')
    elif part in ('recipient','destination','request_id'): changed=replace(request,target=replace(request.target,**{part:'other'}))
    elif part=='requested_at': changed=replace(request,requested_at=request.requested_at+timedelta(seconds=1))
    elif part=='inference_digest': changed=replace(request,expected_inference_digest='0'*64)
    elif part=='inference_cutoff_time': changed=replace(request,inference_cutoff=replace(request.inference_cutoff,captured_at=AT))
    else:
        if part=='input_cutoff_time': ir=replace(ir,scope=replace(ir.scope,repository_cutoff=replace(ir.scope.repository_cutoff,captured_at=AT)))
        elif part in ('review_start','review_end'): ir=replace(ir,scope=replace(ir.scope,**{part:getattr(ir.scope,part)+timedelta(seconds=1)}))
        elif part=='executed_at': ir=replace(ir,executed_at=ir.executed_at+timedelta(seconds=1))
        elif part in ('inference_id','revision'): ir=replace(ir,**{part:'other'})
        elif part=='correction': ir=replace(ir,supersedes=replace(request.inference_reference,version='prior'),correction_reason='corrected')
        else:
            field={'A':'earlier_laboratory','B':'later_laboratory','M':'medication'}[part[0]]; pin=getattr(ir,field)
            pin=replace(pin,expected_digest='0'*64) if part.endswith('digest') else replace(pin,reference=replace(pin.reference,version='other'))
            ir=replace(ir,**{field:pin})
        changed=replace(request,inference_request=ir)
    forbid_fresh(monkeypatch)
    for op in (execute,reconcile):
        with pytest.raises(RecordConflict) as caught: op(registered,changed)
        bounded(caught.value)


def test_original_complete_assembly_once_and_targeted_final_reads(registered,monkeypatch):
    request,facts=prepare(registered,extra=True)
    with transaction(registered) as repo: repo.append_fact(lab('unrelated-after','7',AT),target=TARGET)
    seen=[]; assembly_fn=w._assemble; builder=w.build_patient_state_temporal_inference; terminal=PatientRepository.list_bounded_history
    def assembled(repo,scope,**reads):
        seen.append(('assembly',scope.repository_cutoff)); result=assembly_fn(repo,scope,**reads)
        assert len(result.snapshot.ordered_items)==4
        return result
    def build(**kw):
        seen.append(('builder',kw['assembly'].snapshot.scope.repository_cutoff))
        assert len(kw['assembly'].snapshot.ordered_items)==4
        return builder(**kw)
    def latest(repo,**kw):
        if kw.get('latest') and kw.get('identity') is not None:
            seen.append(('terminal',kw['identity']))
        return terminal(repo,**kw)
    monkeypatch.setattr(w,'_assemble',assembled); monkeypatch.setattr(w,'build_patient_state_temporal_inference',build)
    monkeypatch.setattr(PatientRepository,'list_bounded_history',latest)
    saved=execute(registered,request,clock=Clock())
    assert saved.record.decision.outcome=='released'
    assert seen[:2]==[('assembly',request.inference_request.scope.repository_cutoff),('builder',request.inference_request.scope.repository_cutoff)]
    assert seen[2:]==[('terminal',FactIdentity(kind=f.kind,id=f.id)) for f in facts]
    assert saved.record.final_recheck.final_cutoff.fact_watermark==6


@pytest.mark.parametrize('role',[0,1,2,3])
@pytest.mark.parametrize('change',['same','provenance','event'])
def test_selected_successors_material_without_substitution(case,registered,role,change):
    request,facts=case; f=facts[role]; successor=revision(f,'2')
    if change=='provenance': successor=replace(successor,provenance=replace(successor.provenance,actor='corrected'))
    if change=='event':
        if f.kind=='medication_administration': successor=replace(successor,administered_at=f.time.event+timedelta(minutes=1),time=replace(f.time,event=f.time.event+timedelta(minutes=1)))
        else: successor=replace(successor,time=replace(f.time,event=f.time.event+timedelta(minutes=1)))
    with transaction(registered) as repo: repo.append_revision(successor,target=TARGET)
    saved=execute(registered,request,clock=Clock()); check=saved.record.final_recheck
    assert check.outcome=='materially_changed' and saved.record.decision.outcome=='withheld'
    assert tuple(f.reference for f in saved.record.decision.assessment.review.candidate.snapshot.facts)==tuple(f.reference for f in facts)
    assert check.inference.inputs==request.inputs
    assert ('inference_superseded' if role==3 else ('A','B','M')[role]+'_superseded') in check.reasons


def test_medication_status_successor_material(case,registered):
    request,facts=case
    with transaction(registered) as repo: repo.append_revision(replace(revision(facts[2],'2'),order_status='held'),target=TARGET)
    assert execute(registered,request,clock=Clock()).record.decision.outcome=='withheld'


@pytest.mark.parametrize('kind',['lab','medication','unsupported','mapping_issue','malformed_unrelated'])
def test_unrelated_final_changes_do_not_affect_review(case,registered,kind):
    request,_=case
    f=lab('unrelated','9',AT) if kind=='lab' else med('medication_order',at=AT) if kind=='medication' else fact(id='unrelated')
    if kind=='medication': f=replace(f,id='unrelated-med')
    if kind=='mapping_issue': f=replace(lab('unrelated','9',AT),time=replace(f.time,event=None))
    with transaction(registered) as repo: repo.append_fact(f,target=TARGET)
    if kind=='malformed_unrelated':
        with registered.begin() as conn: conn.execute(text("UPDATE fact_revision SET payload='PRIVATE_SYNTHETIC' WHERE fact_id='unrelated'"))
    saved=execute(registered,request,clock=Clock())
    assert saved.record.decision.outcome=='released' and saved.record.final_recheck.outcome=='unchanged'
    assert len(saved.record.decision.assessment.review.candidate.snapshot.facts)==4


@pytest.mark.parametrize('part',['statement','applicability','uncertainty','limitations'])
def test_well_formed_semantic_mismatch_withholds(registered,part):
    def transform(i):
        changes={'statement':{'statement':'Synthetic causal claim'},'applicability':{'applicability':'different'},
            'uncertainty':{'uncertainty':('different',)},'limitations':{'validation_limitations':'different'}}
        return replace(i,**changes[part])
    request,_=prepare(registered,transform=transform)
    saved=execute(registered,request,clock=Clock())
    assert saved.record.decision.outcome=='withheld'
    assert saved.record.final_recheck.inference.reconstruction=='mismatch'
    assert saved.record.decision.assessment.content_validation.outcome=='failed'


@pytest.mark.parametrize('part',['method','dependencies','edges','scope'])
def test_contradictory_original_inference_aborts(registered,part):
    def transform(i):
        if part=='method': return replace(i,method=replace(i.method,version='2'))
        if part=='scope': return replace(i,binding=replace(i.binding,target=replace(TARGET,encounter_id='synthetic-e2')))
        if part=='dependencies': return replace(i,inputs=tuple(reversed(i.inputs)),provenance=replace(i.provenance,upstream=tuple(reversed(i.provenance.upstream))))
        return replace(i,provenance=replace(i.provenance,upstream=tuple(LineageEdge(target=x,relationship='copied_from') for x in i.inputs)))
    if part=='scope':
        # Storage itself rejects a contradictory supplied scope before workflow.
        with pytest.raises(ScopeMismatch): prepare(registered,transform=transform)
        return
    request,_=prepare(registered,transform=transform)
    with pytest.raises(StorageIntegrityError): execute(registered,request,clock=Clock())
    assert count(registered)==0


@pytest.mark.parametrize('part',['missing_inference','malformed_inference','bad_digest','malformed_selected','broken_chain'])
def test_integrity_never_becomes_withhold(case,registered,part):
    request,facts=case
    if part=='bad_digest': request=replace(request,expected_inference_digest='0'*64)
    else:
        with registered.begin() as conn:
            if part=='missing_inference': conn.execute(text("DELETE FROM fact_revision WHERE kind='inference'"))
            elif part=='malformed_inference': conn.execute(text("UPDATE fact_revision SET payload='PRIVATE_SYNTHETIC' WHERE kind='inference'"))
            elif part=='malformed_selected': conn.execute(text("UPDATE fact_revision SET payload='PRIVATE_SYNTHETIC' WHERE fact_id='A'"))
        if part=='broken_chain':
            with transaction(registered) as repo: repo.append_revision(revision(facts[0],'2'),target=TARGET)
            with registered.begin() as conn: conn.execute(text('DELETE FROM revision_link'))
    with pytest.raises(StorageIntegrityError) as caught: execute(registered,request,clock=Clock())
    bounded(caught.value); assert count(registered)==0


@pytest.mark.parametrize('part',['content','metadata','missing'])
def test_contradictory_final_exact_evidence_aborts(case,registered,monkeypatch,part):
    request,_=case; original=PatientRepository.list_bounded_history
    def altered(repo,**kw):
        result=original(repo,**kw)
        if kw.get('latest') and kw.get('identity') is not None and kw['identity'].id=='A':
            if part=='missing': return dc_replace(result,records=())
            stored=result.records[0]
            stored=dc_replace(stored,fact=replace(stored.fact,uncertainty=('different',))) if part=='content' else dc_replace(stored,ingestion=replace(stored.ingestion,ingested_at=AT))
            result=dc_replace(result,records=(stored,))
        return result
    monkeypatch.setattr(PatientRepository,'list_bounded_history',altered)
    with pytest.raises(StorageIntegrityError): execute(registered,request,clock=Clock())
    assert count(registered)==0


@pytest.mark.parametrize('part',['expired_authority','expired_assessment','backward','naive'])
def test_runtime_policy_and_invalid_clocks(case,registered,part):
    request,_=case
    values=[START+timedelta(seconds=n) for n in range(4)]
    if part=='expired_authority': values=[c.GRANT_WINDOW.end+timedelta(seconds=n) for n in range(4)]
    elif part=='expired_assessment': values[2:]=[START+timedelta(seconds=40),START+timedelta(seconds=41)]
    elif part=='backward': values[2]=START
    else: values[1]=values[1].replace(tzinfo=None)
    if part in ('backward','naive'):
        with pytest.raises(TransactionAborted): execute(registered,request,clock=Clock(values))
        assert count(registered)==0
    else: assert execute(registered,request,clock=Clock(values)).record.decision.outcome=='withheld'


@pytest.mark.parametrize('stage',['builder','safety','fidelity','freshness','authority','append','after_append','poison','interrupt'])
def test_failures_rollback(case,registered,monkeypatch,stage):
    request,_=case
    def fail(*a,**k): raise RuntimeError('PRIVATE_SYNTHETIC')
    if stage=='builder': monkeypatch.setattr(w,'build_patient_state_temporal_inference',fail)
    elif stage in ('safety','fidelity','freshness','authority'):
        name={'safety':'evaluate_patient_state_temporal','fidelity':'validate_patient_state_temporal_content',
            'freshness':'assess_patient_state_temporal_context','authority':'issue_synthetic_patient_state_temporal_authority'}[stage]
        monkeypatch.setattr(g,name,fail)
    else:
        original=store._PatientStateExecutionAdapter.append
        def append(handle,*a,**k):
            if stage=='append': fail()
            saved=original(handle,*a,**k)
            if stage=='poison': handle._lifecycle.fail(); return saved
            if stage=='interrupt': raise KeyboardInterrupt()
            fail()
        monkeypatch.setattr(store._PatientStateExecutionAdapter,'append',append)
    with pytest.raises(KeyboardInterrupt if stage=='interrupt' else TransactionAborted) as caught:
        execute(registered,request,clock=Clock())
    if stage!='interrupt': bounded(caught.value)
    assert count(registered)==0
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==4


@pytest.mark.parametrize('when',['before','after'])
def test_uncertain_completion_requires_explicit_reconciliation(case,registered,monkeypatch,when):
    request,_=case; original=registered.dialect.do_commit
    def fail(connection):
        if when=='after': original(connection)
        raise OperationalError('PRIVATE_SYNTHETIC',{},Exception('PRIVATE_SYNTHETIC'))
    monkeypatch.setattr(registered.dialect,'do_commit',fail)
    with pytest.raises(TransactionCompletionUnknown) as caught: execute(registered,request,clock=Clock())
    bounded(caught.value)
    monkeypatch.setattr(registered.dialect,'do_commit',original)
    forbid_fresh(monkeypatch)
    result=reconcile(registered,request)
    assert result.status==('absent' if when=='before' else 'committed_match')


def test_reconciliation_absence_is_not_execution(case,registered,monkeypatch):
    request,_=case; forbid_fresh(monkeypatch)
    assert reconcile(registered,request).status=='absent' and count(registered)==0
    with pytest.raises(ValidationError): w.PatientStateTemporalReconciliationResult(status='committed_match',stored=None)


def test_foreign_corruption_hidden_visible_corruption_fails(case,registered,monkeypatch):
    request,_=case; execute(registered,request,clock=Clock())
    with registered.begin() as conn: conn.execute(text('UPDATE '+TABLE+" SET payload='PRIVATE_SYNTHETIC'"))
    ir=request.inference_request
    foreign=replace(request,target=replace(request.target,context=replace(TARGET,encounter_id='synthetic-e2')),
        inference_request=replace(ir,scope=replace(ir.scope,encounter_id='synthetic-e2')))
    forbid_fresh(monkeypatch)
    assert reconcile(registered,foreign).status=='absent'
    with pytest.raises(StorageIntegrityError) as caught: reconcile(registered,request)
    bounded(caught.value)


@pytest.mark.parametrize('mode',['same','different','other_id','correction'])
def test_writer_lock_protects_prefix_and_serialized_retry(case,registered,mode):
    request,facts=case; other=create_database(registered.url.database)
    event.listen(other,'connect',lambda dbapi,_:dbapi.execute('PRAGMA busy_timeout=0'))
    attempted=[]; clock=Clock()
    second=replace(request,actor='other') if mode=='different' else replace(request,execution_id=uuid4()) if mode=='other_id' else request
    def correction():
        with transaction(other) as repo: repo.append_revision(revision(facts[0],'2'),target=TARGET)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            def protected_clock():
                if not attempted:
                    attempted.append(True)
                    future=pool.submit(correction if mode=='correction' else lambda:execute(other,second,clock=Clock()))
                    with pytest.raises(OperationalError if mode=='correction' else TransactionAborted): future.result(timeout=10)
                return clock()
            saved=execute(registered,request,clock=protected_clock)
        assert saved.record.decision.outcome=='released' and saved.record.final_recheck.final_cutoff.fact_watermark==4
        if mode=='different':
            with pytest.raises(RecordConflict): execute(other,second,clock=Clock())
        elif mode=='correction':
            correction(); assert execute(other,request,clock=lambda:pytest.fail('retry work'))==saved
            assert execute(other,replace(request,execution_id=uuid4()),clock=Clock()).record.decision.outcome=='withheld'
        else:
            again=execute(other,second,clock=Clock())
            if mode=='same': assert again==saved
        assert count(registered)==(2 if mode in ('other_id','correction') else 1)
    finally: other.dispose()


def test_public_surface_and_no_automatic_recovery():
    tree=ast.parse(Path(w.__file__).read_text())
    reconcile_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='reconcile_patient_state_temporal_execution')
    calls={n.func.id for n in ast.walk(reconcile_node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
    assert calls=={'_validate_request','find_patient_state_temporal_execution','PatientStateTemporalReconciliationResult','next','isinstance','category','TransactionAborted'}
    source=Path(w.__file__).read_text()
    assert 'append_fact(' not in source and 'append_revision(' not in source and 'assemble_patient_state(' not in source


def test_exact_order_one_cutoff_one_connection_and_commit(case,registered,monkeypatch):
    request,_=case; sequence=[]; connections=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        connections.append(id(conn))
        if statement=='BEGIN IMMEDIATE': sequence.append('begin')
        elif statement.startswith('INSERT INTO '+TABLE): sequence.append('append')
    def commit(conn): sequence.append('commit')
    def wrap(obj,name,label):
        original=getattr(obj,name)
        def call(*a,**k): sequence.append(label); return original(*a,**k)
        monkeypatch.setattr(obj,name,call)
    wrap(store._PatientStateExecutionAdapter,'find','lookup')
    wrap(PatientRepository,'capture_cutoff','cutoff')
    wrap(w,'_assemble','assembly')
    wrap(w,'build_patient_state_temporal_inference','builder')
    wrap(w,'_final_recheck','recheck')
    wrap(g,'build_patient_state_temporal_context','context')
    wrap(g,'issue_synthetic_patient_state_temporal_authority','authority')
    wrap(w,'decide_release','decision')
    times=Clock()
    def clock(): sequence.append('clock'); return times()
    event.listen(registered,'before_cursor_execute',capture); event.listen(registered,'commit',commit)
    try: execute(registered,request,clock=clock); sequence.append('returned')
    finally: event.remove(registered,'before_cursor_execute',capture); event.remove(registered,'commit',commit)
    assert sequence==['begin','lookup','clock','cutoff','assembly','builder','recheck','clock','context','clock','authority','decision','clock','append','commit','returned']
    assert len(set(connections))==1


@pytest.mark.parametrize('part',['workflow','profile','raw','bool_version'])
def test_malformed_requests_rejected_before_transaction(case,registered,monkeypatch,part):
    request,_=case
    if part=='raw': request=request.model_dump()
    elif part=='bool_version': request=request.model_copy(update={'inference_cutoff':request.inference_cutoff.model_copy(update={'fact_watermark':True})})
    else: request=request.model_copy(update={part:'unsupported'})
    monkeypatch.setattr(w,'execution_transaction',lambda *a:pytest.fail('invalid request opened transaction'))
    for op in (execute,reconcile):
        with pytest.raises(PersistenceInputError): op(registered,request)


@pytest.mark.parametrize('part',['repository','watermark'])
def test_final_prefix_cannot_precede_or_change_repository(case,registered,monkeypatch,part):
    request,_=case; original=PatientRepository.capture_cutoff
    def capture(repo):
        cutoff=original(repo)
        return replace(cutoff,**({'repository_id':uuid4()} if part=='repository' else {'fact_watermark':0}))
    monkeypatch.setattr(PatientRepository,'capture_cutoff',capture)
    with pytest.raises(StorageIntegrityError): execute(registered,request,clock=Clock())
    assert count(registered)==0


@pytest.mark.parametrize('part',['unavailable','failed'])
def test_typed_final_suitability_withholds(case,registered,monkeypatch,part):
    request,_=case; original=w._final_recheck
    def check(*a,**k):
        result=original(*a,**k); first,*rest=result.evidence
        return replace(result,evidence=(replace(first,suitability=part),*rest))
    monkeypatch.setattr(w,'_final_recheck',check)
    saved=execute(registered,request,clock=Clock())
    assert saved.record.decision.outcome=='withheld'
    assert saved.record.final_recheck.outcome==('unavailable' if part=='unavailable' else 'materially_changed')


@pytest.mark.parametrize('operation',['execute','reconcile'])
def test_corrupted_retained_row_aborts_before_fresh_work(case,registered,monkeypatch,operation):
    request,_=case; execute(registered,request,clock=Clock())
    with registered.begin() as conn: conn.execute(text('UPDATE '+TABLE+" SET payload_digest='bad'"))
    forbid_fresh(monkeypatch)
    with pytest.raises(StorageIntegrityError) as caught: (execute if operation=='execute' else reconcile)(registered,request)
    bounded(caught.value)


def test_unverified_binding_admission_is_not_invented(registered):
    def transform(i):
        return replace(i,binding=replace(i.binding,verification=replace(i.binding.verification,status='unresolved',ambiguity='synthetic ambiguity')))
    request,_=prepare(registered,transform=transform)
    from app.persistence.errors import UnsupportedOperation
    with pytest.raises(UnsupportedOperation): execute(registered,request,clock=Clock())
    assert count(registered)==0


def test_absence_allows_only_explicit_fresh_execution(case,registered):
    request,_=case
    assert reconcile(registered,request).status=='absent' and count(registered)==0
    saved=execute(registered,request,clock=Clock())
    assert reconcile(registered,request).stored==saved
