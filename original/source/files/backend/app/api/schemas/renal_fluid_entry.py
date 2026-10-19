"""Local RF2 product contracts. Existing clinical models/storage are unchanged."""
from decimal import Decimal
import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator, field_validator, TypeAdapter
from app.api.schemas.common import DTO, Identifier, Digest, DecimalString, AwareTimestamp
from app.models.clinical.common import Reference

Short = Annotated[str, Field(strict=True, min_length=1, max_length=128)]
NoteText = Annotated[str, Field(strict=True, min_length=1, max_length=512)]
Category = Literal['output_urine','input_oral','input_enteral','input_iv','input_blood','output_drain','output_other','output_crrt','weight','net_balance_reported','urine_total_reported','balance_total_reported']

class SourceRecord(DTO):
    issuer_namespace: Short
    issuer: Short
    record_namespace: Short
    record_id: Short
    component: Short
    @model_validator(mode='after')
    def unique_record(self):
        if self.component.lower().replace('-','').replace('_','').replace(' ','') in ('wholerecord','collection','series','context'):raise ValueError('no whole-record issuer profile is configured; provide a concrete component')
        if any(s in self.record_namespace.lower() for s in ('series','context','channel','device')):
            raise ValueError('record namespace must identify records, never context/series')
        return self

class Pin(DTO):
    repository: UUID
    reference: Reference
    digest: Digest
    ingestion: Annotated[int, Field(strict=True, ge=1)]
    cutoff: Annotated[int, Field(strict=True, ge=1)]
    @model_validator(mode='after')
    def bounded(self):
        if max(len(self.reference.kind),len(self.reference.id),len(self.reference.version))>256 or self.ingestion>self.cutoff:
            raise ValueError('invalid exact pin')
        return self

class Chart(DTO):
    category: Category
    amount: DecimalString | None = None
    unit: Literal['mL','L','kg','g'] | None = None
    missing_reason: NoteText | None = None
    point: Short | None = None
    start: Short | None = None
    end: Short | None = None
    acquisition: Literal['measured','reported','unknown'] = 'unknown'
    method: Short | None = None
    purpose: Short | None = None
    source_context: NoteText
    uncertainty: NoteText
    source_record: SourceRecord | None = None
    source_version: Short | None = None
    new_collection_reason: NoteText | None = None
    @field_validator('point','start','end')
    @classmethod
    def exact_time(cls,v):
        if v is not None:TypeAdapter(AwareTimestamp).validate_python(v)
        return v
    @model_validator(mode='after')
    def coherent(self):
        if (self.amount is None)!=(self.unit is None) or (self.amount is None)!=(self.missing_reason is not None):
            raise ValueError('record quantity or explicit missing reason')
        if self.amount is not None:
            value=Decimal(self.amount)
            if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?',self.amount):raise ValueError('use an exact decimal such as 0.50 or 35.0000')
            if not value.is_finite() or (value<0 and self.category not in ('net_balance_reported','balance_total_reported')):
                raise ValueError('invalid magnitude')
        if self.unit is not None and self.unit not in (('kg','g') if self.category=='weight' else ('mL','L')):
            raise ValueError('unit category mismatch')
        if self.category=='weight' and (self.start is not None or self.end is not None):raise ValueError('weight is a point assertion')
        if self.category!='weight' and (self.acquisition!='unknown' or self.purpose is not None):raise ValueError('weight-only acquisition/purpose')
        if self.start is not None and self.end is not None and TypeAdapter(AwareTimestamp).validate_python(self.start)>TypeAdapter(AwareTimestamp).validate_python(self.end):raise ValueError('reversed interval')
        if self.source_record is None and not self.new_collection_reason:raise ValueError('explicit new collection reason required')
        return self

class RenalNote(DTO):
    question: NoteText
    findings: NoteText
    possibilities: NoteText
    gaps: NoteText
    plan: NoteText
    pins: Annotated[tuple[Pin,...],Field(min_length=1,max_length=12)]
    @model_validator(mode='after')
    def unique(self):
        keys=[(p.reference.kind,p.reference.id,p.reference.version) for p in self.pins]
        if len(keys)!=len(set(keys)):raise ValueError('duplicate evidence pin')
        return self

class RF2Draft(DTO):
    repository: UUID
    id: UUID
    revision: UUID
    actor: Short
    recorded_at: Short
    chart: Chart | None = None
    note: RenalNote | None = None
    predecessor: Pin | None = None
    reason: NoteText | None = None
    @field_validator('recorded_at')
    @classmethod
    def exact_recorded(cls,v):
        TypeAdapter(AwareTimestamp).validate_python(v)
        return v
    @model_validator(mode='after')
    def shape(self):
        if (self.chart is None)==(self.note is None):raise ValueError('one chart or note required')
        if self.note and any(p.repository!=self.repository for p in self.note.pins):raise ValueError('note pins belong to the original repository')
        if (self.predecessor is None)!=(self.reason is None):raise ValueError('correction needs predecessor and reason')
        if self.predecessor and (self.predecessor.repository!=self.repository or self.predecessor.reference.kind!='circulatory_event' or self.predecessor.reference.id!=str(self.id)):
            raise ValueError('correction must retain original owner')
        if len(self.model_dump_json().encode())>65536:raise ValueError('RF2 request budget exceeded')
        return self

class ResolveRequest(DTO):
    repository: UUID
    pins: Annotated[tuple[Pin,...],Field(max_length=32)]
