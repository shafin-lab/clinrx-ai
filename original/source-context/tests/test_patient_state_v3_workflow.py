"""M7 protected completion, conservative materiality and explicit recovery."""
from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text, event
from app.execution import patient_state_v3_workflow as w, patient_state_v3_execution as c
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference
from app.persistence.repository import transaction, PatientRepository
from app.persistence.shared_transaction import execution_transaction
from app.persistence.bounded_history import AggregateHistoryBudget
from app.persistence.errors import (RecordConflict, StorageIntegrityError, TransactionAborted,
    TransactionCompletionUnknown, QueryLimitExceeded, PersistenceInputError)
from app.persistence import circulatory_executions as store
from test_persistence import database, registered
from test_patient_state_v3 import change, PROV, TARGET, measurement
from test_patient_state_v3_inference import selected, inputs
from test_patient_state_v3_persistence import save, revised


def clock():
    return c.GRANT_WINDOW.start+timedelta(minutes=1)


def forbidden(*args,**kw):
    raise AssertionError('unexpected clinical recomputation or clock')


def prepare(engine):
    assembly,ir=selected(engine)
    inference=build_circulatory_timing_inference(assembly=assembly,request=ir)
    cutoff=save(engine,inference)
    return c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,
        actor=c.GRANT_ACTOR,inference_request=ir,assembly_request=assembly.request,
        inference_cutoff=cutoff,expected_inference_digest=c.digest(inference),requested_at=c.GRANT_WINDOW.start)


def count(engine):
    with engine.connect() as conn:
        return conn.execute(text('SELECT count(*) FROM circulatory_execution')).scalar_one()


def test_release_and_metadata(registered):
    r=prepare(registered)
    with transaction(registered) as repo: before=repo.capture_cutoff()
    saved=w.execute_circulatory_review(registered,r,clock=clock)
    assert saved.record.decision.outcome=='released'
    assert saved.record.final_recheck.outcome=='unchanged'
    assert tuple(f.reference.id for f in saved.record.evidence.facts)==('p','l','v-initiation')
    assert saved.record.decision.assessment.review.rendering.content==saved.record.evidence.inference.statement
    with transaction(registered) as repo: assert repo.capture_cutoff().fact_watermark==before.fact_watermark
    registered.dispose()
    assert w.reconcile_circulatory_execution(registered,r).stored==saved


@pytest.mark.parametrize('index',range(3))
@pytest.mark.parametrize('correction',['same_value','provenance','withdrawn'])
def test_any_successor_is_material(registered,index,correction):
    r=prepare(registered);f=inputs()[index]
    fields={} if correction=='same_value' else {'record_status':'withdrawn'} if correction=='withdrawn' else {'provenance':change(f.provenance,actor='corrected source')}
    save(registered,revised(f,**fields))
    saved=w.execute_circulatory_review(registered,r,clock=clock)
    assert saved.record.decision.outcome=='withheld'
    assert saved.record.evidence.facts[index].reference==f.reference
    assert saved.record.final_recheck.evidence[index].terminal.version=='2'
    assert w.reconcile_circulatory_execution(registered,r).stored==saved


@pytest.mark.parametrize('withheld',[False,True])
def test_retry_and_reconciliation_never_recompute(registered,monkeypatch,withheld):
    r=prepare(registered)
    if withheld:save(registered,revised(inputs()[0]))
    saved=w.execute_circulatory_review(registered,r,clock=clock)
    for name in ('_new_execution','_assemble','build_circulatory_timing_inference','_utc_now','assess_release','decide_release'):
        monkeypatch.setattr(w,name,forbidden)
    for name in ('load_fact','list_bounded_history','capture_cutoff'):
        monkeypatch.setattr(PatientRepository,name,forbidden)
    assert w.execute_circulatory_review(registered,r,clock=forbidden)==saved
    assert w.reconcile_circulatory_execution(registered,r).stored==saved
    assert count(registered)==1


def test_independent_measurement_does_not_change_exact_claim(registered):
    r=prepare(registered);save(registered,measurement(name='independent'))
    assert w.execute_circulatory_review(registered,r,clock=clock).record.decision.outcome=='released'


def test_inference_successor_withholds(registered):
    r=prepare(registered)
    with transaction(registered) as repo: i=repo.load_fact(r.inference_reference,target=TARGET).fact
    save(registered,change(i,revision='2',supersedes=i.reference,correction_reason='source correction'))
    assert w.execute_circulatory_review(registered,r,clock=clock).record.decision.outcome=='withheld'


@pytest.mark.parametrize('field',['actor','requested_at','expected_inference_digest'])
def test_exact_matcher_conflicts(registered,field):
    r=prepare(registered);w.execute_circulatory_review(registered,r,clock=clock)
    value={'actor':'other','requested_at':r.requested_at+timedelta(seconds=1),'expected_inference_digest':'0'*64}[field]
    altered=change(r,**{field:value})
    with pytest.raises(RecordConflict):w.execute_circulatory_review(registered,altered,clock=forbidden)
    with pytest.raises(RecordConflict):w.reconcile_circulatory_execution(registered,altered)


def test_resource_exhaustion_rolls_back_no_withheld(registered):
    r=prepare(registered)
    with pytest.raises(QueryLimitExceeded):
        w.execute_circulatory_review(registered,r,clock=clock,aggregate_budget=AggregateHistoryBudget(max_rows=1))
    assert count(registered)==0


def test_corrupt_source_fails_not_withheld(registered):
    r=prepare(registered)
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET payload='private corrupted' WHERE fact_id='p'"))
    with pytest.raises(StorageIntegrityError):w.execute_circulatory_review(registered,r,clock=clock)
    assert count(registered)==0


def test_shared_poison_closed_and_one_begin(registered):
    r=prepare(registered);sql=[]
    def observe(conn,cursor,statement,*args):sql.append(statement)
    event.listen(registered,'before_cursor_execute',observe)
    try:w.execute_circulatory_review(registered,r,clock=clock)
    finally:event.remove(registered,'before_cursor_execute',observe)
    assert sql.count('BEGIN IMMEDIATE')==1
    with pytest.raises(TransactionAborted):
        with execution_transaction(registered) as tx:
            try:tx.circulatory_executions.append({},target=TARGET)
            except PersistenceInputError:pass
    with pytest.raises(TransactionAborted):tx.repository.capture_cutoff()
    with pytest.raises(TransactionAborted):tx.circulatory_executions.find(r.execution_id,target=TARGET)


@pytest.mark.parametrize('committed',[False,True])
def test_completion_unknown_both_outcomes(registered,monkeypatch,committed):
    r=prepare(registered)
    if committed:
        original=w.execution_transaction
        @contextmanager
        def uncertain(engine):
            with original(engine) as tx:yield tx
            raise TransactionCompletionUnknown('unconfirmed')
        monkeypatch.setattr(w,'execution_transaction',uncertain)
    else:
        def fail(conn):raise RuntimeError('private commit failure')
        event.listen(registered,'commit',fail)
    try:
        with pytest.raises(TransactionCompletionUnknown):w.execute_circulatory_review(registered,r,clock=clock)
    finally:
        if not committed:event.remove(registered,'commit',fail)
    result=w.reconcile_circulatory_execution(registered,r)
    assert result.status==('committed_match' if committed else 'absent')


def test_foreign_and_absent_never_decode(registered,monkeypatch):
    r=prepare(registered)
    monkeypatch.setattr(store,'_decode',forbidden)
    assert w.reconcile_circulatory_execution(registered,r).status=='absent'


def test_corrupt_receipt_not_absence(registered):
    r=prepare(registered);w.execute_circulatory_review(registered,r,clock=clock)
    with registered.begin() as conn:conn.execute(text("UPDATE circulatory_execution SET payload='bad private receipt'"))
    with pytest.raises(StorageIntegrityError):w.reconcile_circulatory_execution(registered,r)


def test_process_control_cleanup(registered,monkeypatch):
    r=prepare(registered)
    def stop(*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(w,'decide_release',stop)
    with pytest.raises(KeyboardInterrupt):w.execute_circulatory_review(registered,r,clock=clock)
    assert count(registered)==0


def test_supporting_calibration_successor_is_material(registered):
    from test_patient_state_v3 import records, h
    from app.execution.patient_state_v3_inference import EvidencePin
    p,l,v=inputs();support=records()[11]
    p=change(p,associations=(h.EvidenceBinding(role='calibration',scope=TARGET,status='resolved',exact=support.reference,provenance=PROV),))
    assembly,ir=selected(registered,(p,l,v,support))
    ir=change(ir,supporting=(EvidencePin(reference=support.reference,expected_digest=support.canonical_digest),))
    i=build_circulatory_timing_inference(assembly=assembly,request=ir);cutoff=save(registered,i)
    r=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
        inference_request=ir,assembly_request=assembly.request,inference_cutoff=cutoff,
        expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
    save(registered,revised(support))
    saved=w.execute_circulatory_review(registered,r,clock=clock)
    assert saved.record.decision.outcome=='withheld'
    assert tuple(x.consumed.id for x in saved.record.final_recheck.evidence)==('p','l','v-initiation','cal')
    assert saved.record.final_recheck.evidence[-1].terminal.version=='2'


def test_bidirectional_rollback_after_execution_append(registered):
    r=prepare(registered);saved=w.execute_circulatory_review(registered,r,clock=clock)
    from app.persistence.errors import UnsupportedOperation
    with transaction(registered) as repo:before=repo.capture_cutoff().fact_watermark
    with pytest.raises(TransactionAborted):
        with execution_transaction(registered) as tx:
            tx.repository.append_fact(measurement(name='provisional'),target=TARGET)
            assert tx.circulatory_executions.append(saved.record,target=TARGET)==saved
            try:tx.repository.append_fact({},target=TARGET)
            except UnsupportedOperation:pass
            with pytest.raises(TransactionAborted):tx.circulatory_executions.find(r.execution_id,target=TARGET)
    with transaction(registered) as repo:assert repo.capture_cutoff().fact_watermark==before
    assert count(registered)==1


def test_retained_reconciliation_after_corrections_and_expiry(registered,monkeypatch):
    r=prepare(registered);saved=w.execute_circulatory_review(registered,r,clock=clock)
    save(registered,revised(inputs()[0]))
    with transaction(registered) as repo:i=repo.load_fact(r.inference_reference,target=TARGET).fact
    save(registered,change(i,revision='2',supersedes=i.reference,correction_reason='later inference correction'))
    monkeypatch.setattr(w,'_utc_now',lambda:c.GRANT_WINDOW.end+timedelta(days=100))
    recovered=w.reconcile_circulatory_execution(registered,r).stored
    assert recovered==saved
    assert recovered.ingested_at.isoformat()==saved.ingested_at.isoformat()
    assert recovered.record.runtime.finalized_at.isoformat()==saved.record.runtime.finalized_at.isoformat()
    assert w.execute_circulatory_review(registered,r,clock=forbidden)==saved


def test_foreign_corrupt_receipt_is_absent(registered,monkeypatch):
    from app.models.clinical.common import ContextTarget
    r=prepare(registered);w.execute_circulatory_review(registered,r,clock=clock)
    with registered.begin() as conn:conn.execute(text("UPDATE circulatory_execution SET payload='private broken payload'"))
    monkeypatch.setattr(store,'_decode',forbidden)
    assert store.find_circulatory_execution(registered,r.execution_id,
        target=ContextTarget(patient_id='synthetic-p2',encounter_id='synthetic-e3')) is None


@pytest.mark.parametrize('stage',['_replay','_final_recheck','assess_release','decide_release'])
def test_failures_never_append_success(registered,monkeypatch,stage):
    r=prepare(registered)
    def failure(*a,**kw):raise RuntimeError('PRIVATE_SQL_AND_PAYLOAD')
    monkeypatch.setattr(w,stage,failure)
    with pytest.raises(TransactionAborted) as caught:w.execute_circulatory_review(registered,r,clock=clock)
    assert 'PRIVATE' not in str(caught.value)
    assert caught.value.__suppress_context__
    assert count(registered)==0


def test_reconciliation_retained_byte_limit_precedes_decode_and_is_operational(registered,monkeypatch):
    r=prepare(registered);w.execute_circulatory_review(registered,r,clock=clock)
    with registered.begin() as conn:
        conn.execute(text('UPDATE circulatory_execution SET payload=:payload'),{'payload':'x'*16777217})
    monkeypatch.setattr(store,'_decode',forbidden)
    with pytest.raises(QueryLimitExceeded):w.reconcile_circulatory_execution(registered,r)
    assert count(registered)==1
