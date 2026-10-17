"""Recorded-state response shapes only; no assembly or projection behavior."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field
from app.api.schemas.common import (DTO, AwareTimestamp, Digest, Envelope, ExactReference, Identifier,
                                    QuantityView, ScopeView, SourceView, Text, TimesView)

Domain = Literal['laboratory', 'medication', 'antimicrobial', 'hemodynamic_support',
                 'respiratory_support', 'renal_support', 'fluid_output', 'microbiology',
                 'procedure', 'history_event']


class EvidenceView(DTO):
    reference: ExactReference
    selection_digest: Digest
    time: TimesView
    source: SourceView
    origin: Literal['observed', 'reported']
    verification: Identifier
    conflict: Identifier
    temporal_status: Identifier
    provenance_recorded_at: AwareTimestamp
    provenance_actor: Text | None = None
    provenance_limitations: tuple[Text, ...] = ()
    provenance_completeness: Identifier
    ingested_at: AwareTimestamp
    disclosures: tuple[Text, ...]


class LaboratoryView(EvidenceView):
    domain: Literal['laboratory'] = 'laboratory'
    concept_id: Identifier
    quantity: QuantityView


class MedicationView(EvidenceView):
    domain: Literal['medication'] = 'medication'
    event_type: Literal['medication_order', 'medication_administration']
    product_id: Identifier | None = None
    ingredient_ids: tuple[Identifier, ...] = ()
    formulation: Text | None = None
    status: Identifier
    dose: QuantityView | None = None
    dose_basis: Identifier | None = None
    route: Text | None = None
    schedule_text: Text | None = None
    frequency_occurrences: Annotated[int, Field(strict=True, gt=0)] | None = None
    frequency_interval: QuantityView | None = None


class CoverageView(DTO):
    domain: Domain
    mapping_support: Literal['supported', 'partial', 'unsupported']
    retrieval: Literal['completed', 'not_attempted']
    candidate_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    retained_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    unsuitable_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    source_completeness: Literal['unknown'] = 'unknown'
    limitations: tuple[Text, ...]


class MappingIssueView(DTO):
    reference: ExactReference
    domain: Literal['laboratory', 'medication'] | None
    reason: Identifier


class PatientStateViewResponse(DTO):
    transport_version: Literal['1'] = '1'
    scope: ScopeView
    state_context: Envelope = Field(repr=False)
    profile_id: Literal['SyntheticLaboratoryMedicationState'] = 'SyntheticLaboratoryMedicationState'
    profile_version: Literal['1'] = '1'
    laboratory: Annotated[tuple[LaboratoryView, ...], Field(max_length=1000)]
    medication: Annotated[tuple[MedicationView, ...], Field(max_length=1000)]
    coverage: Annotated[tuple[CoverageView, ...], Field(min_length=10, max_length=10)]
    issues: Annotated[tuple[MappingIssueView, ...], Field(max_length=2000)]
    disclosures: tuple[Text, ...]
