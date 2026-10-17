"""Transaction-scoped append/load operations. No reconstruction or clinical adjudication."""
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Engine, func, or_, select
from sqlalchemy.orm import Session

from app.models.clinical.common import ContextTarget, Reference
from app.models.clinical.facts import EncounterContext, PatientContext
from .database import require_schema
from .entities import EncounterRow, FactRow, PAYLOAD_VERSION, PatientRow, RepositoryIdentity, RevisionLink
from .errors import (
    PersistenceInputError, RecordConflict, RecordNotFound, ScopeMismatch, StorageIntegrityError,
    TransactionAborted, UnsupportedOperation,
)
from .mapping import (
    canonical_payload, load_encounter, load_fact, load_patient, validate_fact,
)
from .shared_transaction import _Lifecycle, _operation
from .metadata import RepositoryCutoff
from .history import FactIdentity, retrieve
from .lineage import LineageLimits, LineageResult, resolve


def _now():
    return datetime.now(timezone.utc)


class PatientRepository:
    """Obtain through transaction(); methods never commit independently."""

    def __init__(self, session: Session, *, _lifecycle=None):
        self._session = session
        self._lifecycle = _lifecycle if _lifecycle is not None else _Lifecycle()
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

    def _chain(self, kind, fact_id, target=None):
        """Validate the entire encountered chain, including links leaving its scope."""
        rows = self._session.scalars(select(FactRow).where(
            FactRow.kind == kind, FactRow.fact_id == fact_id
        ).order_by(FactRow.ingestion_sequence)).all()
        if not rows:
            return []
        owner = (rows[0].patient_id, rows[0].encounter_id)
        if target is not None and owner != (target.patient_id, target.encounter_id):
            raise ScopeMismatch('revision chain belongs to a different context')
        if any((row.patient_id, row.encounter_id) != owner for row in rows):
            raise StorageIntegrityError('stored revision chain has mixed ownership')
        sequences = [row.ingestion_sequence for row in rows]
        links = self._session.scalars(select(RevisionLink).where(or_(
            RevisionLink.successor_sequence.in_(sequences),
            RevisionLink.predecessor_sequence.in_(sequences)))).all()
        expected = {(previous.ingestion_sequence, current.ingestion_sequence)
                    for previous, current in zip(rows, rows[1:])}
        actual = {(link.predecessor_sequence, link.successor_sequence) for link in links}
        if actual != expected or len(links) != len(expected):
            raise StorageIntegrityError('malformed stored revision links')
        retained = [load_fact(row, self._repository_id) for row in rows]
        target = retained[0].fact.binding.target
        self._target(target)
        previous = None
        for stored in retained:
            if stored.fact.binding.target != target or stored.fact.supersedes != previous:
                raise StorageIntegrityError('stored revision chain disagrees with payload or ownership')
            previous = stored.fact.reference
        return retained

    @_operation
    def append_revision(self, fact, *, target: ContextTarget):
        """Append a reasoned successor; never replace an existing exact revision."""
        fact = validate_fact(fact)
        target = self._target(target)
        if fact.binding.target != target:
            raise ScopeMismatch('fact binding differs from requested patient/encounter')
        if fact.supersedes is None:
            raise PersistenceInputError('revision requires an explicit predecessor and correction reason')
        payload = canonical_payload(fact)
        chain = self._chain(fact.kind, fact.id, target)
        if chain and chain[0].fact.binding.target != target:
            raise ScopeMismatch('revision chain belongs to a different context')
        # Retries precede terminal enforcement: an old revision remains retryable.
        for stored in chain:
            if stored.fact.reference == fact.reference:
                if canonical_payload(stored.fact) != payload:
                    raise RecordConflict('exact fact revision already has different content')
                return stored
        predecessor = next((item for item in chain if item.fact.reference == fact.supersedes), None)
        if predecessor is None:
            raise RecordNotFound('revision predecessor not found')
        if predecessor != chain[-1]:
            raise RecordConflict('revision predecessor already has a successor')
        row = FactRow(kind=fact.kind, fact_id=fact.id, revision=fact.revision,
                      patient_id=target.patient_id, encounter_id=target.encounter_id,
                      payload=payload, payload_version=PAYLOAD_VERSION, ingested_at=_now().isoformat())
        self._session.add(row)
        self._session.flush()
        self._session.add(RevisionLink(successor_sequence=row.ingestion_sequence,
            predecessor_sequence=predecessor.ingestion.ingestion_sequence))
        self._session.flush()
        return load_fact(row, self._repository_id)

    @_operation
    def append_fact(self, fact, *, target: ContextTarget):
        fact = validate_fact(fact)
        target = self._target(target)
        if fact.binding.target != target:
            raise ScopeMismatch('fact binding differs from requested patient/encounter')
        if fact.supersedes is not None:
            raise UnsupportedOperation('use append_revision for corrections')
        payload = canonical_payload(fact)
        self._chain(fact.kind, fact.id, target)
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
            raise UnsupportedOperation('second root is forbidden; use append_revision')
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
        self._chain(reference.kind, reference.id, target)
        return load_fact(row, self._repository_id)

    @_operation
    def list_revisions(self, identity, *, target: ContextTarget, cutoff: RepositoryCutoff):
        identity = FactIdentity.model_validate(identity)
        return retrieve(self, identity=identity, target=target, cutoff=cutoff)

    @_operation
    def load_latest_known(self, identity, *, target: ContextTarget, cutoff: RepositoryCutoff,
                          clinical_filter=None, ingestion_filter=None):
        identity = FactIdentity.model_validate(identity)
        return retrieve(self, identity=identity, target=target, cutoff=cutoff, latest=True,
                        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def load_current_latest_known(self, identity, *, target: ContextTarget,
                                  clinical_filter=None, ingestion_filter=None):
        identity = FactIdentity.model_validate(identity)
        return self.load_latest_known(identity, target=target, cutoff=self.capture_cutoff(),
            clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def list_history(self, *, target: ContextTarget, cutoff: RepositoryCutoff,
                     clinical_filter=None, ingestion_filter=None):
        return retrieve(self, target=target, cutoff=cutoff,
                        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def check_visible_binding_scopes(self, references, *, target, cutoff):
        """Envelope-only check; never inspect future or foreign payload content."""
        from .bounded_history import check_binding_scopes
        return check_binding_scopes(self, references, target=target, cutoff=cutoff)

    @_operation
    def list_bounded_history(self, *, target, cutoff, budget, identity=None, latest=False,
                             family_budget=None, accounting=None, clinical_filter=None, ingestion_filter=None):
        """Bound candidate envelopes/bytes before existing historical decoding."""
        from .bounded_history import bounded_history
        return bounded_history(self, target=target, cutoff=cutoff, budget=budget,
            identity=identity, latest=latest, family_budget=family_budget, accounting=accounting,
            clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def list_latest_known(self, *, target: ContextTarget, cutoff: RepositoryCutoff,
                          clinical_filter=None, ingestion_filter=None):
        return retrieve(self, target=target, cutoff=cutoff, latest=True,
                        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def list_current_latest_known(self, *, target: ContextTarget,
                                  clinical_filter=None, ingestion_filter=None):
        return self.list_latest_known(target=target, cutoff=self.capture_cutoff(),
            clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)

    @_operation
    def resolve_lineage(self, reference: Reference, *, target: ContextTarget,
                        cutoff: RepositoryCutoff, limits: LineageLimits,
                        history_budget=None, family_budget=None, accounting=None) -> LineageResult:
        """Resolve declared exact lineage only in the requested visible prefix."""
        return resolve(self, reference, target=target, cutoff=cutoff, limits=limits,
            history_budget=history_budget, family_budget=family_budget, accounting=accounting)

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
                repository._lifecycle.check()
    finally:
        if repository is not None:
            repository._lifecycle.close()
