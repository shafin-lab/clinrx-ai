"""Patient records and snapshots, independent of knowledge retrieval contracts."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import (
    Binding, ClinicalTime, ClinicalValue, ContextTarget, DomainModel, LineageGraph,
    LineageNode, Origin, Provenance, Quantity, Reference, Source, Text,
    ensure_consistent_revisions, require_kind, validate_origin,
)

FACT_KINDS = (
    'observation', 'condition', 'medication_order', 'medication_administration',
    'procedure', 'derived_value', 'inference',
)


class PatientContext(DomainModel):
    patient_id: Text
    source_identifiers: tuple[Source, ...]


class EncounterContext(DomainModel):
    encounter_id: Text
    patient_id: Text
    time: ClinicalTime
    source: Source


class PatientFact(DomainModel):
    """Base contract; construct a concrete fact category instead."""
    kind: Text
    id: Text
    revision: Text
    binding: Binding
    origin: Origin
    provenance: Provenance
    time: ClinicalTime
    verification: Literal['unverified', 'verified', 'clinician_confirmed'] = 'unverified'
    conflict: Literal['none_known', 'unresolved', 'resolved', 'unknown'] = 'unknown'
    temporal_status: Literal['current', 'historical', 'unknown']
    uncertainty: tuple[Text, ...] = ()
    supersedes: Reference | None = None
    correction_reason: Text | None = None

    @property
    def reference(self) -> Reference:
        return Reference(kind=self.kind, id=self.id, version=self.revision)

    @model_validator(mode='after')
    def revision_integrity(self):
        if type(self) is PatientFact:
            raise ValueError('construct a concrete patient fact category')
        validate_origin(self.origin, self.provenance, {})
        if self.reference in self.provenance.dependencies:
            raise ValueError('a fact cannot derive from itself')
        if (self.supersedes is None) != (self.correction_reason is None):
            raise ValueError('correction requires both previous revision and reason')
        if self.supersedes and (self.supersedes.kind != self.kind or
                                self.supersedes.id != self.id or self.supersedes == self.reference):
            raise ValueError('correction must identify a different revision of the same fact')
        return self


class ClinicalObservation(PatientFact):
    kind: Literal['observation'] = 'observation'
    origin: Literal['observed', 'reported']
    concept_id: Text
    value: ClinicalValue


class ClinicalCondition(PatientFact):
    kind: Literal['condition'] = 'condition'
    origin: Literal['observed', 'reported']
    concept_id: Text
    diagnostic_status: Literal['provisional', 'confirmed', 'refuted', 'unknown']
    # Machine-inferred diagnoses belong to ClinicalInference, not this assertion.


class MedicationIdentity(DomainModel):
    """Internal concept identities, with no implicit ingredient/product equivalence."""
    ingredient_ids: tuple[Text, ...] = ()
    product_id: Text | None = None
    formulation: Text | None = None  # Source description; no terminology mapping assumed.

    @model_validator(mode='after')
    def identifiable_medication(self):
        if not self.ingredient_ids and not self.product_id:
            raise ValueError('medication requires an ingredient or product identity')
        if len(set(self.ingredient_ids)) != len(self.ingredient_ids):
            raise ValueError('duplicate ingredient identities')
        return self


class Frequency(DomainModel):
    occurrences: Annotated[int, Field(strict=True, gt=0)]
    interval: Quantity

    @model_validator(mode='after')
    def positive_interval(self):
        if self.interval.value <= 0:
            raise ValueError('frequency interval must be positive')
        return self


class Dose(DomainModel):
    """Recorded dose semantics; no product compatibility or dimensional validation."""
    amount: Quantity
    basis: Literal[
        'per_dose', 'per_day', 'per_kg_per_dose', 'per_kg_per_day',
        'per_m2_per_dose', 'total_administered', 'unknown',
    ]
    basis_detail: Text | None = None
    concentration: Quantity | None = None
    volume: Quantity | None = None
    rate: Quantity | None = None
    duration: Quantity | None = None
    frequency: Frequency | None = None

    @model_validator(mode='after')
    def explicit_dose(self):
        if self.amount.value <= 0:
            raise ValueError('dose amount must be positive')
        if self.basis == 'unknown' and not self.basis_detail:
            raise ValueError('unknown dose basis requires a limitation')
        for quantity in (self.concentration, self.volume, self.rate, self.duration):
            if quantity is not None and quantity.value <= 0:
                raise ValueError('delivery quantities must be positive when supplied')
        return self


class MedicationOrder(PatientFact):
    kind: Literal['medication_order'] = 'medication_order'
    origin: Literal['observed', 'reported']
    medication: MedicationIdentity
    prescribed_dose: Dose
    route: Text  # Source wording; no normalized route or compatibility claim.
    schedule_text: Text | None = None
    order_status: Literal['draft', 'active', 'held', 'cancelled', 'completed']


class MedicationAdministration(PatientFact):
    kind: Literal['medication_administration'] = 'medication_administration'
    origin: Literal['observed', 'reported']
    medication: MedicationIdentity
    administered_dose: Dose
    route: Text
    administered_at: AwareDatetime
    order: Reference | None = None

    @model_validator(mode='after')
    def actual_delivery(self):
        if self.order:
            require_kind(self.order, 'medication_order')
        if self.administered_dose.basis != 'total_administered':
            raise ValueError('actual administration must record the delivered total')
        if self.time.event != self.administered_at:
            raise ValueError('administration event time must equal administered_at')
        # This slice records a completed delivery event, not a planned/in-progress infusion.
        if self.time.recorded and self.administered_at > self.time.recorded:
            raise ValueError('source administration record cannot precede delivery')
        if self.administered_at > self.provenance.recorded_at:
            raise ValueError('actual administration cannot be recorded before delivery')
        return self


class Procedure(PatientFact):
    kind: Literal['procedure'] = 'procedure'
    origin: Literal['observed', 'reported']
    concept_id: Text
    procedure_status: Literal['planned', 'in_progress', 'performed', 'cancelled', 'unknown']


class CalculationInput(DomainModel):
    parameter: Text
    fact: Reference
    source_value: Quantity | None = None
    evaluated_value: Quantity | None = None
    conversion: Reference | None = None

    @model_validator(mode='after')
    def input_semantics(self):
        require_kind(self.fact, *FACT_KINDS)
        if (self.source_value is None) != (self.evaluated_value is None):
            raise ValueError('retained source/evaluated quantities must be supplied together')
        if self.conversion:
            require_kind(self.conversion, 'unit_conversion')
            if self.source_value is None:
                raise ValueError('conversion requires retained source and evaluated quantities')
        if self.source_value != self.evaluated_value and not self.conversion:
            raise ValueError('changed input representation requires conversion provenance')
        return self


class CalculationExecution(DomainModel):
    reference: Reference
    definition: Reference
    implementation: Reference
    snapshot: Reference
    context: ContextTarget
    inputs: tuple[CalculationInput, ...] = ()
    missing_parameters: tuple[Text, ...] = ()
    configuration: Text
    environment: Text
    rounding_policy: Reference
    assumptions: tuple[Text, ...] = ()
    result: Quantity | None = None
    outcome: Literal['completed', 'missing_input', 'invalid_input', 'failed']
    reason: Text | None = None
    warnings: tuple[Text, ...] = ()
    executed_at: AwareDatetime

    @model_validator(mode='after')
    def valid_execution(self):
        expected = (
            (self.reference, 'calculation_execution'), (self.definition, 'calculation_definition'),
            (self.implementation, 'software'), (self.snapshot, 'snapshot'),
            (self.rounding_policy, 'rounding_policy'),
        )
        for reference, kind in expected:
            require_kind(reference, kind)
        if (self.outcome == 'completed') != (self.result is not None):
            raise ValueError('only completed execution can supply a final result')
        if self.outcome == 'completed':
            if not self.inputs:
                raise ValueError('completed patient calculation requires inputs')
            used_quantities = [self.result] + [item.evaluated_value for item in self.inputs]
            if any(q is not None and q.unit.status == 'unresolved' for q in used_quantities):
                raise ValueError('completed calculation cannot assert a result with unresolved evaluated units')
        if self.outcome != 'completed' and not self.reason:
            raise ValueError('unsuccessful calculation requires a reason')
        parameters = [item.parameter for item in self.inputs]
        if len(set(parameters)) != len(parameters):
            raise ValueError('duplicate calculation parameter')
        if len(set(self.missing_parameters)) != len(self.missing_parameters):
            raise ValueError('duplicate missing parameter')
        if set(parameters) & set(self.missing_parameters):
            raise ValueError('a parameter cannot be both available and missing')
        if self.outcome == 'missing_input' and not self.missing_parameters:
            raise ValueError('missing-input execution requires missing parameter names')
        if self.outcome != 'missing_input' and self.missing_parameters:
            raise ValueError('missing parameters require a missing-input outcome')
        return self


class DerivedValue(PatientFact):
    kind: Literal['derived_value'] = 'derived_value'
    origin: Literal['derived'] = 'derived'
    concept_id: Text
    execution: CalculationExecution

    @model_validator(mode='after')
    def retain_inputs(self):
        if self.execution.outcome != 'completed':
            raise ValueError('a failed execution is not a derived value')
        if self.execution.context != self.binding.target:
            raise ValueError('calculation context differs from derived-value binding')
        inputs = {item.fact for item in self.execution.inputs}
        calculation_parents = {edge.target for edge in self.provenance.upstream
                               if edge.relationship == 'calculated_from'}
        if not inputs.issubset(calculation_parents):
            raise ValueError('derived lineage must retain every input as calculated_from')
        if self.execution.executed_at > self.provenance.recorded_at:
            raise ValueError('derived value cannot be recorded before its execution')
        return self


class ClinicalInference(PatientFact):
    kind: Literal['inference'] = 'inference'
    origin: Literal['inferred'] = 'inferred'
    statement: Text
    inputs: Annotated[tuple[Reference, ...], Field(min_length=1)]
    method: Reference
    applicability: Text
    validation_references: tuple[Reference, ...] = ()
    validation_limitations: Text | None = None
    target: Text | None = None
    horizon: Text | None = None

    @model_validator(mode='after')
    def retain_uncertainty(self):
        if not self.uncertainty:
            raise ValueError('inference requires explicit uncertainty')
        if not set(self.inputs).issubset(self.provenance.dependencies):
            raise ValueError('inference lineage must retain every input revision')
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError('duplicate inference inputs')
        require_kind(self.method, 'model', 'inference_method')
        if not self.validation_references and not self.validation_limitations:
            raise ValueError('missing validation evidence must be disclosed')
        return self


Fact = Annotated[ClinicalObservation | ClinicalCondition | MedicationOrder |
                 MedicationAdministration | Procedure | DerivedValue | ClinicalInference,
                 Field(discriminator='kind')]


class ContextSnapshot(DomainModel):
    id: Text
    version: Text
    patient: PatientContext
    encounter: EncounterContext | None = None
    binding: Binding
    facts: tuple[Fact, ...] = ()
    # Optional local external/intermediate records for validating declared lineage.
    lineage_nodes: tuple[LineageNode, ...] = ()
    sources: tuple[Source, ...]
    created_at: AwareDatetime
    temporal_cutoff: AwareDatetime
    completeness: Literal['complete_for_scope', 'partial', 'unknown']
    completeness_scope: Text
    limitations: tuple[Text, ...] = ()

    @property
    def reference(self):
        return Reference(kind='snapshot', id=self.id, version=self.version)

    @model_validator(mode='after')
    def coherent_snapshot(self):
        target, verification = self.binding.target, self.binding.verification
        if verification.status != 'verified' or target.patient_id != self.patient.patient_id:
            raise ValueError('snapshot requires verified matching patient binding')
        if target.encounter_id is not None:
            if not self.encounter or (self.encounter.encounter_id, self.encounter.patient_id) != (
                    target.encounter_id, target.patient_id):
                raise ValueError('snapshot encounter does not match binding')
        elif self.encounter is not None:
            raise ValueError('longitudinal snapshot cannot carry an encounter')
        if verification.assessed_at > self.created_at:
            raise ValueError('snapshot cannot precede binding verification')
        if self.temporal_cutoff > self.created_at:
            raise ValueError('snapshot cutoff cannot follow creation')
        refs = {fact.reference: fact for fact in self.facts}
        if len(refs) != len(self.facts):
            raise ValueError('duplicate fact revision')
        executions = [fact.execution for fact in self.facts if isinstance(fact, DerivedValue)]
        ensure_consistent_revisions((execution.reference, execution) for execution in executions)
        for fact in self.facts:
            if fact.binding.target != target or fact.binding.verification.status != 'verified':
                raise ValueError('fact requires a verified matching context target')
            if fact.binding.verification.assessed_at > self.created_at:
                raise ValueError('fact binding was not verified at snapshot creation')
            available_times = (fact.provenance.recorded_at, fact.time.recorded,
                               fact.time.retrieved, fact.time.processed)
            if isinstance(fact, DerivedValue):
                available_times += (fact.execution.executed_at,)
            if isinstance(fact, MedicationAdministration):
                available_times += (fact.administered_at,)
            if any(t and t > self.temporal_cutoff for t in available_times):
                raise ValueError('fact was unavailable at snapshot cutoff')
            if isinstance(fact, MedicationAdministration) and fact.order in refs:
                order = refs[fact.order]
                prescribed, delivered = order.medication, fact.medication
                if ((prescribed.product_id and delivered.product_id and
                     prescribed.product_id != delivered.product_id) or
                    (prescribed.ingredient_ids and delivered.ingredient_ids and
                     set(prescribed.ingredient_ids) != set(delivered.ingredient_ids)) or
                    (prescribed.formulation and delivered.formulation and
                     prescribed.formulation != delivered.formulation)):
                    raise ValueError('administration medication differs from order')
            if isinstance(fact, DerivedValue):
                for item in fact.execution.inputs:
                    parent = refs.get(item.fact)
                    if parent and parent.provenance.recorded_at > fact.execution.executed_at:
                        raise ValueError('calculation input was unavailable at execution time')
        if any(node.provenance.recorded_at > self.temporal_cutoff for node in self.lineage_nodes):
            raise ValueError('lineage record was unavailable at snapshot cutoff')
        LineageGraph(nodes=tuple(LineageNode(reference=f.reference, origin=f.origin,
                                           provenance=f.provenance) for f in self.facts)
                     + self.lineage_nodes)
        return self
