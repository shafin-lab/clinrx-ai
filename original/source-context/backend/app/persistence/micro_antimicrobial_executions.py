"""Immutable micro_antimicrobial execution storage; no protected workflow.

Standalone calls own their transaction; the private adapter joins the shared owner.
Retained contracts do not prove authenticated
producers or clinical validity. Execution identities are capability-specific.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from pydantic import AwareDatetime, ValidationError, model_validator
from pydantic_core import PydanticSerializationError
from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.execution.patient_state_v2_execution import (
    MicroAntimicrobialExecutionRecord, MicroAntimicrobialExecutionError,
)
from app.models.clinical.common import ContextTarget, DomainModel
from .database import require_schema
from .entities import MicroAntimicrobialExecutionRow, EncounterRow, PatientRow, RepositoryIdentity
from .errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, SchemaMismatch, ScopeMismatch,
    StorageIntegrityError, TransactionAborted, UnsupportedOperation,
)
from .mapping import canonical_payload, load_encounter, load_patient
from .shared_transaction import _operation

MICRO_ANTIMICROBIAL_EXECUTION_PAYLOAD_VERSION = 1


class StoredMicroAntimicrobialExecution(DomainModel):
    """Storage receipt; ingestion is separate from the immutable M6.4 payload."""
    record: MicroAntimicrobialExecutionRecord
    ingested_at: AwareDatetime

    @model_validator(mode='after')
    def utc_ingestion(self):
        if self.ingested_at.utcoffset() != timedelta(0):
            raise ValueError('execution ingestion requires UTC')
        return self


def _now():
    return datetime.now(timezone.utc)


def _digest(payload):
    return sha256(payload.encode('utf-8')).hexdigest()


@contextmanager
def _session(engine):
    if not isinstance(engine, Engine):
        raise PersistenceInputError('micro_antimicrobial execution persistence requires an Engine')
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
    # Scope constrains SQL before any execution payload is decoded.
    return session.scalar(select(MicroAntimicrobialExecutionRow).where(
        MicroAntimicrobialExecutionRow.execution_id == execution_id,
        MicroAntimicrobialExecutionRow.patient_id == target.patient_id,
        MicroAntimicrobialExecutionRow.encounter_id == target.encounter_id))


def _decode(row, repository_id):
    if type(row.payload_version) is not int or row.payload_version != MICRO_ANTIMICROBIAL_EXECUTION_PAYLOAD_VERSION:
        raise StorageIntegrityError('unsupported execution payload version')
    try:
        if not isinstance(row.payload, str) or not isinstance(row.payload_digest, str):
            raise ValueError()
        if _digest(row.payload) != row.payload_digest:
            raise ValueError()
        record = MicroAntimicrobialExecutionRecord.model_validate_json(row.payload)
        if canonical_payload(record) != row.payload:
            raise ValueError()
        if (str(record.request.execution_id), record.request.target.context.patient_id, record.request.target.context.encounter_id,
                record.payload_version, record.request.inference_cutoff.repository_id) != (
                row.execution_id, row.patient_id, row.encounter_id, row.payload_version, repository_id):
            raise ValueError()
        ingested_at = datetime.fromisoformat(row.ingested_at)
        if ingested_at.utcoffset() != timedelta(0) or ingested_at.isoformat() != row.ingested_at:
            raise ValueError()
        return StoredMicroAntimicrobialExecution(record=record, ingested_at=ingested_at)
    except (ValidationError, PydanticSerializationError, ValueError, TypeError, AttributeError,
            PersistenceInputError, UnsupportedOperation, MicroAntimicrobialExecutionError):
        raise StorageIntegrityError('stored execution failed integrity validation') from None


def _prepare_append(record, target):
    if type(record) is not MicroAntimicrobialExecutionRecord:
        raise PersistenceInputError('expected a MicroAntimicrobialExecutionRecord')
    try:
        record = MicroAntimicrobialExecutionRecord.model_validate(record)
        payload = canonical_payload(record)
    except (ValidationError, PydanticSerializationError, ValueError, TypeError, MicroAntimicrobialExecutionError):
        raise PersistenceInputError('invalid execution record') from None
    target = _target(target)
    if record.request.target.context != target:
        raise ScopeMismatch('execution binding differs from requested context')
    return record, target, payload


def _append(session, record, target, payload):
    repository_id = _identity(session)
    if record.request.inference_cutoff.repository_id != repository_id:
        raise ScopeMismatch('execution belongs to a different repository')
    _owner(session, target, retained=False)
    existing = _scoped_row(session, str(record.request.execution_id), target)
    if existing is not None:
        stored = _decode(existing, repository_id)
        if canonical_payload(stored.record) != payload:
            raise RecordConflict('execution identity already has different content')
        return stored
    collision = session.scalar(select(MicroAntimicrobialExecutionRow.execution_id).where(
        MicroAntimicrobialExecutionRow.execution_id == str(record.request.execution_id)))
    if collision is not None:
        raise RecordConflict('execution identity already has different content')
    row = MicroAntimicrobialExecutionRow(execution_id=str(record.request.execution_id),
        patient_id=target.patient_id, encounter_id=target.encounter_id,
        payload_version=MICRO_ANTIMICROBIAL_EXECUTION_PAYLOAD_VERSION, payload=payload,
        payload_digest=_digest(payload), ingested_at=_now().isoformat())
    session.add(row)
    session.flush()
    return _decode(row, repository_id)


def _prepare_load(execution_id, target):
    try:
        execution_id = str(UUID(str(execution_id)))
    except (ValueError, TypeError, AttributeError):
        raise PersistenceInputError('invalid execution identity') from None
    return execution_id, _target(target)


def _find(session, execution_id, target):
    row = _scoped_row(session, execution_id, target)
    if row is None:
        return None
    stored = _decode(row, _identity(session))
    _owner(session, target, retained=True)
    return stored


class _MicroAntimicrobialExecutionAdapter:
    """Shared-owner handle; never begins, commits, or closes the transaction."""

    def __init__(self, session, lifecycle):
        self._session = session
        self._lifecycle = lifecycle

    @_operation
    def append(self, record: MicroAntimicrobialExecutionRecord, *, target: ContextTarget) -> StoredMicroAntimicrobialExecution:
        return _append(self._session, *_prepare_append(record, target))

    @_operation
    def find(self, execution_id: UUID, *, target: ContextTarget) -> StoredMicroAntimicrobialExecution | None:
        return _find(self._session, *_prepare_load(execution_id, target))

    @_operation
    def load(self, execution_id: UUID, *, target: ContextTarget) -> StoredMicroAntimicrobialExecution:
        stored = _find(self._session, *_prepare_load(execution_id, target))
        if stored is None:
            raise RecordNotFound('execution not found in requested context')
        return stored


def append_micro_antimicrobial_execution(engine: Engine, record: MicroAntimicrobialExecutionRecord, *,
                                     target: ContextTarget) -> StoredMicroAntimicrobialExecution:
    """Insert once or recover identical content; return only after transaction exit."""
    prepared = _prepare_append(record, target)
    with _session(engine) as session:
        return _append(session, *prepared)


def find_micro_antimicrobial_execution(engine: Engine, execution_id: UUID, *,
                                   target: ContextTarget) -> StoredMicroAntimicrobialExecution | None:
    """Scoped absence is None; invalid visible storage always raises."""
    prepared = _prepare_load(execution_id, target)
    with _session(engine) as session:
        return _find(session, *prepared)


def load_micro_antimicrobial_execution(engine: Engine, execution_id: UUID, *,
                                   target: ContextTarget) -> StoredMicroAntimicrobialExecution:
    """Load retained historical content, with indistinguishable missing/foreign errors."""
    prepared = _prepare_load(execution_id, target)
    with _session(engine) as session:
        stored = _find(session, *prepared)
        if stored is None:
            raise RecordNotFound('execution not found in requested context')
        return stored
