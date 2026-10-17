"""Pre-decode visible-history admission; operational accounting is never persisted."""
from dataclasses import dataclass
from typing import Annotated
from pydantic import Field
from sqlalchemy import LargeBinary, cast, func, select, tuple_
from .entities import FactRow
from .history import ClinicalTimeFilter, IngestionTimeFilter, FactIdentity, QueryContract, retrieve
from .metadata import RepositoryCutoff
from .errors import PersistenceInputError, QueryLimitExceeded, ScopeMismatch, StorageIntegrityError


class HistoryBudget(QueryContract):
    # Existing serialized M6 assembly contract: do not add operational fields.
    max_rows: Annotated[int, Field(strict=True, ge=1, le=4096)] = 4096
    max_payload_bytes: Annotated[int, Field(strict=True, ge=1, le=16777216)] = 16777216


class AggregateHistoryBudget(QueryContract):
    max_rows: Annotated[int, Field(strict=True, ge=1, le=100000)] = 16384
    max_payload_bytes: Annotated[int, Field(strict=True, ge=1, le=268435456)] = 67108864


class HistoryAccounting:
    """Trusted synchronous unit-of-work counter, not a request or domain contract.

    Charge each admitted read, even repeated identities/cutoffs. Rejected admission
    consumes no payload allowance; admitted corruption still consumes its read.
    Share only within one synchronous unit. Repository lifecycle owns failure state.
    """
    def __init__(self, budget: AggregateHistoryBudget):
        self._budget = AggregateHistoryBudget.model_validate(budget)
        self._rows = 0
        self._payload_bytes = 0

    @property
    def rows(self):
        return self._rows

    @property
    def payload_bytes(self):
        return self._payload_bytes

    def _charge(self, rows, payload_bytes):
        if (self._rows + rows > self._budget.max_rows
                or self._payload_bytes + payload_bytes > self._budget.max_payload_bytes):
            raise QueryLimitExceeded('aggregate historical budget exceeded')
        self._rows += rows
        self._payload_bytes += payload_bytes


@dataclass(frozen=True)
class _Admission:
    families: tuple[tuple[FactIdentity, tuple[int, ...]], ...]


def _bounded_retrieve(repository, *, target, cutoff, max_rows, max_payload_bytes,
                      identity=None, latest=False, family_budget=None, accounting=None,
                      clinical_filter=None, ingestion_filter=None):
    if type(latest) is not bool:
        raise PersistenceInputError('invalid historical selection mode')
    clinical_filter = ClinicalTimeFilter.model_validate(clinical_filter) if clinical_filter is not None else None
    ingestion_filter = IngestionTimeFilter.model_validate(ingestion_filter) if ingestion_filter is not None else None
    if accounting is not None and type(accounting) is not HistoryAccounting:
        raise PersistenceInputError('invalid historical accounting')
    family_budget = HistoryBudget.model_validate(family_budget) if family_budget is not None else None
    identity = FactIdentity.model_validate(identity) if identity is not None else None
    cutoff = RepositoryCutoff.model_validate(cutoff.model_dump() if isinstance(cutoff, RepositoryCutoff) else cutoff)
    if str(cutoff.repository_id) != repository._repository_id:
        raise ScopeMismatch('cutoff belongs to a different repository')
    target = repository._target(target)
    session = repository._session
    maximum = session.scalar(select(func.max(FactRow.ingestion_sequence))) or 0
    if cutoff.fact_watermark > maximum:
        raise PersistenceInputError('cutoff exceeds visible repository state')
    query = select(FactRow.ingestion_sequence, FactRow.kind, FactRow.fact_id,
        FactRow.patient_id, FactRow.encounter_id,
        func.length(cast(FactRow.payload, LargeBinary))).where(
        FactRow.ingestion_sequence <= cutoff.fact_watermark)
    if identity is None:
        query = query.where(FactRow.patient_id == target.patient_id, FactRow.encounter_id == target.encounter_id)
    else:
        # A foreign member is an ownership failure, not a filtered older terminal.
        query = query.where(FactRow.kind == identity.kind, FactRow.fact_id == identity.id)
    rows = session.execute(query.order_by(FactRow.ingestion_sequence).limit(max_rows + 1)).all()
    if any((row[3], row[4]) != (target.patient_id, target.encounter_id) for row in rows):
        raise ScopeMismatch('visible revision chain does not belong to requested context')
    if len(rows) > max_rows:
        raise QueryLimitExceeded('historical candidate budget exceeded')
    if any(type(row[5]) is not int or row[5] < 0 for row in rows):
        raise StorageIntegrityError('invalid visible payload length')
    total_bytes = sum(row[5] for row in rows)
    if total_bytes > max_payload_bytes:
        raise QueryLimitExceeded('historical candidate budget exceeded')
    families, sizes = {}, {}
    for sequence, kind, fact_id, _, _, size in rows:
        key = (kind, fact_id)
        families.setdefault(key, []).append(sequence)
        sizes[key] = sizes.get(key, 0) + size
    for key, sequences in families.items():
        if family_budget and (len(sequences) > family_budget.max_rows
                or sizes[key] > family_budget.max_payload_bytes):
            raise QueryLimitExceeded('historical family budget exceeded')
    try:
        admitted = []
        for kind, fact_id in families:
            key = FactIdentity(kind=kind, id=fact_id)
            if (key.kind, key.id) != (kind, fact_id):
                raise ValueError()
            admitted.append((key, tuple(families[(kind, fact_id)])))
    except ValueError:
        raise StorageIntegrityError('invalid visible fact identity') from None
    admitted.sort(key=lambda pair: (pair[0].kind, pair[0].id))
    keys = [(key.kind, key.id) for key, _ in admitted]
    # Scoped discovery must also reject foreign successors of discovered families.
    if identity is None:
        for offset in range(0, len(keys), 200):
            owners = session.execute(select(FactRow.patient_id, FactRow.encounter_id).where(
                tuple_(FactRow.kind, FactRow.fact_id).in_(keys[offset:offset + 200]),
                FactRow.ingestion_sequence <= cutoff.fact_watermark).limit(max_rows + 1)).all()
            if any(tuple(row) != (target.patient_id, target.encounter_id) for row in owners):
                raise ScopeMismatch('visible revision chain does not belong to requested context')
            if len(owners) > max_rows:
                raise QueryLimitExceeded('historical candidate budget exceeded')
    if accounting is not None:
        accounting._charge(len(rows), total_bytes)
    return retrieve(repository, target=target, cutoff=cutoff, identity=identity, latest=latest,
        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter,
        _admission=_Admission(tuple(admitted)))


def bounded_history(repository, *, target, cutoff, budget, identity=None, latest=False,
                    family_budget=None, accounting=None, clinical_filter=None, ingestion_filter=None):
    budget = HistoryBudget.model_validate(budget)
    return _bounded_retrieve(repository, target=target, cutoff=cutoff,
        max_rows=budget.max_rows, max_payload_bytes=budget.max_payload_bytes,
        identity=identity, latest=latest, family_budget=family_budget, accounting=accounting,
        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)


def check_binding_scopes(repository, references, *, target, cutoff):
    from app.models.clinical.common import Reference
    target = repository._target(target)
    cutoff = RepositoryCutoff.model_validate(cutoff.model_dump() if isinstance(cutoff, RepositoryCutoff) else cutoff)
    if str(cutoff.repository_id) != repository._repository_id:
        raise ScopeMismatch('cutoff belongs to a different repository')
    if len(references) > 1024:
        raise QueryLimitExceeded('binding query budget exceeded')
    refs = tuple(Reference.model_validate(ref) for ref in references)
    for offset in range(0, len(refs), 100):
        keys = [(ref.kind, ref.id, ref.version) for ref in refs[offset:offset + 100]]
        rows = repository._session.execute(select(FactRow.patient_id, FactRow.encounter_id).where(
            tuple_(FactRow.kind, FactRow.fact_id, FactRow.revision).in_(keys),
            FactRow.ingestion_sequence <= cutoff.fact_watermark)).all()
        if any(tuple(row) != (target.patient_id, target.encounter_id) for row in rows):
            raise ScopeMismatch('exact binding target does not belong to requested context')
