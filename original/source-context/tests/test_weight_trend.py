"""Real SQLite selection/comparison, synthetic only; no clinical release."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text

from app.execution.weight_trend import (
    RecordedWeightComparison, WeightTrendSelectionIssue, WeightTrendSelectionPolicy,
    WeightTrendSelectionResult, compare_recorded_weights, select_weight_observations,
)
from app.models.clinical.common import ClinicalValue, Quantity, Unit
from app.persistence.database import create_database
from app.persistence.errors import ScopeMismatch, StorageIntegrityError
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import AT, TARGET, database, registered, fact, replace
from test_revision_chains import revision

POLICY = WeightTrendSelectionPolicy(concept_id='body-weight', window_start=AT,
    window_end=AT + timedelta(hours=3), available_at=AT + timedelta(hours=4))


def weight(id, value='82', at=AT, label='1'):
    base = fact(id=id, revision=label, concept_id=POLICY.concept_id,
        value=ClinicalValue(status='known', value=Quantity(value=Decimal(value),
            unit=Unit(raw='kg', status='assessed', system='UCUM', code='kg'))),
        verification='verified', conflict='none_known', temporal_status='historical')
    return replace(base, time=replace(base.time, event=at, precision='instant', uncertainty=None),
        provenance=replace(base.provenance, lineage='complete', limitations=()))


def save(engine, *items):
    with transaction(engine) as repo:
        for item in items:
            repo.append_fact(item, target=TARGET)
        return repo.capture_cutoff()


def select(engine, cutoff, policy=POLICY, target=TARGET):
    with transaction(engine) as repo:
        return select_weight_observations(repo, target=target, cutoff=cutoff, policy=policy)


def codes(result):
    return {issue.code for issue in result.issues}


@pytest.mark.parametrize('count,code', [(0, 'insufficient_eligible_inputs'),
    (1, 'insufficient_eligible_inputs'), (2, None), (3, 'ambiguous_eligible_inputs')])
def test_cardinality(registered, count, code):
    cutoff = save(registered, *(weight(str(i), at=AT + timedelta(hours=i)) for i in range(count)))
    result = select(registered, cutoff)
    if code:
        assert codes(result) == {code}
        assert result.selected == () and not result.successful
        assert isinstance(compare_recorded_weights(result), WeightTrendSelectionIssue)
    else:
        assert result.successful and len(result.selected) == 2
        assert result.policy == POLICY and result.cutoff == cutoff and result.target == TARGET


@pytest.mark.parametrize('later,direction', [('79', 'decrease'), ('82', 'unchanged'), ('85', 'increase')])
def test_comparison_exact_values_references_times_and_schema(registered, later, direction):
    a, b = weight('a', label='z'), weight('b', later, AT + timedelta(hours=1), label='a')
    cutoff = save(registered, b, a)
    selection = select(registered, cutoff)
    assert selection.selected == (a, b)  # event time, not ingestion or label order
    result = compare_recorded_weights(selection)
    assert result == RecordedWeightComparison(earlier_reference=a.reference, later_reference=b.reference,
        earlier_kg=Decimal('82'), later_kg=Decimal(later), earlier_event=a.time.event,
        later_event=b.time.event, direction=direction)
    assert RecordedWeightComparison.model_validate_json(result.model_dump_json()) == result
    assert set(result.model_dump()) == {'earlier_reference', 'later_reference', 'earlier_kg',
        'later_kg', 'earlier_event', 'later_event', 'direction'}
    assert 'absolute_change' not in RecordedWeightComparison.model_json_schema()['properties']
    assert 'percentage_change' not in RecordedWeightComparison.model_json_schema()['properties']


@pytest.mark.parametrize('change,code', [
    ('lb', 'unsupported_unit'), ('unresolved_unit', 'unsupported_unit'),
    ('wrong_raw', 'unsupported_unit'), ('zero', 'invalid_value'), ('negative', 'invalid_value'),
    ('text', 'invalid_value'), ('missing_value', 'invalid_value'),
    ('missing_time', 'invalid_or_missing_event_time'), ('imprecise', 'invalid_or_missing_event_time'),
    ('time_uncertainty', 'invalid_or_missing_event_time'), ('conflict', 'unresolved_conflict'),
    ('unknown_conflict', 'unresolved_conflict'), ('unverified', 'unverified_input'),
    ('unresolved_binding', 'unverified_input'), ('limited_provenance', 'unacceptable_provenance'),
    ('unknown_lineage', 'unacceptable_provenance'), ('patient_channel', 'unacceptable_provenance'),
    ('late_recorded', 'source_unavailable_at_cutoff'), ('late_retrieved', 'source_unavailable_at_cutoff'),
    ('late_processed', 'source_unavailable_at_cutoff'), ('late_provenance', 'source_unavailable_at_cutoff'),
    ('late_binding', 'source_unavailable_at_cutoff'),
])
def test_relevant_ineligible_candidate_blocks_even_with_two_good_inputs(registered, change, code):
    item = weight('bad', at=AT + timedelta(hours=2))
    if change in ('lb', 'unresolved_unit', 'wrong_raw'):
        unit = (Unit(raw='lb', status='assessed', system='UCUM', code='[lb_av]') if change == 'lb'
            else Unit(raw='kg', status='unresolved', limitation='unassessed') if change == 'unresolved_unit'
            else Unit(raw='lb', status='assessed', system='UCUM', code='kg'))
        item = replace(item, value=replace(item.value, value=replace(item.value.value, unit=unit)))
    elif change in ('zero', 'negative'):
        item = weight('bad', '0' if change == 'zero' else '-1', AT + timedelta(hours=2))
    elif change == 'text':
        item = replace(item, value=ClinicalValue(status='known', value='82 kg'))
    elif change == 'missing_value':
        item = replace(item, value=ClinicalValue(status='missing', reason='not supplied'))
    elif change in ('missing_time', 'imprecise', 'time_uncertainty'):
        item = replace(item, time=replace(item.time, **({'event': None} if change == 'missing_time'
            else {'precision': 'approximate'} if change == 'imprecise' else {'uncertainty': 'uncertain'})))
    elif change in ('conflict', 'unknown_conflict'):
        item = replace(item, conflict='unresolved' if change == 'conflict' else 'unknown')
    elif change == 'unverified':
        item = replace(item, verification='unverified')
    elif change == 'unresolved_binding':
        item = replace(item, binding=replace(item.binding, verification=replace(item.binding.verification,
            status='unresolved', ambiguity='unresolved synthetic identity')))
    elif change in ('limited_provenance', 'unknown_lineage', 'patient_channel'):
        item = replace(item, provenance=replace(item.provenance, **(
            {'limitations': ('unrecoverable basis',)} if change == 'limited_provenance'
            else {'lineage': 'unknown', 'limitations': ('unknown origin',)} if change == 'unknown_lineage'
            else {'source': replace(item.provenance.source, channel='patient')})))
    else:
        late = POLICY.available_at + timedelta(microseconds=1)
        if change == 'late_provenance':
            item = replace(item, provenance=replace(item.provenance, recorded_at=late))
        elif change == 'late_binding':
            item = replace(item, binding=replace(item.binding,
                verification=replace(item.binding.verification, assessed_at=late)))
        else:
            item = replace(item, time=replace(item.time, **{change.removeprefix('late_'): late}))
    cutoff = save(registered, weight('a'), weight('b', '79', AT + timedelta(hours=1)), item)
    result = select(registered, cutoff)
    assert codes(result) == {code} and result.selected == ()
    assert result.exclusions[0].reference == item.reference and result.exclusions[0].reason == code


@pytest.mark.parametrize('ineligible', ['unit', 'concept', 'window'])
def test_terminal_before_eligibility_no_resurrection_and_old_prefix_replay(registered, ineligible):
    a, b = weight('a', label='z'), weight('b', '79', AT + timedelta(hours=1))
    old = save(registered, a, b)
    before = select(registered, old)
    a2 = revision(a, 'a')
    if ineligible == 'unit':
        a2 = replace(a2, value=replace(a2.value, value=replace(a2.value.value,
            unit=Unit(raw='g', status='assessed', system='UCUM', code='g'))))
    elif ineligible == 'concept':
        a2 = replace(a2, concept_id='height')
    else:
        a2 = replace(a2, time=replace(a2.time, event=POLICY.window_end))
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        new = repo.capture_cutoff()
    result = select(registered, new)
    assert 'insufficient_eligible_inputs' in codes(result) and not result.selected
    assert a.reference not in {e.reference for e in result.exclusions}
    assert select(registered, old) == before


def test_new_cutoff_uses_corrected_exact_reference_old_cutoff_unchanged(registered):
    a, b = weight('a', label='z'), weight('b', '79', AT + timedelta(hours=1))
    old = save(registered, a, b)
    before = select(registered, old)
    a2 = revision(a, '0', value=replace(a.value, value=replace(a.value.value, value=Decimal('80'))))
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        new = repo.capture_cutoff()
    assert select(registered, new).selected == (a2, b)
    assert compare_recorded_weights(select(registered, new)).earlier_reference == a2.reference
    assert select(registered, old) == before


def test_unrelated_and_out_of_window_records_excluded(registered):
    a, b = weight('a'), weight('b', '79', AT + timedelta(hours=1))
    unrelated = replace(weight('height'), concept_id='height', conflict='unresolved')
    outside = replace(weight('outside', at=POLICY.window_end), conflict='unresolved')
    cutoff = save(registered, a, b, unrelated, outside, fact('medication_order'))
    result = select(registered, cutoff)
    assert result.successful and result.selected == (a, b)
    assert {e.reason for e in result.exclusions} == {'unrelated_concept', 'outside_comparison_window', 'unrelated_fact'}


def test_equal_instants_across_offsets_fail(registered):
    a, b = weight('a'), weight('b', at=AT.astimezone(timezone.utc))
    result = select(registered, save(registered, a, b))
    assert codes(result) == {'invalid_measurement_order'}


def test_source_availability_boundary_is_inclusive_and_not_watermark(registered):
    a = weight('a')
    a = replace(a, time=replace(a.time, retrieved=POLICY.available_at))
    cutoff = save(registered, a, weight('b', at=AT + timedelta(hours=1)))
    assert select(registered, cutoff).successful
    assert not select(registered, cutoff, replace(POLICY, available_at=POLICY.window_end)).successful


def test_read_only_deterministic_reopen_preserves_payloads_and_metadata(registered):
    cutoff = save(registered, weight('b', '79', AT + timedelta(hours=1)), weight('a'))
    with transaction(registered) as repo:
        before = repo.list_history(target=TARGET, cutoff=cutoff)
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().split()[0].upper())
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        first = select(registered, cutoff)
        assert select(registered, cutoff) == first
        compare_recorded_weights(first)
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    assert not {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'} & set(statements)
    path = registered.url.database
    registered.dispose()
    reopened = create_database(path)
    try:
        assert select(reopened, cutoff) == first
        with transaction(reopened) as repo:
            assert repo.list_history(target=TARGET, cutoff=cutoff) == before
    finally:
        reopened.dispose()
    with pytest.raises(ValidationError):
        first.selected[0].revision = 'changed'
    assert WeightTrendSelectionResult.model_validate_json(first.model_dump_json()) == first


def test_corrupt_inferred_observation_remains_storage_exception(registered):
    cutoff = save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1)))
    with registered.begin() as connection:
        payload = canonical_payload(weight('a')).replace('"origin":"reported"', '"origin":"inferred"')
        connection.execute(text('UPDATE fact_revision SET payload=:p WHERE fact_id=:id'), {'p': payload, 'id': 'a'})
    with pytest.raises(StorageIntegrityError):
        select(registered, cutoff)


def test_inferred_observation_rejected_by_existing_domain_contract():
    with pytest.raises(ValidationError):
        replace(weight('a'), origin='inferred')


def test_scope_and_foreign_cutoff_errors_are_not_selection_issues(registered):
    cutoff = save(registered, weight('a'))
    with pytest.raises(ScopeMismatch):
        select(registered, replace(cutoff, repository_id='00000000-0000-0000-0000-000000000001'))


def test_forged_selected_pair_revalidated_at_comparison_boundary(registered):
    result = select(registered, save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1))))
    forged = result.model_copy(update={'selected': tuple(reversed(result.selected))})
    with pytest.raises(ValidationError):
        compare_recorded_weights(forged)


@pytest.mark.parametrize('changes', [{'window_end': AT}, {'available_at': AT}, {'version': '2'},
    {'window_start': AT.replace(tzinfo=None)}])
def test_invalid_policy_is_not_normal_selection_failure(changes):
    with pytest.raises(ValidationError):
        replace(POLICY, **changes)


def test_dst_fold_measurement_order_uses_instants(registered):
    zone = ZoneInfo('America/New_York')
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    later = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)
    policy = WeightTrendSelectionPolicy(concept_id=POLICY.concept_id,
        window_start=datetime(2026, 11, 1, 0, tzinfo=zone),
        window_end=datetime(2026, 11, 1, 3, tzinfo=zone), available_at=datetime(2026, 11, 1, 4, tzinfo=zone))
    a, b = weight('a', at=first), weight('b', '79', later)
    result = select(registered, save(registered, b, a), policy)
    assert result.successful
    assert tuple(f.reference for f in result.selected) == (a.reference, b.reference)
    assert tuple(f.time.event.isoformat() for f in result.selected) == (first.isoformat(), later.isoformat())
    assert compare_recorded_weights(result).direction == 'decrease'


@pytest.mark.parametrize('field,value', [('direction', 'increase'), ('earlier_kg', Decimal('0')),
    ('absolute_change', Decimal('-3')), ('later_event', AT)])
def test_comparison_rejects_inconsistent_or_extra_content(registered, field, value):
    selection = select(registered, save(registered, weight('a'), weight('b', '79', AT + timedelta(hours=1))))
    comparison = compare_recorded_weights(selection)
    with pytest.raises(ValidationError):
        replace(comparison, **{field: value})


def test_half_open_window_and_unverified_fact_are_explicit(registered):
    cutoff = save(registered, weight('before', at=AT - timedelta(microseconds=1)),
        weight('a'), weight('b', at=AT + timedelta(hours=1)), weight('end', at=POLICY.window_end))
    result = select(registered, cutoff)
    assert result.successful
    assert {e.reference.id for e in result.exclusions} == {'before', 'end'}


def test_wrong_encounter_does_not_select_other_patient_measurements(registered):
    cutoff = save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1)))
    other = replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3')
    result = select(registered, cutoff, target=other)
    assert codes(result) == {'insufficient_eligible_inputs'} and not result.selected


def test_future_malformed_payload_does_not_change_old_cutoff_selection(registered):
    a, b = weight('a'), weight('b', at=AT + timedelta(hours=1))
    old = save(registered, a, b)
    before = select(registered, old)
    with transaction(registered) as repo:
        repo.append_revision(revision(a, '2'), target=TARGET)
        current = repo.capture_cutoff()
    with registered.begin() as connection:
        connection.execute(text("UPDATE fact_revision SET payload='{}' WHERE fact_id='a' AND revision='2'"))
    assert select(registered, old) == before
    with pytest.raises(StorageIntegrityError):
        select(registered, current)


def test_declared_upstream_provenance_not_treated_as_independent_measurement(registered):
    from app.models.clinical.common import LineageEdge
    a, b = weight('a'), weight('b', at=AT + timedelta(hours=1))
    b = replace(b, provenance=replace(b.provenance,
        upstream=(LineageEdge(target=a.reference, relationship='copied_from'),)))
    result = select(registered, save(registered, a, b))
    assert 'unacceptable_provenance' in codes(result) and not result.selected


@pytest.mark.parametrize('offset_us,eligible', [(-1, False), (0, True), (1, True)])
def test_review_exact_start_boundary(registered, offset_us, eligible):
    a = weight('a', at=POLICY.window_start + timedelta(microseconds=offset_us))
    b = weight('b', at=AT + timedelta(hours=1))
    result = select(registered, save(registered, a, b))
    assert result.successful is eligible
    if eligible:
        assert tuple(f.reference for f in result.selected) == (a.reference, b.reference)
    else:
        assert [(e.reference, e.reason) for e in result.exclusions] == [(a.reference, 'outside_comparison_window')]


@pytest.mark.parametrize('offset_us,eligible', [(-1, True), (0, False), (1, False)])
def test_review_exact_end_boundary(registered, offset_us, eligible):
    a, b = weight('a'), weight('b', at=POLICY.window_end + timedelta(microseconds=offset_us))
    result = select(registered, save(registered, a, b))
    assert result.successful is eligible
    if not eligible:
        assert [(e.reference, e.reason) for e in result.exclusions] == [(b.reference, 'outside_comparison_window')]


@pytest.mark.parametrize('offset_us,eligible', [(-1, True), (0, True), (1, False)])
def test_review_availability_offset_equivalent_instants(registered, offset_us, eligible):
    instant = (POLICY.available_at + timedelta(microseconds=offset_us)).astimezone(timezone(timedelta(hours=-7)))
    a = weight('a')
    a = replace(a, time=replace(a.time, recorded=instant, retrieved=instant, processed=instant),
        provenance=replace(a.provenance, recorded_at=instant), binding=replace(a.binding,
            verification=replace(a.binding.verification, assessed_at=instant)))
    result = select(registered, save(registered, a, weight('b', at=AT + timedelta(hours=1))))
    assert result.successful is eligible
    if not eligible:
        assert 'source_unavailable_at_cutoff' in codes(result)


def test_review_multiple_corrections_never_form_multiple_measurements(registered):
    a, b = weight('a', label='z'), weight('b', at=AT + timedelta(hours=1))
    first = save(registered, a, b)
    a2 = revision(a, 'a', value=replace(a.value, value=replace(a.value.value, value=Decimal('80'))))
    a3 = revision(a2, '00', conflict='unresolved')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        second = repo.capture_cutoff()
        repo.append_revision(a3, target=TARGET)
        third = repo.capture_cutoff()
    assert tuple(f.reference for f in select(registered, first).selected) == (a.reference, b.reference)
    assert tuple(f.reference for f in select(registered, second).selected) == (a2.reference, b.reference)
    result = select(registered, third)
    assert codes(result) == {'unresolved_conflict', 'insufficient_eligible_inputs'}
    assert [(e.reference, e.reason) for e in result.exclusions] == [(a3.reference, 'unresolved_conflict')]


def test_review_exclusion_and_issue_order_is_terminal_ingestion_order_after_reopen(registered):
    unrelated = replace(weight('z'), concept_id='height')
    missing = replace(weight('a'), time=replace(weight('a').time, event=None))
    outside = weight('m', at=POLICY.window_end)
    cutoff = save(registered, unrelated, missing, outside, weight('good'))
    expected = [(unrelated.reference, 'unrelated_concept'),
        (missing.reference, 'invalid_or_missing_event_time'), (outside.reference, 'outside_comparison_window')]
    result = select(registered, cutoff)
    assert [(e.reference, e.reason) for e in result.exclusions] == expected
    assert [(i.reference, i.code) for i in result.issues] == [
        (missing.reference, 'invalid_or_missing_event_time'), (None, 'insufficient_eligible_inputs')]
    registered.dispose()
    reopened = create_database(registered.url.database)
    try:
        assert select(reopened, cutoff) == result
    finally:
        reopened.dispose()


@pytest.mark.parametrize('case', ['same_patient_other_encounter', 'different_patient'])
def test_review_populated_foreign_scope_cannot_affect_cardinality(registered, case):
    other = (replace(TARGET, encounter_id='synthetic-e2') if case == 'same_patient_other_encounter'
        else replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3'))
    a, b = weight('a'), weight('b', at=AT + timedelta(hours=1))
    with transaction(registered) as repo:
        repo.append_fact(a, target=TARGET)
        repo.append_fact(b, target=TARGET)
        for n in range(3):
            item = weight('foreign-' + str(n), at=AT + timedelta(minutes=n))
            item = replace(item, binding=replace(item.binding, target=other), conflict='unresolved')
            repo.append_fact(item, target=other)
        cutoff = repo.capture_cutoff()
    result = select(registered, cutoff)
    assert result.successful and result.exclusions == ()
    assert tuple(f.reference for f in result.selected) == (a.reference, b.reference)


@pytest.mark.parametrize('variant', ['same_revision', 'different_revision'])
def test_review_duplicate_stable_identity_rejected_at_comparison_boundary(registered, variant):
    result = select(registered, save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1))))
    first = result.selected[0]
    duplicate = replace(first, time=replace(first.time, event=AT + timedelta(hours=1)),
        revision=first.revision if variant == 'same_revision' else 'another')
    forged = result.model_copy(update={'selected': (first, duplicate)})
    with pytest.raises(ValidationError):
        compare_recorded_weights(forged)


@pytest.mark.parametrize('path', ['policy', 'reference', 'quantity', 'unit', 'comparison'])
def test_review_nested_returned_contracts_are_frozen(registered, path):
    result = select(registered, save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1))))
    before = result.model_dump_json()
    target, attribute, value = {
        'policy': (result.policy, 'concept_id', 'other'),
        'reference': (result.selected[0].reference, 'version', 'other'),
        'quantity': (result.selected[0].value.value, 'value', Decimal('1')),
        'unit': (result.selected[0].value.value.unit, 'code', 'g'),
        'comparison': (compare_recorded_weights(result), 'direction', 'increase'),
    }[path]
    with pytest.raises(ValidationError):
        setattr(target, attribute, value)
    assert result.model_dump_json() == before


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_review_nonfinite_quantities_rejected_before_ingestion(value):
    with pytest.raises(ValidationError):
        weight('invalid', value)


def test_review_boolean_quantity_is_not_weight(registered):
    item = replace(weight('boolean'), value=ClinicalValue(status='known', value=True))
    result = select(registered, save(registered, item, weight('b', at=AT + timedelta(hours=1))))
    assert codes(result) == {'invalid_value', 'insufficient_eligible_inputs'}


@pytest.mark.parametrize('unit', [
    Unit(raw='KG', status='assessed', system='UCUM', code='kg'),
    Unit(raw='kg', status='assessed', system='local', code='kg'),
    Unit(raw='kg', status='assessed', system='UCUM', code='g'),
    Unit(raw=None, status='assessed', system='UCUM', code='kg'),
])
def test_review_unsupported_unit_spellings_and_namespaces_not_normalized(registered, unit):
    a = weight('a')
    a = replace(a, value=replace(a.value, value=replace(a.value.value, unit=unit)))
    result = select(registered, save(registered, a, weight('b', at=AT + timedelta(hours=1))))
    assert 'unsupported_unit' in codes(result) and not result.selected


def test_review_visible_unrelated_corruption_is_not_ordinary_exclusion(registered):
    unrelated = replace(weight('height'), concept_id='height')
    cutoff = save(registered, weight('a'), weight('b', at=AT + timedelta(hours=1)), unrelated)
    with registered.begin() as connection:
        connection.execute(text("UPDATE fact_revision SET payload='{}' WHERE fact_id='height'"))
    with pytest.raises(StorageIntegrityError):
        select(registered, cutoff)


@pytest.mark.parametrize('year,offset', [(1, 14), (9999, -14)])
def test_review_boundary_instants_without_utc_datetime_overflow(registered, year, offset):
    start = (datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=offset))) if year == 1
        else datetime(9999, 12, 31, 23, 59, 55, tzinfo=timezone(timedelta(hours=offset))))
    policy = WeightTrendSelectionPolicy(concept_id=POLICY.concept_id,
        window_start=start, window_end=start + timedelta(seconds=3), available_at=start + timedelta(seconds=4))
    items = []
    for n, value in enumerate(('82', '79')):
        item = weight(str(n), value, start + timedelta(seconds=n))
        item = replace(item, time=replace(item.time, recorded=start, retrieved=start, processed=start),
            provenance=replace(item.provenance, recorded_at=start), binding=replace(item.binding,
                verification=replace(item.binding.verification, assessed_at=start)))
        items.append(item)
    result = select(registered, save(registered, *reversed(items)), policy)
    assert result.successful
    comparison = compare_recorded_weights(result)
    assert comparison.direction == 'decrease'
    assert comparison.earlier_event.isoformat() == start.isoformat()
    assert comparison.later_reference == items[1].reference
