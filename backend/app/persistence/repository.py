"""Transaction-scoped append/load operations. No reconstruction or clinical adjudication."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from uuid import UUID

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.models.clinical.common import ContextTarget, Reference
from app.models.clinical.facts import EncounterContext, PatientContext
from .database import require_schema
from .entities import EncounterRow, FactRow, PAYLOAD_VERSION, PatientRow, RepositoryIdentity
from .errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch, StorageIntegrityError,
    TransactionAborted, UnsupportedOperation,
)
from .mapping import (
    canonical_payload, load_encounter, load_fact, load_patient, validate_fact,
)
from .metadata import RepositoryCutoff


def _now():
    return datetime.now(timezone.utc)


def _operation(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        if not self._active or self._failed:
            raise TransactionAborted('repository transaction is closed or failed')
        try:
            return method(self, *args, **kwargs)
        except (ValidationError, PydanticSerializationError):
            self._failed = True
            raise PersistenceInputError(f'invalid domain input for {method.__name__}') from None
        except Exception:
            self._failed = True
            raise
    return checked


class PatientRepository:
    """Obtain through transaction(); methods never commit independently."""

    def __init__(self, session: Session):
        self._session = session
        self._active = True
        self._failed = False
        identity = session.get(RepositoryIdentity, 1)
        if identity is None:
            raise StorageIntegrityError('missing repository identity')
        try:
            self._repository_id = str(UUID(identity.repository_id))
        except (ValueError, TypeError):
            raise StorageIntegrityError('invalid repository identity') from None

    @_operation
    def register_patient(self, patient: PatientContext) -> PatientContext:
        patient = PatientContext.model_validate(patient)
        payload = canonical_payload(patient)
        existing = self._session.get(PatientRow, patient.patient_id)
        if existing:
            retained = load_patient(existing)
            if canonical_payload(retained) != payload:
                raise RecordConflict('patient registration already has different content')
            return retained
        self._session.add(PatientRow(patient_id=patient.patient_id, payload=payload,
                                    payload_version=PAYLOAD_VERSION, ingested_at=_now().isoformat()))
        self._session.flush()
        return patient

    @_operation
    def load_patient(self, patient_id: str) -> PatientContext:
        row = self._session.get(PatientRow, patient_id)
        if row is None:
            raise RecordNotFound('patient not registered')
        return load_patient(row)

    @_operation
    def register_encounter(self, encounter: EncounterContext) -> EncounterContext:
        encounter = EncounterContext.model_validate(encounter)
        self.load_patient(encounter.patient_id)
        existing = self._session.get(EncounterRow, encounter.encounter_id)
        payload = canonical_payload(encounter)
        if existing:
            if existing.patient_id != encounter.patient_id:
                raise ScopeMismatch('encounter belongs to a different patient')
            retained = load_encounter(existing)
            if canonical_payload(retained) != payload:
                raise RecordConflict('encounter registration already has different content')
            return retained
        self._session.add(EncounterRow(encounter_id=encounter.encounter_id,
            patient_id=encounter.patient_id, payload=payload, payload_version=PAYLOAD_VERSION,
            ingested_at=_now().isoformat()))
        self._session.flush()
        return encounter

    @_operation
    def load_encounter(self, *, patient_id: str, encounter_id: str) -> EncounterContext:
        row = self._session.get(EncounterRow, encounter_id)
        if row is None:
            raise RecordNotFound('encounter not registered')
        if row.patient_id != patient_id:
            raise ScopeMismatch('encounter does not belong to requested patient')
        self.load_patient(patient_id)
        return load_encounter(row)

    def _target(self, target: ContextTarget) -> ContextTarget:
        target = ContextTarget.model_validate(target)
        if target.encounter_id is None:
            raise UnsupportedOperation('longitudinal-context persistence is deferred')
        self.load_encounter(patient_id=target.patient_id, encounter_id=target.encounter_id)
        return target

    @_operation
    def append_fact(self, fact, *, target: ContextTarget):
        fact = validate_fact(fact)
        target = self._target(target)
        if fact.binding.target != target:
            raise ScopeMismatch('fact binding differs from requested patient/encounter')
        if fact.supersedes is not None:
            raise UnsupportedOperation('correction persistence is deferred')
        payload = canonical_payload(fact)
        existing = self._session.scalar(select(FactRow).where(
            FactRow.kind == fact.kind, FactRow.fact_id == fact.id, FactRow.revision == fact.revision))
        if existing:
            stored = load_fact(existing, self._repository_id)
            if stored.fact.binding.target != target:
                raise ScopeMismatch('exact reference belongs to a different context')
            if canonical_payload(stored.fact) != payload:
                raise RecordConflict('exact fact revision already has different content')
            return stored
        if self._session.scalar(select(FactRow.ingestion_sequence).where(
                FactRow.kind == fact.kind, FactRow.fact_id == fact.id).limit(1)) is not None:
            raise UnsupportedOperation('additional revisions require the future correction workflow')
        row = FactRow(kind=fact.kind, fact_id=fact.id, revision=fact.revision,
                      patient_id=target.patient_id, encounter_id=target.encounter_id,
                      payload=payload, payload_version=PAYLOAD_VERSION, ingested_at=_now().isoformat())
        self._session.add(row)
        self._session.flush()
        return load_fact(row, self._repository_id)

    @_operation
    def load_fact(self, reference: Reference, *, target: ContextTarget):
        reference = Reference.model_validate(reference)
        target = self._target(target)
        row = self._session.scalar(select(FactRow).where(FactRow.kind == reference.kind,
            FactRow.fact_id == reference.id, FactRow.revision == reference.version))
        if row is None:
            raise RecordNotFound('exact fact revision not found')
        if (row.patient_id, row.encounter_id) != (target.patient_id, target.encounter_id):
            raise ScopeMismatch('exact reference does not belong to requested context')
        return load_fact(row, self._repository_id)

    @_operation
    def capture_cutoff(self) -> RepositoryCutoff:
        """Capture a fact prefix, provisional until commit; not clinical reconstruction."""
        watermark = self._session.scalar(select(func.max(FactRow.ingestion_sequence))) or 0
        return RepositoryCutoff(repository_id=self._repository_id,
                                fact_watermark=watermark, captured_at=_now())


@contextmanager
def transaction(engine: Engine):
    """One atomic unit. Even a caught repository failure aborts the whole unit.

    Returned records/metadata are provisional until this context exits successfully.
    No caller-managed Session is required or exposed as part of the public API.
    """
    repository = None
    try:
        with Session(engine, expire_on_commit=False) as session:
            with session.begin():
                require_schema(session.connection())
                repository = PatientRepository(session)
                yield repository
                if repository._failed:
                    raise TransactionAborted('a failed operation invalidated this transaction')
    finally:
        if repository is not None:
            repository._active = False
