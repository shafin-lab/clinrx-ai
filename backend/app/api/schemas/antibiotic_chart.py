"""Manual antibiotic charting in the opt-in synthetic workspace, not prescribing."""
from typing import Annotated, Literal
from uuid import UUID
from decimal import Decimal
from pydantic import Field, StrictStr, TypeAdapter, model_validator
from app.api.schemas.common import DTO, DecimalString, Digest, AwareTimestamp, ExactReference

Short=Annotated[StrictStr,Field(min_length=1,max_length=256)]
Note=Annotated[StrictStr,Field(min_length=1,max_length=1000)]
Stamp=Annotated[StrictStr,Field(min_length=20,max_length=64)]

class AntibioticDraft(DTO):
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
        return self

class AntibioticHistoryRequest(DTO):
    state_context: str=Field(min_length=1,max_length=65536)
    reference: ExactReference
