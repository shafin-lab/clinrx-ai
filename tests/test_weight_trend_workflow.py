"""Protected synthetic execution against real SQLite, with independent expectations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import subprocess
import sys
from threading import Event
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from app.execution import weight_trend_workflow as workflow
from app.execution.weight_trend import WeightTrendExclusion
from app.execution.weight_trend_execution import weight_trend_lineage_witness, weight_trend_selection_manifest
from app.execution.weight_trend_release import GRANT_TARGET, GRANT_WINDOW
from app.persistence import executions
from app.persistence.database import create_database
from app.persistence.errors import PersistenceInputError, RecordConflict, RecordNotFound, StorageIntegrityError, TransactionAborted
from app.persistence.executions import load_weight_trend_execution as load, append_weight_trend_execution as append
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction, PatientRepository
from app.persistence.shared_transaction import execution_transaction
from test_persistence import AT, ROOT, TARGET, database, registered, fact, replace
from test_revision_chains import revision
from test_weight_trend import POLICY, weight, select
from test_weight_trend_inference import build, persist, resolve
from test_weight_trend_release import case, NOW
from test_weight_trend_execution_persistence import make_record
from test_weight_trend_shared_transaction import counts, trace, private, SECRET

TIME = NOW.astimezone(timezone.utc)


def request_for(case, **updates):
    args = dict(execution_id=uuid4(), target=GRANT_TARGET, actor='synthetic-orchestrator',
        original=weight_trend_selection_manifest(case['selection']), comparison=case['comparison'],
        inference=case['inference'].reference, lineage=weight_trend_lineage_witness(case['lineage']),
        requested_at=TIME-timedelta(seconds=1))
    args.update(updates)
    return workflow.WeightTrendReviewRequest(**args)


def run(engine, request, clock=lambda: TIME):
    return workflow.execute_weight_trend_review(engine, request, clock=clock)


def change_evidence(engine, case, kind):
    a = case['selection'].selected[0]
    with transaction(engine) as repo:
        if kind == 'third': repo.append_fact(weight('c', '80', AT+timedelta(hours=2)), target=TARGET)
        elif kind == 'unrelated': repo.append_fact(fact(id='unrelated'), target=TARGET)
        elif kind in ('outside', 'boundary'):
            at = POLICY.window_end if kind == 'boundary' else POLICY.window_end+timedelta(hours=1)
            repo.append_fact(weight('outside', '80', at), target=TARGET)
        elif kind == 'inference': repo.append_revision(revision(case['inference']), target=TARGET)
        else:
            corrected = revision(a)
            if kind == 'correction':
                corrected = replace(corrected, value=replace(a.value, value=replace(a.value.value, value=Decimal('81'))))
            elif kind == 'ineligible': corrected = replace(corrected, verification='unverified')
            repo.append_revision(corrected, target=TARGET)


@pytest.mark.parametrize('actor,outcome', [('synthetic-orchestrator','released'), ('synthetic-denied','withheld')])
def test_real_commit_reopen_and_exact_cutoff(case, registered, monkeypatch, actor, outcome):
    request = request_for(case, actor=actor)
    captured = []
    original = PatientRepository.capture_cutoff
    def capture(self):
        value = original(self)
        captured.append(value)
        return value
    monkeypatch.setattr(PatientRepository, 'capture_cutoff', capture)
    with trace(registered) as events:
        result = run(registered, request)
        assert events['commits'] == 1 and events['rollbacks'] == 0
        assert events['sql'].count('BEGIN IMMEDIATE') == 1
        assert len(events['connections']) == 1
        assert not any(s.startswith(('UPDATE', 'DELETE', 'INSERT INTO fact_revision')) for s in events['sql'])
    record = result.record
    assert record.decision.outcome == outcome
    assert canonical_payload(record.final_recheck.final.cutoff) == canonical_payload(captured[0])
    assert record.final_recheck.final.cutoff.fact_watermark == 3
    assert record.original.selected == request.original.selected
    assert record.decision.assessment.assessor == workflow.WORKFLOW_ASSESSOR
    assert record.decision.assessment.state.freshness.assessor == workflow.FINAL_CONTEXT_ASSESSOR
    if outcome == 'released':
        assert record.decision.reasons == ()
        assert record.decision.assessment.content_validation.outcome == 'matched'
        assert all(c.outcome == 'no_detected_violation' for e in record.decision.assessment.review.evaluations for c in e.checks)
    path = registered.url.database
    registered.dispose()
    reopened = create_database(path)
    try:
        assert load(reopened, request.execution_id, target=TARGET) == result
        with transaction(reopened) as repo: assert repo.capture_cutoff().fact_watermark == 3
    finally: reopened.dispose()


def test_producers_execute_under_writer_reservation(case, registered, monkeypatch):
    request = request_for(case)
    called = []
    names = ['build_weight_trend_snapshot', 'build_weight_trend_candidate', 'render_weight_trend',
        'evaluate_weight_trend', 'validate_weight_trend_content', 'assess_weight_trend_dependencies',
        'assess_weight_trend_final_context', 'issue_synthetic_weight_release', 'assemble_weight_trend_runtime',
        'assess_release', 'decide_release']
    with trace(registered) as events:
        for name in names:
            original = getattr(workflow, name)
            def observed(*args, _name=name, _original=original, **kwargs):
                assert events['sql'].count('BEGIN IMMEDIATE') == 1 and events['commits'] == 0
                assert counts(registered) == (3, 0)
                called.append(_name)
                return _original(*args, **kwargs)
            monkeypatch.setattr(workflow, name, observed)
        result = run(registered, request)
    assert called == names[:5] + ['assess_weight_trend_final_context', 'assess_weight_trend_dependencies'] + names[7:]
    assert result.record.decision.outcome == 'released'


@pytest.mark.parametrize('kind', ['digest', 'exclusion', 'value', 'decimal', 'offset', 'lineage'])
def test_historical_assertion_contradictions_abort(case, registered, kind):
    request = request_for(case)
    if kind == 'digest': request = replace(request, original=replace(request.original, selected_payload_digests=('0'*64, request.original.selected_payload_digests[1])))
    elif kind == 'exclusion':
        exclusion = WeightTrendExclusion(reference=replace(request.inference, id='not-present'), reason='unrelated_fact')
        request = replace(request, original=replace(request.original, exclusions=(exclusion,)))
    elif kind == 'value': request = replace(request, comparison=replace(request.comparison, earlier_kg=Decimal('83')))
    elif kind == 'decimal': request = replace(request, comparison=replace(request.comparison, earlier_kg=Decimal('82.00')))
    elif kind == 'offset': request = replace(request, comparison=replace(request.comparison, earlier_event=request.comparison.earlier_event.astimezone(timezone.utc)))
    else:
        nodes = request.lineage.nodes
        request = replace(request, lineage=replace(request.lineage, nodes=(replace(nodes[0], payload_digest='0'*64), *nodes[1:])))
    with pytest.raises(StorageIntegrityError) as error: run(registered, request)
    private(error.value)
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('missing', ['observation', 'inference'])
def test_missing_required_historical_evidence_aborts(case, registered, missing):
    request = request_for(case)
    with registered.begin() as conn:
        conn.execute(text('DELETE FROM fact_revision WHERE kind=:kind'), {'kind': missing})
    with pytest.raises(StorageIntegrityError if missing == 'observation' else (StorageIntegrityError, RecordNotFound)):
        run(registered, request)
    assert counts(registered)[1] == 0


@pytest.mark.parametrize('field', ['statement', 'method', 'time'])
def test_inference_canonical_contradiction_after_matching_witness(case, registered, field):
    inference = case['inference']
    if field == 'statement': inference = replace(inference, statement='Different bounded synthetic statement')
    elif field == 'method': inference = replace(inference, method=replace(inference.method, version='other'))
    else:
        t = POLICY.available_at-timedelta(seconds=1)
        inference = replace(inference, time=replace(inference.time, event=t, recorded=t, processed=t),
                            provenance=replace(inference.provenance, recorded_at=t))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload=:p WHERE kind='inference'"), {'p': canonical_payload(inference)})
    with transaction(registered) as repo:
        graph = repo.resolve_lineage(inference.reference, target=TARGET, cutoff=case['lineage'].cutoff, limits=LineageLimits())
    request = request_for(case, lineage=weight_trend_lineage_witness(graph))
    with pytest.raises(StorageIntegrityError): run(registered, request)
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('kind,expected', [('correction','selected_exact_references_changed'),
    ('same_value','selected_exact_references_changed'), ('ineligible','final_selection_failed'),
    ('third','final_selection_failed'), ('inference','inference_superseded')])
def test_relevant_pretransaction_changes_withhold(case, registered, kind, expected):
    request = request_for(case)
    change_evidence(registered, case, kind)
    saved = run(registered, request)
    record = saved.record
    assert record.final_recheck.outcome == 'materially_changed'
    assert expected in record.final_recheck.reasons
    assert record.decision.outcome == 'withheld'
    assert record.decision.assessment.state.freshness.material_change
    assert not record.decision.assessment.state.freshness.adequate
    assert record.comparison == request.comparison and record.inference == request.inference
    # Correctly passing historical checks are not fabricated failures.
    assert record.decision.assessment.content_validation.outcome == 'matched'
    assert all(c.outcome == 'no_detected_violation' for e in record.decision.assessment.review.evaluations for c in e.checks)
    if kind in ('ineligible', 'third'): assert record.final_recheck.final.selected == ()
    assert load(registered, request.execution_id, target=TARGET) == saved


@pytest.mark.parametrize('kind', ['unrelated', 'outside', 'boundary'])
def test_benign_prefix_growth_does_not_withhold(case, registered, kind):
    request = request_for(case)
    change_evidence(registered, case, kind)
    record = run(registered, request).record
    assert record.final_recheck.final.cutoff.fact_watermark == 4
    assert len(record.final_recheck.final.exclusions) > len(record.original.exclusions)
    assert record.final_recheck.outcome == 'unchanged'
    assert record.decision.outcome == 'released'


@pytest.mark.parametrize('kind', ['hard_failure', 'unavailable', 'freshness', 'dependency', 'policy'])
def test_valid_governance_negative_commits_withholding(case, registered, monkeypatch, kind):
    if kind in ('hard_failure', 'unavailable'):
        original = workflow.evaluate_weight_trend
        def altered(**kwargs):
            evaluation = original(**kwargs)
            check = replace(evaluation.checks[0], outcome=kind, reason='Synthetic injected producer result')
            return replace(evaluation, checks=(check, *evaluation.checks[1:]), exact_meaning='failed' if kind == 'hard_failure' else 'unavailable')
        monkeypatch.setattr(workflow, 'evaluate_weight_trend', altered)
    elif kind == 'freshness':
        original = workflow.assess_weight_trend_final_context
        monkeypatch.setattr(workflow, 'assess_weight_trend_final_context', lambda **kw: replace(original(**kw), adequate=False))
    elif kind == 'dependency':
        original = workflow.assess_weight_trend_dependencies
        def altered(**kwargs):
            values = original(**kwargs)
            return (replace(values[0], state='unavailable', validity=None), *values[1:])
        monkeypatch.setattr(workflow, 'assess_weight_trend_dependencies', altered)
    else:
        original = workflow.weight_trend_governance_policy
        monkeypatch.setattr(workflow, 'weight_trend_governance_policy', lambda **kw:
            replace(original(**kw), safety_policy=replace(original(**kw).safety_policy, version='other')))
    request = request_for(case)
    saved = run(registered, request)
    assert saved.record.decision.outcome == 'withheld'
    assert load(registered, request.execution_id, target=TARGET) == saved


@pytest.mark.parametrize('field', ['actor', 'requested_at', 'comparison', 'original', 'lineage', 'target'])
def test_changed_retry_request_conflicts_before_work(case, registered, monkeypatch, field):
    request = request_for(case)
    saved = run(registered, request)
    if field == 'actor': changed = replace(request, actor='synthetic-denied')
    elif field == 'requested_at': changed = replace(request, requested_at=request.requested_at-timedelta(seconds=1))
    elif field == 'comparison': changed = replace(request, comparison=replace(request.comparison, earlier_kg=Decimal('83')))
    elif field == 'original': changed = replace(request, original=replace(request.original, cutoff=replace(request.original.cutoff, captured_at=TIME)))
    elif field == 'lineage': changed = replace(request, lineage=replace(request.lineage, cutoff=replace(request.lineage.cutoff, captured_at=TIME)))
    else: changed = replace(request, target=replace(request.target, recipient='another'))
    def forbidden(*args, **kwargs): pytest.fail('retry performed new work')
    monkeypatch.setattr(workflow, '_new_execution', forbidden)
    with pytest.raises(RecordConflict): run(registered, changed, clock=forbidden)
    assert load(registered, request.execution_id, target=TARGET) == saved


def test_retry_after_correction_ignores_new_facts_and_clock(case, registered, monkeypatch):
    request = request_for(case)
    saved = run(registered, request)
    change_evidence(registered, case, 'correction')
    # Even unrelated later corruption must not turn recovery into a new fact scan.
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='{}' WHERE revision='second'"))
    def forbidden(*args, **kwargs): pytest.fail('recovery reran selection or governance')
    for name in ('_new_execution', 'select_weight_observations', 'evaluate_weight_trend', 'assess_release'):
        monkeypatch.setattr(workflow, name, forbidden)
    assert run(registered, request, clock=forbidden) == saved


def test_legacy_envelope_cannot_claim_protected_workflow(case, registered):
    record = make_record(case)
    append(registered, record, target=TARGET)
    request = workflow.WeightTrendReviewRequest(execution_id=record.execution_id, target=record.target,
        actor=record.actor, original=record.original, comparison=record.comparison, inference=record.inference,
        lineage=record.lineage, requested_at=record.started_at)
    with pytest.raises(RecordConflict): run(registered, request)


def test_new_id_and_coherent_new_evidence_can_use_corrected_observation(case, registered):
    original = request_for(case)
    saved = run(registered, original)
    change_evidence(registered, case, 'correction')
    with transaction(registered) as repo: cutoff = repo.capture_cutoff()
    selection = select(registered, cutoff)
    comparison = workflow.compare_recorded_weights(selection)
    inference = workflow.build_weight_trend_inference(selection=selection, comparison=comparison,
        inference_id='new-weight-inference', executed_at=TIME)
    retained, output = persist(registered, inference)
    graph = resolve(registered, retained.fact, output)
    request = workflow.WeightTrendReviewRequest(execution_id=uuid4(), target=GRANT_TARGET, actor=original.actor,
        original=weight_trend_selection_manifest(selection), comparison=comparison, inference=inference.reference,
        lineage=weight_trend_lineage_witness(graph), requested_at=TIME)
    new = run(registered, request)
    assert new.record.decision.outcome == 'released'
    assert new.record.original.selected[0].version == 'second'
    assert load(registered, original.execution_id, target=TARGET) == saved


@pytest.mark.parametrize('outcome', ['released', 'withheld'])
def test_process_restart_exact_retry(case, registered, outcome):
    request = request_for(case, actor='synthetic-denied' if outcome == 'withheld' else 'synthetic-orchestrator')
    saved = run(registered, request)
    script = '''
import sys
from app.execution.weight_trend_workflow import WeightTrendReviewRequest, execute_weight_trend_review
from app.persistence.database import create_database
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
def forbidden(): raise RuntimeError('recovery read clock')
try:
    request=WeightTrendReviewRequest.model_validate_json(sys.argv[2])
    stored=execute_weight_trend_review(engine,request,clock=forbidden)
    print(canonical_payload(stored.record))
    print(stored.ingested_at.isoformat())
finally: engine.dispose()
'''
    process = subprocess.run([sys.executable, '-c', script, registered.url.database, request.model_dump_json()],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT/'backend'), 'PYTHONDONTWRITEBYTECODE':'1'},
        text=True, capture_output=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert process.stdout.splitlines() == [canonical_payload(saved.record), saved.ingested_at.isoformat()]


@pytest.mark.parametrize('kind', ['absent', 'foreign'])
def test_find_absence_is_normal_and_private(case, registered, monkeypatch, kind):
    request = request_for(case)
    if kind == 'foreign': run(registered, request)
    def forbidden(*args): pytest.fail('foreign payload decoded')
    monkeypatch.setattr(executions, '_decode', forbidden)
    with execution_transaction(registered) as tx:
        target = replace(TARGET, encounter_id='synthetic-e2') if kind == 'foreign' else TARGET
        assert tx.executions.find(request.execution_id, target=target) is None
        assert tx.repository.capture_cutoff().fact_watermark == 3


@pytest.mark.parametrize('kind,category', [('corrupt',StorageIntegrityError), ('invalid',PersistenceInputError), ('sql',TransactionAborted)])
def test_find_failures_poison(case, registered, kind, category):
    request = request_for(case)
    run(registered, request)
    if kind == 'corrupt':
        with registered.begin() as conn: conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
    def fail(*args): raise OperationalError(SECRET, {}, Exception(SECRET))
    with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
        if kind == 'sql': event.listen(registered, 'before_cursor_execute', fail)
        try:
            with pytest.raises(category) as error:
                tx.executions.find(SECRET if kind == 'invalid' else request.execution_id, target=TARGET)
            private(error.value)
            with pytest.raises(TransactionAborted): tx.repository.capture_cutoff()
        finally:
            if kind == 'sql': event.remove(registered, 'before_cursor_execute', fail)


@pytest.mark.parametrize('kind', ['builder', 'append', 'read_sql', 'insert_sql', 'precommit', 'postcommit', 'interrupt'])
def test_failures_never_return_success_and_preserve_privacy(case, registered, monkeypatch, kind):
    request = request_for(case)
    listener = None
    def fail(*args, **kwargs):
        if kind == 'interrupt': raise KeyboardInterrupt(SECRET)
        raise RuntimeError(SECRET)
    if kind in ('builder', 'interrupt'): monkeypatch.setattr(workflow, 'build_weight_trend_candidate', fail)
    elif kind == 'append': monkeypatch.setattr(executions._ExecutionAdapter, 'append', fail)
    elif kind in ('read_sql', 'insert_sql'):
        def listener(conn, cursor, statement, parameters, context, executemany):
            if (kind == 'read_sql' and 'FROM fact_revision' in statement) or statement.startswith('INSERT INTO weight_trend_execution'):
                raise OperationalError(SECRET, {'secret': SECRET}, Exception('driver detail'))
        event.listen(registered, 'after_cursor_execute', listener)
    elif kind == 'precommit':
        listener = fail
        event.listen(registered, 'commit', listener)
    else:
        original = registered.dialect.do_commit
        def committed_then_error(conn):
            original(conn)
            raise RuntimeError(SECRET)
        monkeypatch.setattr(registered.dialect, 'do_commit', committed_then_error)
    try:
        with pytest.raises(KeyboardInterrupt if kind == 'interrupt' else TransactionAborted) as error:
            run(registered, request)
        if kind != 'interrupt': private(error.value)
        if kind in ('precommit', 'postcommit'):
            assert str(error.value) == 'transaction completion could not be confirmed'
    finally:
        if listener is not None:
            event.remove(registered, 'commit' if kind == 'precommit' else 'after_cursor_execute', listener)
    assert counts(registered) == (3, 1 if kind == 'postcommit' else 0)


@pytest.mark.parametrize('kind', ['payload', 'request', 'retry'])
def test_corruption_and_malformed_request_never_withhold(case, registered, kind):
    request = request_for(case)
    if kind == 'payload':
        with registered.begin() as conn: conn.execute(text("UPDATE fact_revision SET payload='{}'"))
    elif kind == 'retry':
        run(registered, request)
        with registered.begin() as conn: conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
    else: request = request.model_copy(update={'actor': SECRET, 'original': {'bad': SECRET}})
    with pytest.raises(PersistenceInputError if kind == 'request' else StorageIntegrityError) as error:
        run(registered, request)
    private(error.value)
    assert counts(registered)[1] == (1 if kind == 'retry' else 0)


@pytest.mark.parametrize('kind', ['correction', 'third'])
def test_writer_excluded_between_recheck_and_append_then_later_change(case, registered, monkeypatch, kind):
    request = request_for(case)
    contender = create_database(registered.url.database)
    def zero_timeout(conn, record): conn.execute('PRAGMA busy_timeout=0')
    event.listen(contender, 'connect', zero_timeout)
    reached = Event()
    original = workflow.assess_weight_trend_final_recheck
    def protected(**kwargs):
        result = original(**kwargs)
        reached.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            attempt = pool.submit(change_evidence, contender, case, kind)
            with pytest.raises(OperationalError): attempt.result(timeout=5)
        assert counts(registered) == (3, 0)
        return result
    monkeypatch.setattr(workflow, 'assess_weight_trend_final_recheck', protected)
    try:
        saved = run(registered, request)
        assert reached.is_set() and saved.record.decision.outcome == 'released'
        change_evidence(contender, case, kind)
        assert load(registered, request.execution_id, target=TARGET) == saved
    finally: contender.dispose()


def test_clock_is_after_lock_wait_and_expired_grant_is_not_reused(case, registered):
    request = request_for(case)
    worker = create_database(registered.url.database)
    attempted = Event()
    clocks = []
    def before(conn, cursor, statement, parameters, context, executemany):
        if statement == 'BEGIN IMMEDIATE': attempted.set()
    event.listen(worker, 'before_cursor_execute', before)
    def clock():
        clocks.append(True)
        return GRANT_WINDOW.end
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction(registered):
                future = pool.submit(run, worker, request, clock)
                assert attempted.wait(5)
                assert clocks == []
            saved = future.result(timeout=10)
        assert saved.record.decision.outcome == 'withheld'
        assert saved.record.decision.assessment.state.authorization.issued_at == GRANT_WINDOW.end
        assert saved.record.decision.assessment.state.authorization.outcome == 'deny'
        assert len(clocks) == 4
    finally: worker.dispose()


@pytest.mark.parametrize('kind', ['naive', 'backward_acquired', 'backward_observation', 'backward_decision', 'backward_finalization'])
def test_bad_clock_chronology_aborts(case, registered, kind):
    request = request_for(case)
    values = [TIME]*4
    index = {'naive':0, 'backward_acquired':0, 'backward_observation':1, 'backward_decision':2, 'backward_finalization':3}[kind]
    values[index] = TIME.replace(tzinfo=None) if kind == 'naive' else TIME-timedelta(seconds=2)
    ticks = iter(values)
    with pytest.raises(TransactionAborted): run(registered, request, clock=lambda:next(ticks))
    assert counts(registered) == (3, 0)


def test_current_date_outside_grant_honestly_withholds(case, registered):
    saved = run(registered, request_for(case), clock=lambda:datetime(2026,10,3,tzinfo=timezone.utc))
    assert saved.record.decision.outcome == 'withheld'
    assert saved.record.decision.assessment.state.authorization.outcome == 'deny'


def test_request_is_frozen_and_rejects_governance_objects(case):
    request = request_for(case)
    with pytest.raises(ValidationError): request.actor = 'changed'
    with pytest.raises(ValidationError):
        workflow.WeightTrendReviewRequest.model_validate({**request.model_dump(), 'decision': {}})


def test_wrong_exact_inference_ref_is_required_evidence_failure(case, registered):
    request = request_for(case)
    # Keep the compact assertions internally consistent, but name an absent exact root.
    request = workflow.WeightTrendReviewRequest.model_validate_json(
        request.model_dump_json().replace(request.inference.id, 'absent-inference'))
    with pytest.raises(RecordNotFound): run(registered, request)
    assert counts(registered) == (3, 0)


def test_inference_with_extra_declared_edge_is_integrity_failure(case, registered):
    from app.models.clinical.common import LineageEdge, Reference
    inference = case['inference']
    extra = Reference(kind='observation', id='absent-third', version='1')
    inference = replace(inference, inputs=(*inference.inputs, extra),
        provenance=replace(inference.provenance, upstream=(*inference.provenance.upstream,
            LineageEdge(target=extra, relationship='derived_from'))))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload=:p WHERE kind='inference'"), {'p': canonical_payload(inference)})
    with pytest.raises(StorageIntegrityError): run(registered, request_for(case))
    assert counts(registered) == (3, 0)


def test_final_context_rejects_recheck_for_different_evidence(case, registered, monkeypatch):
    original = workflow.assess_weight_trend_final_context
    def altered(**kwargs):
        check = kwargs['recheck']
        # A structurally valid check with unrelated original digests must not certify this request.
        final = replace(check.final, selected_payload_digests=('0'*64, '1'*64))
        kwargs['recheck'] = replace(check, original_payload_digests=('0'*64, '1'*64), final=final)
        return original(**kwargs)
    monkeypatch.setattr(workflow, 'assess_weight_trend_final_context', altered)
    with pytest.raises(StorageIntegrityError): run(registered, request_for(case))
    assert counts(registered) == (3, 0)


def test_observation_expiry_between_evidence_and_decision_withholds(case, registered):
    ticks = iter([TIME, TIME, TIME+timedelta(seconds=31), TIME+timedelta(seconds=31)])
    record = run(registered, request_for(case), clock=lambda:next(ticks)).record
    assert record.decision.outcome == 'withheld'
    assert 'content_validation_expired_or_future' in record.decision.reasons


def test_foreign_execution_find_never_decodes_corruption(case, registered, monkeypatch):
    request = request_for(case)
    run(registered, request)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC'"))
    def forbidden(*args): pytest.fail('foreign stored body decoded')
    monkeypatch.setattr(executions, '_decode', forbidden)
    with execution_transaction(registered) as tx:
        target = replace(TARGET, encounter_id='synthetic-e2')
        assert tx.executions.find(request.execution_id, target=target) is None
        assert tx.executions.find(uuid4(), target=target) is None
        assert tx.repository.capture_cutoff().fact_watermark == 3


def test_guarded_append_failure_after_insert_is_rolled_back(case, registered, monkeypatch):
    original = executions._decode
    def fail(row, identity):
        original(row, identity)
        raise RuntimeError(SECRET)
    monkeypatch.setattr(executions, '_decode', fail)
    with pytest.raises(TransactionAborted) as error: run(registered, request_for(case))
    private(error.value)
    assert counts(registered) == (3, 0)


def test_caught_adapter_failure_in_builder_still_prevents_commit(case, registered, monkeypatch):
    from contextlib import contextmanager
    owned = workflow.execution_transaction
    handles = []
    @contextmanager
    def capture(engine):
        with owned(engine) as tx:
            handles.append(tx)
            yield tx
    monkeypatch.setattr(workflow, 'execution_transaction', capture)
    original = workflow.build_weight_trend_candidate
    def faulty_builder(**kwargs):
        try:
            handles[0].executions.find(SECRET, target=TARGET)
        except PersistenceInputError:
            pass
        return original(**kwargs)
    monkeypatch.setattr(workflow, 'build_weight_trend_candidate', faulty_builder)
    with pytest.raises(TransactionAborted): run(registered, request_for(case))
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('failed', [False, True])
def test_find_rejects_after_exit_or_poison_without_sql(registered, failed):
    with trace(registered) as events:
        if failed:
            with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
                with pytest.raises(PersistenceInputError): tx.executions.find(SECRET, target=TARGET)
                before = len(events['sql'])
                with pytest.raises(TransactionAborted): tx.executions.find(uuid4(), target=TARGET)
                assert len(events['sql']) == before
        else:
            with execution_transaction(registered) as tx:
                assert tx.executions.find(uuid4(), target=TARGET) is None
        before = len(events['sql'])
        with pytest.raises(TransactionAborted): tx.executions.find(uuid4(), target=TARGET)
        assert len(events['sql']) == before


def test_inference_family_disappearing_is_integrity_not_withholding(case, registered, monkeypatch):
    from dataclasses import replace as dc_replace
    original = PatientRepository.load_latest_known
    def absent(self, *args, **kwargs):
        return dc_replace(original(self, *args, **kwargs), records=())
    monkeypatch.setattr(PatientRepository, 'load_latest_known', absent)
    with pytest.raises(StorageIntegrityError): run(registered, request_for(case))
    assert counts(registered) == (3, 0)


def test_request_cutoff_cannot_claim_future_prefix(case, registered):
    request = request_for(case)
    request = replace(request, lineage=replace(request.lineage,
        cutoff=replace(request.lineage.cutoff, fact_watermark=999)))
    with pytest.raises(StorageIntegrityError): run(registered, request)
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('part', ['request_id', 'intended_use', 'destination', 'decimal', 'event_offset',
    'requested_offset', 'inference_version', 'inference_id', 'lineage_metadata', 'lineage_limitation',
    'policy_window', 'policy_availability', 'policy_concept', 'exclusion'])
def test_adversarial_deep_retry_differences_conflict_without_reads(case, registered, monkeypatch, part):
    request = request_for(case)
    saved = run(registered, request)
    if part in ('request_id', 'destination'):
        changed = replace(request, target=replace(request.target, **{part:'different'}))
    elif part == 'intended_use':
        changed = replace(request, target=replace(request.target, intended_use=replace(request.target.intended_use, version='other')))
    elif part == 'decimal': changed = replace(request, comparison=replace(request.comparison, earlier_kg=Decimal('82.00')))
    elif part == 'event_offset':
        changed = replace(request, comparison=replace(request.comparison, earlier_event=request.comparison.earlier_event.astimezone(timezone.utc)))
    elif part == 'requested_offset':
        changed = replace(request, requested_at=request.requested_at.astimezone(timezone(timedelta(hours=5,minutes=30))))
    elif part in ('inference_version', 'inference_id'):
        data = request.model_dump(mode='json')
        old = request.inference.model_dump(mode='json')
        def walk(value):
            if isinstance(value, dict):
                if value == old: value['version' if part == 'inference_version' else 'id'] = 'different'
                else:
                    for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(data)
        changed = workflow.WeightTrendReviewRequest.model_validate(data)
    elif part.startswith('lineage_'):
        nodes = request.lineage.nodes
        node = nodes[0]
        if part == 'lineage_metadata':
            node = replace(node, ingestion=replace(node.ingestion, ingested_at=node.ingestion.ingested_at+timedelta(microseconds=1)))
        else: node = replace(node, limitations=(*node.limitations, 'additional disclosure'))
        changed = replace(request, lineage=replace(request.lineage, nodes=(node,*nodes[1:])))
    elif part.startswith('policy_'):
        policy = request.original.policy
        if part == 'policy_window': policy = replace(policy, window_start=policy.window_start-timedelta(microseconds=1))
        elif part == 'policy_availability': policy = replace(policy, available_at=policy.available_at+timedelta(microseconds=1))
        else: policy = replace(policy, concept_id='different-concept')
        changed = replace(request, original=replace(request.original, policy=policy))
    else:
        exclusion = WeightTrendExclusion(reference=replace(request.inference,id='different'),reason='unrelated_fact')
        changed = replace(request, original=replace(request.original, exclusions=(exclusion,)))
    assert canonical_payload(changed) != canonical_payload(request)
    def forbidden(*args, **kwargs): pytest.fail('conflicting retry performed clinical work')
    monkeypatch.setattr(PatientRepository, 'capture_cutoff', forbidden)
    monkeypatch.setattr(workflow, 'select_weight_observations', forbidden)
    monkeypatch.setattr(workflow, 'issue_synthetic_weight_release', forbidden)
    with pytest.raises(RecordConflict): run(registered, changed, clock=forbidden)
    assert load(registered, request.execution_id, target=TARGET) == saved


@pytest.mark.parametrize('marker', ['SyntheticWeightProtectedExecution/v2', 'SyntheticWeightOrchestration/v1', 'other', '', {'invalid':'marker'}])
def test_adversarial_changed_retained_workflow_marker(case, registered, monkeypatch, marker):
    import json
    from hashlib import sha256
    request = request_for(case)
    saved = run(registered, request)
    data = saved.record.model_dump(mode='json')
    data['decision']['assessment']['assessor'] = marker
    payload = json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    with registered.begin() as conn:
        conn.execute(text('UPDATE weight_trend_execution SET payload=:p,payload_digest=:d'),
            {'p':payload,'d':sha256(payload.encode()).hexdigest()})
    def forbidden(*args, **kwargs): pytest.fail('marker failure reran workflow')
    monkeypatch.setattr(workflow, '_new_execution', forbidden)
    expected = RecordConflict if isinstance(marker,str) and marker else StorageIntegrityError
    with pytest.raises(expected) as error: run(registered, request, clock=forbidden)
    private(error.value)
    assert counts(registered) == (3, 1)


@pytest.mark.parametrize('corruption', ['payload', 'digest', 'version', 'nested'])
@pytest.mark.parametrize('scope', ['patient', 'encounter'])
def test_adversarial_find_foreign_corruption_never_decoded(case, registered, monkeypatch, corruption, scope):
    request = request_for(case)
    run(registered, request)
    with registered.begin() as conn:
        if corruption == 'version':
            conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            conn.execute(text('UPDATE weight_trend_execution SET payload_version=99'))
        elif corruption == 'nested':
            import json
            from hashlib import sha256
            payload = conn.execute(text('SELECT payload FROM weight_trend_execution')).scalar_one()
            data = json.loads(payload)
            data['comparison'] = {'invalid': 'CONFIDENTIAL_SYNTHETIC'}
            payload = json.dumps(data, sort_keys=True, separators=(',', ':'))
            conn.execute(text('UPDATE weight_trend_execution SET payload=:p,payload_digest=:d'),
                {'p': payload, 'd': sha256(payload.encode()).hexdigest()})
        elif corruption == 'digest': conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
        else: conn.execute(text("UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC'"))
    target = replace(TARGET, **({'patient_id':'foreign'} if scope=='patient' else {'encounter_id':'foreign'}))
    def forbidden(*args): pytest.fail('decoded foreign content')
    monkeypatch.setattr(executions, '_decode', forbidden)
    with execution_transaction(registered) as tx:
        assert tx.executions.find(request.execution_id,target=target) is None
        assert tx.executions.find(uuid4(),target=target) is None
        assert tx.repository.capture_cutoff().fact_watermark == 3


@pytest.mark.parametrize('stage', ['weight_trend_selection_manifest', 'compare_recorded_weights',
    'build_weight_trend_inference', 'weight_trend_lineage_witness', 'build_weight_trend_snapshot',
    'build_weight_trend_candidate', 'render_weight_trend', 'evaluate_weight_trend',
    'validate_weight_trend_content', 'assess_weight_trend_dependencies', 'assess_weight_trend_final_context',
    'issue_synthetic_weight_release', 'assemble_weight_trend_runtime', 'assess_release', 'decide_release',
    'WeightTrendExecutionRecord', 'assess_weight_trend_final_recheck', 'select_weight_observations'])
def test_adversarial_each_builder_failure_aborts_and_sanitizes(case, registered, monkeypatch, stage):
    import traceback
    request = request_for(case)
    def fail(*args, **kwargs): raise RuntimeError(SECRET)
    if stage == 'select_weight_observations':
        original = workflow.select_weight_observations
        calls = 0
        def final_selection_failure(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2: raise RuntimeError(SECRET)
            return original(*args, **kwargs)
        monkeypatch.setattr(workflow, stage, final_selection_failure)
    else:
        monkeypatch.setattr(workflow, stage, fail)
    with pytest.raises(TransactionAborted) as error: run(registered, request)
    private(error.value)
    assert SECRET not in repr(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__
    # Python retains introspectable context; standard traceback formatting suppresses it.
    assert error.value.__context__ is not None
    assert SECRET not in ''.join(traceback.format_exception(error.value))
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('stage', ['build_weight_trend_candidate', 'assess_release', 'WeightTrendExecutionRecord'])
@pytest.mark.parametrize('category', [KeyboardInterrupt, SystemExit])
def test_adversarial_process_control_exception_identity_preserved(case, registered, monkeypatch, stage, category):
    request = request_for(case)
    interruption = category('synthetic interruption')
    def fail(*args, **kwargs): raise interruption
    monkeypatch.setattr(workflow, stage, fail)
    with pytest.raises(category) as error: run(registered, request)
    assert error.value is interruption
    assert counts(registered) == (3, 0)


@pytest.mark.parametrize('committed', [False, True])
def test_adversarial_explicit_retry_after_completion_uncertainty(case, registered, monkeypatch, committed):
    request = request_for(case)
    original = registered.dialect.do_commit
    def fail(conn):
        if committed: original(conn)
        raise RuntimeError(SECRET)
    with monkeypatch.context() as patch:
        patch.setattr(registered.dialect, 'do_commit', fail)
        with pytest.raises(TransactionAborted, match='transaction completion could not be confirmed'):
            run(registered, request)
    assert counts(registered) == (3, 1 if committed else 0)
    retained = load(registered,request.execution_id,target=TARGET) if committed else None
    change_evidence(registered,case,'same_value')
    if committed:
        def forbidden(*args, **kwargs): pytest.fail('committed uncertain attempt recomputed')
        monkeypatch.setattr(workflow, '_new_execution', forbidden)
        assert run(registered,request,clock=forbidden) == retained
    else:
        saved = run(registered,request)
        assert saved.record.decision.outcome == 'withheld'
        assert saved.record.final_recheck.outcome == 'materially_changed'
    assert counts(registered) == (4,1)


@pytest.mark.parametrize('kind', ['inference','third','unrelated'])
def test_adversarial_retry_after_other_later_changes(case, registered, monkeypatch, kind):
    request = request_for(case)
    saved = run(registered,request)
    change_evidence(registered,case,kind)
    def forbidden(*args, **kwargs): pytest.fail('retry accessed new clinical evidence')
    monkeypatch.setattr(PatientRepository,'capture_cutoff',forbidden)
    monkeypatch.setattr(PatientRepository,'resolve_lineage',forbidden)
    monkeypatch.setattr(workflow,'select_weight_observations',forbidden)
    assert run(registered,request,clock=forbidden) == saved


@pytest.mark.parametrize('component', ['safety', 'fidelity', 'dependencies', 'freshness_items', 'authorization_digest', 'runtime_output'])
def test_adversarial_required_governance_evidence_cannot_be_removed(case, registered, monkeypatch, component):
    if component == 'safety':
        original = workflow.evaluate_weight_trend
        monkeypatch.setattr(workflow,'evaluate_weight_trend',lambda **kw:replace(original(**kw),checks=original(**kw).checks[:1]))
    elif component == 'fidelity':
        original = workflow.validate_weight_trend_content
        monkeypatch.setattr(workflow,'validate_weight_trend_content',lambda **kw:replace(original(**kw),outcome='unavailable'))
    elif component == 'dependencies': monkeypatch.setattr(workflow,'assess_weight_trend_dependencies',lambda **kw:())
    elif component == 'freshness_items':
        original = workflow.assess_weight_trend_final_context
        monkeypatch.setattr(workflow,'assess_weight_trend_final_context',lambda **kw:replace(original(**kw),items=()))
    elif component == 'authorization_digest':
        original = workflow.issue_synthetic_weight_release
        monkeypatch.setattr(workflow,'issue_synthetic_weight_release',lambda **kw:replace(original(**kw),content_digest='0'*64))
    else:
        original = workflow.assemble_weight_trend_runtime
        monkeypatch.setattr(workflow,'assemble_weight_trend_runtime',lambda **kw:replace(original(**kw),output_state='stale'))
    saved=run(registered,request_for(case))
    assert saved.record.decision.outcome == 'withheld'
    assert load(registered,saved.record.execution_id,target=TARGET) == saved


@pytest.mark.parametrize('kind', ['same_value', 'third'])
def test_adversarial_same_value_and_third_race_with_events(case, registered, monkeypatch, kind):
    request=request_for(case)
    contender=create_database(registered.url.database)
    attempted=Event()
    def zero(conn, record): conn.execute('PRAGMA busy_timeout=0')
    def before(conn,cursor,statement,parameters,context,executemany):
        if statement == 'BEGIN IMMEDIATE': attempted.set()
    event.listen(contender,'connect',zero)
    event.listen(contender,'before_cursor_execute',before)
    original=workflow.assess_weight_trend_final_recheck
    def protected(**kwargs):
        result=original(**kwargs)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(change_evidence,contender,case,kind)
            assert attempted.wait(5)
            with pytest.raises(OperationalError): pending.result(timeout=5)
        return result
    monkeypatch.setattr(workflow,'assess_weight_trend_final_recheck',protected)
    try:
        saved=run(registered,request)
        assert saved.record.decision.outcome=='released'
        change_evidence(contender,case,kind)
        assert load(registered,request.execution_id,target=TARGET)==saved
    finally: contender.dispose()
