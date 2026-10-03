"""Immutable synthetic execution append/recovery, separate from clinical facts.

Standalone calls own their transactions; the private adapter can join the narrow
shared context. No release orchestration. Scope checks do not authenticate callers.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.execution.weight_trend_execution import WeightTrendExecutionRecord
from app.models.clinical.common import ContextTarget
from .database import require_schema
from .entities import EncounterRow, PatientRow, RepositoryIdentity, WeightTrendExecutionRow
from .errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, SchemaMismatch, ScopeMismatch,
    StorageIntegrityError, TransactionAborted, UnsupportedOperation,
)
from .mapping import canonical_payload, load_encounter, load_patient
from .shared_transaction import _operation

# Execution format is independently versioned; clinical PAYLOAD_VERSION is unchanged.
EXECUTION_PAYLOAD_VERSION = 1


@dataclass(frozen=True)
class StoredWeightTrendExecution:
    record: WeightTrendExecutionRecord
    # Assigned UTC ingestion time, not a clinical time or a commit timestamp.
    ingested_at: datetime


def _now():
    return datetime.now(timezone.utc)


def _digest(payload):
    return sha256(payload.encode('utf-8')).hexdigest()


@contextmanager
def _session(engine):
    """Private per-call boundary, using the existing SQLite connection policy."""
    if not isinstance(engine, Engine):
        raise PersistenceInputError('execution persistence requires an Engine')
    try:
        with Session(engine, expire_on_commit=False) as session:
            with session.begin():
                require_schema(session.connection())
                yield session
    except SchemaMismatch:
        raise SchemaMismatch('execution storage requires the reviewed schema revision') from None
    except SQLAlchemyError:
        raise TransactionAborted('execution storage operation failed') from None


def _target(target):
    try:
        target = ContextTarget.model_validate(target)
    except (ValidationError, ValueError, TypeError):
        raise PersistenceInputError('invalid execution scope') from None
    if target.encounter_id is None:
        raise UnsupportedOperation('execution persistence requires an encounter')
    return target


def _identity(session):
    rows = session.scalars(select(RepositoryIdentity)).all()
    try:
        if len(rows) != 1 or rows[0].singleton != 1:
            raise ValueError()
        return UUID(rows[0].repository_id)
    except (ValueError, TypeError, AttributeError):
        raise StorageIntegrityError('invalid repository identity') from None


def _owner(session, target, *, retained):
    encounter = session.scalar(select(EncounterRow).where(
        EncounterRow.encounter_id == target.encounter_id, EncounterRow.patient_id == target.patient_id))
    patient = session.get(PatientRow, target.patient_id)
    if encounter is None or patient is None:
        if retained:
            raise StorageIntegrityError('execution ownership is inconsistent')
        raise RecordNotFound('execution context not registered')
    load_patient(patient)
    load_encounter(encounter)


def _scoped_row(session, execution_id, target):
    # Scope must constrain SQL before any execution payload is decoded.
    return session.scalar(select(WeightTrendExecutionRow).where(
        WeightTrendExecutionRow.execution_id == execution_id,
        WeightTrendExecutionRow.patient_id == target.patient_id,
        WeightTrendExecutionRow.encounter_id == target.encounter_id))


def _decode(row, repository_id):
    if row.payload_version != EXECUTION_PAYLOAD_VERSION:
        raise StorageIntegrityError('unsupported execution payload version')
    try:
        if not isinstance(row.payload, str) or not isinstance(row.payload_digest, str):
            raise ValueError()
        if _digest(row.payload) != row.payload_digest:
            raise ValueError()
        record = WeightTrendExecutionRecord.model_validate_json(row.payload)
        if canonical_payload(record) != row.payload:
            raise ValueError()
        if (str(record.execution_id), record.target.context.patient_id, record.target.context.encounter_id,
                record.payload_version, record.repository_id) != (
                row.execution_id, row.patient_id, row.encounter_id, row.payload_version, repository_id):
            raise ValueError()
        # Only our assigned, canonical UTC metadata is accepted; no normalization.
        ingested_at = datetime.fromisoformat(row.ingested_at)
        if ingested_at.utcoffset() != timedelta(0) or ingested_at.isoformat() != row.ingested_at:
            raise ValueError()
        return StoredWeightTrendExecution(record, ingested_at)
    except (ValidationError, PydanticSerializationError, ValueError, TypeError, AttributeError,
            PersistenceInputError, UnsupportedOperation):
        raise StorageIntegrityError('stored execution failed integrity validation') from None


def _prepare_append(record, target):
    if type(record) is not WeightTrendExecutionRecord:
        raise PersistenceInputError('expected a WeightTrendExecutionRecord')
    try:
        record = WeightTrendExecutionRecord.model_validate(record)
        payload = canonical_payload(record)
    except (ValidationError, PydanticSerializationError, ValueError, TypeError):
        raise PersistenceInputError('invalid execution record') from None
    target = _target(target)
    if record.target.context != target:
        raise ScopeMismatch('execution binding differs from requested context')
    return record, target, payload


def _append(session, record, target, payload):
    repository_id = _identity(session)
    if record.repository_id != repository_id:
        raise ScopeMismatch('execution belongs to a different repository')
    _owner(session, target, retained=False)
    existing = _scoped_row(session, str(record.execution_id), target)
    if existing is not None:
        stored = _decode(existing, repository_id)
        if canonical_payload(stored.record) != payload:
            raise RecordConflict('execution identity already has different content')
        return stored
    # A global UUID collision in another scope must not decode foreign content.
    collision = session.scalar(select(WeightTrendExecutionRow.execution_id).where(
        WeightTrendExecutionRow.execution_id == str(record.execution_id)))
    if collision is not None:
        raise RecordConflict('execution identity already has different content')
    row = WeightTrendExecutionRow(execution_id=str(record.execution_id),
        patient_id=target.patient_id, encounter_id=target.encounter_id,
        payload_version=EXECUTION_PAYLOAD_VERSION, payload=payload,
        payload_digest=_digest(payload), ingested_at=_now().isoformat())
    session.add(row)
    session.flush()
    return _decode(row, repository_id)


def _prepare_load(execution_id, target):
    try:
        execution_id = str(UUID(str(execution_id)))
    except (ValueError, TypeError, AttributeError):
        raise PersistenceInputError('invalid execution identity') from None
    target = _target(target)
    return execution_id, target


def _find(session, execution_id, target):
    row = _scoped_row(session, execution_id, target)
    if row is None:
        return None
    stored = _decode(row, _identity(session))
    _owner(session, target, retained=True)
    return stored


def _load(session, execution_id, target):
    stored = _find(session, execution_id, target)
    if stored is None:
        raise RecordNotFound('execution not found in requested context')
    return stored


class _ExecutionAdapter:
    """Constructed only by the shared context; never owns commit or rollback."""

    def __init__(self, session, lifecycle):
        self._session = session
        self._lifecycle = lifecycle

    @_operation
    def append(self, record: WeightTrendExecutionRecord, *, target: ContextTarget) -> StoredWeightTrendExecution:
        return _append(self._session, *_prepare_append(record, target))

    @_operation
    def find(self, execution_id: UUID, *, target: ContextTarget) -> StoredWeightTrendExecution | None:
        """Normal scoped absence is data; all exceptional failures still poison."""
        return _find(self._session, *_prepare_load(execution_id, target))

    @_operation
    def load(self, execution_id: UUID, *, target: ContextTarget) -> StoredWeightTrendExecution:
        return _load(self._session, *_prepare_load(execution_id, target))


def append_weight_trend_execution(engine: Engine, record: WeightTrendExecutionRecord, *,
                                  target: ContextTarget) -> StoredWeightTrendExecution:
    """Insert once or recover retained content; this call owns its transaction."""
    prepared = _prepare_append(record, target)
    with _session(engine) as session:
        return _append(session, *prepared)


def load_weight_trend_execution(engine: Engine, execution_id: UUID, *,
                                target: ContextTarget) -> StoredWeightTrendExecution:
    """Recover historical content; return only after the owned transaction exits."""
    prepared = _prepare_load(execution_id, target)
    with _session(engine) as session:
        return _load(session, *prepared)
