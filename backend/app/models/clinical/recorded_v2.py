"""M6.1 shared recorded-data contracts. No persistence admission or clinical policy."""
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .common import ContextTarget, DomainModel, Provenance, LineageEdge, Quantity, Reference, Text
from .facts import PatientFact
from app.persistence.canonical import canonical_payload

RawText = Annotated[str, Field(min_length=1, max_length=4096)]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


def instant(value):
    """Compare actual instants without UTC datetime overflow or DST fold equality."""
    offset = value.utcoffset()
    return (((value.toordinal()*24+value.hour)*60+value.minute)*60+value.second)*1_000_000 + value.microsecond - ((offset.days*86400+offset.seconds)*1_000_000+offset.microseconds)


def ref_key(ref):
    return ref.kind, ref.id, ref.version


class Contract(DomainModel):
    @model_validator(mode='after')
    def canonical(self):
        canonical_payload(self)
        return self

    @property
    def canonical_digest(self):
        return sha256(canonical_payload(self).encode('utf-8')).hexdigest()


class BoundedProvenance(Provenance):
    upstream: Annotated[tuple[LineageEdge, ...], Field(max_length=32)] = ()
    limitations: Annotated[tuple[Text, ...], Field(max_length=32)] = ()

    @model_validator(mode='before')
    @classmethod
    def accept_existing_provenance(cls, value):
        return value.model_dump() if isinstance(value, Provenance) else value

    @model_validator(mode='after')
    def bounded_basis(self):
        if any(len(edge.basis) > 16 for edge in self.upstream):
            raise ValueError('provenance basis exceeds bounds')
        return self


class RecordedTime(Contract):
    status: Literal['known', 'missing', 'unknown', 'not_recorded']
    precision: Literal['instant', 'day', 'approximate', 'bounded', 'unknown'] = 'unknown'
    value: AwareDatetime | None = None
    lower: AwareDatetime | None = None
    upper: AwareDatetime | None = None
    uncertainty: Text | None = None

    @model_validator(mode='after')
    def shape(self):
        if self.status != 'known':
            if self.value is not None or self.lower is not None or self.upper is not None or self.precision != 'unknown':
                raise ValueError('unavailable time cannot supply an anchor or precision')
        elif self.precision == 'bounded':
            if self.lower is None or self.upper is None or instant(self.lower) > instant(self.upper):
                raise ValueError('bounded time requires ordered bounds')
            if self.value is not None and not instant(self.lower) <= instant(self.value) <= instant(self.upper):
                raise ValueError('representative time lies outside bounds')
        elif self.precision in ('instant', 'day', 'approximate'):
            if self.value is None or self.lower is not None or self.upper is not None:
                raise ValueError('recorded time requires one representative value')
            if self.precision == 'approximate' and not self.uncertainty:
                raise ValueError('approximate time requires uncertainty')
        else:
            raise ValueError('known time requires explicit precision')
        return self

    @property
    def anchor(self):
        return self.value if self.value is not None else self.lower


def missing_time():
    return RecordedTime(status='not_recorded')


class SourceCode(Contract):
    namespace: Text
    code: Text
    version: Text | None = None
    raw_display: RawText


class RecordedConcept(Contract):
    raw_display: RawText
    coding: SourceCode | None = None


class ExactQuantity(Quantity):
    @field_validator('value', mode='before')
    @classmethod
    def no_float(cls, value):
        if not isinstance(value, (str, Decimal, int)) or isinstance(value, bool):
            raise ValueError('quantity requires Decimal, decimal string or integer; never float')
        return value


class NonnegativeQuantity(ExactQuantity):
    @model_validator(mode='after')
    def nonnegative(self):
        if self.value < 0:
            raise ValueError('negative measured magnitude')
        return self


class PositiveQuantity(ExactQuantity):
    @model_validator(mode='after')
    def positive(self):
        if self.value <= 0:
            raise ValueError('positive recorded amount required')
        return self


class StableIdentity(Contract):
    kind: Text
    id: Text


ROLE_KINDS = {
    'specimen': ('microbiology_specimen',),
    'isolate': ('microbiology_isolate',),
    'collection_set': ('blood_culture_set',),
    'bottle': ('blood_culture_bottle',),
    'order': ('antimicrobial_order', 'medication_order'),
}


class DomainBinding(Contract):
    """An association assertion, not derived_from evidence or a repository lookup."""
    role: Literal['specimen', 'isolate', 'collection_set', 'bottle', 'order']
    scope: ContextTarget
    status: Literal['resolved', 'unresolved', 'ambiguous']
    stable_target: StableIdentity | None = None
    exact: Reference | None = None
    candidates: Annotated[tuple[Reference, ...], Field(max_length=16)] = ()
    provenance: BoundedProvenance
    limitation: Text | None = None

    @field_validator('candidates')
    @classmethod
    def ordered(cls, refs):
        if len(set(refs)) != len(refs):
            raise ValueError('duplicate binding candidates')
        return tuple(sorted(refs, key=ref_key))

    @model_validator(mode='after')
    def coherent(self):
        if self.scope.encounter_id is None:
            raise ValueError('binding requires encounter scope')
        if self.status == 'resolved':
            if self.exact is None or self.stable_target is None or self.candidates:
                raise ValueError('resolved binding requires one exact stable target')
        elif self.exact is not None or not self.limitation:
            raise ValueError('unresolved binding requires limitation and no exact target')
        if self.status == 'ambiguous' and len(self.candidates) < 2:
            raise ValueError('ambiguous binding requires multiple candidates')
        if self.status == 'unresolved' and self.candidates:
            raise ValueError('unresolved binding has no candidate assertions')
        refs = self.candidates + ((self.exact,) if self.exact else ())
        if self.stable_target and self.stable_target.kind not in ROLE_KINDS[self.role]:
            raise ValueError('binding target kind differs from role')
        for ref in refs:
            if ref.kind not in ROLE_KINDS[self.role]:
                raise ValueError('binding reference kind differs from role')
            if self.stable_target and (ref.kind, ref.id) != (self.stable_target.kind, self.stable_target.id):
                raise ValueError('binding exact identity contradicts stable target')
        if len(self.provenance.upstream) > 32 or len(self.provenance.limitations) > 32:
            raise ValueError('binding provenance exceeds contract bounds')
        return self


class ReportState(Contract):
    status: Literal['preliminary', 'interim', 'final', 'withdrawn']
    change: Literal['original', 'amended', 'corrected', 'superseded'] = 'original'
    reported: RecordedTime = Field(default_factory=missing_time)
    available: RecordedTime = Field(default_factory=missing_time)
    preliminary_reported: RecordedTime = Field(default_factory=missing_time)
    final_reported: RecordedTime = Field(default_factory=missing_time)
    changed: RecordedTime = Field(default_factory=missing_time)


class RecordedFactV2(PatientFact):
    """Recorded v2 kinds; separate from the original governance Fact union."""
    contract_version: Literal['2'] = '2'
    provenance: BoundedProvenance
    origin: Literal['observed', 'reported']
    source_identifiers: Annotated[tuple[SourceCode, ...], Field(max_length=16)] = ()
    domain_bindings: Annotated[tuple[DomainBinding, ...], Field(max_length=16)] = ()
    disclosures: Annotated[tuple[Text, ...], Field(max_length=32)] = ()
    uncertainty: Annotated[tuple[Text, ...], Field(max_length=32)] = ()

    @model_validator(mode='after')
    def v2_integrity(self):
        if type(self) is RecordedFactV2:
            raise ValueError('construct a concrete v2 record')
        if self.time.event is not None or self.time.effective_start is not None or self.time.effective_end is not None:
            raise ValueError('use typed v2 clinical times; common time retains recording/retrieval/processing only')
        if self.binding.target.encounter_id is None:
            raise ValueError('v2 record requires encounter scope')
        if len({b.role for b in self.domain_bindings}) != len(self.domain_bindings):
            raise ValueError('duplicate binding role')
        for binding in self.domain_bindings:
            if binding.scope != self.binding.target or binding.exact == self.reference:
                raise ValueError('domain binding scope or self-reference invalid')
        if len(self.provenance.upstream) > 32 or len(self.provenance.limitations) > 32:
            raise ValueError('provenance exceeds contract bounds')
        if any(len(e.basis) > 16 for e in self.provenance.upstream):
            raise ValueError('provenance basis exceeds contract bounds')
        if len(set(self.source_identifiers)) != len(self.source_identifiers):
            raise ValueError('duplicate source identifier')
        canonical_payload(self)
        return self

    def require_roles(self, required, allowed):
        roles = {b.role for b in self.domain_bindings}
        if not set(required) <= roles or not roles <= set(allowed):
            raise ValueError('domain binding roles differ from record type')

    @property
    def stable_identity(self):
        return StableIdentity(kind=self.kind, id=self.id)

    @property
    def canonical_digest(self):
        return sha256(canonical_payload(self).encode('utf-8')).hexdigest()

    @property
    def semantic_time(self):
        raise NotImplementedError
