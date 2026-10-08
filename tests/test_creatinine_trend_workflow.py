"""Protected D4 composition against real synthetic SQLite history."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace as dc_replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import ast
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.execution import creatinine_trend_workflow as workflow
from app.execution.creatinine_trend import CreatinineTrendExclusion
from app.execution.creatinine_trend_execution import (
    CreatinineTrendReviewRequest, creatinine_trend_lineage_witness, creatinine_trend_request_projection,
)
from app.execution.creatinine_trend_release import GRANT_WINDOW
from app.persistence import creatinine_executions as store
from app.persistence.database import create_database
from app.persistence.errors import (
    PersistenceInputError, QueryLimitExceeded, RecordConflict, RecordNotFound, SchemaMismatch, StorageIntegrityError, UnsupportedOperation,
    TransactionAborted, TransactionCompletionUnknown,
)
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository, transaction
from test_persistence import ROOT, TARGET, AT, database, registered, replace
from test_revision_chains import revision
from test_creatinine_trend import creatinine, changed_unit, POLICY
from test_creatinine_trend_release import case, evidence, partial_graph
from test_creatinine_trend_execution import request_for as base_request
from test_creatinine_trend_execution_persistence import row
from test_weight_trend_shared_transaction import trace, private, SECRET

TIME=GRANT_WINDOW.start+timedelta(seconds=1)


def request_for(case,**updates):
    return replace(base_request(case),execution_id=uuid4(),requested_at=TIME-timedelta(seconds=1),**updates)


def run(engine,request,clock=None):
    return workflow.execute_creatinine_trend_review(engine,request,clock=(lambda:TIME) if clock is None else clock)


def counts(engine):
    conn=sqlite3.connect(f'file:{engine.url.database}?mode=ro',uri=True,timeout=0)
    try:
        return tuple(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                     for table in ('fact_revision','creatinine_trend_execution'))
    finally: conn.close()


def change(engine,case,kind):
    a=case['selection'].selected[0]
    if kind in ('value','same_value','unit','unverified','conflict','provenance','availability'):
        altered=revision(a,'corrected')
        if kind=='value': altered=replace(altered,value=replace(a.value,value=replace(a.value.value,value=Decimal('1.1'))))
        elif kind=='unit': altered=changed_unit(altered,raw='µmol/L',code='umol/L')
        elif kind=='unverified': altered=replace(altered,verification='unverified')
        elif kind=='conflict': altered=replace(altered,conflict='unresolved')
        elif kind=='provenance': altered=replace(altered,provenance=replace(altered.provenance,limitations=('synthetic unknown source',)))
        elif kind=='availability': altered=replace(altered,time=replace(altered.time,processed=POLICY.available_at+timedelta(microseconds=1)))
        with transaction(engine) as repo: repo.append_revision(altered,target=TARGET)
    elif kind=='inference':
        with transaction(engine) as repo: repo.append_revision(revision(case['inference'],'corrected'),target=TARGET)
    else:
        extra=creatinine('extra','1.30',AT+timedelta(hours=2),sample='sample-a' if kind=='duplicate' else 'sample-extra')
        if kind=='unrelated': extra=replace(extra,concept_id='potassium')
        elif kind=='outside': extra=creatinine('outside',at=POLICY.window_end)
        with transaction(engine) as repo: repo.append_fact(extra,target=TARGET)


@pytest.mark.parametrize('actor,outcome',[('synthetic-creatinine-orchestrator','released'),('denied','withheld')])
def test_fresh_execution_exact_evidence_and_commit(case,registered,monkeypatch,actor,outcome):
    request=request_for(case,actor=actor)
    ticks=iter(TIME+timedelta(seconds=i) for i in range(4))
    captured=[]
    capture=PatientRepository.capture_cutoff
    def observe(repo):
        result=capture(repo); captured.append(result); return result
    monkeypatch.setattr(PatientRepository,'capture_cutoff',observe)
    with trace(registered) as events:
        saved=run(registered,request,lambda:next(ticks))
        assert events['commits']==1 and events['rollbacks']==0
        assert events['sql'].count('BEGIN IMMEDIATE')==1 and len(events['connections'])==1
        assert not any(s.startswith(('UPDATE','DELETE','INSERT INTO fact_revision')) for s in events['sql'])
    record=saved.record
    assert record.decision.outcome==outcome
    assert canonical_payload(record.request)==canonical_payload(request)
    assert canonical_payload(record.lineage)==canonical_payload(request.lineage)
    assert record.original.selected==tuple(f.reference for f in case['selection'].selected)
    assert record.inference==case['inference'].reference
    assert record.comparison==case['comparison']
    assert [str(record.comparison.earlier_value),str(record.comparison.later_value)]==['1.00','1.20']
    assert record.final_recheck.outcome=='unchanged'
    assert record.final_recheck.inference_terminal.status=='current'
    assert canonical_payload(record.final_recheck.final.cutoff)==canonical_payload(captured[0])
    assert record.requested_at==request.requested_at and record.started_at==TIME
    assert record.finalized_at==TIME+timedelta(seconds=3)
    assessment=record.decision.assessment
    assert assessment.review.candidate.created_at==TIME+timedelta(seconds=1)
    assert record.decision.at==assessment.state.authorization.issued_at==TIME+timedelta(seconds=2)
    assert assessment.assessor=='SyntheticCreatinineProtectedExecution/v1'
    assert assessment.state.freshness.assessor=='SyntheticCreatinineFinalContext/v1'
    assert 'recheck='+sha256(canonical_payload(record.final_recheck).encode()).hexdigest() in assessment.state.freshness.rationale
    if outcome=='released':
        assert assessment.content_validation.outcome=='matched' and record.decision.reasons==()
    assert counts(registered)==(3,1)
    assert store.load_creatinine_trend_execution(registered,request.execution_id,target=TARGET)==saved
    registered.dispose()
    reopened=create_database(registered.url.database)
    try: assert store.load_creatinine_trend_execution(reopened,request.execution_id,target=TARGET)==saved
    finally: reopened.dispose()


@pytest.mark.parametrize('kind',['value','same_value','third','duplicate','unit','unverified','conflict','provenance','availability','inference'])
def test_material_change_durably_withholds_without_replacement(case,registered,kind):
    request=request_for(case)
    change(registered,case,kind)
    before=counts(registered)[0]
    saved=run(registered,request)
    record=saved.record
    assert record.decision.outcome=='withheld'
    assert record.final_recheck.outcome=='materially_changed'
    assert record.decision.assessment.state.freshness.material_change
    assert not record.decision.assessment.state.freshness.adequate
    assert record.decision.assessment.content_validation.outcome=='matched'
    assert all(c.outcome=='no_detected_violation' for e in record.decision.assessment.review.evaluations for c in e.checks)
    assert canonical_payload(record.request)==canonical_payload(request)
    assert record.decision.assessment.review.candidate.snapshot.facts[-1]==case['inference']
    assert record.comparison==request.comparison and record.inference==request.inference
    assert counts(registered)==(before,1)
    assert store.load_creatinine_trend_execution(registered,request.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('kind',['unrelated','outside','execution'])
def test_benign_growth_does_not_material_change(case,registered,kind):
    request=request_for(case)
    if kind=='execution': run(registered,request_for(case))
    else: change(registered,case,kind)
    saved=run(registered,request)
    assert saved.record.final_recheck.outcome=='unchanged' and saved.record.decision.outcome=='released'
    assert saved.record.final_recheck.final.cutoff.fact_watermark==(3 if kind=='execution' else 4)


@pytest.mark.parametrize('kind',['hard_failure','unavailable','fidelity','context','dependency','missing_safety','missing_dependencies','authority_digest','runtime'])
def test_governance_inadequacy_is_completed_withholding(case,registered,monkeypatch,kind):
    if kind in ('hard_failure','unavailable','missing_safety'):
        original=workflow.evaluate_creatinine_trend
        def altered(**kw):
            result=original(**kw)
            if kind=='missing_safety': return replace(result,checks=result.checks[:1])
            check=replace(result.checks[0],outcome=kind,reason='Synthetic negative producer evidence')
            return replace(result,checks=(check,*result.checks[1:]),exact_meaning='failed' if kind=='hard_failure' else 'unavailable')
        monkeypatch.setattr(workflow,'evaluate_creatinine_trend',altered)
    elif kind=='fidelity':
        original=workflow.validate_creatinine_trend_content
        monkeypatch.setattr(workflow,'validate_creatinine_trend_content',lambda **kw:replace(original(**kw),outcome='failed'))
    elif kind=='context':
        original=workflow.assess_creatinine_trend_final_context
        monkeypatch.setattr(workflow,'assess_creatinine_trend_final_context',lambda **kw:replace(original(**kw),adequate=False))
    elif kind in ('dependency','missing_dependencies'):
        original=workflow.assess_creatinine_trend_dependencies
        def altered(**kw):
            result=original(**kw)
            return () if kind=='missing_dependencies' else (replace(result[0],state='unavailable',validity=None),*result[1:])
        monkeypatch.setattr(workflow,'assess_creatinine_trend_dependencies',altered)
    elif kind=='authority_digest':
        original=workflow.issue_synthetic_creatinine_release
        monkeypatch.setattr(workflow,'issue_synthetic_creatinine_release',lambda **kw:replace(original(**kw),content_digest='0'*64))
    else:
        original=workflow.assemble_creatinine_trend_runtime
        monkeypatch.setattr(workflow,'assemble_creatinine_trend_runtime',lambda **kw:replace(original(**kw),output_state='stale'))
    saved=run(registered,request_for(case))
    assert saved.record.decision.outcome=='withheld'
    assert store.load_creatinine_trend_execution(registered,saved.record.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('time',[GRANT_WINDOW.start-timedelta(seconds=1),GRANT_WINDOW.end,GRANT_WINDOW.end+timedelta(days=1)])
def test_fixed_authority_window_not_extended(case,registered,time):
    request=replace(request_for(case),requested_at=time-timedelta(seconds=1))
    saved=run(registered,request,lambda:time)
    assert saved.record.decision.outcome=='withheld'
    assert saved.record.decision.assessment.state.authorization.outcome=='deny'
    assert saved.record.decision.assessment.state.authorization.validity==GRANT_WINDOW


def test_expiry_between_observation_and_decision_withholds(case,registered):
    ticks=iter((TIME,TIME,TIME+timedelta(seconds=31),TIME+timedelta(seconds=31)))
    result=run(registered,request_for(case),lambda:next(ticks))
    assert result.record.decision.outcome=='withheld'


def forbid_work(monkeypatch):
    def forbidden(*args,**kwargs): pytest.fail('retained retry performed clinical work or sampled clock')
    for name in ('capture_cutoff','resolve_lineage','list_history','list_latest_known','load_latest_known','load_fact'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    for name in ('_new_execution','_tick','select_creatinine_observations','assess_creatinine_trend_final_recheck',
                 'build_creatinine_trend_snapshot','evaluate_creatinine_trend','assess_release','decide_release'):
        monkeypatch.setattr(workflow,name,forbidden)
    return forbidden


@pytest.mark.parametrize('variant',['released','withheld'])
@pytest.mark.parametrize('later',['same_value','inference','unrelated'])
def test_exact_retry_skips_all_new_work(case,registered,monkeypatch,variant,later):
    request=request_for(case,actor='denied' if variant=='withheld' else 'synthetic-creatinine-orchestrator')
    saved=run(registered,request)
    change(registered,case,later)
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='{}' WHERE ingestion_sequence=4"))
    before=row(registered)
    forbidden=forbid_work(monkeypatch)
    with trace(registered) as events: again=run(registered,request,forbidden)
    assert canonical_payload(again)==canonical_payload(saved) and row(registered)==before
    assert not any('FROM fact_revision' in s or s.startswith(('INSERT','UPDATE','DELETE')) for s in events['sql'])
    assert events['commits']==1


@pytest.mark.parametrize('field',['actor','target','requested_at','requested_offset','manifest','lineage','exclusions'])
def test_different_request_conflicts_before_work(case,registered,monkeypatch,field):
    request=request_for(case)
    saved=run(registered,request)
    if field=='actor': changed=replace(request,actor='denied')
    elif field=='target': changed=replace(request,target=replace(request.target,recipient='different'))
    elif field=='requested_at': changed=replace(request,requested_at=request.requested_at-timedelta(seconds=1))
    elif field=='requested_offset': changed=replace(request,requested_at=request.requested_at.astimezone(AT.tzinfo))
    elif field=='manifest': changed=replace(request,original=replace(request.original,cutoff=replace(request.original.cutoff,captured_at=TIME)))
    elif field=='lineage': changed=replace(request,lineage=replace(request.lineage,cutoff=replace(request.lineage.cutoff,captured_at=TIME)))
    else:
        exclusion=CreatinineTrendExclusion(reference=replace(request.inference,id='absent'),reason='unrelated_fact')
        changed=replace(request,original=replace(request.original,exclusions=(exclusion,)))
    forbidden=forbid_work(monkeypatch)
    with pytest.raises(RecordConflict) as error: run(registered,changed,forbidden)
    private(error.value)
    assert store.load_creatinine_trend_execution(registered,request.execution_id,target=TARGET)==saved


@pytest.mark.parametrize('kind',['digest','sample','decimal','offset','exclusion','lineage','output_future','repository'])
def test_coherent_but_false_historical_assertions_abort(case,registered,kind):
    request=request_for(case)
    if kind=='digest':
        manifest=replace(request.original,selected_payload_digests=('0'*64,request.original.selected_payload_digests[1]))
        nodes=tuple(replace(n,payload_digest='0'*64) if n.reference==manifest.selected[0] else n for n in request.lineage.nodes)
        request=replace(request,original=manifest,lineage=replace(request.lineage,nodes=nodes))
    elif kind=='sample': request=replace(request,original=replace(request.original,selected_samples=(replace(request.original.selected_samples[0],identifier='different'),request.original.selected_samples[1])))
    elif kind in ('decimal','offset'):
        m=request.original
        if kind=='decimal':
            m=replace(m,selected_values=(Decimal('1.000'),m.selected_values[1]))
        else: m=replace(m,selected_sample_times=(m.selected_sample_times[0].astimezone(timezone.utc),m.selected_sample_times[1]))
        request=replace(request,original=m,comparison=m.comparison)
    elif kind=='exclusion': request=replace(request,original=replace(request.original,exclusions=(CreatinineTrendExclusion(reference=replace(request.inference,id='absent'),reason='unrelated_fact'),)))
    elif kind=='lineage':
        nodes=request.lineage.nodes
        request=replace(request,lineage=replace(request.lineage,nodes=(replace(nodes[0],ingestion=replace(nodes[0].ingestion,ingested_at=TIME)),*nodes[1:])))
    elif kind=='output_future': request=replace(request,lineage=replace(request.lineage,cutoff=replace(request.lineage.cutoff,fact_watermark=1000)))
    else:
        old=str(request.original.cutoff.repository_id)
        request=CreatinineTrendReviewRequest.model_validate_json(canonical_payload(request).replace(old,str(uuid4())))
    with pytest.raises(StorageIntegrityError) as error: run(registered,request)
    private(error.value)
    assert counts(registered)==(3,0)


@pytest.mark.parametrize('kind',['observation_missing','inference_missing','corrupt','same_ref_payload','same_ref_sample'])
def test_required_historical_storage_contradictions_abort(case,registered,kind):
    request=request_for(case)
    with registered.begin() as conn:
        if kind.endswith('missing'):
            conn.execute(text('DELETE FROM fact_revision WHERE kind=:kind'),{'kind':kind.split('_')[0]})
        elif kind=='corrupt': conn.execute(text("UPDATE fact_revision SET payload='{}'"))
        else:
            a=case['selection'].selected[0]
            if kind=='same_ref_sample': changed=replace(a,provenance=replace(a.provenance,source=replace(a.provenance.source,identifier='other-sample')))
            else: changed=replace(a,value=replace(a.value,value=replace(a.value.value,value=Decimal('1.10'))))
            conn.execute(text('UPDATE fact_revision SET payload=:p WHERE fact_id=:id'),{'p':canonical_payload(changed),'id':a.id})
    with pytest.raises(StorageIntegrityError) as error: run(registered,request)
    private(error.value)
    assert counts(registered)[1]==0


@pytest.mark.parametrize('kind',['statement','method','time','applicability','uncertainty'])
def test_inference_rebuilt_even_if_witness_matches_corruption(case,registered,kind):
    inference=case['inference']
    if kind=='statement': changed=replace(inference,statement='Different bounded statement')
    elif kind=='method': changed=replace(inference,method=replace(inference.method,version='other'))
    elif kind=='time':
        time=POLICY.available_at-timedelta(seconds=1)
        changed=replace(inference,time=replace(inference.time,event=time,recorded=time,processed=time),provenance=replace(inference.provenance,recorded_at=time))
    elif kind=='applicability': changed=replace(inference,applicability='Different scope')
    else: changed=replace(inference,uncertainty=('Different uncertainty',))
    with registered.begin() as conn: conn.execute(text("UPDATE fact_revision SET payload=:p WHERE kind='inference'"),{'p':canonical_payload(changed)})
    with transaction(registered) as repo:
        graph=repo.resolve_lineage(changed.reference,target=TARGET,cutoff=case['lineage'].cutoff,limits=LineageLimits())
    request=request_for(case,lineage=creatinine_trend_lineage_witness(graph))
    with pytest.raises(StorageIntegrityError): run(registered,request)
    assert counts(registered)==(3,0)


def test_valid_inference_revision_metadata_is_retained(case,registered):
    old=case['inference']
    revised=revision(old,'reasoned-revision')
    with transaction(registered) as repo:
        repo.append_revision(revised,target=TARGET)
        cutoff=repo.capture_cutoff()
        graph=repo.resolve_lineage(revised.reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())
    request=request_for(case,inference=revised.reference,lineage=creatinine_trend_lineage_witness(graph))
    saved=run(registered,request)
    assert saved.record.decision.outcome=='released'
    retained=saved.record.decision.assessment.review.candidate.snapshot.facts[-1]
    assert retained.supersedes==old.reference and retained.correction_reason==revised.correction_reason
    assert saved.record.lineage.direct_dependencies==old.inputs
    assert old.reference not in saved.record.lineage.nodes[-1].ancestry


@pytest.mark.parametrize('kind',['missing','contradictory_digest'])
def test_impossible_terminal_check_is_integrity_failure(case,registered,monkeypatch,kind):
    original=PatientRepository.load_latest_known
    def altered(repo,*args,**kw):
        result=original(repo,*args,**kw)
        if kind=='missing': return dc_replace(result,records=())
        node=result.records[0]
        changed=replace(node.fact,statement='Contradictory exact retained inference')
        return dc_replace(result,records=(dc_replace(node,fact=changed),))
    monkeypatch.setattr(PatientRepository,'load_latest_known',altered)
    with pytest.raises(StorageIntegrityError): run(registered,request_for(case))
    assert counts(registered)==(3,0)


@pytest.mark.parametrize('kind',['naive','backward_start','backward_observation','backward_decision','backward_finalization','invalid'])
def test_invalid_clock_never_persists(case,registered,kind):
    values=[TIME]*4
    index={'naive':0,'backward_start':0,'backward_observation':1,'backward_decision':2,'backward_finalization':3,'invalid':0}[kind]
    values[index]=TIME.replace(tzinfo=None) if kind=='naive' else SECRET if kind=='invalid' else TIME-timedelta(seconds=2)
    ticks=iter(values)
    with pytest.raises(TransactionAborted): run(registered,request_for(case),lambda:next(ticks))
    assert counts(registered)==(3,0)


@pytest.mark.parametrize('kind',['dict','actor','comparison','cutoff','extra'])
def test_malformed_request_before_transaction(case,registered,kind):
    request=request_for(case)
    if kind=='dict': request=request.model_dump()
    elif kind=='actor': request=request.model_copy(update={'actor':''})
    elif kind=='comparison': request=request.model_copy(update={'comparison':replace(request.comparison,earlier_value=Decimal('1.1'))})
    elif kind=='cutoff': request=request.model_copy(update={'original':request.original.model_copy(update={'cutoff':request.original.cutoff.model_copy(update={'fact_watermark':True})})})
    else: request=request.model_copy(update={'decision':SECRET})
    with trace(registered) as events:
        with pytest.raises(PersistenceInputError) as error: run(registered,request)
        private(error.value)
        assert events['sql']==[]


@pytest.mark.parametrize('kind',['builder','after_append','read_sql','insert_sql','caught_adapter'])
def test_operational_failure_rollback_no_row(case,registered,monkeypatch,kind):
    request=request_for(case)
    listener=None
    def fail(*args,**kw): raise RuntimeError(SECRET)
    if kind=='builder': monkeypatch.setattr(workflow,'build_creatinine_trend_candidate',fail)
    elif kind=='after_append':
        original=store._CreatinineExecutionAdapter.append
        def altered(*args,**kw): original(*args,**kw); raise RuntimeError(SECRET)
        monkeypatch.setattr(store._CreatinineExecutionAdapter,'append',altered)
    elif kind=='caught_adapter':
        original=workflow._new_execution
        def altered(tx,*args):
            with pytest.raises(RecordNotFound): tx.repository.load_patient('absent')
            return original(tx,*args)
        monkeypatch.setattr(workflow,'_new_execution',altered)
    else:
        def listener(conn,cursor,statement,parameters,context,many):
            if ('FROM fact_revision' in statement if kind=='read_sql' else statement.startswith('INSERT INTO creatinine_trend_execution')):
                raise OperationalError(SECRET,{},Exception(SECRET))
        event.listen(registered,'after_cursor_execute',listener)
    try:
        with pytest.raises(TransactionAborted) as error: run(registered,request)
        assert type(error.value) is TransactionAborted
        private(error.value)
    finally:
        if listener: event.remove(registered,'after_cursor_execute',listener)
    assert counts(registered)==(3,0)


@pytest.mark.parametrize('committed',[False,True])
def test_completion_uncertainty_never_returns_or_reconciles(case,registered,monkeypatch,committed):
    request=request_for(case)
    commit=registered.dialect.do_commit
    handles=[]
    context=workflow.execution_transaction
    @contextmanager
    def tracked(engine):
        with context(engine) as tx:
            handles.append(tx)
            yield tx
    monkeypatch.setattr(workflow,'execution_transaction',tracked)
    def fail(conn):
        if committed: commit(conn)
        raise RuntimeError(SECRET)
    with monkeypatch.context() as m:
        m.setattr(registered.dialect,'do_commit',fail)
        with pytest.raises(TransactionCompletionUnknown) as error: run(registered,request)
        private(error.value)
    assert counts(registered)==(3,int(committed))
    for tx in handles:
        with pytest.raises(TransactionAborted): tx.repository.capture_cutoff()
        with pytest.raises(TransactionAborted): tx.executions.find(uuid4(),target=TARGET)
        with pytest.raises(TransactionAborted): tx.creatinine_executions.find(request.execution_id,target=TARGET)


@pytest.mark.parametrize('category',[KeyboardInterrupt,SystemExit])
def test_process_control_preserved(case,registered,monkeypatch,category):
    signal=category(SECRET)
    def fail(**kw): raise signal
    monkeypatch.setattr(workflow,'build_creatinine_trend_candidate',fail)
    with pytest.raises(category) as error: run(registered,request_for(case))
    assert error.value is signal and counts(registered)==(3,0)


@pytest.mark.parametrize('different',[False,True])
def test_serialized_same_id_callers(case,registered,monkeypatch,different):
    request=request_for(case)
    contender=create_database(registered.url.database)
    entered=Event(); release=Event(); attempted=Event()
    original=workflow._new_execution
    executions=[]
    def held(tx,req,clock):
        executions.append(req.execution_id)
        entered.set()
        assert release.wait(5)
        return original(tx,req,clock)
    def before(conn,cursor,statement,parameters,context,many):
        if statement=='BEGIN IMMEDIATE': attempted.set()
    monkeypatch.setattr(workflow,'_new_execution',held)
    event.listen(contender,'before_cursor_execute',before)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(run,registered,request)
            assert entered.wait(5)
            other=replace(request,actor='denied') if different else request
            second=pool.submit(run,contender,other)
            try: assert attempted.wait(5)
            finally: release.set()
            saved=first.result(timeout=15)
            if different:
                with pytest.raises(RecordConflict): second.result(timeout=15)
            else: assert second.result(timeout=15)==saved
        assert executions==[request.execution_id] and counts(registered)==(3,1)
    finally:
        release.set(); contender.dispose()


def test_clock_sampled_after_writer_lock(case,registered):
    request=request_for(case)
    contender=create_database(registered.url.database)
    attempted=Event(); clocks=[]
    def before(conn,cursor,statement,parameters,context,many):
        if statement=='BEGIN IMMEDIATE': attempted.set()
    event.listen(contender,'before_cursor_execute',before)
    def clock(): clocks.append(True); return GRANT_WINDOW.end
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction(registered):
                future=pool.submit(run,contender,request,clock)
                assert attempted.wait(5) and clocks==[]
            saved=future.result(timeout=15)
        assert len(clocks)==4 and saved.record.decision.outcome=='withheld'
    finally: contender.dispose()


def test_competing_revision_cannot_enter_after_final_recheck(case,registered,monkeypatch):
    contender=create_database(registered.url.database)
    def zero(conn,record): conn.execute('PRAGMA busy_timeout=0')
    event.listen(contender,'connect',zero)
    original=workflow.assess_creatinine_trend_final_recheck
    def protected(**kw):
        result=original(**kw)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(change,contender,case,'same_value')
            with pytest.raises(OperationalError): future.result(timeout=5)
        assert counts(registered)==(3,0)
        return result
    monkeypatch.setattr(workflow,'assess_creatinine_trend_final_recheck',protected)
    try:
        saved=run(registered,request_for(case))
        assert saved.record.decision.outcome=='released'
        change(contender,case,'same_value')
        assert store.load_creatinine_trend_execution(registered,saved.record.execution_id,target=TARGET)==saved
    finally: contender.dispose()


def test_foreign_corrupt_retry_row_not_decoded(case,registered,monkeypatch):
    request=request_for(case)
    run(registered,request)
    with registered.begin() as conn:
        conn.execute(text("UPDATE creatinine_trend_execution SET patient_id='synthetic-p2',encounter_id='synthetic-e3',payload='CONFIDENTIAL_SYNTHETIC'"))
    def forbidden(*args): pytest.fail('foreign payload decoded')
    monkeypatch.setattr(store,'_decode',forbidden)
    with pytest.raises(RecordConflict) as error: run(registered,request)
    private(error.value)
    assert counts(registered)==(3,1)


@pytest.mark.parametrize('outcome',['released','withheld'])
def test_process_reopen_retry_without_clock(case,registered,outcome):
    request=request_for(case,actor='denied' if outcome=='withheld' else 'synthetic-creatinine-orchestrator')
    saved=run(registered,request)
    registered.dispose()
    script='''
import sys
from app.execution.creatinine_trend_execution import CreatinineTrendReviewRequest
from app.execution.creatinine_trend_workflow import execute_creatinine_trend_review
from app.persistence.database import create_database
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
def forbidden(): raise RuntimeError('clock sampled on retry')
try:
    result=execute_creatinine_trend_review(engine,CreatinineTrendReviewRequest.model_validate_json(sys.argv[2]),clock=forbidden)
    print(canonical_payload(result))
finally: engine.dispose()
'''
    proc=subprocess.run([sys.executable,'-c',script,registered.url.database,canonical_payload(request)],
        capture_output=True,text=True,check=True,timeout=30,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert proc.stdout.strip()==canonical_payload(saved)


def test_no_framework_weight_or_automatic_reconciliation():
    source=Path(workflow.__file__).read_text()
    tree=ast.parse(source)
    assert {n.name for n in tree.body if isinstance(n,ast.ClassDef)} == {'CreatinineTrendReconciliationResult'}
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any('weight' in name or 'sqlalchemy' in name for name in imports)
    assert not any(word in source for word in ('append_fact(', 'append_revision(', 'load_creatinine_trend_execution('))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_creatinine_trend_review')
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id == 'reconcile_creatinine_trend_execution' for n in ast.walk(function))
    assert isinstance(function.body[-1],ast.Return)
    for node in ast.walk(function):
        if isinstance(node,ast.With): assert not any(isinstance(child,ast.Return) for child in ast.walk(node))


@pytest.mark.parametrize('kind', ['session', 'connection'])
def test_workflow_rejects_transaction_handles(case, registered, kind):
    request = request_for(case)
    with (Session(registered) if kind == 'session' else registered.connect()) as handle:
        with pytest.raises(PersistenceInputError) as error:
            run(handle, request)
        private(error.value)
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('category', [QueryLimitExceeded, SchemaMismatch, UnsupportedOperation])
def test_typed_storage_failures_remain_distinct_and_private(case, registered, monkeypatch, category):
    def fail(*args, **kwargs):
        raise category(SECRET)
    monkeypatch.setattr(PatientRepository, 'resolve_lineage', fail)
    with pytest.raises(category) as error:
        run(registered, request_for(case))
    assert type(error.value) is category
    private(error.value)
    assert counts(registered) == (3, 0)


def test_partial_historical_lineage_cannot_complete(case, registered, monkeypatch):
    graph = partial_graph(case)
    request = request_for(case, lineage=creatinine_trend_lineage_witness(graph))
    monkeypatch.setattr(PatientRepository, 'resolve_lineage', lambda *args, **kwargs: graph)
    with pytest.raises(StorageIntegrityError):
        run(registered, request)
    assert graph.coverage == 'partial' and graph.unresolved
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('earlier,later,direction', [
    ('1.20', '1.00', 'decrease'), ('1.00', '1.00', 'unchanged'), ('1.00', '1.20', 'increase'),
])
def test_all_directions_retained_through_protected_completion(registered, earlier, later, direction):
    data = evidence(registered, earlier, later)
    saved = run(registered, request_for(data))
    assert saved.record.decision.outcome == 'released'
    assert saved.record.comparison.direction == direction
    assert str(saved.record.comparison.earlier_value) == earlier
    assert str(saved.record.comparison.later_value) == later
    assert saved.record.decision.assessment.review.candidate.snapshot.facts[-1].statement == data['inference'].statement
