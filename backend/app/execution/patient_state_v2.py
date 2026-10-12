"""M6.1 supplied v2 state only. No repository reads, assembly or inference."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, field_validator, model_validator
from app.models.clinical.common import ContextTarget, Reference, Text
from app.models.clinical.recorded_v2 import Contract, Digest, SourceCode, instant, ref_key
from app.models.clinical.microbiology import (Specimen, DirectExamination, CultureFinding,
    IsolateIdentification, SusceptibilityResult, ResistanceFinding, MolecularResult,
    BloodCultureSet, BloodCultureBottle)
from app.models.clinical.antimicrobials import (AntimicrobialOrder,
    CompletedAntimicrobialAdministration, AntimicrobialNonDelivery)
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff

RecordedFact = Annotated[Specimen | DirectExamination | CultureFinding | IsolateIdentification |
    SusceptibilityResult | ResistanceFinding | MolecularResult | BloodCultureSet |
    BloodCultureBottle | AntimicrobialOrder | CompletedAntimicrobialAdministration |
    AntimicrobialNonDelivery, Field(discriminator='kind')]


def metadata(value):
    if isinstance(value, (IngestionMetadata, RepositoryCutoff)):
        value = value.model_dump()
    if isinstance(value, dict) and 'payload_version' in value and type(value['payload_version']) is not int:
        raise ValueError('payload version must be an exact integer')
    return value


class PatientStateScopeV2(Contract):
    contract_version: Literal['2'] = '2'
    patient_id: Text
    encounter_id: Text
    review_start: AwareDatetime
    review_end: AwareDatetime
    repository_cutoff: RepositoryCutoff

    _metadata = field_validator('repository_cutoff', mode='before')(metadata)

    @property
    def target(self):
        return ContextTarget(patient_id=self.patient_id, encounter_id=self.encounter_id)

    @model_validator(mode='after')
    def ordered(self):
        if instant(self.review_start) > instant(self.review_end):
            raise ValueError('reversed review window')
        return self


class RetainedStateItemV2(Contract):
    fact: RecordedFact
    expected_digest: Digest
    ingestion: IngestionMetadata | None = None
    inclusion: Literal['in_window', 'contextual_parent', 'unplaced']
    contextual_for: Annotated[tuple[Reference, ...], Field(max_length=64)] = ()
    disclosures: Annotated[tuple[Text, ...], Field(max_length=32)] = ()

    _metadata = field_validator('ingestion', mode='before')(metadata)

    @field_validator('contextual_for')
    @classmethod
    def context_order(cls, refs):
        if len(set(refs)) != len(refs):
            raise ValueError('duplicate contextual child')
        return tuple(sorted(refs, key=ref_key))

    @model_validator(mode='after')
    def coherent(self):
        if self.expected_digest != self.fact.canonical_digest:
            raise ValueError('retained fact digest differs')
        if self.ingestion is None and not self.disclosures:
            raise ValueError('missing ingestion requires disclosure')
        if (self.inclusion == 'contextual_parent') != bool(self.contextual_for):
            raise ValueError('contextual inclusion requires exact children only')
        if self.inclusion == 'in_window' and self.fact.semantic_time.anchor is None:
            raise ValueError('unplaced evidence cannot assert window placement')
        if self.inclusion != 'in_window' and not self.disclosures:
            raise ValueError('non-window inclusion requires disclosure')
        return self

    @property
    def reference(self):
        return self.fact.reference

    @property
    def ordering_key(self):
        anchor = self.fact.semantic_time.anchor
        return (anchor is None, instant(anchor) if anchor is not None else 0, *ref_key(self.reference))


Refs = Annotated[tuple[Reference, ...], Field(max_length=512)]
ChildRefs = Annotated[tuple[Reference, ...], Field(max_length=64)]


def ordered_refs(refs):
    if len(set(refs)) != len(refs):
        raise ValueError('duplicate view reference')
    return tuple(sorted(refs, key=ref_key))


class SpecimenGroup(Contract):
    specimen: Reference
    examinations: ChildRefs = ()
    cultures: ChildRefs = ()
    isolates: ChildRefs = ()
    molecular_results: ChildRefs = ()

    _order = field_validator('examinations', 'cultures', 'isolates', 'molecular_results')(ordered_refs)


class IsolateGroup(Contract):
    isolate: Reference
    susceptibilities: ChildRefs = ()
    resistance_findings: ChildRefs = ()

    _order = field_validator('susceptibilities', 'resistance_findings')(ordered_refs)


class MolecularPanelGroup(Contract):
    """An explicit supplied grouping, never an independent durable fact."""
    panel: SourceCode
    targets: Annotated[tuple[Reference, ...], Field(min_length=1, max_length=64)]

    _order = field_validator('targets')(ordered_refs)


class MicrobiologyView(Contract):
    references: Refs = ()
    specimens: Annotated[tuple[SpecimenGroup, ...], Field(max_length=128)] = ()
    isolates: Annotated[tuple[IsolateGroup, ...], Field(max_length=256)] = ()
    panels: Annotated[tuple[MolecularPanelGroup, ...], Field(max_length=64)] = ()

    _order_refs = field_validator('references')(ordered_refs)

    @field_validator('specimens', 'isolates', 'panels')
    @classmethod
    def ordered_groups(cls, values):
        def key(value):
            if isinstance(value, SpecimenGroup):
                return ref_key(value.specimen)
            if isinstance(value, IsolateGroup):
                return ref_key(value.isolate)
            return value.panel.namespace, value.panel.code, value.panel.version or ''
        if len({key(v) for v in values}) != len(values):
            raise ValueError('duplicate view grouping identity')
        return tuple(sorted(values, key=key))


class AntimicrobialView(Contract):
    orders: Refs = ()
    administrations: Refs = ()
    non_delivery: Refs = ()

    _order = field_validator('orders', 'administrations', 'non_delivery')(ordered_refs)


class MappingIssueV2(Contract):
    reference: Reference
    reason: Literal['unsupported_source_structure', 'specimen_mapped_organism_unavailable',
        'susceptibility_incomplete', 'unknown_isolate_binding', 'ambiguous_isolate_binding',
        'missing_collection_time', 'missing_administration_time', 'unsupported_antimicrobial_identity',
        'unknown_mapping', 'binding_target_unavailable', 'bounded_result_limit_exceeded']


class CoverageV2(Contract):
    domain: Literal['microbiology', 'antimicrobial']
    mapping_support: Literal['supported', 'partial', 'unsupported']
    retrieval: Literal['completed', 'not_attempted', 'limit_exceeded']
    candidate_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    retained_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    source_completeness: Literal['unknown'] = 'unknown'
    limitations: Annotated[tuple[Text, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode='after')
    def coherent(self):
        if self.mapping_support == 'unsupported' and self.retrieval != 'not_attempted':
            raise ValueError('unsupported mapping cannot claim retrieval')
        if self.retrieval != 'completed' and (self.candidate_count is not None or self.retained_count is not None):
            raise ValueError('incomplete retrieval cannot claim complete counts')
        if self.retrieval == 'completed':
            if self.candidate_count is None or self.retained_count is None or self.retained_count > self.candidate_count:
                raise ValueError('completed retrieval requires consistent counts')
        return self


class PatientStateSnapshotV2(Contract):
    contract_version: Literal['2'] = '2'
    scope: PatientStateScopeV2
    items: Annotated[tuple[RetainedStateItemV2, ...], Field(max_length=512)] = ()
    microbiology: MicrobiologyView = Field(default_factory=MicrobiologyView)
    antimicrobial: AntimicrobialView = Field(default_factory=AntimicrobialView)
    # Same identities, not duplicate records. Admission of existing medication facts is M6.2+.
    medication_references: Refs = ()
    coverage: Annotated[tuple[CoverageV2, ...], Field(max_length=2)] = ()
    issues: Annotated[tuple[MappingIssueV2, ...], Field(max_length=512)] = ()
    disclosures: Annotated[tuple[Text, ...], Field(max_length=32)] = ()

    _order_medication = field_validator('medication_references')(ordered_refs)

    @field_validator('items')
    @classmethod
    def order_items(cls, items):
        return tuple(sorted(items, key=lambda i: i.ordering_key))

    @field_validator('coverage')
    @classmethod
    def order_coverage(cls, values):
        if len({c.domain for c in values}) != len(values):
            raise ValueError('duplicate coverage domain')
        return tuple(sorted(values, key=lambda c: c.domain))

    @field_validator('issues')
    @classmethod
    def order_issues(cls, values):
        if len(set(values)) != len(values):
            raise ValueError('duplicate mapping issue')
        return tuple(sorted(values, key=lambda i: (*ref_key(i.reference), i.reason)))

    @model_validator(mode='after')
    def consistent(self):
        items = {i.reference: i for i in self.items}
        if len(items) != len(self.items):
            raise ValueError('duplicate exact retained reference')
        if len({(r.kind, r.id) for r in items}) != len(items):
            raise ValueError('snapshot cannot assert multiple revisions of one stable fact')
        sequences = set()
        for item in self.items:
            if item.fact.binding.target != self.scope.target:
                raise ValueError('retained scope differs from snapshot')
            meta = item.ingestion
            if meta:
                if meta.repository_id != self.scope.repository_cutoff.repository_id or meta.ingestion_sequence > self.scope.repository_cutoff.fact_watermark:
                    raise ValueError('ingestion outside repository prefix')
                if meta.ingestion_sequence in sequences:
                    raise ValueError('duplicate ingestion identity')
                sequences.add(meta.ingestion_sequence)
            if item.inclusion == 'in_window':
                time = item.fact.semantic_time
                lo = time.lower if time.lower is not None else time.value
                hi = time.upper if time.upper is not None else time.value
                if instant(lo) > instant(self.scope.review_end) or instant(hi) < instant(self.scope.review_start):
                    raise ValueError('semantic time outside closed review window')
            for child in item.contextual_for:
                if child not in items or not any(b.exact == item.reference for b in items[child].fact.domain_bindings):
                    raise ValueError('contextual parent must be bound by supplied exact child')
            own_bindings = {b.role: b for b in item.fact.domain_bindings}
            bottle_binding = own_bindings.get('bottle')
            specimen_binding = own_bindings.get('specimen')
            if bottle_binding and specimen_binding and bottle_binding.exact in items:
                bottle_specimen = next((b for b in items[bottle_binding.exact].fact.domain_bindings if b.role == 'specimen'), None)
                if bottle_specimen and bottle_specimen.exact and specimen_binding.exact and bottle_specimen.exact != specimen_binding.exact:
                    raise ValueError('bottle and specimen bindings contradict')
            for binding in item.fact.domain_bindings:
                if binding.exact and binding.exact not in items and not any(i.reference == item.reference and i.reason == 'binding_target_unavailable' for i in self.issues):
                    raise ValueError('absent exact binding target requires explicit outcome')

        def check(refs, kinds):
            if len(set(refs)) != len(refs):
                raise ValueError('duplicate view reference')
            for ref in refs:
                if ref not in items or ref.kind not in kinds:
                    raise ValueError('view reference missing or wrong subtype')

        micro_kinds = ('microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture',
            'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance',
            'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle')
        check(self.microbiology.references, micro_kinds)
        check(self.antimicrobial.orders, ('antimicrobial_order',))
        check(self.antimicrobial.administrations, ('antimicrobial_administration',))
        check(self.antimicrobial.non_delivery, ('antimicrobial_non_delivery',))
        check(self.medication_references, ('antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery'))
        declared = set(self.microbiology.references + self.antimicrobial.orders + self.antimicrobial.administrations + self.antimicrobial.non_delivery)
        if declared != set(items):
            raise ValueError('domain views must reference each canonical item')
        def bound(parent, children, kinds, role):
            check(children, kinds)
            for child in children:
                if not any(b.role == role and b.status == 'resolved' and b.exact == parent for b in items[child].fact.domain_bindings):
                    raise ValueError('view grouping contradicts exact domain binding')
        if len({g.specimen for g in self.microbiology.specimens}) != len(self.microbiology.specimens) or len({g.isolate for g in self.microbiology.isolates}) != len(self.microbiology.isolates):
            raise ValueError('duplicate grouping parent')
        for group in self.microbiology.specimens:
            check((group.specimen,), ('microbiology_specimen',))
            for children, kind in ((group.examinations,'microbiology_direct_examination'), (group.cultures,'microbiology_culture'), (group.isolates,'microbiology_isolate'), (group.molecular_results,'microbiology_molecular')):
                bound(group.specimen, children, (kind,), 'specimen')
        for group in self.microbiology.isolates:
            check((group.isolate,), ('microbiology_isolate',))
            bound(group.isolate, group.susceptibilities, ('microbiology_susceptibility',), 'isolate')
            bound(group.isolate, group.resistance_findings, ('microbiology_resistance',), 'isolate')
        if len({p.panel for p in self.microbiology.panels}) != len(self.microbiology.panels):
            raise ValueError('duplicate molecular panel group')
        for panel in self.microbiology.panels:
            check(panel.targets, ('microbiology_molecular',))
            # Panel grouping uses an explicit namespaced identity, not target ordering.
            for ref in panel.targets:
                source = items[ref].fact.panel_identifier
                if source is None or panel.panel != source:
                    raise ValueError('panel grouping differs from source identity')
        for coverage in self.coverage:
            count = len(self.microbiology.references) if coverage.domain == 'microbiology' else len(self.antimicrobial.orders + self.antimicrobial.administrations + self.antimicrobial.non_delivery)
            if coverage.retrieval != 'completed' and count:
                raise ValueError('uncompleted retrieval cannot supply a completed domain view')
            if coverage.retrieval == 'completed':
                if count != coverage.retained_count:
                    raise ValueError('coverage retained count differs from view')
        return self
