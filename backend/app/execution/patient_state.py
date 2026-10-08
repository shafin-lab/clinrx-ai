"""Pure bounded recorded-state contracts; no assembly, reasoning or storage."""
from datetime import timezone
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from app.models.clinical.common import (
    Binding, ClinicalTime, ClinicalValue, ContextTarget, DomainModel, Provenance,
    Quantity, Reference, Source, Text, validate_origin,
)
from app.models.clinical.facts import Dose, Frequency, MedicationIdentity
from app.persistence.mapping import canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff


def _instant(value):
    return value.astimezone(timezone.utc)


def _metadata(value):
    # StorageMetadata does not revalidate instances itself. Revalidate supplied
    # copies here without changing its existing persistence semantics.
    if isinstance(value, (RepositoryCutoff, IngestionMetadata)):
        value = value.model_dump()
    if isinstance(value, dict) and 'payload_version' in value and type(value['payload_version']) is not int:
        raise ValueError('ingestion payload version must be an exact integer')
    return value


class PatientStateScope(DomainModel):
    patient_id: Text
    encounter_id: Text
    review_start: AwareDatetime
    review_end: AwareDatetime
    repository_cutoff: RepositoryCutoff
    state_contract_version: Literal['1'] = '1'

    _cutoff = field_validator('repository_cutoff', mode='before')(_metadata)

    @property
    def target(self):
        return ContextTarget(patient_id=self.patient_id, encounter_id=self.encounter_id)

    @model_validator(mode='after')
    def ordered(self):
        if _instant(self.review_start) > _instant(self.review_end):
            raise ValueError('review interval is reversed')
        canonical_payload(self)
        return self


class RecordedParameter(DomainModel):
    concept_id: Text
    value: ClinicalValue


class LaboratoryState(DomainModel):
    domain: Literal['laboratory'] = 'laboratory'
    concept_id: Text
    value: ClinicalValue
    specimen: Source | None = None
    specimen_type: Text | None = None
    status: Text | None = None


class MedicationState(DomainModel):
    domain: Literal['medication'] = 'medication'
    medication: MedicationIdentity
    dose: Dose | None = None
    route: Text | None = None
    frequency: Frequency | None = None
    schedule_text: Text | None = None
    status: Text

    @model_validator(mode='after')
    def consistent_frequency(self):
        if self.frequency is not None and self.dose is not None and self.dose.frequency is not None:
            if canonical_payload(self.frequency) != canonical_payload(self.dose.frequency):
                raise ValueError('recorded frequency contradicts dose frequency')
        return self


class AntimicrobialState(MedicationState):
    domain: Literal['antimicrobial'] = 'antimicrobial'
    recorded_indication: Text | None = None


class HemodynamicSupportState(DomainModel):
    domain: Literal['hemodynamic_support'] = 'hemodynamic_support'
    support_id: Text
    agent: MedicationIdentity | None = None
    status: Text
    rate: Quantity | None = None
    dose: Dose | None = None
    parameters: tuple[RecordedParameter, ...] = ()


class RespiratorySupportState(DomainModel):
    domain: Literal['respiratory_support'] = 'respiratory_support'
    mode: Text
    status: Text
    parameters: tuple[RecordedParameter, ...] = ()


class RenalSupportState(DomainModel):
    domain: Literal['renal_support'] = 'renal_support'
    modality: Text
    status: Text
    parameters: tuple[RecordedParameter, ...] = ()


class FluidOutputState(DomainModel):
    domain: Literal['fluid_output'] = 'fluid_output'
    category: Text
    quantity: Quantity
    site: Text | None = None


class RecordedSusceptibility(DomainModel):
    antimicrobial: MedicationIdentity
    result: ClinicalValue
    method: Text | None = None


class MicrobiologyState(DomainModel):
    domain: Literal['microbiology'] = 'microbiology'
    specimen: Source | None = None
    specimen_type: Text | None = None
    collected_at: AwareDatetime | None = None
    organisms: tuple[Text, ...] = ()
    result: ClinicalValue
    status: Text
    susceptibilities: tuple[RecordedSusceptibility, ...] = ()

    @model_validator(mode='after')
    def specimen_disclosure(self):
        if self.specimen is None and self.specimen_type is None:
            raise ValueError('recorded specimen identity or type required')
        return self


class ProcedureState(DomainModel):
    domain: Literal['procedure'] = 'procedure'
    concept_id: Text
    status: Text
    site: Text | None = None
    recorded_context: Text | None = None


class HistoryEventState(DomainModel):
    domain: Literal['history_event'] = 'history_event'
    concept_id: Text
    status: Text
    recorded_context: Text | None = None


StatePayload = Annotated[
    LaboratoryState | MedicationState | AntimicrobialState | HemodynamicSupportState |
    RespiratorySupportState | RenalSupportState | FluidOutputState | MicrobiologyState |
    ProcedureState | HistoryEventState, Field(discriminator='domain')]

# Structural source-category compatibility only; no concept/eligibility policy.
_REFERENCE_KINDS = {
    'laboratory': ('observation',),
    'medication': ('medication_order', 'medication_administration'),
    'antimicrobial': ('medication_order', 'medication_administration'),
    'hemodynamic_support': ('observation', 'medication_order', 'medication_administration'),
    'respiratory_support': ('observation', 'procedure'),
    'renal_support': ('observation', 'procedure'),
    'fluid_output': ('observation',),
    'microbiology': ('observation',),
    'procedure': ('procedure',),
    'history_event': ('observation', 'condition', 'procedure'),
}


class RetainedStateItem(DomainModel):
    """Supplied source evidence, not proof of a repository read or authentic mapping.

    payload_digest covers the typed domain payload, not a persistence FactRow.
    Source/ref/time/provenance are retained once here, not copied into payloads.
    """
    reference: Reference
    binding: Binding
    origin: Literal['observed', 'reported']
    time: ClinicalTime
    provenance: Provenance
    ingestion: IngestionMetadata | None = None
    payload: StatePayload
    payload_digest: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    temporal_basis: Literal['event', 'effective_interval', 'contextual_history'] = 'event'
    verification: Literal['unverified', 'verified', 'clinician_confirmed'] = 'unverified'
    conflict: Literal['none_known', 'unresolved', 'resolved', 'unknown'] = 'unknown'
    temporal_status: Literal['current', 'historical', 'unknown'] = 'unknown'
    disclosures: tuple[Text, ...] = ()

    _ingestion = field_validator('ingestion', mode='before')(_metadata)

    @property
    def domain(self):
        return self.payload.domain

    @property
    def ordering_key(self):
        # Required temporal evidence, never an ingestion-time fallback.
        anchor = self.time.event or self.time.effective_start
        return (_instant(anchor), self.domain, self.reference.kind, self.reference.id, self.reference.version)

    @property
    def canonical_digest(self):
        return sha256(canonical_payload(self).encode('utf-8')).hexdigest()

    @model_validator(mode='after')
    def coherent(self):
        if self.binding.target.encounter_id is None:
            raise ValueError('state items require an encounter scope')
        if self.reference.kind not in _REFERENCE_KINDS[self.domain]:
            raise ValueError('source reference category differs from state domain')
        if sha256(canonical_payload(self.payload).encode('utf-8')).hexdigest() != self.payload_digest:
            raise ValueError('state payload digest differs from supplied content')
        validate_origin(self.origin, self.provenance, {})
        if self.reference in self.provenance.dependencies:
            raise ValueError('state item cannot depend on itself')
        if self.ingestion is None and not self.disclosures:
            raise ValueError('missing durable ingestion metadata must be disclosed')
        if self.time.effective_end is not None and (
                self.time.effective_start is None or
                _instant(self.time.effective_end) < _instant(self.time.effective_start)):
            raise ValueError('effective interval is reversed by actual instant')
        if self.temporal_basis == 'event' and self.time.event is None:
            raise ValueError('event basis requires a clinical event time')
        if self.temporal_basis == 'effective_interval' and self.time.effective_start is None:
            raise ValueError('interval basis requires a recorded effective start')
        if self.temporal_basis == 'contextual_history' and (
                self.domain != 'history_event' or (self.time.event is None and self.time.effective_start is None)):
            raise ValueError('contextual history requires a history item with recorded timing')
        parameters = getattr(self.payload, 'parameters', ())
        if len({p.concept_id for p in parameters}) != len(parameters):
            raise ValueError('duplicate recorded parameter identity')
        canonical_payload(self)
        return self


_BUCKETS = ('laboratory', 'medication', 'antimicrobial', 'hemodynamic_support',
            'respiratory_support', 'renal_support', 'fluid_output', 'microbiology',
            'procedure', 'history_event')


class PatientStateSnapshot(DomainModel):
    """Bounded supplied state, separate from governance and inference dependencies."""
    scope: PatientStateScope
    laboratory: tuple[RetainedStateItem, ...] = ()
    medication: tuple[RetainedStateItem, ...] = ()
    antimicrobial: tuple[RetainedStateItem, ...] = ()
    hemodynamic_support: tuple[RetainedStateItem, ...] = ()
    respiratory_support: tuple[RetainedStateItem, ...] = ()
    renal_support: tuple[RetainedStateItem, ...] = ()
    fluid_output: tuple[RetainedStateItem, ...] = ()
    microbiology: tuple[RetainedStateItem, ...] = ()
    procedure: tuple[RetainedStateItem, ...] = ()
    history_event: tuple[RetainedStateItem, ...] = ()
    disclosures: tuple[Text, ...] = ()

    @field_validator(*_BUCKETS)
    @classmethod
    def deterministic_items(cls, items):
        return tuple(sorted(items, key=lambda item: item.ordering_key))

    @property
    def ordered_items(self):
        return tuple(sorted((item for name in _BUCKETS for item in getattr(self, name)),
                            key=lambda item: item.ordering_key))

    @property
    def canonical_digest(self):
        return sha256(canonical_payload(self).encode('utf-8')).hexdigest()

    @model_validator(mode='after')
    def bounded(self):
        refs, sequences = set(), set()
        scope = self.scope
        start, end = _instant(scope.review_start), _instant(scope.review_end)
        for domain in _BUCKETS:
            for item in getattr(self, domain):
                if item.domain != domain:
                    raise ValueError('item payload belongs to a different state bucket')
                if item.binding.target != scope.target:
                    raise ValueError('state item patient/encounter differs from snapshot')
                if item.reference in refs:
                    raise ValueError('duplicate exact state reference')
                refs.add(item.reference)
                metadata = item.ingestion
                if metadata is not None:
                    if (metadata.repository_id != scope.repository_cutoff.repository_id or
                            metadata.ingestion_sequence > scope.repository_cutoff.fact_watermark):
                        raise ValueError('state ingestion lies outside repository prefix')
                    if metadata.ingestion_sequence in sequences:
                        raise ValueError('different state records share one ingestion identity')
                    sequences.add(metadata.ingestion_sequence)
                time = item.time
                if item.temporal_basis == 'event':
                    if not start <= _instant(time.event) <= end:
                        raise ValueError('event lies outside closed review window')
                elif item.temporal_basis == 'effective_interval':
                    if (_instant(time.effective_start) > end or
                            (time.effective_end is not None and _instant(time.effective_end) < start)):
                        raise ValueError('recorded interval does not overlap review window')
                else:
                    if _instant(time.event or time.effective_start) > end:
                        raise ValueError('contextual history follows review end')
        canonical_payload(self)
        return self
