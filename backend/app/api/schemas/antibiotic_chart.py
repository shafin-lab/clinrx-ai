"""Manual antibiotic charting in the opt-in synthetic workspace, not prescribing."""
from typing import Annotated, Literal
from uuid import UUID
from decimal import Decimal
from pydantic import Field, StrictStr, TypeAdapter, model_validator, model_serializer, StrictBool
from app.api.schemas.common import DTO, DecimalString, Digest, AwareTimestamp, ExactReference

Short=Annotated[StrictStr,Field(min_length=1,max_length=256)]
Note=Annotated[StrictStr,Field(min_length=1,max_length=1000)]
Stamp=Annotated[StrictStr,Field(min_length=20,max_length=64)]


Small=Annotated[StrictStr,Field(max_length=64)]
class DoseReviewInputs(DTO):
    age: Small
    weight: Small
    creatinine: Small
    factor: Small
class DoseReviewSuggestion(DTO):
    medicine: Short
    amount: Small
    unit: Literal['g','mg']
    route: Literal['IV','PO']
    schedule: Short
    initial: Short | None
    band: Short
class DoseReviewContext(DTO):
    indication: Small
    infusion: Small
    phase: Small
    bodySize: Small
    hepatic: Small
    special: Small
    safetyReviewed: StrictBool
    renalFunction: Small
    support: Small
    cvvhMode: Small
    flow: Small
    flowDefinitionReviewed: StrictBool
    residual: Small
    downtime: Small
    hdFlux: Small
    hdStable: Small
    hdInterval: Small
    hdTimingReviewed: StrictBool
class DoseReviewScope(DTO):
    repository: UUID
    patient: Short
    encounter: Short
    cutoff: Annotated[int,Field(strict=True,ge=0)]
    start: Stamp
    end: Stamp
    @model_validator(mode='after')
    def interval(self):
        if TypeAdapter(AwareTimestamp).validate_python(self.start)>TypeAdapter(AwareTimestamp).validate_python(self.end):raise ValueError('ordered review interval required')
        return self
class DoseReviewSource(DTO):
    role: Literal['weight','creatinine','patient_context','ast','isolate','specimen']
    reference: ExactReference
    digest: Digest
    ingestion: Annotated[int,Field(strict=True,ge=1)]
    component: Short | None = Field(default=None,exclude_if=lambda value:value is None)
class DoseReview(DTO):
    version: Literal['CandidateDoseReview/v1']
    profile_version: Short
    source: Short
    suggestion: DoseReviewSuggestion
    inputs: DoseReviewInputs
    crcl: Annotated[float,Field(strict=True,gt=0,allow_inf_nan=False)] | None
    context: DoseReviewContext
    basis: Literal['empiric','ast']
    scope: DoseReviewScope
    sources: Annotated[list[DoseReviewSource],Field(max_length=6)]
    @model_validator(mode='after')
    def exact_roles(self):
        roles=[s.role for s in self.sources]
        kinds={'weight':{'circulatory_event','observation'},'creatinine':{'observation','laboratory_report'},'patient_context':{'circulatory_event'},'ast':{'microbiology_susceptibility'},'isolate':{'microbiology_isolate'},'specimen':{'microbiology_specimen'}}
        if any(s.reference.kind not in kinds[s.role] for s in self.sources):raise ValueError('source kind does not match its role')
        if any((s.component is not None)!=(s.role=='creatinine' and s.reference.kind=='laboratory_report') for s in self.sources):raise ValueError('laboratory creatinine requires one exact component')
        if len(set(roles))!=len(roles) or any(s.ingestion>self.scope.cutoff for s in self.sources):raise ValueError('unique in-cutoff source roles required')
        if (self.basis=='ast')!=all(role in roles for role in ('ast','isolate','specimen')) or self.basis=='empiric' and any(r in roles for r in ('ast','isolate','specimen')):raise ValueError('exact AST chain or explicit empiric basis required')
        return self

class AntibioticDraft(DTO):
    dose_review: DoseReview | None = None
    dose_review_amendment: Literal[True] | None = None
    repository: UUID
    id: UUID
    revision: UUID
    mode: Literal['prescription','given','held','missed','refused','not_given']
    medicine: Short
    product: Short
    amount: DecimalString | None = None
    unit: Literal['mg','g','IU'] | None = None
    dose_detail: Short | None = None
    route: Short
    schedule: Short | None = None
    indication: Note
    point: Stamp
    actor: Short
    source_record: Short
    recorded_at: Stamp
    order: ExactReference | None = None
    culture_ref: ExactReference | None = None
    predecessor: ExactReference | None = None
    predecessor_digest: Digest | None = None
    correction_reason: Note | None = None

    @model_serializer(mode='wrap')
    def preserve_legacy_serialization(self, handler):
        data=handler(self)
        if 'dose_review' not in self.model_fields_set:data.pop('dose_review',None)
        if 'dose_review_amendment' not in self.model_fields_set:data.pop('dose_review_amendment',None)
        return data

    @model_validator(mode='after')
    def coherent(self):
        point=TypeAdapter(AwareTimestamp).validate_python(self.point)
        recorded=TypeAdapter(AwareTimestamp).validate_python(self.recorded_at)
        if self.mode!='prescription' and point>recorded:raise ValueError('completed/non-delivery record cannot precede the event')
        if self.mode in ('prescription','given'):
            if self.amount is None or not Decimal(self.amount).is_finite() or Decimal(self.amount)<=0 or not self.unit or not self.dose_detail:raise ValueError('explicit positive dose, unit and product/component basis required')
        elif any(x is not None for x in (self.amount,self.unit,self.dose_detail)):
            raise ValueError('non-delivery cannot assert an administered amount')
        if (self.mode=='prescription')!=(self.schedule is not None):raise ValueError('schedule belongs only to a prescription record')
        if self.mode=='prescription' and self.order is not None:raise ValueError('prescription cannot link another prescription as its parent')
        if self.order and self.order.kind!='antimicrobial_order':raise ValueError('exact antimicrobial order required')
        if self.culture_ref and self.culture_ref.kind!='microbiology_susceptibility':raise ValueError('exact susceptibility result required')
        if any(not getattr(self,k).strip() for k in ('medicine','product','route','indication','actor','source_record')):raise ValueError('nonblank source fields required')
        if (self.predecessor is None)!=(self.predecessor_digest is None) or (self.predecessor is None)!=(self.correction_reason is None):raise ValueError('correction requires exact predecessor, digest and reason')
        if self.predecessor and (self.predecessor.id!=str(self.id) or self.predecessor.version==str(self.revision)):raise ValueError('correction must retain stable identity and append a new revision')
        if self.dose_review:
            r=self.dose_review
            if self.mode!='prescription' or r.scope.repository!=self.repository:raise ValueError('candidate context belongs to its prescription repository')
            ast=next((s.reference for s in r.sources if s.role=='ast'),None)
            if ast!=self.culture_ref:raise ValueError('candidate AST and retained culture citation differ')
        if self.dose_review_amendment and (not self.dose_review or not self.predecessor or self.mode!='prescription'):raise ValueError('explicit dose review amendment requires a prescription predecessor and new review')
        from app.persistence.canonical import canonical_payload
        if len(canonical_payload(self).encode('utf-8'))>4096:raise ValueError('source metadata exceeds bound')
        return self

class AntibioticHistoryRequest(DTO):
    state_context: str=Field(min_length=1,max_length=65536)
    reference: ExactReference
