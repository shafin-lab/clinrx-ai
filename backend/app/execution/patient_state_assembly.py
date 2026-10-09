"""One explicit repository prefix projected into recorded laboratory/medication state."""
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator
from sqlalchemy import Engine

from app.execution.patient_state import (
    LaboratoryState, MedicationState, PatientStateScope, PatientStateSnapshot,
    RetainedStateItem,
)
from app.models.clinical.common import DomainModel, Quantity, Reference
from app.models.clinical.facts import ClinicalObservation, MedicationAdministration, MedicationOrder
from app.persistence.errors import PersistenceError, PersistenceInputError, StorageIntegrityError, TransactionAborted
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction

Domain = Literal['laboratory', 'medication', 'antimicrobial', 'hemodynamic_support',
                 'respiratory_support', 'renal_support', 'fluid_output', 'microbiology',
                 'procedure', 'history_event']
DOMAINS = ('laboratory', 'medication', 'antimicrobial', 'hemodynamic_support',
           'respiratory_support', 'renal_support', 'fluid_output', 'microbiology',
           'procedure', 'history_event')
Reason = Literal['unsupported_source_profile', 'structurally_unsuitable_source_shape',
                 'missing_required_event_time', 'unsupported_temporal_precision',
                 'outside_review_window']
_REASONS = ('unsupported_source_profile', 'structurally_unsuitable_source_shape',
            'missing_required_event_time', 'unsupported_temporal_precision', 'outside_review_window')
_UNSUITABLE = frozenset(_REASONS[1:4])
Limitation = Literal['source_completeness_unknown', 'availability_by_clinical_time_not_established',
                     'narrow_laboratory_source_profile', 'mapping_unsupported']
_COMMON_LIMITS = ('source_completeness_unknown', 'availability_by_clinical_time_not_established')
DISCLOSURES = (
    'Only the versioned synthetic laboratory source profile and durable medication orders/administrations are mapped.',
    'Unsupported domains may contain real-world evidence; an empty bucket does not establish clinical absence.',
    'Source completeness is unknown, including for completed retrieval.',
    'Availability by clinical time is not established; the repository prefix is not an availability timestamp.',
)
Count = Annotated[int, Field(strict=True, ge=0)]


def _instant(value):
    offset = value.utcoffset()
    wall = (((value.toordinal() * 24 + value.hour) * 60 + value.minute) * 60 + value.second) * 1_000_000 + value.microsecond
    return wall - ((offset.days * 86400 + offset.seconds) * 1_000_000 + offset.microseconds)


def _support(domain):
    return 'partial' if domain == 'laboratory' else 'supported' if domain == 'medication' else 'unsupported'


def _limits(domain):
    return _COMMON_LIMITS + (('narrow_laboratory_source_profile',) if domain == 'laboratory'
                            else () if domain == 'medication' else ('mapping_unsupported',))


class DomainSourceCoverage(DomainModel):
    domain: Domain
    mapping_support: Literal['supported', 'partial', 'unsupported']
    retrieval: Literal['completed', 'not_attempted']
    candidate_count: Count | None = None
    retained_count: Count | None = None
    unsuitable_count: Count | None = None
    source_completeness: Literal['unknown'] = 'unknown'
    limitations: tuple[Limitation, ...]

    @model_validator(mode='after')
    def coherent(self):
        counts = (self.candidate_count, self.retained_count, self.unsuitable_count)
        if self.mapping_support != _support(self.domain) or self.limitations != _limits(self.domain):
            raise ValueError('coverage must match the fixed assembly profile')
        if self.mapping_support == 'unsupported':
            if self.retrieval != 'not_attempted' or any(n is not None for n in counts):
                raise ValueError('unsupported coverage cannot claim retrieval or counts')
        elif (self.retrieval != 'completed' or any(n is None for n in counts)
              or self.retained_count + self.unsuitable_count > self.candidate_count):
            raise ValueError('completed coverage requires consistent counts')
        return self


class PatientStateMappingIssue(DomainModel):
    reference: Reference
    domain: Literal['laboratory', 'medication'] | None
    reason: Reason

    @model_validator(mode='after')
    def coherent(self):
        if self.domain is None and self.reason != 'unsupported_source_profile':
            raise ValueError('unclassified source requires unsupported profile issue')
        if self.domain == 'medication' and self.reason == 'unsupported_source_profile':
            raise ValueError('durable medication types have a mapping')
        return self


def _issue_key(issue):
    ref = issue.reference
    return (ref.kind, ref.id, ref.version, _REASONS.index(issue.reason))


def _snapshot_disclosures(issues):
    return DISCLOSURES + (('Some terminal source records were omitted; consult the typed assembly mapping issues.',) if issues else ())


class PatientStateAssemblyResult(DomainModel):
    snapshot: PatientStateSnapshot
    profile_id: Literal['SyntheticLaboratoryMedicationState'] = 'SyntheticLaboratoryMedicationState'
    profile_version: Literal['1'] = '1'
    coverage: tuple[DomainSourceCoverage, ...]
    issues: tuple[PatientStateMappingIssue, ...] = ()

    @model_validator(mode='after')
    def coherent(self):
        if tuple(c.domain for c in self.coverage) != DOMAINS:
            raise ValueError('require exactly ten ordered coverage entries')
        if self.issues != tuple(sorted(self.issues, key=_issue_key)):
            raise ValueError('mapping issues must have canonical order')
        refs = [i.reference for i in self.issues]
        retained = self.snapshot.ordered_items
        if len(set(refs)) != len(refs) or set(refs).intersection(i.reference for i in retained):
            raise ValueError('mapping outcomes must have distinct exact identities')
        if any(i.ingestion is None for i in retained):
            raise ValueError('source-backed assembly requires ingestion metadata')
        if self.snapshot.disclosures != _snapshot_disclosures(self.issues):
            raise ValueError('snapshot must retain assembly limitations')
        for coverage in self.coverage:
            items = getattr(self.snapshot, coverage.domain)
            if coverage.mapping_support == 'unsupported':
                if items:
                    raise ValueError('unsupported bucket cannot contain assembled items')
            else:
                issues = tuple(i for i in self.issues if i.domain == coverage.domain)
                if (coverage.retained_count != len(items)
                        or coverage.candidate_count != len(items) + len(issues)
                        or coverage.unsuitable_count != sum(i.reason in _UNSUITABLE for i in issues)):
                    raise ValueError('coverage differs from mapping outcomes')
        canonical_payload(self)
        return self


def _temporal_reason(fact, scope, basis):
    time = fact.time
    start, end = _instant(scope.review_start), _instant(scope.review_end)
    if basis == 'effective_interval':
        if time.precision == 'unknown':
            return 'unsupported_temporal_precision'
        if (_instant(time.effective_start) > end or
                (time.effective_end is not None and _instant(time.effective_end) < start)):
            return 'outside_review_window'
        return None
    if time.event is None:
        return 'missing_required_event_time'
    if time.precision != 'instant' or time.uncertainty is not None:
        return 'unsupported_temporal_precision'
    return None if start <= _instant(time.event) <= end else 'outside_review_window'


def _map(stored, scope):
    fact = stored.fact
    basis = 'event'
    if isinstance(fact, ClinicalObservation):
        domain = 'laboratory'
        source = fact.provenance.source
        if (fact.concept_id != 'synthetic-serum-creatinine'
                or source.namespace != 'clinrx.synthetic.serum-creatinine'
                or source.version != '1' or source.channel not in ('measurement', 'external_record')):
            return domain, None, 'unsupported_source_profile'
        if fact.value.status != 'known' or not isinstance(fact.value.value, Quantity):
            return domain, None, 'structurally_unsuitable_source_shape'
        payload = LaboratoryState(concept_id=fact.concept_id, value=fact.value)
    elif isinstance(fact, MedicationOrder):
        domain = 'medication'
        basis = 'effective_interval' if fact.time.effective_start is not None else 'event'
        payload = MedicationState(medication=fact.medication, dose=fact.prescribed_dose,
            route=fact.route, frequency=fact.prescribed_dose.frequency,
            schedule_text=fact.schedule_text, status=fact.order_status)
    elif isinstance(fact, MedicationAdministration):
        domain = 'medication'
        payload = MedicationState(medication=fact.medication, dose=fact.administered_dose,
            route=fact.route, frequency=fact.administered_dose.frequency, status='administered')
    else:
        return None, None, 'unsupported_source_profile'
    reason = _temporal_reason(fact, scope, basis)
    if reason:
        return domain, None, reason
    disclosures = tuple('Source uncertainty: ' + text for text in fact.uncertainty)
    if basis == 'effective_interval':
        disclosures += ('Recorded interval overlap does not establish currently active therapy; an absent end remains unknown.',)
        if fact.time.precision != 'instant' or fact.time.uncertainty is not None:
            disclosures += ('Interval membership uses recorded representative endpoints; timing precision and uncertainty remain retained.',)
    if domain == 'laboratory':
        disclosures += ('Dedicated specimen identity and result status are not represented by this durable observation model.',)
    item = RetainedStateItem(reference=fact.reference, binding=fact.binding,
        origin=fact.origin, time=fact.time, provenance=fact.provenance, ingestion=stored.ingestion,
        payload=payload, payload_digest=sha256(canonical_payload(payload).encode('utf-8')).hexdigest(),
        temporal_basis=basis, verification=fact.verification, conflict=fact.conflict,
        temporal_status=fact.temporal_status, disclosures=disclosures)
    return domain, item, None


def _assemble(repository, scope):
    history = repository.list_latest_known(target=scope.target, cutoff=scope.repository_cutoff)
    if (history.target != scope.target or canonical_payload(history.cutoff) != canonical_payload(scope.repository_cutoff)
            or history.selection != 'latest_known' or history.clinical_filter is not None
            or history.ingestion_filter is not None or history.identity is not None):
        raise StorageIntegrityError('historical result does not match assembly request')
    seen, stable = {}, set()
    buckets = {'laboratory': [], 'medication': []}
    issues = []
    for stored in history.records:
        fact, metadata = stored.fact, stored.ingestion
        if (fact.binding.target != scope.target or metadata.repository_id != scope.repository_cutoff.repository_id
                or metadata.ingestion_sequence > scope.repository_cutoff.fact_watermark):
            raise StorageIntegrityError('historical record lies outside assembly scope')
        signature = (canonical_payload(fact), canonical_payload(metadata))
        ref = fact.reference
        if ref in seen:
            if seen[ref] != signature:
                raise StorageIntegrityError('contradictory exact historical record')
            continue
        key = (ref.kind, ref.id)
        if key in stable:
            raise StorageIntegrityError('historical result contains multiple terminal revisions')
        seen[ref] = signature
        stable.add(key)
        domain, item, reason = _map(stored, scope)
        if reason is not None:
            issues.append(PatientStateMappingIssue(reference=ref, domain=domain, reason=reason))
        else:
            buckets[domain].append(item)
    issues = tuple(sorted(issues, key=_issue_key))
    snapshot = PatientStateSnapshot(scope=scope, **buckets, disclosures=_snapshot_disclosures(issues))
    coverage = []
    for domain in DOMAINS:
        counts = {}
        if domain in buckets:
            own = tuple(i for i in issues if i.domain == domain)
            counts = dict(candidate_count=len(buckets[domain]) + len(own), retained_count=len(buckets[domain]),
                          unsuitable_count=sum(i.reason in _UNSUITABLE for i in own))
        coverage.append(DomainSourceCoverage(domain=domain, mapping_support=_support(domain),
            retrieval='completed' if domain in buckets else 'not_attempted', limitations=_limits(domain), **counts))
    return PatientStateAssemblyResult(snapshot=snapshot, coverage=tuple(coverage), issues=issues)


def assemble_patient_state(engine: Engine, *, scope: PatientStateScope) -> PatientStateAssemblyResult:
    """Return only after one existing transaction exits; no clocks, writes or retries."""
    if not isinstance(engine, Engine):
        raise PersistenceInputError('patient state assembly requires an Engine')
    try:
        scope = PatientStateScope.model_validate(scope)
    except (ValidationError, ValueError, TypeError):
        raise PersistenceInputError('invalid patient state scope') from None
    try:
        with transaction(engine) as repository:
            result = _assemble(repository, scope)
        return result
    except PersistenceError as error:
        raise error from None
    except Exception:
        raise TransactionAborted('patient state assembly failed') from None
