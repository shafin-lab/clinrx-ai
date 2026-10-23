"""M10 source owners: exact quantities, independent clinical events and VET reports."""
from decimal import Decimal
from typing import Annotated, Literal, Union
from uuid import UUID
from pydantic import Field, StrictBool, StrictStr, TypeAdapter, field_validator, model_validator
from app.models.clinical.common import DomainModel, Reference
from app.models.clinical.recorded_v2 import RecordedFactV2, RecordedTime, missing_time
from app.api.schemas.common import AwareTimestamp

Text = Annotated[StrictStr, Field(min_length=1, max_length=4096)]
Short = Annotated[StrictStr, Field(min_length=1,max_length=256)]
DecimalText = Annotated[StrictStr, Field(pattern=r'^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,12})?$')]
Stamp = Annotated[StrictStr,Field(min_length=20,max_length=40)]

class M10Time(DomainModel):
    status: Literal['known','unknown','not_recorded'] = 'not_recorded'
    precision: Literal['instant','day','approximate','bounded','unknown'] = 'unknown'
    value: Stamp | None = None
    lower: Stamp | None = None
    upper: Stamp | None = None
    uncertainty: Text | None = None
    @model_validator(mode='after')
    def coherent(self):
        for v in (self.value,self.lower,self.upper):
            if v is not None: TypeAdapter(AwareTimestamp).validate_python(v)
        if self.status!='known':
            if any(v is not None for v in (self.value,self.lower,self.upper)) or self.precision!='unknown': raise ValueError('unknown time cannot have a value')
        elif self.precision=='bounded':
            if not self.lower or not self.upper or self.value or TypeAdapter(AwareTimestamp).validate_python(self.lower)>TypeAdapter(AwareTimestamp).validate_python(self.upper): raise ValueError('ordered bounds required')
        elif self.precision in ('instant','day','approximate'):
            if not self.value or self.lower or self.upper:raise ValueError('one source timestamp required')
            if self.precision=='approximate' and not self.uncertainty:raise ValueError('approximate time needs uncertainty')
        else:raise ValueError('known time needs precision')
        return self
    def recorded(self):
        return RecordedTime(status=self.status,precision=self.precision,value=self.value,lower=self.lower,upper=self.upper,uncertainty=self.uncertainty)

class EvidencePin(DomainModel):
    reference: Reference
    digest: Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{64}$')]
    component_id: Short | None = None

class ProductAttribute(DomainModel):
    name: Literal['leukodepleted','irradiated','washed','cmv_seronegative','pathogen_reduced','antigen_selected','phenotype_matched','hla_hpa_selected','volume_reduced','frozen_deglycerolised','other']
    value: Literal['yes','no','unknown','not_applicable']
    source: Text
    verification: Literal['source_reported','verified','unverified'] = 'source_reported'

class Product(DomainModel):
    family: Literal['prbc','plasma','platelets','cryoprecipitate','whole_blood','cell_salvage','pcc','fibrinogen_concentrate','factor_concentrate','antifibrinolytic','protamine','calcium','other']
    preparation: Short
    label: Text
    modifications: Annotated[tuple[ProductAttribute,...],Field(max_length=16)] = ()
    donation_id: Short | None = None
    product_code: Short | None = None
    division: Short | None = None
    component_id: Short | None = None
    pool_id: Short | None = None
    constituents: Annotated[tuple[Short,...],Field(max_length=128)] = ()
    units_per_pool: Annotated[int,Field(strict=True,gt=0,le=128)] | None = None
    supplier: Short | None = None
    batch: Short | None = None
    vial_strength: Text | None = None
    factor_basis: Short | None = None
    donor_group: Short | None = None
    raw_barcode: Text | None = None
    barcode_parser: Short | None = None
    @model_validator(mode='after')
    def unique_attributes(self):
        if len({a.name for a in self.modifications})!=len(self.modifications):raise ValueError('duplicate product modification')
        if self.units_per_pool and self.constituents and len(self.constituents)!=self.units_per_pool:raise ValueError('pool composition disagrees')
        return self

class Amount(DomainModel):
    dimension: Literal['count','volume','dose','vials','fraction','platelet_content']
    value: DecimalText
    unit: Short
    basis: Short
    @model_validator(mode='after')
    def amount(self):
        if self.dimension=='volume' and self.unit!='mL':raise ValueError('actual volume must be recorded in mL')
        if self.dimension=='fraction' and Decimal(self.value)>1:raise ValueError('partial fraction exceeds one')
        return self

class CommonData(DomainModel):
    title: Text
    occurred: M10Time = Field(default_factory=M10Time)
    linked_sources: Annotated[tuple[EvidencePin,...],Field(max_length=64)] = ()
    narrative: Annotated[StrictStr,Field(max_length=16384)] | None = None
    record_status: Literal['recorded','withdrawn','invalid'] = 'recorded'

class DeliveryData(CommonData):
    product: Product
    delivery_id: Short
    grain: Literal['component_episode','reported_aggregate'] = 'component_episode'
    status: Literal['in_progress','completed','stopped','not_given','unknown']
    amounts: Annotated[tuple[Amount,...],Field(max_length=16)] = ()
    missing_amount_reason: Text | None = None
    started: M10Time = Field(default_factory=M10Time)
    ended: M10Time = Field(default_factory=M10Time)
    indication: Text
    route: Short = 'IV'
    reason: Text | None = None
    replacement_rationale: Text | None = None
    component_exposures: Annotated[int,Field(strict=True,ge=0,le=10000)] | None = None
    completed_as: EvidencePin | None = None
    retracted_medication: EvidencePin | None = None
    promote_to_medication: StrictBool = False
    @model_validator(mode='after')
    def delivered(self):
        if not self.amounts and not self.missing_amount_reason:raise ValueError('delivered quantities or missing reason required')
        if self.status=='not_given' and any(Decimal(a.value)>0 for a in self.amounts):raise ValueError('not given cannot carry a positive delivered quantity')
        if len({(a.dimension,a.unit,a.basis) for a in self.amounts})!=len(self.amounts):raise ValueError('duplicate quantity basis')
        if self.started.precision=='instant' and self.ended.precision=='instant' and TypeAdapter(AwareTimestamp).validate_python(self.started.value)>TypeAdapter(AwareTimestamp).validate_python(self.ended.value):raise ValueError('administration end before start')
        if self.product.family=='pcc' and any(a.dimension=='dose' and (a.unit!='IU' or not self.product.factor_basis) for a in self.amounts):raise ValueError('PCC dose requires IU and labelled factor basis')
        if self.product.family=='fibrinogen_concentrate' and any(a.dimension=='dose' and a.unit!='g' for a in self.amounts):raise ValueError('fibrinogen concentrate dose requires grams')
        if self.completed_as and self.retracted_medication:raise ValueError('completed and retracted canonical links are mutually exclusive')
        if self.completed_as and self.status!='completed':raise ValueError('completed medication link requires completed course')
        return self

class RequestData(CommonData):
    product: Product
    indication: Text
    quantities: Annotated[tuple[Amount,...],Field(max_length=16)] = ()
    priority: Literal['routine','urgent','emergency','unknown'] = 'unknown'
    requested_modifications: Annotated[tuple[ProductAttribute,...],Field(max_length=16)] = ()
    schedule: Text | None = None
    authorisation: Text | None = None

class DispositionData(CommonData):
    product: Product
    status: Literal['allocated','issued','returned','wasted','released','unknown']
    quantities: Annotated[tuple[Amount,...],Field(max_length=16)] = ()
    authorisation: Text | None = None

class CompatibilityData(CommonData):
    patient_group: Short | None = None
    donor_group: Short | None = None
    antibody_screen: Text | None = None
    antibodies: Text | None = None
    compatibility_result: Text | None = None
    specimen_id: Short | None = None
    specimen_valid_until: M10Time = Field(default_factory=M10Time)
    emergency_release: Literal['yes','no','unknown'] = 'unknown'
    blood_bank_authorisation: Text | None = None
    requirements: Annotated[tuple[ProductAttribute,...],Field(max_length=16)] = ()

class ReactionData(CommonData):
    implicated: Annotated[tuple[EvidencePin,...],Field(max_length=32)] = ()
    symptoms: Text
    classification: Text | None = None
    severity: Text | None = None
    actions: Text
    investigation: Text | None = None
    outcome: Text | None = None

class EpisodeData(CommonData):
    setting: Literal['trauma','cardiac_surgery','liver','obstetric','general_surgery','medical_icu','other','unknown'] = 'unknown'
    bleeding: Literal['yes','no','unknown'] = 'unknown'
    location: Text | None = None
    major_haemorrhage_protocol: Literal['activated','deactivated','not_activated','unknown'] = 'unknown'
    blood_loss_ml: DecimalText | None = None
    ended: M10Time = Field(default_factory=M10Time)

class AssessmentData(CommonData):
    findings: Text
    decision: Text
    rationale: Text
    plan: Text
    interpretation: dict | None = None
    reassesses: EvidencePin | None = None
    population: Literal['adult','child','neonate','obstetric','unknown'] = 'unknown'
    @field_validator('interpretation')
    @classmethod
    def bounded_interpretation(cls,v):
        import json
        if v is not None and len(json.dumps(v))>60000:raise ValueError('interpretation exceeds budget')
        return v

class CoverageData(CommonData):
    aggregate: EvidencePin
    constituents: Annotated[tuple[EvidencePin,...],Field(min_length=1,max_length=128)]
    relationship: Literal['included_in_aggregate','fully_explained_by_constituents','same_delivery','possible_overlap']
    complete: StrictBool = False
    basis: Short

class FluidLinkData(CommonData):
    administration: EvidencePin
    fluid: EvidencePin
    relationship: Literal['same_delivery','partial_overlap','possible_overlap']
    matched_volume_ml: DecimalText | None = None

class MedicationDetailData(CommonData):
    administration: EvidencePin
    product: Product
    amounts: Annotated[tuple[Amount,...],Field(max_length=16)] = ()
    replacement_rationale: Text | None = None

class VetObservation(DomainModel):
    id: Short
    assay: Short
    parameter: Short
    result_type: Literal['numeric','qualitative','narrative','unavailable'] = 'numeric'
    raw_value: Text | None = None
    value: Annotated[StrictStr,Field(max_length=128)] | None = None
    unit: Short | None = None
    state: Literal['final','preliminary','pending','not_measured','not_applicable','no_clot','aborted','invalid','unknown']
    comparator: Literal['eq','lt','le','gt','ge'] = 'eq'
    reference_low: Annotated[StrictStr,Field(max_length=128)] | None = None
    reference_high: Annotated[StrictStr,Field(max_length=128)] | None = None
    source_label: Text | None = None
    observed_at: M10Time = Field(default_factory=M10Time)
    available_at: M10Time = Field(default_factory=M10Time)
    elapsed_seconds: DecimalText | None = None
    timing_origin: Literal['run_start','clot_start','maximum_amplitude','source_defined','unknown'] = 'unknown'
    maturation: Literal['mature','pending','unknown'] = 'unknown'
    @model_validator(mode='after')
    def observed(self):
        import re
        if self.result_type in ('qualitative','narrative'):
            if not self.raw_value or self.value is not None:raise ValueError('qualitative/narrative VET requires raw text and no numeric value')
            return self
        if self.result_type=='unavailable' and self.state in ('final','preliminary'):raise ValueError('unavailable output cannot be a measured result')
        for value in (self.value,self.reference_low,self.reference_high):
            if value is not None and not re.fullmatch(r'[+-]?(?:[0-9]{1,12})(?:\.[0-9]{1,12})?',value):raise ValueError('exact bounded decimal VET value required')
        if self.state in ('final','preliminary') and (self.value is None or self.unit is None):raise ValueError('measured VET result requires original value and unit')
        if self.state not in ('final','preliminary') and self.value is not None:raise ValueError('unavailable VET result cannot contain a number')
        return self

class VetData(CommonData):
    device: Short
    profile_id: Short
    profile_version: Short
    cartridge: Short
    run_id: Short
    specimen_id: Short | None = None
    sampled: M10Time = Field(default_factory=M10Time)
    report_status: Literal['preliminary','final','corrected','withdrawn','invalid','aborted']
    update_mode: Literal['full','patch'] = 'full'
    base_digest: Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{64}$')] | None = None
    observations: Annotated[tuple[VetObservation,...],Field(max_length=256)] = ()
    original_report: Annotated[StrictStr,Field(max_length=65536)] | None = None
    attachment_digests: Annotated[tuple[Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{64}$')],...],Field(max_length=8)] = ()
    @model_validator(mode='after')
    def progression(self):
        if len({o.id for o in self.observations})!=len(self.observations):raise ValueError('duplicate VET observation identity')
        if (self.update_mode=='patch') != (self.base_digest is not None):raise ValueError('patch requires exact base digest; full report has none')
        return self

class M10Fact(RecordedFactV2):
    source_issuer: Short
    source_record: Short
    available: M10Time
    data: CommonData
    @property
    def semantic_time(self):return self.available.recorded()

class TransfusionAdministration(M10Fact):
    kind: Literal['transfusion_administration']='transfusion_administration'
    data: DeliveryData
    @model_validator(mode='after')
    def component(self):
        if self.data.product.family in ('pcc','fibrinogen_concentrate','factor_concentrate','antifibrinolytic','protamine','calcium'):raise ValueError('haemostatic medicine must use medication course owner')
        if self.data.completed_as:raise ValueError('blood components cannot become medication administrations')
        return self
class HaemostaticMedicationCourse(M10Fact):
    kind: Literal['haemostatic_medication_course']='haemostatic_medication_course'
    data: DeliveryData
    @model_validator(mode='after')
    def medicine(self):
        if self.data.product.family in ('prbc','plasma','platelets','cryoprecipitate','whole_blood','cell_salvage'):raise ValueError('blood component must use transfusion administration owner')
        return self
class TransfusionRequest(M10Fact):
    kind: Literal['transfusion_request']='transfusion_request'
    data: RequestData
class TransfusionPrescription(M10Fact):
    kind: Literal['transfusion_prescription']='transfusion_prescription'
    data: RequestData
class BloodProductDisposition(M10Fact):
    kind: Literal['blood_product_disposition']='blood_product_disposition'
    data: DispositionData
class TransfusionCompatibility(M10Fact):
    kind: Literal['transfusion_compatibility']='transfusion_compatibility'
    data: CompatibilityData
class TransfusionReaction(M10Fact):
    kind: Literal['transfusion_reaction']='transfusion_reaction'
    data: ReactionData
class HaemorrhageEpisode(M10Fact):
    kind: Literal['haemorrhage_episode']='haemorrhage_episode'
    data: EpisodeData
class M10Assessment(M10Fact):
    kind: Literal['m10_assessment']='m10_assessment'
    data: AssessmentData
class TransfusionCoverageLink(M10Fact):
    kind: Literal['transfusion_coverage_link']='transfusion_coverage_link'
    data: CoverageData
class FluidAdministrationLink(M10Fact):
    kind: Literal['fluid_administration_link']='fluid_administration_link'
    data: FluidLinkData
class M10MedicationDetail(M10Fact):
    kind: Literal['m10_medication_detail']='m10_medication_detail'
    data: MedicationDetailData
class ViscoelasticReport(M10Fact):
    kind: Literal['viscoelastic_report']='viscoelastic_report'
    data: VetData

M10_MODELS=(TransfusionAdministration,HaemostaticMedicationCourse,TransfusionRequest,TransfusionPrescription,BloodProductDisposition,TransfusionCompatibility,TransfusionReaction,HaemorrhageEpisode,M10Assessment,TransfusionCoverageLink,FluidAdministrationLink,M10MedicationDetail,ViscoelasticReport)
M10_FACTS={m.model_fields['kind'].default:m for m in M10_MODELS}
M10Record=Union[tuple(M10_MODELS)]
