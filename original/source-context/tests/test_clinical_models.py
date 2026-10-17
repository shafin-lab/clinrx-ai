"""Synthetic records only; these tests verify contracts, not clinical correctness."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.clinical.common import (
    Binding, ClinicalTime, ClinicalValue, LineageGraph, LineageNode, Provenance,
    Quantity, Reference, Source, ContextTarget, IdentityVerification, LineageEdge, Unit,
)
from app.models.clinical.facts import (
    CalculationExecution, ClinicalCondition, ClinicalInference, ClinicalObservation,
    ContextSnapshot, DerivedValue, EncounterContext, Fact, MedicationAdministration,
    MedicationOrder, PatientContext, Procedure, PatientFact, CalculationInput,
    MedicationIdentity, Dose, Frequency,
)
from app.models.clinical.decisions import (
    ClinicalClaim, ClinicalRecommendation, EvidenceReference, HumanDecision,
    KnowledgeReference, RecommendationReview, RecommendationState,
    RenderedRecommendation, SafetyCheck, SafetyEvaluation,
)

NOW = datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
SOURCE = Source(namespace='synthetic', identifier='source-1', channel='measurement')
BINDING = Binding(
    target=ContextTarget(patient_id='p1', encounter_id='e1'),
    verification=IdentityVerification(status='verified', method='test-fixture',
        verifier='test-system', assessed_at=NOW, source=SOURCE),
)
TIME = ClinicalTime(event=NOW, recorded=NOW, precision='instant')


def ref(kind, id='r1', version='1'):
    return Reference(kind=kind, id=id, version=version)


def quantity(value, unit):
    return Quantity(value=value, unit=Unit(raw=unit, status='assessed', system='UCUM', code=unit))


def provenance(upstream=(), **changes):
    edges = tuple(item if isinstance(item, LineageEdge) else
                  LineageEdge(target=item.fact if isinstance(item, CalculationInput) else item,
                              relationship='calculated_from' if isinstance(item, CalculationInput) else 'derived_from')
                  for item in upstream)
    data = dict(source=SOURCE, actor='test-system', recorded_at=NOW,
                upstream=edges, lineage='complete')
    data.update(changes)
    return Provenance(**data)


def binding(**changes):
    target = BINDING.target.model_dump()
    verification = BINDING.verification.model_dump()
    for key, value in changes.items():
        (target if key in target else verification)[key] = value
    return Binding(target=ContextTarget(**target), verification=IdentityVerification(**verification))


def fact_fields(**changes):
    data = dict(id='f1', revision='1', binding=BINDING, origin='observed',
                provenance=provenance(), time=TIME, temporal_status='current')
    data.update(changes)
    return data


def observation(**changes):
    data = dict(concept_id='test-measurement', value=ClinicalValue(status='known', value=quantity(value='2.5', unit='mg/L')))
    data.update(changes)
    return ClinicalObservation(**fact_fields(**data))


def snapshot(facts=(), **changes):
    data = dict(id='s1', version='1', patient=PatientContext(patient_id='p1', source_identifiers=(SOURCE,)),
                encounter=EncounterContext(encounter_id='e1', patient_id='p1', time=TIME, source=SOURCE),
                binding=BINDING, facts=facts, sources=(SOURCE,), created_at=NOW, temporal_cutoff=NOW,
                completeness='unknown', completeness_scope='synthetic test only', limitations=('not a clinical feed',))
    data.update(changes)
    return ContextSnapshot(**data)


def inference(**changes):
    inputs = (observation().reference,)
    data = dict(id='i1', origin='inferred', statement='Synthetic hypothesis', inputs=inputs,
                provenance=provenance(inputs), method=ref('model'), applicability='synthetic only',
                uncertainty=('unvalidated hypothesis',), validation_limitations='no clinical validation')
    data.update(changes)
    return ClinicalInference(**fact_fields(**data))


def execution(**changes):
    data = dict(reference=ref('calculation_execution'), definition=ref('calculation_definition'),
                implementation=ref('software'), snapshot=ref('snapshot', 's0'),
                context=BINDING.target,
                inputs=(CalculationInput(parameter='measurement', fact=observation().reference),), configuration='fixture-config-1', environment='fixture-env-1',
                rounding_policy=ref('rounding_policy', 'no-rounding'), result=quantity(value='5', unit='mg/L'),
                outcome='completed', executed_at=NOW)
    if changes.get('outcome') == 'missing_input':
        data['missing_parameters'] = ('other_required_parameter',)
    data.update(changes)
    return CalculationExecution(**data)


def candidate(**changes):
    data = dict(id='rec1', revision='1', snapshot=snapshot((observation(),)), intended_use=ref('intended_use'),
                claims=(ClinicalClaim(id='claim1', action='Synthetic review proposal', rationale='test',
                                      classifications=('evidence_derived',), basis=(ref('evidence'),)),),
                provenance=provenance(), created_at=NOW)
    data.update(changes)
    return ClinicalRecommendation(**data)


def rendering(c=None, **changes):
    c = c or candidate()
    data = dict(id='render1', revision='1', candidate=c.reference, snapshot=c.snapshot.reference,
                content='Synthetic test content', destination='test-only', rendered_at=NOW)
    data.update(changes)
    return RenderedRecommendation(**data)


def evaluation(**changes):
    c = candidate()
    data = dict(id='eval1', revision='1', candidate=c.reference, rendering=rendering(c).reference,
                snapshot=c.snapshot.reference, policy=ref('safety_policy'),
                checks=(SafetyCheck(id='check1', rule=ref('safety_rule'), required=True,
                                    outcome='no_detected_violation', reason='test', coverage='schema only'),),
                exact_meaning='matched', coverage='synthetic fixture', limitations=('not clinical validation',),
                evaluated_at=NOW)
    data.update(changes)
    return SafetyEvaluation(**data)


@pytest.mark.parametrize('origin', ['derived', 'inferred'])
def test_inference_cannot_be_observation(origin):
    with pytest.raises(ValidationError):
        observation(origin=origin)


def test_fact_union_preserves_type_and_origin_after_json_roundtrip():
    f = inference()
    restored = TypeAdapter(Fact).validate_json(f.model_dump_json())
    assert isinstance(restored, ClinicalInference)
    assert restored.origin == 'inferred'
    with pytest.raises(ValidationError):
        ClinicalObservation.model_validate(f.model_dump())


def test_reported_verification_and_conflict_are_independent():
    f = observation(origin='reported', verification='clinician_confirmed', conflict='unresolved')
    assert (f.origin, f.verification, f.conflict) == ('reported', 'clinician_confirmed', 'unresolved')


@pytest.mark.parametrize('status', ['unknown', 'missing', 'not_measured', 'not_applicable'])
def test_missingness_is_not_zero_or_negative(status):
    assert ClinicalValue(status=status, reason='unavailable').value is None
    with pytest.raises(ValidationError):
        ClinicalValue(status=status, value=False, reason='unavailable')
    assert ClinicalValue(status='known', value=False).value is False


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_quantities_rejected(value):
    with pytest.raises(ValidationError):
        quantity(value=value, unit='mg')


def test_units_and_timezone_are_required():
    with pytest.raises(ValidationError):
        quantity(value='2', unit=' ')
    with pytest.raises(ValidationError):
        ClinicalTime(event=datetime(2026, 9, 25), precision='instant')
    assert ClinicalTime(precision='unknown').event is None
    with pytest.raises(ValidationError):
        ClinicalTime(effective_start=NOW, effective_end=NOW-timedelta(hours=1), precision='instant')


def test_order_does_not_establish_administration():
    order = MedicationOrder(**fact_fields(medication=MedicationIdentity(product_id='drug1'),
                                          prescribed_dose=Dose(amount=quantity(value='1', unit='mg'), basis='per_dose'),
                                          route='oral', schedule_text='test schedule', order_status='active'))
    with pytest.raises(ValidationError):
        MedicationAdministration.model_validate(order.model_dump())
    admin = MedicationAdministration(**fact_fields(id='a1', medication=MedicationIdentity(product_id='drug1'),
                administered_dose=Dose(amount=quantity(value='1', unit='mg'), basis='total_administered'), route='oral', administered_at=NOW, order=order.reference))
    assert len(snapshot((order, admin)).facts) == 2
    with pytest.raises(ValidationError):
        snapshot((order, admin.model_copy(update={'medication': MedicationIdentity(product_id='drug2')})))


def test_condition_and_procedure_have_separate_status():
    c = ClinicalCondition(**fact_fields(concept_id='condition1', diagnostic_status='provisional'))
    p = Procedure(**fact_fields(id='proc1', concept_id='procedure1', procedure_status='planned'))
    assert snapshot((c, p)).facts[1].procedure_status == 'planned'


def test_derived_result_retains_execution_and_input_versions():
    e = execution()
    d = DerivedValue(**fact_fields(id='d1', origin='derived', concept_id='calculated1',
                                   execution=e, provenance=provenance(e.inputs)))
    assert d.execution.result.value == 5
    assert d.execution.inputs[0].fact.version == '1'
    with pytest.raises(ValidationError):
        DerivedValue.model_validate({**d.model_dump(), 'provenance': provenance().model_dump()})
    with pytest.raises(ValidationError):
        CalculationExecution.model_validate({**e.model_dump(), 'implementation': None})


@pytest.mark.parametrize('outcome', ['missing_input', 'invalid_input', 'failed'])
def test_failed_calculation_never_becomes_normal_value(outcome):
    with pytest.raises(ValidationError):
        execution(outcome=outcome, reason='failed')
    failed = execution(outcome=outcome, result=None, reason='failed')
    with pytest.raises(ValidationError):
        DerivedValue(**fact_fields(origin='derived', concept_id='derived', execution=failed,
                                   provenance=provenance(failed.inputs)))


def test_inference_requires_inputs_method_and_uncertainty():
    for changes in ({'inputs': ()}, {'method': None}, {'uncertainty': ()}, {'provenance': provenance()}):
        with pytest.raises(ValidationError):
            inference(**changes)


def test_snapshot_rejects_wrong_patient_encounter_and_unresolved_identity():
    for changes in ({'patient_id': 'p2'}, {'encounter_id': 'e2'},
                    {'status': 'unresolved', 'ambiguity': 'two candidate patients'}):
        changed_binding = binding(**changes)
        with pytest.raises(ValidationError):
            snapshot(binding=changed_binding)
    with pytest.raises(ValidationError):
        snapshot((observation(binding=binding(patient_id='p2')),))


def test_longitudinal_context_is_explicit():
    longitudinal = binding(encounter_id=None, longitudinal_context_id='long1')
    assert snapshot(binding=longitudinal, encounter=None).binding.target.longitudinal_context_id == 'long1'
    with pytest.raises(ValidationError):
        binding(encounter_id=None)


def test_snapshot_does_not_rewrite_past_available_information():
    with pytest.raises(ValidationError):
        snapshot((observation(),), temporal_cutoff=NOW-timedelta(seconds=1))
    old = observation()
    corrected = observation(revision='2', supersedes=old.reference, correction_reason='source correction')
    assert len(snapshot((old, corrected)).facts) == 2
    with pytest.raises(ValidationError):
        observation(supersedes=old.reference)


def test_inference_reimport_cannot_become_reported_observation():
    i = inference()
    with pytest.raises(ValidationError):
        observation(id='copy', origin='reported', provenance=provenance((i.reference,)))
    # Reject even if the referenced inference is absent from the local snapshot.
    with pytest.raises(ValidationError):
        observation(provenance=provenance((ref('derived_value', 'external'),)))


def test_lineage_cycles_shared_ancestry_and_unknown_independence():
    a, b, root = ref('inference', 'a'), ref('inference', 'b'), ref('observation', 'root')
    def node(r, parents):
        return LineageNode(reference=r, origin='inferred', provenance=provenance(parents))
    with pytest.raises(ValidationError):
        LineageGraph(nodes=(node(a, (b,)), node(b, (a,))))
    graph = LineageGraph(nodes=(node(a, (root,)), node(b, (root,))))
    assert graph.support_relationship(a, b) == 'dependent'
    assert graph.support_relationship(a, ref('inference', 'unknown')) == 'unknown'
    with pytest.raises(ValidationError):
        Provenance(source=SOURCE, actor='system', recorded_at=NOW, lineage='unknown')


def test_snapshot_roundtrip_is_immutable_and_revalidates_copies():
    s = snapshot((observation(), inference()))
    assert ContextSnapshot.model_validate_json(s.model_dump_json()) == s
    with pytest.raises(ValidationError):
        s.facts[0].origin = 'inferred'
    with pytest.raises(ValidationError):
        snapshot((observation().model_copy(update={'origin': 'inferred'}),))


def test_evidence_and_knowledge_are_distinct_and_recovery_is_explicit():
    k = KnowledgeReference(id='k', version='1', applicability='synthetic')
    with pytest.raises(ValidationError):
        EvidenceReference.model_validate(k.model_dump())
    data = dict(id='e', version='1', citation='Synthetic', locator='test:1', retrieved_at=NOW)
    with pytest.raises(ValidationError):
        EvidenceReference(**data)
    assert EvidenceReference(**data, recovery_limitation='not retained').source_version is None


def test_review_lifecycle_does_not_release_or_present():
    c = candidate()
    assert RecommendationReview(candidate=c).state == RecommendationState.CANDIDATE
    assert RecommendationReview(candidate=c, rendering=rendering()).state == RecommendationState.RENDERED
    reviewed = RecommendationReview(candidate=c, rendering=rendering(), evaluations=(evaluation(),))
    assert reviewed.state == RecommendationState.EVALUATED
    assert reviewed.evaluations[0].outcome == 'no_detected_violation'
    for state in ('released', 'presented', 'evaluated'):
        with pytest.raises(ValidationError):
            candidate(state=state)
    with pytest.raises(ValidationError):
        RecommendationReview(candidate=c, state='released')


@pytest.mark.parametrize('field,wrong', [('candidate', ref('recommendation', 'rec1', '2')),
                                       ('rendering', ref('rendering', 'render1', '2')),
                                       ('snapshot', ref('snapshot', 'other'))])
def test_evaluation_cannot_be_reused_after_content_or_context_change(field, wrong):
    with pytest.raises(ValidationError):
        RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(evaluation(**{field: wrong}),))


def test_missing_and_empty_checks_are_not_passes():
    with pytest.raises(ValidationError):
        evaluation(checks=())
    unavailable = SafetyCheck(id='check1', rule=ref('safety_rule'), required=True,
                              outcome='unavailable', reason='timeout', coverage='test')
    assert evaluation(checks=(unavailable,)).outcome == 'incomplete'
    assert evaluation(exact_meaning='failed').outcome == 'hard_failure'


@pytest.mark.parametrize('action', ['acknowledge', 'accept', 'override_attempt'])
def test_human_action_cannot_rewrite_failed_safety(action):
    check = SafetyCheck(id='check1', rule=ref('safety_rule'), required=True,
                        outcome='hard_failure', reason='identity failure', coverage='test')
    e = evaluation(checks=(check,))
    event = HumanDecision(id='h1', evaluation=e, actor='clinician', role='test-role',
                          authority=ref('authority'), at=NOW, action=action,
                          rationale='synthetic test', target_check_id='check1')
    assert event.evaluation.outcome == e.outcome == 'hard_failure'
    with pytest.raises(ValidationError):
        event.evaluation.checks[0].outcome = 'no_detected_violation'
    with pytest.raises(ValidationError):
        SafetyCheck.model_validate({**check.model_dump(), 'overrideable': True})


def test_modification_requires_new_candidate_revision():
    data = dict(id='h1', evaluation=evaluation(), actor='clinician', role='reviewer', authority=ref('authority'),
                at=NOW, action='modify', rationale='changed clinical meaning')
    with pytest.raises(ValidationError):
        HumanDecision(**data, new_candidate=candidate().reference)
    assert HumanDecision(**data, new_candidate=ref('recommendation', 'rec1', '2')).new_candidate.version == '2'


def test_late_retrieval_is_not_available_at_historical_cutoff():
    late = ClinicalTime(event=NOW, retrieved=NOW+timedelta(hours=1), precision='instant')
    with pytest.raises(ValidationError):
        snapshot((observation(time=late),))


def test_json_schema_preserves_discriminated_fact_categories():
    schema = ContextSnapshot.model_json_schema()
    assert schema['properties']['facts']['items']['discriminator']['propertyName'] == 'kind'
    assert len(schema['properties']['facts']['items']['oneOf']) == 7


@pytest.mark.parametrize('value', [0, 1, 0.0, 1.0, 2.5, Decimal('0'), Decimal('1'), Decimal('2.5')])
def test_numeric_measurement_cannot_coerce_to_boolean_python(value):
    with pytest.raises(ValidationError):
        ClinicalValue(status='known', value=value)
    measured = ClinicalValue(status='known', value=quantity(value=value, unit='mg/L'))
    assert isinstance(measured.value, Quantity)


@pytest.mark.parametrize('value', [0, 1, 0.0, 1.0, 2.5])
def test_numeric_measurement_cannot_coerce_to_boolean_json(value):
    with pytest.raises(ValidationError):
        ClinicalValue.model_validate_json(json.dumps({'status': 'known', 'value': value}))


@pytest.mark.parametrize('value', [True, False])
def test_strict_boolean_and_quantity_roundtrip(value):
    boolean = ClinicalValue(status='known', value=value)
    assert ClinicalValue.model_validate_json(boolean.model_dump_json()).value is value
    measured = ClinicalValue(status='known', value=quantity(value='1.00', unit='mg/L'))
    assert ClinicalValue.model_validate_json(measured.model_dump_json()) == measured


def derived(e=None, **changes):
    e = e or execution()
    data = dict(id='d1', origin='derived', concept_id='calculated', execution=e,
                provenance=provenance(e.inputs))
    data.update(changes)
    return DerivedValue(**fact_fields(**data))


def administration(**changes):
    data = dict(id='a1', medication=MedicationIdentity(product_id='drug1'),
                administered_dose=Dose(amount=quantity(value='1', unit='mg'), basis='total_administered'),
                route='oral', administered_at=NOW)
    data.update(changes)
    return MedicationAdministration(**fact_fields(**data))


def test_execution_and_derived_availability_at_cutoff():
    later = NOW + timedelta(hours=1)
    future_execution = execution(executed_at=later)
    with pytest.raises(ValidationError, match='before its execution'):
        derived(future_execution)
    late_fact = derived(future_execution, provenance=provenance(future_execution.inputs, recorded_at=later))
    with pytest.raises(ValidationError, match='unavailable at snapshot cutoff'):
        snapshot((observation(), late_fact), created_at=later, temporal_cutoff=NOW)
    assert snapshot((observation(), derived())).facts[1].execution.executed_at == NOW


@pytest.mark.parametrize('event', [None, NOW - timedelta(minutes=1), NOW + timedelta(minutes=1)])
def test_administration_event_time_must_match(event):
    with pytest.raises(ValidationError, match='event time must equal'):
        administration(time=ClinicalTime(event=event, precision='instant'))


def test_actual_administration_cannot_precede_delivery_or_exceed_cutoff():
    later = NOW + timedelta(hours=1)
    with pytest.raises(ValidationError, match='record cannot precede delivery'):
        administration(administered_at=later, time=ClinicalTime(event=later, recorded=NOW, precision='instant'),
                       provenance=provenance(recorded_at=later))
    with pytest.raises(ValidationError, match='recorded before delivery'):
        administration(administered_at=later, time=ClinicalTime(event=later, precision='instant'))
    delivered = administration(administered_at=later, time=ClinicalTime(event=later, recorded=later, precision='instant'),
                               provenance=provenance(recorded_at=later))
    with pytest.raises(ValidationError, match='unavailable at snapshot cutoff'):
        snapshot((delivered,), created_at=later)
    # Equivalent timezone offsets denote the same instant, not a contradiction.
    offset_time = NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert snapshot((administration(administered_at=offset_time),)).facts[0].time.event == NOW


def test_future_planned_and_effective_times_remain_representable():
    future = NOW + timedelta(days=3)
    planned = Procedure(**fact_fields(concept_id='procedure', procedure_status='planned',
        time=ClinicalTime(event=future, effective_start=future, recorded=NOW, precision='instant')))
    assert snapshot((planned,)).facts[0].time.event == future
    assert snapshot((observation(time=ClinicalTime(event=NOW, effective_start=future, precision='instant')),))


def test_local_conflicting_execution_revisions_rejected_but_shared_execution_allowed():
    e = execution()
    assert len(snapshot((observation(), derived(e), derived(e, id='d2'))).facts) == 3
    conflicting = execution(result=quantity(value='999', unit='mg/L'))
    with pytest.raises(ValidationError, match='conflicting content for exact revision'):
        snapshot((observation(), derived(e), derived(conflicting, id='d2')))
    # A separately identified retry/revision is not a collision.
    new = execution(reference=ref('calculation_execution', version='2'), result=quantity(value='999', unit='mg/L'))
    assert snapshot((observation(), derived(e), derived(new, id='d2')))


def test_local_conflicting_safety_evaluation_revisions_rejected():
    good, failed = evaluation(), evaluation(exact_meaning='failed')
    assert good.reference == failed.reference
    with pytest.raises(ValidationError, match='conflicting content for exact revision'):
        RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(good, failed))
    assert RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(good, good))
    revised = evaluation(revision='2', exact_meaning='failed')
    assert RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(good, revised))


def test_zero_available_inputs_records_named_missing_parameters_without_references():
    missing = execution(inputs=(), outcome='missing_input', result=None, reason='source unavailable',
                        missing_parameters=('weight', 'creatinine'))
    assert missing.inputs == ()
    assert CalculationExecution.model_validate_json(missing.model_dump_json()) == missing
    for changes in ({'inputs': ()}, {'outcome': 'missing_input', 'result': None, 'reason': 'missing', 'missing_parameters': ()}):
        with pytest.raises(ValidationError):
            execution(**changes)
    with pytest.raises(ValidationError, match='both available and missing'):
        execution(outcome='missing_input', result=None, reason='missing', missing_parameters=('measurement',))
    with pytest.raises(ValidationError, match='missing-input outcome'):
        execution(missing_parameters=('weight',))


def test_named_input_conversion_and_rounding_provenance():
    raw = Quantity(value='1000', unit=Unit(raw='micrograms', status='assessed', system='UCUM', code='ug'))
    normalized = Quantity(value='1', unit=Unit(raw='mg', status='normalized', system='UCUM', code='mg'))
    converted = CalculationInput(parameter='mass', fact=observation().reference, source_value=raw,
        evaluated_value=normalized, conversion=ref('unit_conversion', 'ug-to-mg'))
    result = execution(inputs=(converted,))
    assert result.inputs[0].conversion.version == '1'
    assert result.rounding_policy.kind == 'rounding_policy'
    assert CalculationExecution.model_validate_json(result.model_dump_json()) == result
    for changes in ({'conversion': None}, {'conversion': ref('evidence')}, {'fact': ref('evidence')}, {'source_value': None}):
        with pytest.raises(ValidationError):
            CalculationInput.model_validate({**converted.model_dump(), **changes})
    with pytest.raises(ValidationError, match='duplicate calculation parameter'):
        execution(inputs=(converted, converted))
    # One fact can legitimately fill two named roles; this is not independent corroboration.
    other = CalculationInput(parameter='other_mass', fact=observation().reference)
    assert execution(inputs=(converted, other))
    with pytest.raises(ValidationError):
        execution(rounding_policy=ref('evidence'))
    with pytest.raises(ValidationError, match='context differs'):
        derived(execution(context=ContextTarget(patient_id='p2', encounter_id='e2')))


def test_raw_assessed_and_unresolved_units_are_explicit():
    unknown = Unit(raw='ambiguous source unit', status='unresolved', limitation='mapping not established')
    assert Quantity(value='3', unit=unknown).unit.code is None
    assert Unit(raw=' mg ', status='assessed', system='UCUM', code='mg').raw == ' mg '
    for data in ({'status': 'unresolved'}, {'status': 'normalized', 'raw': 'mg'},
                 {'status': 'unresolved', 'limitation': 'unknown', 'system': 'UCUM', 'code': 'mg'}):
        with pytest.raises(ValidationError):
            Unit(**data)
    with pytest.raises(ValidationError):
        Quantity(value='3', unit='mg')


def test_medication_identity_dose_and_optional_delivery_structure():
    med = MedicationIdentity(ingredient_ids=('ingredient1',), product_id='product1', formulation='solution')
    dose = Dose(amount=quantity(value='2', unit='mg'), basis='per_dose',
        concentration=quantity(value='1', unit='mg/mL'), volume=quantity(value='2', unit='mL'),
        rate=quantity(value='1', unit='mL/min'), duration=quantity(value='2', unit='min'),
        frequency=Frequency(occurrences=2, interval=quantity(value='1', unit='d')))
    order = MedicationOrder(**fact_fields(medication=med, prescribed_dose=dose, route='oral', order_status='active'))
    assert MedicationOrder.model_validate_json(order.model_dump_json()) == order
    assert order.medication.ingredient_ids != (order.medication.product_id,)
    for value in ('0', '-1'):
        with pytest.raises(ValidationError, match='must be positive'):
            Dose(amount=quantity(value=value, unit='mg'), basis='per_dose')
    with pytest.raises(ValidationError):
        MedicationIdentity(formulation='unknown product')
    with pytest.raises(ValidationError):
        Dose(amount=quantity(value='1', unit='mg'), basis='unknown')
    with pytest.raises(ValidationError, match='delivered total'):
        administration(administered_dose=dose)


def test_reverification_preserves_target_without_rewriting_fact_assertion():
    later = NOW + timedelta(hours=1)
    new_binding = binding(verifier='second-verifier', assessed_at=later)
    old = observation()
    s = snapshot((old,), binding=new_binding, created_at=later)
    assert s.binding.target == old.binding.target
    assert s.facts[0].binding.verification.verifier == 'test-system'
    assert s.binding.verification.verifier == 'second-verifier'
    with pytest.raises(ValidationError):
        snapshot((old,), binding=binding(patient_id='other'))
    with pytest.raises(ValidationError):
        snapshot((observation(binding=binding(status='unresolved', ambiguity='uncertain match')),))
    assert binding(status='unresolved', ambiguity='uncertain match').verification.assessed_at == NOW


def test_intermediate_copied_record_retains_inferred_origin():
    original = inference()
    bridge_ref = ref('source_record', 'external-note')
    bridge = LineageNode(reference=bridge_ref, origin='inferred', provenance=provenance((
        LineageEdge(target=original.reference, relationship='copied_from'),)))
    copied = inference(id='copy', inputs=(bridge_ref,), provenance=provenance((
        LineageEdge(target=bridge_ref, relationship='copied_from'),)))
    s = snapshot((observation(), original, copied), lineage_nodes=(bridge,))
    restored = ContextSnapshot.model_validate_json(s.model_dump_json())
    assert restored.facts[2].origin == 'inferred'
    graph = LineageGraph(nodes=(LineageNode(reference=original.reference, origin=original.origin, provenance=original.provenance),
                               bridge, LineageNode(reference=copied.reference, origin=copied.origin, provenance=copied.provenance)))
    assert graph.support_relationship(original.reference, copied.reference) == 'dependent'
    relabeled = observation(id='copy', origin='reported', provenance=provenance((
        LineageEdge(target=bridge_ref, relationship='copied_from'),)))
    with pytest.raises(ValidationError, match='retain its derived/inferred origin'):
        snapshot((observation(), original, relabeled), lineage_nodes=(bridge,))
    with pytest.raises(ValidationError):
        snapshot((observation(), original), lineage_nodes=(bridge.model_copy(update={'origin': 'reported'}),))


def test_genuine_later_confirmation_is_separate_from_prior_inference():
    later = NOW + timedelta(hours=1)
    original = inference()
    new_source = Source(namespace='synthetic', identifier='independent-exam', channel='measurement')
    new_observation = observation(id='new-evidence', time=ClinicalTime(event=later, recorded=later, precision='instant'),
                                  provenance=provenance(source=new_source, recorded_at=later))
    edge = LineageEdge(target=original.reference, relationship='independent_confirmation',
                       basis=(new_observation.reference,), rationale='new independently acquired examination')
    confirmation = ClinicalCondition(**fact_fields(id='confirmed', concept_id='condition1', diagnostic_status='confirmed',
        time=ClinicalTime(event=later, recorded=later, precision='instant'), provenance=provenance((edge,), recorded_at=later)))
    s = snapshot((observation(), original, new_observation, confirmation), created_at=later, temporal_cutoff=later)
    assert s.facts[1].origin == 'inferred'
    assert s.facts[3].origin == 'observed'
    graph = LineageGraph(nodes=tuple(LineageNode(reference=f.reference, origin=f.origin, provenance=f.provenance) for f in s.facts))
    # The event asserts independent confirmation; the graph cannot certify that assertion from IDs.
    assert graph.support_relationship(original.reference, confirmation.reference) == 'unknown'
    same_basis = LineageEdge(target=original.reference, relationship='independent_confirmation',
                            basis=(observation().reference,), rationale='same old evidence')
    dependent = ClinicalCondition.model_validate({**confirmation.model_dump(),
        'provenance': provenance((same_basis,), recorded_at=later).model_dump()})
    with pytest.raises(ValidationError, match='claims to confirm independently'):
        snapshot((observation(), original, dependent), created_at=later, temporal_cutoff=later)


def test_order_relationship_is_not_evidence_of_delivery():
    edge = LineageEdge(target=ref('medication_order'), relationship='fulfills_order')
    assert edge.dependencies == ()
    with pytest.raises(ValidationError):
        LineageEdge(target=ref('inference'), relationship='fulfills_order')
    with pytest.raises(ValidationError):
        LineageEdge(target=ref('inference'), relationship='independent_confirmation')


def test_derived_outcome_and_review_state_are_python_only_roundtrippable_properties():
    e = evaluation(exact_meaning='failed')
    review = RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(e,))
    assert 'outcome' not in json.loads(e.model_dump_json())
    assert 'state' not in json.loads(review.model_dump_json())
    for mode in ('validation', 'serialization'):
        assert 'outcome' not in SafetyEvaluation.model_json_schema(mode=mode)['properties']
        assert 'state' not in RecommendationReview.model_json_schema(mode=mode)['properties']
    assert SafetyEvaluation.model_validate_json(e.model_dump_json()).outcome == 'hard_failure'
    assert RecommendationReview.model_validate_json(review.model_dump_json()).state == RecommendationState.EVALUATED
    with pytest.raises(ValidationError):
        SafetyEvaluation.model_validate({**e.model_dump(), 'outcome': 'no_detected_violation'})


def test_all_not_applicable_is_not_applicable_coverage_or_clinical_validity():
    check = SafetyCheck(id='check1', rule=ref('safety_rule'), required=True,
                        outcome='not_applicable', reason='outside this check scope', coverage='none')
    e = evaluation(checks=(check,))
    assert e.outcome == 'not_applicable'
    assert e.outcome != 'no_detected_violation'
    assert 'clinically_valid' not in e.model_dump()
    assert not hasattr(e, 'clinically_valid')
    assert RecommendationReview(candidate=candidate(), rendering=rendering(), evaluations=(e,)).state == RecommendationState.EVALUATED


def test_patient_fact_base_and_reference_boundaries_fail_with_validation_errors():
    for fields in (fact_fields(), fact_fields(kind='observation')):
        with pytest.raises(ValidationError):
            PatientFact(**fields)
    with pytest.raises(ValidationError):
        rendering(candidate=ref('evidence'))
    with pytest.raises(ValidationError):
        SafetyCheck(id='check', rule=ref('observation'), required=True, outcome='no_detected_violation',
                    reason='test', coverage='test')
    with pytest.raises(ValidationError):
        observation(clinical_status='current')
    assert observation(temporal_status='historical').temporal_status == 'historical'


def test_completed_calculation_does_not_use_unresolved_evaluated_units():
    unknown = Quantity(value='1', unit=Unit(raw='?', status='unresolved', limitation='unit unknown'))
    unresolved_input = CalculationInput(parameter='measurement', fact=observation().reference,
                                        source_value=unknown, evaluated_value=unknown)
    with pytest.raises(ValidationError, match='unresolved evaluated units'):
        execution(inputs=(unresolved_input,))
    with pytest.raises(ValidationError, match='unresolved evaluated units'):
        execution(result=unknown)
    assert execution(inputs=(unresolved_input,), result=None, outcome='invalid_input', reason='unit unresolved')


def test_partially_known_medication_identity_is_not_an_automatic_mismatch():
    order = MedicationOrder(**fact_fields(medication=MedicationIdentity(ingredient_ids=('ingredient1',)),
        prescribed_dose=Dose(amount=quantity(value='1', unit='mg'), basis='per_dose'),
        route='oral', order_status='active'))
    delivered = administration(medication=MedicationIdentity(ingredient_ids=('ingredient1',), product_id='product1'),
                               order=order.reference)
    assert snapshot((order, delivered))  # Records coexist; product equivalence is not certified.


def test_intermediate_lineage_conflicts_and_late_arrivals_are_rejected():
    original = inference()
    bridge = LineageNode(reference=ref('source_record', 'note'), origin='inferred',
        provenance=provenance((LineageEdge(target=original.reference, relationship='copied_from'),)))
    changed = LineageNode.model_validate({**bridge.model_dump(), 'provenance': provenance(actor='other').model_dump()})
    with pytest.raises(ValidationError, match='conflicting content'):
        snapshot((observation(), original), lineage_nodes=(bridge, changed))
    late = LineageNode.model_validate({**bridge.model_dump(),
        'provenance': provenance(recorded_at=NOW+timedelta(hours=1)).model_dump()})
    with pytest.raises(ValidationError, match='lineage record was unavailable'):
        snapshot((observation(), original), lineage_nodes=(late,))


def test_candidate_rejects_conflicting_local_knowledge_and_evidence_revisions():
    knowledge = KnowledgeReference(id='k1', version='1', applicability='synthetic only')
    other_knowledge = KnowledgeReference(id='k1', version='1', applicability='contradictory scope')
    with pytest.raises(ValidationError, match='conflicting content'):
        candidate(knowledge=(knowledge, other_knowledge))
    evidence = EvidenceReference(id='e1', version='1', citation='first source', locator='test:1',
                                 retrieved_at=NOW, recovery_limitation='not retained')
    other_evidence = EvidenceReference.model_validate({**evidence.model_dump(), 'citation': 'different source'})
    with pytest.raises(ValidationError, match='conflicting content'):
        candidate(evidence=(evidence, other_evidence))
    assert candidate(knowledge=(knowledge, knowledge), evidence=(evidence, evidence))
