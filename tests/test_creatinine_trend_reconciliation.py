"""Explicit D5 recovery from durable synthetic execution rows only."""
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from decimal import Decimal
import ast
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.execution import creatinine_trend_workflow as workflow
from app.execution.creatinine_trend_execution import CreatinineTrendReviewRequest
from app.persistence import creatinine_executions as store
from app.persistence.database import create_database
from app.persistence.errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, SchemaMismatch,
    StorageIntegrityError, TransactionAborted, TransactionCompletionUnknown,
)
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository
from app.persistence.shared_transaction import execution_transaction
from test_persistence import ROOT, TARGET, database, registered, replace
from test_creatinine_trend_release import case
from test_creatinine_trend_workflow import request_for, run, change, counts, TIME
from test_creatinine_trend_execution_persistence import row, mutate_payload, write_payload
from test_weight_trend_shared_transaction import trace, private, SECRET

reconcile = workflow.reconcile_creatinine_trend_execution


def forbid_work(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('reconciliation invoked execution, current clinical work, or a clock')
    for name in ('capture_cutoff', 'resolve_lineage', 'list_history', 'list_latest_known',
                 'load_latest_known', 'load_fact', 'load_patient', 'load_encounter'):
        monkeypatch.setattr(PatientRepository, name, forbidden)
    # Keep D1/D2 pure validation of retained payload intact. These are workflow
    # producers, not the existing contract validator's retained-content checks.
    for name in ('execute_creatinine_trend_review', 'execution_transaction', '_new_execution',
                 '_replay', '_tick', '_utc_now', 'select_creatinine_observations',
                 'compare_recorded_creatinine', 'build_creatinine_trend_inference',
                 'assess_creatinine_trend_final_recheck', 'build_creatinine_trend_snapshot',
                 'build_creatinine_trend_candidate', 'render_creatinine_trend',
                 'evaluate_creatinine_trend', 'validate_creatinine_trend_content',
                 'assess_creatinine_trend_final_context', 'assess_creatinine_trend_dependencies',
                 'issue_synthetic_creatinine_release', 'assemble_creatinine_trend_runtime',
                 'assess_release', 'decide_release'):
        monkeypatch.setattr(workflow, name, forbidden)
    monkeypatch.setattr(store, '_now', forbidden)


@pytest.mark.parametrize('actor,outcome', [('synthetic-creatinine-orchestrator', 'released'), ('denied', 'withheld')])
def test_exact_retention_read_only_without_work(case, registered, monkeypatch, actor, outcome):
    request = request_for(case, actor=actor)
    saved = run(registered, request)
    before = row(registered)
    forbid_work(monkeypatch)
    with trace(registered) as events:
        result = reconcile(registered, request)
    assert result.status == 'committed_match'
    assert canonical_payload(result.stored) == canonical_payload(saved)
    assert result.stored.record.decision.outcome == outcome
    assert result.stored.record.finalized_at == saved.record.finalized_at
    assert result.stored.ingested_at == saved.ingested_at
    assert events['sql'].count('BEGIN IMMEDIATE') == 1 and len(events['connections']) == 1
    assert not any(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'DROP', 'ALTER')) for s in events['sql'])
    assert not any('fact_revision' in s or 'revision_link' in s for s in events['sql'])
    assert row(registered) == before and counts(registered) == (3, 1)
    with pytest.raises(FrozenInstanceError): result.status = 'absent'
    with pytest.raises(ValidationError): result.stored.ingested_at = TIME
    with pytest.raises(ValidationError): result.stored.record.original.selected_samples[0].identifier = 'different'


@pytest.mark.parametrize('status,stored', [('committed_match', None), ('committed_match', object()),
    ('absent', object()), ('conflict', None), ('corrupt', None), ('unknown', None)])
def test_result_invalid_states(status, stored):
    with pytest.raises(ValueError): workflow.CreatinineTrendReconciliationResult(status, stored)


def test_absence_does_no_work(case, registered, monkeypatch):
    request = request_for(case)
    forbid_work(monkeypatch)
    with trace(registered) as events:
        assert reconcile(registered, request) == workflow.CreatinineTrendReconciliationResult('absent', None)
    assert counts(registered) == (3, 0)
    assert not any('fact_revision' in s or s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for s in events['sql'])


@pytest.mark.parametrize('part', ['target', 'actor', 'manifest', 'comparison', 'decimal', 'offset',
    'inference', 'lineage', 'requested_at', 'requested_offset', 'sample', 'digest'])
def test_exact_request_differences_conflict(case, registered, monkeypatch, part):
    request = request_for(case)
    run(registered, request)
    before = row(registered)
    if part == 'target': changed = replace(request, target=replace(request.target, recipient='different'))
    elif part == 'actor': changed = replace(request, actor='different')
    elif part == 'manifest': changed = replace(request, original=replace(request.original, cutoff=replace(request.original.cutoff, captured_at=TIME)))
    elif part in ('comparison', 'decimal', 'offset'):
        m = request.original
        if part == 'offset': m = replace(m, selected_sample_times=(m.selected_sample_times[0].astimezone(timezone.utc), m.selected_sample_times[1]))
        else: m = replace(m, selected_values=(Decimal('1.10' if part == 'comparison' else '1.000'), m.selected_values[1]))
        changed = replace(request, original=m, comparison=m.comparison)
    elif part == 'lineage': changed = replace(request, lineage=replace(request.lineage, cutoff=replace(request.lineage.cutoff, captured_at=TIME)))
    elif part == 'sample':
        m = request.original
        changed = replace(request, original=replace(m, selected_samples=(replace(m.selected_samples[0], identifier='other'), m.selected_samples[1])))
    elif part == 'digest':
        m = replace(request.original, selected_payload_digests=('0'*64, request.original.selected_payload_digests[1]))
        nodes = tuple(replace(n, payload_digest='0'*64) if n.reference == m.selected[0] else n for n in request.lineage.nodes)
        changed = replace(request, original=m, lineage=replace(request.lineage, nodes=nodes))
    elif part == 'inference':
        data = request.model_dump(mode='json')
        old = request.inference.model_dump(mode='json')
        def walk(value):
            if isinstance(value, dict):
                if value == old: value['version'] = 'other'
                else:
                    for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(data)
        changed = CreatinineTrendReviewRequest.model_validate(data)
    else:
        t = request.requested_at
        changed = replace(request, requested_at=t-timedelta(seconds=1) if part == 'requested_at' else t.astimezone(timezone(timedelta(hours=5, minutes=30))))
    assert canonical_payload(changed) != canonical_payload(request)
    forbid_work(monkeypatch)
    with pytest.raises(RecordConflict) as error: reconcile(registered, changed)
    private(error.value)
    assert row(registered) == before


@pytest.mark.parametrize('scope', ['patient', 'encounter'])
@pytest.mark.parametrize('corrupt', [False, True])
def test_foreign_scope_is_absence_without_decode(case, registered, monkeypatch, scope, corrupt):
    request = request_for(case)
    run(registered, request)
    if corrupt: write_payload(registered, SECRET)
    target = replace(TARGET, **{scope+'_id': 'foreign'})
    foreign = replace(request, target=replace(request.target, context=target),
        original=replace(request.original, target=target), lineage=replace(request.lineage, target=target))
    def forbidden(*args): pytest.fail('foreign row decoded')
    monkeypatch.setattr(store, '_decode', forbidden)
    forbid_work(monkeypatch)
    assert reconcile(registered, foreign) == reconcile(registered, replace(foreign, execution_id=uuid4()))
    assert reconcile(registered, foreign).status == 'absent'


@pytest.mark.parametrize('part', ['digest', 'json', 'version', 'id', 'scope', 'workflow', 'typed', 'ingested', 'finalized', 'decision'])
def test_visible_corruption_never_absence_or_conflict(case, registered, part):
    request = request_for(case)
    run(registered, request)
    if part == 'json': write_payload(registered, SECRET)
    elif part in ('digest', 'version', 'ingested'):
        column, value = {'digest': ('payload_digest', 'bad'), 'version': ('payload_version', 99), 'ingested': ('ingested_at', SECRET)}[part]
        with registered.begin() as conn:
            conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            conn.execute(text('UPDATE creatinine_trend_execution SET '+column+'=:v'), {'v': value})
    else:
        def corrupt(d):
            if part == 'id': d['execution_id'] = str(uuid4())
            elif part == 'scope': d['target']['context']['patient_id'] = 'foreign'
            elif part == 'workflow': d['decision']['assessment']['assessor'] = 'SyntheticCreatinineProtectedExecution/v2'
            elif part == 'typed': d['comparison'] = {'invalid': SECRET}
            elif part == 'finalized': d['finalized_at'] = '2000-01-01T00:00:00+00:00'
            else: d['decision']['outcome'] = 'withheld'
        mutate_payload(registered, corrupt)
    with pytest.raises(StorageIntegrityError) as error: reconcile(registered, replace(request, actor='different'))
    private(error.value)


@pytest.mark.parametrize('outcome', ['released', 'withheld'])
@pytest.mark.parametrize('later', ['value', 'same_value', 'third', 'duplicate', 'inference', 'unrelated', 'expiry', 'corrupt_facts'])
def test_later_state_cannot_change_retained_completion(case, registered, monkeypatch, outcome, later):
    request = request_for(case, actor='denied' if outcome == 'withheld' else 'synthetic-creatinine-orchestrator')
    saved = run(registered, request)
    if later == 'corrupt_facts':
        with registered.begin() as conn: conn.execute(text("UPDATE fact_revision SET payload='{}'"))
    elif later != 'expiry': change(registered, case, later)
    before = row(registered)
    forbid_work(monkeypatch)
    assert canonical_payload(reconcile(registered, request).stored) == canonical_payload(saved)
    assert row(registered) == before


@pytest.mark.parametrize('material', [False, True])
def test_absent_then_explicit_execution(case, registered, material):
    request = request_for(case)
    assert reconcile(registered, request).status == 'absent'
    assert counts(registered) == (3, 0)
    if material: change(registered, case, 'same_value')
    saved = run(registered, request)
    assert saved.record.decision.outcome == ('withheld' if material else 'released')
    assert reconcile(registered, request).stored == saved


@pytest.mark.parametrize('committed', [False, True])
@pytest.mark.parametrize('outcome', ['released', 'withheld'])
def test_uncertainty_recovered_only_by_explicit_lookup(case, registered, monkeypatch, committed, outcome):
    request = request_for(case, actor='denied' if outcome == 'withheld' else 'synthetic-creatinine-orchestrator')
    commit = registered.dialect.do_commit
    append = store._CreatinineExecutionAdapter.append
    provisional = []
    def observed(*args, **kw):
        saved = append(*args, **kw); provisional.append(saved); return saved
    def fail(conn):
        if committed: commit(conn)
        raise RuntimeError(SECRET)
    def forbidden(*args, **kw): pytest.fail('D4 invoked automatic reconciliation')
    with monkeypatch.context() as m:
        m.setattr(store._CreatinineExecutionAdapter, 'append', observed)
        m.setattr(registered.dialect, 'do_commit', fail)
        m.setattr(workflow, 'reconcile_creatinine_trend_execution', forbidden)
        with pytest.raises(TransactionCompletionUnknown) as error: run(registered, request)
        private(error.value)
    forbid_work(monkeypatch)
    result = reconcile(registered, request)
    assert result.status == ('committed_match' if committed else 'absent')
    assert result.stored == (provisional[0] if committed else None)
    if committed:
        assert result.stored.ingested_at == provisional[0].ingested_at
        assert result.stored.record.finalized_at == provisional[0].record.finalized_at
    assert counts(registered) == (3, int(committed))


@pytest.mark.parametrize('kind', ['sql', 'internal', 'completion', 'not_found', 'message'])
def test_lookup_errors_never_become_absence(case, registered, monkeypatch, kind):
    request = request_for(case)
    run(registered, request)
    listener = None
    if kind == 'sql':
        def listener(*args): raise OperationalError(SECRET, {}, RuntimeError(SECRET))
        event.listen(registered, 'before_cursor_execute', listener)
    elif kind == 'completion':
        def fail(*args): raise RuntimeError(SECRET)
        monkeypatch.setattr(registered.dialect, 'do_commit', fail)
    else:
        def fail(*args, **kw):
            raise (RecordNotFound(SECRET) if kind == 'not_found' else RuntimeError('not found' if kind == 'message' else SECRET))
        monkeypatch.setattr(workflow, 'find_creatinine_trend_execution', fail)
    try:
        with pytest.raises(TransactionAborted) as error: reconcile(registered, request)
        assert type(error.value) is TransactionAborted
        private(error.value)
    finally:
        if listener: event.remove(registered, 'before_cursor_execute', listener)


@pytest.mark.parametrize('kind', ['dict', 'forged', 'comparison', 'session', 'connection'])
def test_invalid_input(case, registered, kind):
    request = request_for(case)
    if kind in ('session', 'connection'):
        with (Session(registered) if kind == 'session' else registered.connect()) as handle:
            with pytest.raises(PersistenceInputError): reconcile(handle, request)
    else:
        if kind == 'dict': request = request.model_dump()
        elif kind == 'forged': request = request.model_copy(update={'actor': SECRET, 'requested_at': 'invalid'})
        else: request = request.model_copy(update={'comparison': replace(request.comparison, earlier_value=Decimal('1.1'))})
        with trace(registered) as events:
            with pytest.raises(PersistenceInputError) as error: reconcile(registered, request)
            private(error.value)
            assert events['sql'] == []


def test_unmigrated_database_is_error(case, tmp_path):
    engine = create_database(tmp_path/'unmigrated.sqlite3')
    try:
        with pytest.raises(SchemaMismatch) as error: reconcile(engine, request_for(case))
        private(error.value)
    finally: engine.dispose()


@pytest.mark.parametrize('category', [KeyboardInterrupt, SystemExit])
def test_process_control_during_read_releases_transaction(case, registered, category):
    request = request_for(case)
    signal = category('interruption')
    def fail(conn, cursor, statement, parameters, context, many):
        if 'FROM creatinine_trend_execution' in statement: raise signal
    event.listen(registered, 'before_cursor_execute', fail)
    try:
        with pytest.raises(category) as error: reconcile(registered, request)
        assert error.value is signal
    finally: event.remove(registered, 'before_cursor_execute', fail)
    assert reconcile(registered, request).status == 'absent'


def test_lock_contention_is_bounded_error_not_absence(case, registered):
    request = request_for(case)
    contender = create_database(registered.url.database)
    def zero(connection, record): connection.execute('PRAGMA busy_timeout=0')
    event.listen(contender, 'connect', zero)
    try:
        with execution_transaction(registered):
            with trace(contender) as events:
                with pytest.raises(TransactionAborted) as error: reconcile(contender, request)
                private(error.value)
                assert events['sql'] == ['BEGIN IMMEDIATE']
        assert reconcile(contender, request).status == 'absent'
    finally: contender.dispose()


@pytest.mark.parametrize('outcome', ['released', 'withheld'])
@pytest.mark.parametrize('seed', ['1', '777'])
def test_reopen_separate_process_exact_recovery(case, registered, outcome, seed):
    request = request_for(case, actor='denied' if outcome == 'withheld' else 'synthetic-creatinine-orchestrator')
    saved = run(registered, request)
    path = registered.url.database
    registered.dispose()
    reopened = create_database(path)
    try: assert canonical_payload(reconcile(reopened, request).stored) == canonical_payload(saved)
    finally: reopened.dispose()
    script = '''
import sys
from app.execution.creatinine_trend_execution import CreatinineTrendReviewRequest
from app.execution.creatinine_trend_workflow import reconcile_creatinine_trend_execution
from app.persistence.database import create_database
from app.persistence.mapping import canonical_payload
engine=create_database(sys.argv[1])
try:
    result=reconcile_creatinine_trend_execution(engine,CreatinineTrendReviewRequest.model_validate_json(sys.argv[2]))
    print(result.status)
    print(canonical_payload(result.stored))
finally: engine.dispose()
'''
    proc = subprocess.run([sys.executable, '-c', script, path, canonical_payload(request)],
        capture_output=True, text=True, check=True, timeout=30, cwd=ROOT,
        env={**os.environ, 'PYTHONHASHSEED': seed, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT/'backend')})
    assert proc.stdout.splitlines() == ['committed_match', canonical_payload(saved)]


def test_generated_fields_and_same_matcher(case, registered, monkeypatch):
    request = request_for(case)
    change(registered, case, 'unrelated')
    ticks = iter(TIME+timedelta(seconds=i) for i in range(4))
    saved = run(registered, request, lambda: next(ticks))
    assert saved.record.final_recheck.final.cutoff.fact_watermark == 4
    assert saved.record.finalized_at == TIME+timedelta(seconds=3)
    matcher = workflow._require_creatinine_request_match
    calls = []
    def observed(stored, candidate):
        calls.append(candidate.execution_id)
        return matcher(stored, candidate)
    monkeypatch.setattr(workflow, '_require_creatinine_request_match', observed)
    assert reconcile(registered, request).stored == saved
    assert run(registered, request) == saved
    assert calls == [request.execution_id, request.execution_id]


def test_lookup_object_is_returned_without_replacement(case, registered, monkeypatch):
    request = request_for(case)
    saved = run(registered, request)
    monkeypatch.setattr(workflow, 'find_creatinine_trend_execution', lambda *args, **kw: saved)
    assert reconcile(registered, request).stored is saved


def test_reconciliation_has_no_automatic_execution_or_framework():
    tree = ast.parse(Path(workflow.__file__).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'reconcile_creatinine_trend_execution')
    calls = {ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
    assert calls == {'_validate_request', 'find_creatinine_trend_execution', '_require_creatinine_request_match',
        'CreatinineTrendReconciliationResult', 'next', 'isinstance', 'category', 'TransactionAborted'}
    assert not any(isinstance(n, (ast.For, ast.While, ast.With)) for n in ast.walk(fn))
    assert {n.name for n in tree.body if isinstance(n, ast.ClassDef)} == {'CreatinineTrendReconciliationResult'}
