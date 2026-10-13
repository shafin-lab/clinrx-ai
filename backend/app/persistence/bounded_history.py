"""Finite visible-prefix history for M6 assembly; no eligibility filtering."""
from typing import Annotated
from pydantic import Field
from sqlalchemy import LargeBinary, cast, func, select, tuple_
from .entities import FactRow
from .history import QueryContract, retrieve
from .metadata import RepositoryCutoff
from .errors import PersistenceInputError, QueryLimitExceeded, ScopeMismatch


class HistoryBudget(QueryContract):
    max_rows: Annotated[int, Field(strict=True, ge=1, le=4096)] = 4096
    max_payload_bytes: Annotated[int, Field(strict=True, ge=1, le=16777216)] = 16777216


def bounded_history(repository, *, target, cutoff, budget):
    budget = HistoryBudget.model_validate(budget)
    cutoff = RepositoryCutoff.model_validate(cutoff.model_dump() if isinstance(cutoff, RepositoryCutoff) else cutoff)
    if str(cutoff.repository_id) != repository._repository_id:
        raise ScopeMismatch('cutoff belongs to a different repository')
    target = repository._target(target)
    session = repository._session
    maximum = session.scalar(select(func.max(FactRow.ingestion_sequence))) or 0
    if cutoff.fact_watermark > maximum:
        raise PersistenceInputError('cutoff exceeds visible repository state')
    # Read bounded envelopes and byte lengths, never payloads, before decoding.
    rows = session.execute(select(FactRow.kind, FactRow.fact_id,
        func.length(cast(FactRow.payload, LargeBinary))).where(
        FactRow.patient_id == target.patient_id, FactRow.encounter_id == target.encounter_id,
        FactRow.ingestion_sequence <= cutoff.fact_watermark)
        .order_by(FactRow.ingestion_sequence).limit(budget.max_rows + 1)).all()
    if len(rows) > budget.max_rows or sum(row[2] for row in rows) > budget.max_payload_bytes:
        raise QueryLimitExceeded('historical candidate budget exceeded')
    keys = sorted({(row[0], row[1]) for row in rows})
    # Inspect all visible envelopes in each discovered stable chain, including
    # foreign successors. Chunk parameters, but never filter foreign rows away.
    for offset in range(0, len(keys), 200):
        chain_rows = session.execute(select(FactRow.patient_id, FactRow.encounter_id).where(
            tuple_(FactRow.kind, FactRow.fact_id).in_(keys[offset:offset + 200]),
            FactRow.ingestion_sequence <= cutoff.fact_watermark).limit(budget.max_rows + 1)).all()
        if any(tuple(row) != (target.patient_id, target.encounter_id) for row in chain_rows):
            raise ScopeMismatch('visible revision chain does not belong to requested context')
        if len(chain_rows) > budget.max_rows:
            raise QueryLimitExceeded('historical candidate budget exceeded')
    # Same locked transaction and cutoff: existing validation remains authoritative.
    return retrieve(repository, target=target, cutoff=cutoff)


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
