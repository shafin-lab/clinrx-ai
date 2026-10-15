"""Synthetic Phase 2 construction and real durable exact-lineage integration."""
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text

from app.execution.weight_trend import (
    RECORDED_WEIGHT_TREND_METHOD, RecordedWeightComparison, WeightTrendSelectionIssue,
    build_weight_trend_inference, compare_recorded_weights,
)
from app.models.clinical.common import ClinicalValue, Quantity, Reference, Unit
from app.models.clinical.facts import ClinicalInference
from app.persistence.database import create_database
from app.persistence.errors import RecordConflict, RecordNotFound, StorageIntegrityError
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import AT, TARGET, database, registered, replace
from test_revision_chains import revision
from test_weight_trend import POLICY, save, select, weight

EXECUTED = POLICY.available_at


def build(selection, comparison=None, **changes):
    return build_weight_trend_inference(selection=selection,
        comparison=compare_recorded_weights(selection) if comparison is None else comparison,
        inference_id=changes.pop('inference_id', 'weight-trend-1'),
        executed_at=changes.pop('executed_at', EXECUTED), **changes)


def selected_pair(engine, earlier='82', later='79'):
    a, b = weight('a', earlier, label='z'), weight('b', later, AT + timedelta(hours=1), label='0')
    cutoff = save(engine, b, a)
    return select(engine, cutoff), (a, b)


def persist(engine, inference):
    with transaction(engine) as repo:
        stored = repo.append_fact(inference, target=TARGET)
    with transaction(engine) as repo:
        cutoff = repo.capture_cutoff()
    return stored, cutoff


def resolve(engine, inference, cutoff):
    with transaction(engine) as repo:
        return repo.resolve_lineage(inference.reference, target=TARGET, cutoff=cutoff, limits=LineageLimits())


@pytest.mark.parametrize('earlier,later,statement', [
    ('82', '79', 'Recorded weight decreased from 82 kg to 79 kg between the selected observations. '
        'This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.'),
    ('82', '82', 'Recorded weight was unchanged at 82 kg between the selected observations. '
        'This comparison does not establish nutritional status. Synthetic evaluation only.'),
    ('79', '82', 'Recorded weight increased from 79 kg to 82 kg between the selected observations. '
        'This comparison does not establish cause or nutritional diagnosis. Synthetic evaluation only.'),
])
def test_exact_bounded_inference_semantics(registered, earlier, later, statement):
    selection, (a, b) = selected_pair(registered, earlier, later)
    inference = build(selection)
    assert isinstance(inference, ClinicalInference)
    assert inference.origin == 'inferred' and inference.verification == 'unverified'
    assert inference.method == Reference(kind='inference_method', id='RecordedWeightTrend', version='1')
    assert inference.inputs == (a.reference, b.reference)
    assert [(e.relationship, e.target, e.basis) for e in inference.provenance.upstream] == [
        ('derived_from', a.reference, ()), ('derived_from', b.reference, ())]
    assert inference.provenance.dependencies == (a.reference, b.reference)
    assert inference.statement == statement
    assert inference.applicability == 'Synthetic recorded-weight comparison within the selected patient/encounter and event window only.'
    assert inference.validation_limitations == 'Not clinically validated; no diagnosis, causal interpretation or treatment recommendation.'
    assert inference.target is None and inference.horizon is None
    assert a.uncertainty[0] in inference.uncertainty
    assert inference.provenance.source.channel == 'system'
    assert inference.provenance.source.identifier == 'RecordedWeightTrend'
    assert inference.provenance.source.version == '1'
    assert inference.provenance.actor == 'RecordedWeightTrend/v1'
    assert inference.provenance.lineage == 'complete' and inference.provenance.limitations
    assert inference.binding == selection.selected[0].binding
    assert inference.time.event == inference.time.recorded == inference.time.processed == EXECUTED
    assert inference.provenance.recorded_at == EXECUTED
    assert ClinicalInference.model_validate_json(inference.model_dump_json()) == inference


def test_principal_reopen_persist_commit_and_exact_durable_dependencies(registered):
    a, b = weight('a', label='z'), weight('b', '79', AT + timedelta(hours=1), label='0')
    save(registered, b, a)
    path = registered.url.database
    registered.dispose()
    engine = create_database(path)
    try:
        with transaction(engine) as repo:
            input_cutoff = repo.capture_cutoff()
        selection = select(engine, input_cutoff)
        inference = build(selection)
        stored, output_cutoff = persist(engine, inference)
        assert output_cutoff.repository_id == input_cutoff.repository_id
        assert output_cutoff.fact_watermark > input_cutoff.fact_watermark
        assert output_cutoff.fact_watermark >= stored.ingestion.ingestion_sequence
    finally:
        engine.dispose()
    engine = create_database(path)
    try:
        with transaction(engine) as repo:
            loaded = repo.load_fact(inference.reference, target=TARGET)
        assert loaded == stored
        assert canonical_payload(loaded.fact) == canonical_payload(inference)
        assert loaded.fact.method == RECORDED_WEIGHT_TREND_METHOD
        with pytest.raises(RecordNotFound):
            resolve(engine, inference, input_cutoff)
        statements = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement.strip().split()[0].upper())
        event.listen(engine, 'before_cursor_execute', capture)
        try:
            result = resolve(engine, inference, output_cutoff)
            assert resolve(engine, inference, output_cutoff) == result
        finally:
            event.remove(engine, 'before_cursor_execute', capture)
        assert not {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'} & set(statements)
        assert result.reference == inference.reference and result.target == TARGET
        assert [(d.owner, d.ordinal, d.source, d.basis_ordinal) for d in result.dependencies
                if d.owner == inference.reference] == [
            (inference.reference, 0, a.reference, None), (inference.reference, 1, b.reference, None)]
        assert [(x.owner, x.edge.relationship, x.edge.target) for x in result.assertions
                if x.owner == inference.reference] == [
            (inference.reference, 'derived_from', a.reference), (inference.reference, 'derived_from', b.reference)]
        assert dict(result.ancestry)[inference.reference] == frozenset((inference.reference, a.reference, b.reference))
        assert result.unresolved == () and result.associations == ()
        assert result.coverage == 'complete_for_declared_visible_graph'
        with engine.connect() as conn:
            assert set(inspect(conn).get_table_names()) == {
                'patient', 'encounter', 'fact_revision', 'revision_link', 'repository_identity', 'weight_trend_execution', 'creatinine_trend_execution', 'patient_state_temporal_execution', 'micro_antimicrobial_execution', 'circulatory_execution', 'alembic_version'}
    finally:
        engine.dispose()


def test_later_correction_never_substitutes_exact_input_or_mutates_inference(registered):
    selection, (a, b) = selected_pair(registered)
    inference = build(selection)
    stored, output = persist(registered, inference)
    old_graph = resolve(registered, inference, output)
    a2 = revision(a, 'opaque-new', value=replace(a.value, value=replace(a.value.value, value=Decimal('80'))))
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        later = repo.capture_cutoff()
    assert select(registered, selection.cutoff) == selection
    newer = select(registered, later)
    assert tuple(f.reference for f in newer.selected) == (a2.reference, b.reference)
    assert build(newer, inference_id='new-attempt').inputs == (a2.reference, b.reference)
    graph = resolve(registered, inference, later)
    assert tuple(d.source for d in graph.dependencies if d.owner == inference.reference) == (a.reference, b.reference)
    assert a2.reference not in dict(graph.ancestry)[inference.reference]
    assert resolve(registered, inference, output) == old_graph
    with transaction(registered) as repo:
        assert repo.load_fact(inference.reference, target=TARGET) == stored
        assert repo.append_fact(inference, target=TARGET) == stored


@pytest.mark.parametrize('change', ['value', 'reference', 'time', 'offset', 'direction', 'duplicate', 'reversed'])
def test_tampered_comparison_cannot_build_inference(registered, change):
    selection, _ = selected_pair(registered)
    comparison = compare_recorded_weights(selection)
    if change == 'value':
        comparison = replace(comparison, earlier_kg=Decimal('83'))
    elif change == 'reference':
        comparison = replace(comparison, earlier_reference=replace(comparison.earlier_reference, version='2'))
    elif change == 'time':
        comparison = replace(comparison, earlier_event=comparison.earlier_event + timedelta(microseconds=1))
    elif change == 'offset':
        comparison = replace(comparison, earlier_event=comparison.earlier_event.astimezone(timezone.utc))
    elif change == 'direction':
        comparison = comparison.model_copy(update={'direction': 'increase'})
    elif change == 'duplicate':
        comparison = comparison.model_copy(update={'later_reference': comparison.earlier_reference})
    else:
        comparison = comparison.model_copy(update={'earlier_reference': comparison.later_reference,
            'later_reference': comparison.earlier_reference, 'earlier_event': comparison.later_event,
            'later_event': comparison.earlier_event})
    with pytest.raises(ValueError):
        build(selection, comparison)


@pytest.mark.parametrize('case', ['zero', 'one', 'ambiguous', 'unit', 'time', 'conflict'])
def test_failed_selection_returns_issue_not_inference(registered, case):
    items = [] if case == 'zero' else [weight('a')]
    if case not in ('zero', 'one'):
        items.append(weight('b', '79', AT + timedelta(hours=1)))
    if case == 'ambiguous':
        items.append(weight('c', at=AT + timedelta(hours=2)))
    elif case == 'unit':
        items[0] = replace(items[0], value=ClinicalValue(status='known', value=Quantity(value=82,
            unit=Unit(raw='g', status='assessed', system='UCUM', code='g'))))
    elif case == 'time':
        items[0] = replace(items[0], time=replace(items[0].time, event=None))
    elif case == 'conflict':
        items[0] = replace(items[0], conflict='unresolved')
    selection = select(registered, save(registered, *items))
    assert not selection.successful
    assert build(selection) == selection.issues[0]
    assert isinstance(build(selection), WeightTrendSelectionIssue)


@pytest.mark.parametrize('case', ['duplicate_stable', 'inferred_origin', 'reversed', 'equal_time'])
def test_forged_selection_revalidated(registered, case):
    selection, _ = selected_pair(registered)
    a, b = selection.selected
    if case == 'duplicate_stable':
        b = b.model_copy(update={'id': a.id, 'revision': 'other'})
    elif case == 'inferred_origin':
        a = a.model_copy(update={'origin': 'inferred'})
    elif case == 'equal_time':
        b = b.model_copy(update={'time': replace(b.time, event=a.time.event.astimezone(timezone.utc))})
    pair = (b, a) if case == 'reversed' else (a, b)
    forged = selection.model_copy(update={'selected': pair})
    with pytest.raises(ValidationError):
        build(forged, compare_recorded_weights(selection))


@pytest.mark.parametrize('at', [EXECUTED - timedelta(microseconds=1), EXECUTED.replace(tzinfo=None)])
def test_execution_time_cannot_precede_availability_or_be_naive(registered, at):
    selection, _ = selected_pair(registered)
    with pytest.raises(ValueError):
        build(selection, executed_at=at)


def test_builder_is_pure_and_retained_inference_and_lineage_are_frozen(registered):
    selection, _ = selected_pair(registered)
    before = selection.model_dump_json()
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        inference = build(selection)
        assert canonical_payload(build(selection)) == canonical_payload(inference)
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    assert statements == [] and selection.model_dump_json() == before
    stored, cutoff = persist(registered, inference)
    with transaction(registered) as repo:
        loaded = repo.load_fact(inference.reference, target=TARGET)
    with pytest.raises(ValidationError):
        loaded.fact.statement = 'malnutrition'
    with pytest.raises(ValidationError):
        loaded.fact.method.version = '2'
    graph = resolve(registered, inference, cutoff)
    with pytest.raises(FrozenInstanceError):
        graph.reference = Reference(kind='inference', id='other', version='1')
    with pytest.raises(ValidationError):
        graph.nodes[-1].stored.fact.origin = 'observed'
    assert loaded == stored
    assert resolve(registered, inference, cutoff) == graph


def test_existing_domain_origin_rules_not_weakened(registered):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    with pytest.raises(ValidationError):
        replace(inference, origin='observed')
    with pytest.raises(ValidationError):
        replace(selection.selected[0], origin='inferred')


def test_malformed_persisted_inference_fails_not_normalized(registered):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    _, cutoff = persist(registered, inference)
    with registered.begin() as connection:
        payload = canonical_payload(inference).replace('"origin":"inferred"', '"origin":"observed"')
        connection.execute(text('UPDATE fact_revision SET payload=:p WHERE fact_id=:id'),
            {'p': payload, 'id': inference.id})
    with pytest.raises(StorageIntegrityError):
        resolve(registered, inference, cutoff)
    with pytest.raises(StorageIntegrityError):
        with transaction(registered) as repo:
            repo.load_fact(inference.reference, target=TARGET)


def test_exact_id_retry_conflicts_instead_of_rewriting(registered):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    stored, _ = persist(registered, inference)
    with pytest.raises(RecordConflict):
        persist(registered, replace(inference, statement='different retained content'))
    with transaction(registered) as repo:
        assert repo.load_fact(inference.reference, target=TARGET) == stored


def test_equal_numeric_value_with_changed_decimal_representation_not_substituted(registered):
    selection, _ = selected_pair(registered)
    comparison = compare_recorded_weights(selection)
    changed = replace(comparison, earlier_kg=Decimal('82.0'))
    with pytest.raises(ValueError, match='exact selected observations'):
        build(selection, changed)


@pytest.mark.parametrize('microseconds', [0, 1])
def test_execution_availability_boundary_retains_supplied_offset(registered, microseconds):
    selection, _ = selected_pair(registered)
    at = (EXECUTED + timedelta(microseconds=microseconds)).astimezone(timezone(timedelta(hours=-7)))
    inference = build(selection, executed_at=at)
    assert inference.time.recorded.isoformat() == at.isoformat()
    assert inference.provenance.recorded_at.isoformat() == at.isoformat()
    stored, _ = persist(registered, inference)
    assert canonical_payload(stored.fact) == canonical_payload(inference)


def test_successful_selection_cannot_accept_issue_as_comparison(registered):
    selection, _ = selected_pair(registered)
    with pytest.raises(ValidationError):
        build(selection, WeightTrendSelectionIssue(code='invalid_measurement_order'))


@pytest.mark.parametrize('earlier,later,direction_word', [('82', '79', 'decreased'),
    ('82', '82', 'unchanged'), ('79', '82', 'increased')])
def test_all_directions_retain_method_statement_and_limits_after_reopen(registered, earlier, later, direction_word):
    selection, _ = selected_pair(registered, earlier, later)
    inference = build(selection)
    stored, output = persist(registered, inference)
    registered.dispose()
    engine = create_database(registered.url.database)
    try:
        with transaction(engine) as repo:
            loaded = repo.load_fact(inference.reference, target=TARGET)
        assert loaded == stored
        assert direction_word in loaded.fact.statement
        assert loaded.fact.method == Reference(kind='inference_method', id='RecordedWeightTrend', version='1')
        assert loaded.fact.uncertainty == inference.uncertainty
        assert loaded.fact.provenance.limitations == inference.provenance.limitations
        assert loaded.fact.validation_limitations == inference.validation_limitations
        assert tuple(d.source for d in resolve(engine, inference, output).dependencies
            if d.owner == inference.reference) == inference.inputs
    finally:
        engine.dispose()
