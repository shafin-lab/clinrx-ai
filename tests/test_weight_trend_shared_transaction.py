"""Atomic synthetic persistence, independently observed through real SQLite."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields
from datetime import timedelta
import sqlite3
import traceback
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.clinical.common import ContextTarget, Reference
from app.persistence import executions, repository
from app.persistence.database import create_database
from app.persistence.errors import (
    PersistenceInputError, QueryLimitExceeded, RecordConflict, RecordNotFound,
    SchemaMismatch, ScopeMismatch, StorageIntegrityError, TransactionAborted, UnsupportedOperation,
)
from app.persistence.executions import append_weight_trend_execution as append, load_weight_trend_execution as load
from app.persistence.lineage import LineageLimits
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from test_persistence import TARGET, database, registered, fact, patient, replace
from test_weight_trend_execution_persistence import case, make_record

SECRET = 'CONFIDENTIAL_SYNTHETIC'


@contextmanager
def trace(engine):
    events = dict(sql=[], connections=set(), commits=0, rollbacks=0)
    def sql(conn, cursor, statement, parameters, context, executemany):
        events['sql'].append(statement)
        events['connections'].add(id(conn))
    def commit(conn): events['commits'] += 1
    def rollback(conn): events['rollbacks'] += 1
    listeners = [('before_cursor_execute', sql), ('commit', commit), ('rollback', rollback)]
    for name, handler in listeners: event.listen(engine, name, handler)
    try:
        yield events
    finally:
        for name, handler in listeners: event.remove(engine, name, handler)


def counts(engine):
    # No application BEGIN IMMEDIATE hook: this is a short external read observer.
    conn = sqlite3.connect(f'file:{engine.url.database}?mode=ro', uri=True, timeout=0)
    try:
        return tuple(conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                     for table in ('fact_revision', 'weight_trend_execution'))
    finally:
        conn.close()


def private(error):
    rendered = ''.join(traceback.format_exception(error))
    for fragment in (SECRET, 'input_value=', 'INSERT INTO', 'SELECT *', 'driver detail'):
        assert fragment not in rendered
    assert error.__cause__ is None


def rejected(tx, events):
    before = list(events['sql'])
    with pytest.raises(TransactionAborted): tx.repository.capture_cutoff()
    with pytest.raises(TransactionAborted): tx.executions.load(uuid4(), target=TARGET)
    # Guard precedes even argument binding / input validation.
    with pytest.raises(TransactionAborted): tx.executions.append()
    assert events['sql'] == before


@pytest.mark.parametrize('variant', ['released', 'withheld', 'failure'])
def test_atomic_success_and_single_connection(case, registered, variant):
    record = make_record(case, variant)
    before = counts(registered)
    with trace(registered) as events:
        with execution_transaction(registered) as tx:
            assert {f.name for f in fields(tx)} == {'repository', 'executions', 'creatinine_executions', 'patient_state_executions', 'micro_antimicrobial_executions', 'circulatory_executions'}
            assert not any(hasattr(tx, name) for name in ('session', 'connection', 'commit', 'rollback', 'reset'))
            assert not any(isinstance(value, Session) for value in vars(tx).values())
            with pytest.raises(FrozenInstanceError): tx.repository = None
            saved_fact = tx.repository.append_fact(fact(id='atomic'), target=TARGET)
            saved = tx.executions.append(record, target=TARGET)
            assert tx.executions.load(record.execution_id, target=TARGET) == saved
            assert tx.repository.load_fact(saved_fact.fact.reference, target=TARGET) == saved_fact
            assert counts(registered) == before
            assert events['commits'] == 0
            assert len(events['connections']) == 1
            assert events['sql'].count('BEGIN IMMEDIATE') == 1
        assert events['commits'] == 1 and events['rollbacks'] == 0
        rejected(tx, events)
    assert counts(registered) == (before[0] + 1, before[1] + 1)
    assert load(registered, record.execution_id, target=TARGET) == saved


@pytest.mark.parametrize('caught', [False, True])
@pytest.mark.parametrize('failure,category', [
    ('execution_conflict', RecordConflict), ('repository_conflict', RecordConflict),
    ('repository_missing', RecordNotFound), ('execution_missing', RecordNotFound),
    ('repository_validation', PersistenceInputError), ('execution_validation', PersistenceInputError),
    ('execution_scope', ScopeMismatch), ('query_limit', QueryLimitExceeded),
    ('unsupported', UnsupportedOperation), ('wrong_arguments', TransactionAborted),
])
def test_all_failures_abort_both_even_when_caught(case, registered, failure, category, caught):
    record = make_record(case)
    before = counts(registered)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted if caught else category):
            with execution_transaction(registered) as tx:
                tx.repository.append_fact(fact(id='prior'), target=TARGET)
                tx.executions.append(record, target=TARGET)
                def fail():
                    if failure == 'execution_conflict':
                        tx.executions.append(replace(record, finalized_at=record.finalized_at + timedelta(seconds=1)), target=TARGET)
                    elif failure == 'repository_conflict':
                        tx.repository.append_fact(fact(id='prior', concept_id='changed'), target=TARGET)
                    elif failure == 'repository_missing': tx.repository.load_patient('absent')
                    elif failure == 'execution_missing': tx.executions.load(uuid4(), target=TARGET)
                    elif failure == 'repository_validation': tx.repository.append_fact(fact().model_copy(update={'origin': SECRET}), target=TARGET)
                    elif failure == 'execution_validation': tx.executions.append({'secret': SECRET}, target=TARGET)
                    elif failure == 'execution_scope':
                        tx.executions.append(record, target=replace(TARGET, encounter_id='foreign'))
                    elif failure == 'query_limit':
                        tx.repository.resolve_lineage(record.inference, target=TARGET,
                            cutoff=tx.repository.capture_cutoff(), limits=LineageLimits(max_records=1))
                    elif failure == 'unsupported':
                        tx.repository.append_fact(fact(), target=ContextTarget(patient_id=TARGET.patient_id,
                            longitudinal_context_id='unsupported'))
                    else: tx.repository.capture_cutoff(unexpected=SECRET)
                if caught:
                    with pytest.raises(category) as error: fail()
                    private(error.value)
                    rejected(tx, events)
                else:
                    fail()
        assert events['commits'] == 0
        rejected(tx, events)
    assert counts(registered) == before


@pytest.mark.parametrize('adapter', ['repository', 'executions'])
def test_validation_failure_before_any_operation_sql(case, registered, adapter):
    with trace(registered) as events:
        with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
            before = list(events['sql'])
            with pytest.raises(PersistenceInputError):
                if adapter == 'repository': tx.repository.append_fact(fact().model_copy(update={'origin': SECRET}), target=TARGET)
                else: tx.executions.append({}, target=TARGET)
            assert events['sql'] == before
            rejected(tx, events)


@pytest.mark.parametrize('adapter', ['repository', 'executions'])
@pytest.mark.parametrize('kind', ['sql', 'internal', 'interrupt'])
def test_injected_operation_errors_are_guarded(case, registered, adapter, kind):
    record = make_record(case)
    before = counts(registered)
    table = 'fact_revision' if adapter == 'repository' else 'weight_trend_execution'
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO ' + table):
            if kind == 'sql': raise OperationalError('SELECT * ' + SECRET, {'secret': SECRET}, Exception('driver detail'))
            if kind == 'internal': raise RuntimeError(SECRET)
            raise KeyboardInterrupt(SECRET)
    event.listen(registered, 'after_cursor_execute', fail)
    try:
        with trace(registered) as events:
            with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
                with pytest.raises(KeyboardInterrupt if kind == 'interrupt' else TransactionAborted) as error:
                    if adapter == 'repository': tx.repository.append_fact(fact(), target=TARGET)
                    else: tx.executions.append(record, target=TARGET)
                if kind != 'interrupt': private(error.value)
                rejected(tx, events)
            rejected(tx, events)
    finally:
        event.remove(registered, 'after_cursor_execute', fail)
    assert counts(registered) == before


@pytest.mark.parametrize('kind', ['repository', 'execution', 'execution_version'])
def test_malformed_reads_poison_shared_state(case, registered, kind):
    record = make_record(case)
    append(registered, record, target=TARGET)
    with registered.begin() as conn:
        if kind == 'repository': conn.execute(text("UPDATE fact_revision SET payload='{}'"))
        elif kind == 'execution': conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
        else:
            conn.exec_driver_sql('PRAGMA ignore_check_constraints=ON')
            conn.execute(text('UPDATE weight_trend_execution SET payload_version=2'))
    with trace(registered) as events:
        with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
            with pytest.raises(StorageIntegrityError) as error:
                if kind == 'repository': tx.repository.load_fact(record.inference, target=TARGET)
                else: tx.executions.load(record.execution_id, target=TARGET)
            private(error.value)
            rejected(tx, events)


def test_empty_history_and_unresolved_lineage_are_normal_results(registered):
    with execution_transaction(registered) as tx:
        cutoff = tx.repository.capture_cutoff()
        assert tx.repository.list_history(target=TARGET, cutoff=cutoff).records == ()
        inference = fact('inference')  # Its declared observation is intentionally absent.
        tx.repository.append_fact(inference, target=TARGET)
        graph = tx.repository.resolve_lineage(inference.reference, target=TARGET,
            cutoff=tx.repository.capture_cutoff(), limits=LineageLimits())
        assert graph.coverage == 'partial'
        assert graph.unresolved[0].reference == inference.inputs[0]
        assert tx.repository.capture_cutoff().fact_watermark == 1
    assert counts(registered) == (1, 0)


@pytest.mark.parametrize('committed', [False, True])
def test_idempotency_preserves_metadata_without_second_insert(case, registered, monkeypatch, committed):
    record = make_record(case)
    saved = append(registered, record, target=TARGET) if committed else None
    with trace(registered) as events:
        with execution_transaction(registered) as tx:
            if saved is None: saved = tx.executions.append(record, target=TARGET)
            before = len(events['sql'])
            def forbidden(): pytest.fail('retry refreshed ingestion time')
            monkeypatch.setattr(executions, '_now', forbidden)
            assert tx.executions.append(record, target=TARGET) == saved
            assert tx.executions.load(record.execution_id, target=TARGET) == saved
            assert not any(s.startswith(('INSERT', 'UPDATE', 'DELETE')) for s in events['sql'][before:])
    assert counts(registered) == (3, 1)


def test_execution_insert_leaves_fact_history_and_lineage_unchanged(case, registered):
    record = make_record(case)
    with execution_transaction(registered) as tx:
        repo = tx.repository
        before = repo.capture_cutoff()
        history = repo.list_history(target=TARGET, cutoff=before)
        graph = repo.resolve_lineage(record.inference, target=TARGET, cutoff=before, limits=LineageLimits())
        tx.executions.append(record, target=TARGET)
        assert repo.capture_cutoff().fact_watermark == before.fact_watermark
        assert repo.list_history(target=TARGET, cutoff=before) == history
        assert repo.resolve_lineage(record.inference, target=TARGET, cutoff=before, limits=LineageLimits()) == graph


@pytest.mark.parametrize('exit_kind', ['caller_error', 'interrupt', 'commit_sql', 'commit_internal'])
def test_exit_failure_invalidates_handles_and_rolls_back(case, registered, exit_kind):
    record = make_record(case)
    before = counts(registered)
    def fail_commit(conn):
        if exit_kind == 'commit_sql': raise OperationalError(SECRET, {}, Exception('driver detail'))
        raise RuntimeError(SECRET)
    if exit_kind.startswith('commit'): event.listen(registered, 'commit', fail_commit)
    try:
        with trace(registered) as events:
            expected = {'caller_error': ValueError, 'interrupt': KeyboardInterrupt}.get(exit_kind, TransactionAborted)
            returned_success = False
            with pytest.raises(expected) as error:
                with execution_transaction(registered) as tx:
                    tx.repository.append_fact(fact(), target=TARGET)
                    saved = tx.executions.append(record, target=TARGET)
                    if exit_kind == 'caller_error': raise ValueError('caller failure')
                    if exit_kind == 'interrupt': raise KeyboardInterrupt('caller interruption')
                returned_success = True
            assert not returned_success
            assert saved.record.execution_id == record.execution_id  # Still only a provisional value.
            if exit_kind.startswith('commit'):
                assert str(error.value) == 'transaction completion could not be confirmed'
                private(error.value)
            rejected(tx, events)
    finally:
        if exit_kind.startswith('commit'): event.remove(registered, 'commit', fail_commit)
    assert counts(registered) == before


def test_cross_scope_missing_is_private_and_poisoned(case, registered, monkeypatch):
    record = make_record(case)
    append(registered, record, target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload='CONFIDENTIAL_SYNTHETIC'"))
    def forbidden(*args): pytest.fail('foreign payload decoded')
    monkeypatch.setattr(executions, '_decode', forbidden)
    messages = []
    for identity in (record.execution_id, uuid4()):
        with trace(registered) as events:
            with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
                with pytest.raises(RecordNotFound) as error:
                    tx.executions.load(identity, target=replace(TARGET, encounter_id='synthetic-e2'))
                private(error.value)
                messages.append(str(error.value))
                rejected(tx, events)
    assert messages == ['execution not found in requested context'] * 2


@pytest.mark.parametrize('outer_kind', ['shared', 'legacy'])
def test_nested_contexts_are_independent_and_contend(registered, outer_kind):
    contender = create_database(registered.url.database)
    def no_wait(connection, record): connection.execute('PRAGMA busy_timeout=0')
    event.listen(contender, 'connect', no_wait)
    outer = execution_transaction if outer_kind == 'shared' else transaction
    inner = transaction if outer_kind == 'shared' else execution_transaction
    try:
        with outer(registered) as handle:
            repo = handle.repository if outer_kind == 'shared' else handle
            repo.append_fact(fact(), target=TARGET)
            with trace(contender) as events:
                with pytest.raises(OperationalError if outer_kind == 'shared' else TransactionAborted):
                    with inner(contender): pytest.fail('competing writer acquired reservation')
                assert events['sql'] == ['BEGIN IMMEDIATE']
            # An independently owned failed transaction does not join or poison this one.
            assert repo.capture_cutoff().fact_watermark == 1
    finally:
        contender.dispose()
    assert counts(registered) == (1, 0)


@pytest.mark.parametrize('handle_kind', ['session', 'connection'])
@pytest.mark.parametrize('api', ['append', 'load', 'shared'])
def test_engine_only_boundaries_reject_raw_handles(case, registered, handle_kind, api):
    record = make_record(case)
    handle = Session(registered) if handle_kind == 'session' else registered.connect()
    try:
        with trace(registered) as events:
            with pytest.raises(PersistenceInputError, match='Engine'):
                if api == 'append': append(handle, record, target=TARGET)
                elif api == 'load': load(handle, record.execution_id, target=TARGET)
                else:
                    with execution_transaction(handle): pytest.fail('raw handle accepted')
            assert events['sql'] == []
    finally:
        handle.close()


def test_standalone_apis_and_legacy_failure_behavior(case, registered):
    record = make_record(case)
    saved = append(registered, record, target=TARGET)
    assert load(registered, record.execution_id, target=TARGET) == saved
    with pytest.raises(TransactionAborted), transaction(registered) as repo:
        repo.append_fact(fact(), target=TARGET)
        with pytest.raises(RecordNotFound): repo.load_patient('missing')
    assert counts(registered) == (3, 1)
    with pytest.raises(TransactionAborted): repo.capture_cutoff()


def test_legacy_internal_exception_is_not_reclassified(registered, monkeypatch):
    def fail(*args): raise RuntimeError('legacy injected failure')
    monkeypatch.setattr(repository, '_now', fail)
    with pytest.raises(RuntimeError, match='legacy injected failure'), transaction(registered) as repo:
        repo.append_fact(fact(), target=TARGET)
    assert counts(registered) == (0, 0)


def test_schema_failure_is_sanitized_without_implicit_migration(tmp_path):
    engine = create_database(tmp_path / 'unmigrated.sqlite3')
    try:
        with pytest.raises(SchemaMismatch) as error:
            with execution_transaction(engine): pytest.fail('unmigrated store accepted')
        private(error.value)
    finally:
        engine.dispose()


@pytest.mark.parametrize('category', [StorageIntegrityError, SchemaMismatch])
def test_commit_exception_category_cannot_bypass_completion_boundary(case, registered, category):
    record = make_record(case)
    before = counts(registered)
    def fail(conn): raise category(SECRET)
    event.listen(registered, 'commit', fail)
    try:
        with trace(registered) as events:
            with pytest.raises(TransactionAborted) as error:
                with execution_transaction(registered) as tx:
                    tx.executions.append(record, target=TARGET)
            assert str(error.value) == 'transaction completion could not be confirmed'
            private(error.value)
            rejected(tx, events)
    finally:
        event.remove(registered, 'commit', fail)
    assert counts(registered) == before


def test_post_commit_exception_does_not_claim_rollback(case, registered, monkeypatch):
    record = make_record(case)
    original = registered.dialect.do_commit
    def committed_then_failed(connection):
        original(connection)
        raise RuntimeError(SECRET)
    monkeypatch.setattr(registered.dialect, 'do_commit', committed_then_failed)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted) as error:
            with execution_transaction(registered) as tx:
                tx.executions.append(record, target=TARGET)
        assert str(error.value) == 'transaction completion could not be confirmed'
        private(error.value)
        rejected(tx, events)
    # This is fault injection, not reconciliation: an exception cannot prove rollback.
    assert counts(registered) == (3, 1)


@pytest.mark.parametrize('adapter', ['repository', 'executions'])
def test_read_sql_failure_is_sanitized_at_call_boundary(case, registered, adapter):
    record = make_record(case)
    before = counts(registered)
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('SELECT'):
            raise OperationalError(SECRET, {}, Exception(SECRET))
    with trace(registered) as events:
        with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
            tx.repository.append_fact(fact(), target=TARGET)
            event.listen(registered, 'before_cursor_execute', fail)
            try:
                with pytest.raises(TransactionAborted) as error:
                    if adapter == 'repository': tx.repository.capture_cutoff()
                    else: tx.executions.load(record.execution_id, target=TARGET)
                private(error.value)
                rejected(tx, events)
            finally:
                event.remove(registered, 'before_cursor_execute', fail)
    assert counts(registered) == before


def test_serialization_error_before_sql_poisons(case, registered, monkeypatch):
    from pydantic_core import PydanticSerializationError
    def fail(*args): raise PydanticSerializationError(SECRET)
    monkeypatch.setattr(repository, 'canonical_payload', fail)
    with trace(registered) as events:
        with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
            before = list(events['sql'])
            with pytest.raises(PersistenceInputError) as error:
                tx.repository.register_patient(patient())
            private(error.value)
            assert events['sql'] == before
            rejected(tx, events)


def test_stored_retry_is_validated_in_shared_context(case, registered):
    record = make_record(case)
    append(registered, record, target=TARGET)
    with registered.begin() as conn:
        conn.execute(text("UPDATE weight_trend_execution SET payload_digest='bad'"))
    with trace(registered) as events:
        with pytest.raises(TransactionAborted), execution_transaction(registered) as tx:
            with pytest.raises(StorageIntegrityError): tx.executions.append(record, target=TARGET)
            rejected(tx, events)
