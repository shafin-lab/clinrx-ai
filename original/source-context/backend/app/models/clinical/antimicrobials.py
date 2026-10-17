"""M6.1 recorded antimicrobial contracts, not exposure or treatment reasoning."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .common import Text
from .recorded_v2 import (BoundedProvenance, Contract, PositiveQuantity, RecordedConcept, RecordedFactV2,
    RecordedTime, SourceCode, RawText, instant, missing_time)


class AntimicrobialIdentity(Contract):
    identity_version: Literal['1'] = '1'
    source_code: SourceCode
    raw_display: RawText
    canonical_id: Text | None = None
    ingredient_ids: Annotated[tuple[Text, ...], Field(max_length=16)] = ()
    product: RecordedConcept | None = None
    formulation: RawText | None = None
    mapping_status: Literal['mapped', 'unknown', 'unsupported', 'ambiguous']
    mapping_provenance: BoundedProvenance
    limitation: Text | None = None

    @model_validator(mode='after')
    def explicit_mapping(self):
        if self.mapping_status == 'mapped':
            if not self.canonical_id or not self.ingredient_ids:
                raise ValueError('mapped antimicrobial requires canonical ingredient/combo identity')
        elif self.canonical_id is not None or self.ingredient_ids or not self.limitation:
            raise ValueError('unresolved mapping cannot assert canonical equivalence')
        if len(set(self.ingredient_ids)) != len(self.ingredient_ids):
            raise ValueError('duplicate ingredient identity')
        if len(self.mapping_provenance.upstream) > 32 or len(self.mapping_provenance.limitations) > 32:
            raise ValueError('mapping provenance exceeds bounds')
        return self


class RecordedFrequency(Contract):
    occurrences: Annotated[int, Field(strict=True, gt=0)]
    interval: PositiveQuantity


class RecordedDose(Contract):
    amount: PositiveQuantity
    basis: Literal['per_dose', 'per_day', 'per_kg_per_dose', 'per_kg_per_day',
                   'per_m2_per_dose', 'total_administered', 'unknown']
    basis_detail: Text | None = None
    concentration: PositiveQuantity | None = None
    volume: PositiveQuantity | None = None
    rate: PositiveQuantity | None = None
    duration: PositiveQuantity | None = None

    @model_validator(mode='after')
    def basis_disclosure(self):
        if self.basis == 'unknown' and not self.basis_detail:
            raise ValueError('unknown dose basis requires disclosure')
        return self


class DocumentedTherapyPurpose(Contract):
    category: Literal['empiric', 'targeted', 'prophylactic', 'definitive', 'suppression']
    source_wording: RawText
    provenance: BoundedProvenance


class AntimicrobialOrder(RecordedFactV2):
    kind: Literal['antimicrobial_order'] = 'antimicrobial_order'
    antimicrobial: AntimicrobialIdentity
    prescribed_dose: RecordedDose | None = None
    route: RecordedConcept | None = None
    frequency: RecordedFrequency | None = None
    schedule: RawText | None = None
    scheduling: Literal['standing', 'prn', 'unknown'] = 'unknown'
    recorded_indication: RawText | None = None
    therapy_purpose: DocumentedTherapyPurpose | None = None
    order_status: Literal['draft', 'active', 'held', 'cancelled', 'completed', 'discontinued', 'unknown']
    created: RecordedTime = Field(default_factory=missing_time)
    intended_start: RecordedTime = Field(default_factory=missing_time)
    intended_end: RecordedTime = Field(default_factory=missing_time)
    discontinued: RecordedTime = Field(default_factory=missing_time)
    discontinuation_reason: RawText | None = None

    @property
    def semantic_time(self):
        return self.created

    @model_validator(mode='after')
    def order_shape(self):
        self.require_roles((), ())
        a, b = self.intended_start, self.intended_end
        if a.precision == b.precision == 'instant' and instant(a.value) > instant(b.value):
            raise ValueError('intended interval reversed')
        return self


class CompletedAntimicrobialAdministration(RecordedFactV2):
    kind: Literal['antimicrobial_administration'] = 'antimicrobial_administration'
    antimicrobial: AntimicrobialIdentity
    administered_dose: RecordedDose
    route: RecordedConcept | None = None
    completion: Literal['completed'] = 'completed'
    administered: RecordedTime = Field(default_factory=missing_time)
    infusion_start: RecordedTime = Field(default_factory=missing_time)
    infusion_end: RecordedTime = Field(default_factory=missing_time)
    therapy_purpose: DocumentedTherapyPurpose | None = None

    @property
    def semantic_time(self):
        return self.administered if self.administered.anchor is not None else self.infusion_start

    @model_validator(mode='after')
    def delivery_shape(self):
        self.require_roles((), ('order',))
        if self.administered_dose.basis != 'total_administered':
            raise ValueError('completed delivery requires recorded total')
        a, b = self.infusion_start, self.infusion_end
        if a.precision == b.precision == 'instant' and instant(a.value) > instant(b.value):
            raise ValueError('infusion interval reversed')
        return self


class AntimicrobialNonDelivery(RecordedFactV2):
    kind: Literal['antimicrobial_non_delivery'] = 'antimicrobial_non_delivery'
    antimicrobial: AntimicrobialIdentity
    status: Literal['held', 'refused', 'missed', 'cancelled', 'not_given', 'other']
    occurred: RecordedTime = Field(default_factory=missing_time)
    recorded_reason: RawText | None = None
    other_status: RawText | None = None

    @property
    def semantic_time(self):
        return self.occurred

    @model_validator(mode='after')
    def non_delivery_shape(self):
        self.require_roles((), ('order',))
        if (self.status == 'other') != (self.other_status is not None):
            raise ValueError('other non-delivery status requires explicit wording only')
        return self
