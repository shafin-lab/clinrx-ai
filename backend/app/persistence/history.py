"""Cutoff-bounded revision retrieval, not clinical context reconstruction."""
from dataclasses import dataclass
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, StrictBool, model_validator
from sqlalchemy import func, or_, select

from app.models.clinical.common import ContextTarget, Text
from .entities import FactRow, RevisionLink
from .errors import PersistenceInputError, ScopeMismatch, StorageIntegrityError
from .mapping import StoredFact, load_fact
from .metadata import RepositoryCutoff, StorageMetadata


def _instant_key(value):
    """Exact microseconds on an unbounded UTC ordinal axis; never build UTC dates.

    Inputs pass AwareDatetime validation first. utcoffset() honors DST fold.
    Integer arithmetic preserves microseconds even beyond UTC year 1/9999.
    """
    offset = value.utcoffset()
    if offset is None:
        raise ValueError('instant comparison requires an aware datetime')
    wall = (((value.toordinal() * 24 + value.hour) * 60 + value.minute) * 60
            + value.second) * 1_000_000 + value.microsecond
    offset_us = (offset.days * 86400 + offset.seconds) * 1_000_000 + offset.microseconds
    return wall - offset_us


class QueryContract(StorageMetadata):
    model_config = ConfigDict(frozen=True, extra='forbid', revalidate_instances='always')


class FactIdentity(QueryContract):
    kind: Literal['observation', 'medication_order', 'medication_administration', 'inference', 'microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture', 'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance', 'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle', 'antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery', 'circulatory_pressure', 'circulatory_cardiac', 'circulatory_volume', 'circulatory_dynamic', 'circulatory_device_prediction', 'circulatory_perfusion', 'circulatory_oxygen', 'circulatory_lactate', 'circulatory_echo', 'circulatory_ecg', 'circulatory_vasoactive', 'circulatory_monitoring', 'circulatory_assessment', 'circulatory_event', 'circulatory_signal', 'laboratory_report', 'respiratory_record', 'transfusion_administration', 'haemostatic_medication_course', 'transfusion_request', 'transfusion_prescription', 'blood_product_disposition', 'transfusion_compatibility', 'transfusion_reaction', 'haemorrhage_episode', 'm10_assessment', 'transfusion_coverage_link', 'fluid_administration_link', 'm10_medication_detail', 'viscoelastic_report']
    id: Text


class TimeWindow(QueryContract):
    """Half-open query interval [start, end); at least one bound is required."""
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.start is None and self.end is None:
            raise ValueError('a time filter requires a bound')
        if self.start is not None and self.end is not None and _instant_key(self.start) >= _instant_key(self.end):
            raise ValueError('time filter requires start before end')
        return self


class ClinicalTimeFilter(TimeWindow):
    axis: Literal['event', 'effective']
    include_unknown: StrictBool = False
    include_imprecise: StrictBool = False


class IngestionTimeFilter(TimeWindow):
    """Assigned ingestion time only, never a commit-visibility assertion."""


@dataclass(frozen=True)
class HistoryResult:
    cutoff: RepositoryCutoff
    target: ContextTarget
    records: tuple[StoredFact, ...]
    selection: Literal['history', 'latest_known']
    identity: FactIdentity | None = None
    clinical_filter: ClinicalTimeFilter | None = None
    ingestion_filter: IngestionTimeFilter | None = None


def _instant_matches(value, window):
    return (window.start is None or _instant_key(value) >= _instant_key(window.start)) and (window.end is None or _instant_key(value) < _instant_key(window.end))


def _clinical_matches(stored, window):
    time = stored.fact.time
    start = time.event if window.axis == 'event' else time.effective_start
    if start is None or time.precision == 'unknown':
        return window.include_unknown
    if time.precision != 'instant' and not window.include_imprecise:
        return False
    if window.axis == 'event':
        return _instant_matches(start, window)
    # Retained effective endpoints are inclusive (the domain permits start=end).
    # A missing end is open-ended for this recorded-interval overlap predicate;
    # it does not assert current clinical applicability.
    return ((window.end is None or _instant_key(start) < _instant_key(window.end)) and
            (window.start is None or time.effective_end is None or _instant_key(time.effective_end) >= _instant_key(window.start)))


def _visible_chain(repository, identity, target, watermark, admitted_sequences=None):
    session = repository._session
    query = select(FactRow).where(
        FactRow.kind == identity.kind, FactRow.fact_id == identity.id,
        FactRow.ingestion_sequence <= watermark).order_by(FactRow.ingestion_sequence)
    if admitted_sequences is not None:
        query = query.limit(len(admitted_sequences) + 1)
    rows = session.scalars(query).all()
    if admitted_sequences is not None and tuple(row.ingestion_sequence for row in rows) != admitted_sequences:
        raise StorageIntegrityError('visible history differs from admitted envelopes')
    if not rows:
        return []
    # Check every visible envelope before decoding any member of this chain.
    # Reject mixed ownership, never filter it into an older terminal revision.
    if any((row.patient_id, row.encounter_id) != (target.patient_id, target.encounter_id)
           for row in rows):
        raise ScopeMismatch('visible revision chain does not belong to requested context')
    sequences = [row.ingestion_sequence for row in rows]
    # Future successors are deliberately excluded, including their payloads and
    # validation failures. Do not reuse the full-database _chain validator here.
    link_query = select(RevisionLink).where(
        RevisionLink.successor_sequence <= watermark,
        or_(RevisionLink.successor_sequence.in_(sequences),
            RevisionLink.predecessor_sequence.in_(sequences)))
    if admitted_sequences is not None:
        # At most two incident links per admitted row under the reviewed schema.
        link_query = link_query.limit(2 * len(sequences) + 1)
    links = session.scalars(link_query).all()
    expected = {(a.ingestion_sequence, b.ingestion_sequence) for a, b in zip(rows, rows[1:])}
    if {(link.predecessor_sequence, link.successor_sequence) for link in links} != expected or len(links) != len(expected):
        raise StorageIntegrityError('malformed visible revision links')
    retained = [load_fact(row, repository._repository_id) for row in rows]
    if any(item.fact.binding.target != target for item in retained):
        raise ScopeMismatch('visible revision chain does not belong to requested context')
    previous = None
    for stored in retained:
        if stored.fact.supersedes != previous:
            raise StorageIntegrityError('visible revision chain disagrees with retained payload')
        previous = stored.fact.reference
    return retained


def retrieve(repository, *, target, cutoff, identity=None, latest=False,
             clinical_filter=None, ingestion_filter=None, _admission=None):
    """Internal helper; called only inside checked repository operations."""
    # RepositoryCutoff predates revalidate_instances: round-trip Python fields to
    # revalidate even model_copy/model_construct objects supplied by callers.
    cutoff = RepositoryCutoff.model_validate(
        cutoff.model_dump(warnings=False) if isinstance(cutoff, RepositoryCutoff) else cutoff)
    if str(cutoff.repository_id) != repository._repository_id:
        raise ScopeMismatch('cutoff belongs to a different repository')
    maximum = repository._session.scalar(select(func.max(FactRow.ingestion_sequence))) or 0
    if cutoff.fact_watermark > maximum:
        raise PersistenceInputError('cutoff exceeds visible repository state')
    target = repository._target(target)
    identity = FactIdentity.model_validate(identity) if identity is not None else None
    clinical_filter = ClinicalTimeFilter.model_validate(clinical_filter) if clinical_filter is not None else None
    ingestion_filter = IngestionTimeFilter.model_validate(ingestion_filter) if ingestion_filter is not None else None
    admitted = None if _admission is None else dict(_admission.families)
    if admitted is not None:
        identities = [identity] if identity is not None else list(admitted)
    elif identity is not None:
        identities = [identity]
    else:
        keys = repository._session.execute(select(FactRow.kind, FactRow.fact_id).where(
            FactRow.patient_id == target.patient_id, FactRow.encounter_id == target.encounter_id,
            FactRow.ingestion_sequence <= cutoff.fact_watermark).distinct()).all()
        try:
            identities = []
            for kind, fact_id in keys:
                key = FactIdentity(kind=kind, id=fact_id)
                if (key.kind, key.id) != (kind, fact_id):
                    raise ValueError('noncanonical stored identity')
                identities.append(key)
        except ValueError:
            raise StorageIntegrityError('invalid visible fact identity') from None
    records = []
    for key in identities:
        chain = _visible_chain(repository, key, target, cutoff.fact_watermark,
            None if admitted is None else admitted.get(key, ()))
        # Both filters apply after latest selection, so neither can resurrect an
        # older revision. Validate all encountered visible records before filtering.
        records.extend(chain[-1:] if latest else chain)
    records.sort(key=lambda item: item.ingestion.ingestion_sequence)
    records = tuple(item for item in records
        if (clinical_filter is None or _clinical_matches(item, clinical_filter))
        and (ingestion_filter is None or _instant_matches(item.ingestion.ingested_at, ingestion_filter)))
    return HistoryResult(cutoff=cutoff, target=target, records=records,
        selection='latest_known' if latest else 'history', identity=identity,
        clinical_filter=clinical_filter, ingestion_filter=ingestion_filter)
