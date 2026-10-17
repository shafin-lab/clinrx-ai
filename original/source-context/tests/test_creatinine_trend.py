"""Independent synthetic Phase A expectations against real SQLite history."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import permutations
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text

from app.execution.creatinine_trend import (
    CreatinineTrendExclusion, CreatinineTrendSelectionIssue, CreatinineTrendSelectionPolicy,
    CreatinineTrendSelectionResult, RecordedCreatinineComparison,
    compare_recorded_creatinine, select_creatinine_observations,
)
from app.models.clinical.common import ClinicalValue, LineageEdge, Quantity, Unit
from app.persistence.database import create_database
from app.persistence.errors import PersistenceInputError, ScopeMismatch, StorageIntegrityError, UnsupportedOperation
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import AT, TARGET, database, registered, fact, replace
from test_revision_chains import revision

POLICY = CreatinineTrendSelectionPolicy(window_start=AT,
    window_end=AT + timedelta(hours=3), available_at=AT + timedelta(hours=4))


def creatinine(id, value='1.200', at=AT, sample=None, label='1'):
    base = fact(id=id, revision=label, concept_id='synthetic-serum-creatinine',
        value=ClinicalValue(status='known', value=Quantity(value=Decimal(value),
            unit=Unit(raw='mg/dL', status='assessed', system='UCUM', code='mg/dL'))),
        verification='verified', conflict='none_known')
    return replace(base, time=replace(base.time, event=at, recorded=at, retrieved=at,
        processed=at, precision='instant', uncertainty=None),
        binding=replace(base.binding, verification=replace(base.binding.verification, assessed_at=at)),
        provenance=replace(base.provenance, recorded_at=at, lineage='complete', limitations=(),
            source=replace(base.provenance.source, namespace='clinrx.synthetic.serum-creatinine',
                identifier=sample if sample is not None else 'sample-' + id, version='1')))


def save(engine, *items):
    with transaction(engine) as repo:
        for item in items:
            repo.append_fact(item, target=item.binding.target)
        return repo.capture_cutoff()


def select(engine, cutoff, policy=POLICY, target=TARGET):
    with transaction(engine) as repo:
        return select_creatinine_observations(repo, target=target, cutoff=cutoff, policy=policy)


def issues(result):
    return [(item.reference.id if item.reference else None, item.code) for item in result.issues]


def changed_unit(item, **updates):
    return replace(item, value=replace(item.value, value=replace(item.value.value,
        unit=replace(item.value.value.unit, **updates))))


def pair(engine):
    return select(engine, save(engine, creatinine('a'), creatinine('b', '1.500', AT + timedelta(hours=1))))


@pytest.mark.parametrize('count,expected', [(0, 'insufficient_eligible_inputs'),
    (1, 'insufficient_eligible_inputs'), (2, None), (3, 'ambiguous_eligible_inputs'),
    (4, 'ambiguous_eligible_inputs')])
def test_cardinality_no_latest_two(registered, count, expected):
    records = [creatinine(str(i), at=AT + timedelta(minutes=i)) for i in range(count)]
    result = select(registered, save(registered, *records))
    assert result.target == TARGET and result.policy == POLICY
    if expected:
        assert issues(result) == [(None, expected)] and result.selected == ()
        assert compare_recorded_creatinine(result) == CreatinineTrendSelectionIssue(code=expected)
    else:
        assert result.successful and result.selected == tuple(records)


@pytest.mark.parametrize('a,b,direction', [('1.200', '1.5000', 'increase'),
    ('2.000', '1.200', 'decrease'), ('1.20', '1.2000', 'unchanged'),
    ('1E-1000', '1E+1000', 'increase')])
def test_comparison_independent_expected_payload(registered, a, b, direction):
    first = creatinine('a', a, label='z')
    second = creatinine('b', b, (AT + timedelta(hours=1)).astimezone(timezone.utc), label='a')
    selection = select(registered, save(registered, second, first))
    assert selection.selected == (first, second)
    comparison = compare_recorded_creatinine(selection)
    assert comparison.model_dump(mode='json') == {
        'earlier_reference': {'kind': 'observation', 'id': 'a', 'version': 'z'},
        'later_reference': {'kind': 'observation', 'id': 'b', 'version': 'a'},
        'earlier_value': a, 'later_value': b, 'unit': 'mg/dL',
        'earlier_sample_time': AT.isoformat(),
        'later_sample_time': (AT + timedelta(hours=1)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'direction': direction,
    }
    assert RecordedCreatinineComparison.model_validate_json(comparison.model_dump_json()) == comparison
    assert str(comparison.earlier_value) == a and str(comparison.later_value) == b


@pytest.mark.parametrize('updates', [dict(raw=None), dict(raw='µmol/L', code='umol/L'),
    dict(raw='mg/dl'), dict(raw=' mg/dL'), dict(raw='mg/dL '), dict(raw='mg per dL'),
    dict(system='local'), dict(code='mg/L'),
    dict(status='unresolved', system=None, code=None, limitation='unknown')])
def test_exact_unit_no_normalization(registered, updates):
    bad = changed_unit(creatinine('bad'), **updates)
    result = select(registered, save(registered, bad, creatinine('b', at=AT + timedelta(hours=1))))
    assert issues(result) == [('bad', 'unsupported_unit'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('status', ['assessed', 'normalized'])
def test_exact_unit_supported_status(registered, status):
    a = changed_unit(creatinine('a'), status=status)
    result = select(registered, save(registered, a, creatinine('b', at=AT + timedelta(hours=1))))
    assert result.successful and compare_recorded_creatinine(result).unit == 'mg/dL'


@pytest.mark.parametrize('value', ['0', '-0', '-1', '0E-1000'])
def test_nonpositive_not_eligible(registered, value):
    result = select(registered, save(registered, creatinine('bad', value),
        creatinine('b', at=AT + timedelta(hours=1))))
    assert issues(result) == [('bad', 'invalid_value'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('value', [True, False, '1.2 mg/dL', '1.2', None])
def test_nonquantity_values(registered, value):
    content = ClinicalValue(status='missing', reason='missing') if value is None else ClinicalValue(status='known', value=value)
    bad = replace(creatinine('bad'), value=content)
    result = select(registered, save(registered, bad, creatinine('b', at=AT + timedelta(hours=1))))
    assert issues(result) == [('bad', 'invalid_value'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity', True])
def test_malformed_quantity_rejected_by_domain(value):
    with pytest.raises(ValidationError):
        Quantity(value=value, unit=Unit(raw='mg/dL', status='assessed', system='UCUM', code='mg/dL'))


@pytest.mark.parametrize('case,code', [
    ('event', 'invalid_or_missing_sample_time'), ('precision', 'invalid_or_missing_sample_time'),
    ('time_uncertainty', 'invalid_or_missing_sample_time'), ('conflict', 'unresolved_conflict'),
    ('unverified', 'unverified_input'), ('binding', 'unverified_input'),
    ('namespace', 'unacceptable_provenance'), ('version', 'unacceptable_provenance'),
    ('channel', 'unacceptable_provenance'), ('lineage', 'unacceptable_provenance'),
    ('limitations', 'unacceptable_provenance'), ('upstream', 'unacceptable_provenance'),
    ('uncertainty', 'unacceptable_provenance'),
    ('recorded', 'invalid_result_timing'), ('retrieved', 'invalid_result_timing'),
    ('processed', 'invalid_result_timing'), ('before_sample', 'invalid_result_timing'),
    ('before_recorded', 'invalid_result_timing'), ('before_retrieved', 'invalid_result_timing'),
    ('provenance_time', 'invalid_result_timing'), ('late_processing', 'source_unavailable_at_bound'),
    ('late_binding', 'source_unavailable_at_bound'),
])
def test_relevant_bad_third_blocks_two_good_samples(registered, case, code):
    item = creatinine('bad', at=AT + timedelta(hours=2))
    if case in ('event', 'recorded', 'retrieved', 'processed'):
        item = replace(item, time=replace(item.time, **{case: None}))
    elif case == 'precision':
        item = replace(item, time=replace(item.time, precision='day'))
    elif case == 'time_uncertainty':
        item = replace(item, time=replace(item.time, uncertainty='unknown collection time'))
    elif case == 'conflict':
        item = replace(item, conflict='unresolved')
    elif case == 'unverified':
        item = replace(item, verification='unverified')
    elif case == 'binding':
        item = replace(item, binding=replace(item.binding, verification=replace(item.binding.verification,
            status='unresolved', ambiguity='synthetic ambiguity')))
    elif case in ('namespace', 'version', 'channel'):
        update = {'namespace': 'another-source'} if case == 'namespace' else {'version': None} if case == 'version' else {'channel': 'clinician'}
        item = replace(item, provenance=replace(item.provenance, source=replace(item.provenance.source, **update)))
    elif case in ('lineage', 'limitations', 'upstream'):
        update = {'lineage': 'unknown', 'limitations': ('unknown',)} if case == 'lineage' else {'limitations': ('limited',)} if case == 'limitations' else {
            'upstream': (LineageEdge(target=creatinine('a').reference, relationship='copied_from'),)}
        item = replace(item, provenance=replace(item.provenance, **update))
    elif case == 'uncertainty':
        item = replace(item, uncertainty=('uncertain specimen',))
    elif case == 'provenance_time':
        item = replace(item, provenance=replace(item.provenance, recorded_at=item.time.recorded + timedelta(microseconds=1)))
    elif case.startswith('before_'):
        field = {'before_sample': 'recorded', 'before_recorded': 'retrieved', 'before_retrieved': 'processed'}[case]
        item = replace(item, time=replace(item.time, **{field: item.time.event - timedelta(microseconds=1)}))
        if case == 'before_sample':
            # Isolate chronology: provenance must otherwise agree with recording.
            item = replace(item, provenance=replace(item.provenance, recorded_at=item.time.recorded))
    elif case == 'late_processing':
        item = replace(item, time=replace(item.time, processed=POLICY.available_at + timedelta(microseconds=1)))
    else:
        item = replace(item, binding=replace(item.binding, verification=replace(item.binding.verification,
            assessed_at=POLICY.available_at + timedelta(microseconds=1))))
    result = select(registered, save(registered, creatinine('a'), creatinine('b', at=AT + timedelta(hours=1)), item))
    assert issues(result) == [('bad', code)]  # eligible count is two BEFORE blocking
    assert [(e.reference.id, e.reason) for e in result.exclusions] == [('bad', code)]
    assert not result.selected and not result.successful


@pytest.mark.parametrize('origin,channel,verification,uncertainty,temporal', [
    ('observed', 'measurement', 'verified', (), 'unknown'),
    ('reported', 'external_record', 'clinician_confirmed', ('synthetic uncertainty',), 'historical'),
    ('reported', 'measurement', 'verified', (), 'current'),
])
def test_allowed_profile_and_temporal_status(registered, origin, channel, verification, uncertainty, temporal):
    a = creatinine('a')
    a = replace(a, origin=origin, verification=verification, uncertainty=uncertainty, temporal_status=temporal,
        provenance=replace(a.provenance, source=replace(a.provenance.source, channel=channel)))
    assert select(registered, save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))).successful


@pytest.mark.parametrize('origin', ['inferred', 'derived'])
def test_disallowed_origin_is_domain_error(origin):
    with pytest.raises(ValidationError):
        replace(creatinine('bad'), origin=origin)


@pytest.mark.parametrize('boundary,us,success', [('start', -1, False), ('start', 0, True),
    ('start', 1, True), ('end', -1, True), ('end', 0, False), ('end', 1, False)])
def test_half_open_microsecond_boundaries(registered, boundary, us, success):
    at = (POLICY.window_start if boundary == 'start' else POLICY.window_end) + timedelta(microseconds=us)
    candidate = creatinine('edge', at=at)
    result = select(registered, save(registered, candidate, creatinine('middle', at=AT + timedelta(hours=1))))
    assert result.successful is success
    if not success:
        assert [(e.reference.id, e.reason) for e in result.exclusions] == [('edge', 'outside_sample_window')]
        assert issues(result) == [(None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('us,success', [(-1, True), (0, True), (1, False)])
def test_inclusive_availability_offsets(registered, us, success):
    available = (POLICY.available_at + timedelta(microseconds=us)).astimezone(timezone.utc)
    a = creatinine('a')
    a = replace(a, time=replace(a.time, recorded=available, retrieved=available, processed=available),
        provenance=replace(a.provenance, recorded_at=available.astimezone(AT.tzinfo)),
        binding=replace(a.binding, verification=replace(a.binding.verification, assessed_at=available)))
    cutoff = save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))
    result = select(registered, cutoff)
    assert result.successful is success
    if not success:
        assert issues(result) == [('a', 'source_unavailable_at_bound'), (None, 'insufficient_eligible_inputs')]


def test_result_entry_does_not_replace_sample_time_or_order(registered):
    a, b = creatinine('a'), creatinine('b', at=AT + timedelta(hours=1))
    entered = AT + timedelta(hours=2)
    a = replace(a, time=replace(a.time, recorded=entered, retrieved=entered, processed=entered),
        provenance=replace(a.provenance, recorded_at=entered))
    result = select(registered, save(registered, b, a))
    assert tuple(f.id for f in result.selected) == ('a', 'b')
    assert compare_recorded_creatinine(result).earlier_sample_time == AT
    missing = replace(a, time=replace(a.time, event=None))
    with pytest.raises(ValidationError):
        compare_recorded_creatinine(result.model_copy(update={'selected': (missing, b)}))


@pytest.mark.parametrize('same_offset', [False, True])
def test_equal_sample_instants_block(registered, same_offset):
    at = AT if same_offset else AT.astimezone(timezone.utc)
    result = select(registered, save(registered, creatinine('a'), creatinine('b', at=at)))
    assert issues(result) == [(None, 'invalid_measurement_order')] and not result.selected


def test_dst_fold_actual_instant_order(registered):
    zone = ZoneInfo('America/New_York')
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    policy = CreatinineTrendSelectionPolicy(window_start=datetime(2026, 11, 1, 0, tzinfo=zone),
        window_end=datetime(2026, 11, 1, 3, tzinfo=zone), available_at=datetime(2026, 11, 1, 4, tzinfo=zone))
    # Result is later by instant even though its local wall time is earlier.
    a = creatinine('a', at=first)
    a = replace(a, time=replace(a.time, recorded=later, retrieved=later, processed=later),
        provenance=replace(a.provenance, recorded_at=later))
    b = creatinine('b', at=later)
    result = select(registered, save(registered, b, a), policy)
    assert tuple(f.id for f in result.selected) == ('a', 'b')
    comparison = compare_recorded_creatinine(result)
    assert comparison.earlier_sample_time.isoformat() == first.isoformat()
    assert comparison.later_sample_time.isoformat() == later.isoformat()


@pytest.mark.parametrize('year,offset', [(1, 14), (9999, -14)])
def test_extreme_instants_without_datetime_utc_overflow(registered, year, offset):
    start = datetime(year, 1, 1, tzinfo=timezone(timedelta(hours=offset))) if year == 1 else datetime(
        year, 12, 31, 23, 59, 55, tzinfo=timezone(timedelta(hours=offset)))
    policy = CreatinineTrendSelectionPolicy(window_start=start, window_end=start + timedelta(seconds=3),
        available_at=start + timedelta(seconds=4))
    result = select(registered, save(registered, creatinine('b', at=start + timedelta(seconds=1)),
        creatinine('a', at=start)), policy)
    assert tuple(f.id for f in result.selected) == ('a', 'b')


@pytest.mark.parametrize('ineligible', ['unit', 'conflict', 'concept', 'window'])
def test_multicorrection_terminal_before_filter_and_old_prefix(registered, ineligible):
    a, b = creatinine('a', label='z'), creatinine('b', at=AT + timedelta(hours=1))
    old = save(registered, a, b)
    a2 = revision(a, 'a', value=replace(a.value, value=replace(a.value.value, value=Decimal('1.300'))))
    a3 = revision(a2, '00')
    if ineligible == 'unit':
        a3 = changed_unit(a3, raw='µmol/L', code='umol/L')
    elif ineligible == 'conflict':
        a3 = replace(a3, conflict='unresolved')
    elif ineligible == 'concept':
        a3 = replace(a3, concept_id='another-concept')
    else:
        a3 = replace(a3, time=replace(a3.time, event=POLICY.window_end))
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        middle = repo.capture_cutoff()
        repo.append_revision(a3, target=TARGET)
        current = repo.capture_cutoff()
    assert select(registered, old).selected == (a, b)
    assert select(registered, middle).selected == (a2, b)
    result = select(registered, current)
    assert result.selected == () and issues(result)[-1] == (None, 'insufficient_eligible_inputs')
    assert [e.reference for e in result.exclusions] == [a3.reference]
    assert compare_recorded_creatinine(select(registered, middle)).earlier_reference == a2.reference


def test_one_revision_family_cannot_supply_two_measurements(registered):
    a = creatinine('a')
    save(registered, a)
    with transaction(registered) as repo:
        repo.append_revision(revision(a, '2'), target=TARGET)
        cutoff = repo.capture_cutoff()
    result = select(registered, cutoff)
    assert issues(result) == [(None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('bad', [False, True])
def test_duplicate_sample_blocks_independently_and_orders_issues(registered, bad):
    a = creatinine('a', sample='shared')
    duplicate = creatinine('duplicate', at=AT + timedelta(hours=1), sample='shared')
    if bad:
        duplicate = replace(duplicate, conflict='unresolved')
    result = select(registered, save(registered, duplicate, a))
    expected = ([('duplicate', 'unresolved_conflict')] if bad else []) + [
        ('duplicate', 'duplicate_sample_measurement'), ('a', 'duplicate_sample_measurement')]
    if bad:
        expected.append((None, 'insufficient_eligible_inputs'))
    assert issues(result) == expected and result.selected == ()
    assert compare_recorded_creatinine(result) == result.issues[0]


def test_duplicate_bad_third_does_not_disappear_after_eligibility(registered):
    a, b = creatinine('a'), creatinine('b', at=AT + timedelta(hours=1))
    bad = changed_unit(creatinine('bad', sample='sample-a', at=AT + timedelta(hours=2)), raw='mg/dl')
    result = select(registered, save(registered, a, b, bad))
    assert issues(result) == [('a', 'duplicate_sample_measurement'), ('bad', 'unsupported_unit'),
        ('bad', 'duplicate_sample_measurement')]


def test_three_eligible_with_duplicate_still_reports_ambiguity(registered):
    result = select(registered, save(registered, creatinine('a', sample='same'),
        creatinine('b', at=AT + timedelta(hours=1), sample='same'),
        creatinine('c', at=AT + timedelta(hours=2))))
    assert issues(result) == [('a', 'duplicate_sample_measurement'), ('b', 'duplicate_sample_measurement'),
        (None, 'ambiguous_eligible_inputs')]


def test_irrelevant_duplicates_and_other_fact_are_benign(registered):
    outside = creatinine('outside', at=POLICY.window_end, sample='sample-a')
    other = replace(creatinine('other', sample='sample-a'), concept_id='other', conflict='unresolved')
    result = select(registered, save(registered, other, creatinine('b', at=AT + timedelta(hours=1)),
        outside, fact('medication_order'), creatinine('a')))
    assert result.successful
    assert [(e.reference.id, e.reason) for e in result.exclusions] == [
        ('other', 'unrelated_concept'), ('outside', 'outside_sample_window'), ('medication_order-1', 'unrelated_fact')]


@pytest.mark.parametrize('other', [replace(TARGET, encounter_id='synthetic-e2'),
    replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3')])
def test_scope_isolation_with_populated_foreign_samples(registered, other):
    foreign = creatinine('foreign', sample='sample-a', at=AT + timedelta(hours=1))
    foreign = replace(foreign, binding=replace(foreign.binding, target=other))
    cutoff = save(registered, creatinine('a'), foreign)
    assert issues(select(registered, cutoff)) == [(None, 'insufficient_eligible_inputs')]
    assert issues(select(registered, cutoff, target=other)) == [(None, 'insufficient_eligible_inputs')]
    cutoff = save(registered, creatinine('b', at=AT + timedelta(hours=2)))
    result = select(registered, cutoff)
    assert result.successful and not result.exclusions


@pytest.mark.parametrize('order', list(permutations(('a', 'b', 'irrelevant'))))
def test_insertion_order_does_not_change_pair(registered, order):
    records = {'a': creatinine('a', label='z'), 'b': creatinine('b', at=AT + timedelta(hours=1), label='a'),
        'irrelevant': replace(creatinine('other'), concept_id='other')}
    result = select(registered, save(registered, *(records[key] for key in order)))
    assert result.selected == (records['a'], records['b'])


def test_terminal_ingestion_order_exclusions_after_correction_and_reopen(registered):
    a = replace(creatinine('a'), conflict='unresolved')
    missing = replace(creatinine('z'), time=replace(creatinine('z').time, event=None))
    save(registered, a, missing)
    a2 = revision(a, '2', verification='unverified')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        cutoff = repo.capture_cutoff()
    result = select(registered, cutoff)
    assert [(e.reference.id, e.reason) for e in result.exclusions] == [
        ('z', 'invalid_or_missing_sample_time'), ('a', 'unresolved_conflict')]
    assert issues(result) == [('z', 'invalid_or_missing_sample_time'), ('a', 'unresolved_conflict'),
        (None, 'insufficient_eligible_inputs')]
    registered.dispose()
    reopened = create_database(registered.url.database)
    try:
        assert select(reopened, cutoff).model_dump_json() == result.model_dump_json()
    finally:
        reopened.dispose()


@pytest.mark.parametrize('case', ['reverse', 'same_exact', 'same_family', 'same_sample', 'scope',
    'invalid_value', 'naive', 'inferred', 'blocking_exclusion', 'excluded_selected', 'cutoff'])
def test_forged_selection_revalidated(registered, case):
    result = pair(registered)
    a, b = result.selected
    if case == 'reverse':
        forged = result.model_copy(update={'selected': (b, a)})
    elif case in ('blocking_exclusion', 'excluded_selected'):
        exclusion = CreatinineTrendExclusion(reference=a.reference,
            reason='unsupported_unit' if case == 'blocking_exclusion' else 'unrelated_concept')
        forged = result.model_copy(update={'exclusions': (exclusion,)})
    elif case == 'cutoff':
        forged = result.model_copy(update={'cutoff': result.cutoff.model_copy(update={'fact_watermark': -1})})
    else:
        if case == 'same_exact':
            b = a
        elif case == 'same_family':
            b = replace(b, id=a.id, revision='another')
        elif case == 'same_sample':
            b = replace(b, provenance=replace(b.provenance, source=a.provenance.source))
        elif case == 'scope':
            b = replace(b, binding=replace(b.binding, target=replace(TARGET, encounter_id='synthetic-e2')))
        elif case == 'invalid_value':
            b = b.model_copy(update={'value': b.value.model_copy(update={
                'value': b.value.value.model_copy(update={'value': Decimal('NaN')})})})
        elif case == 'naive':
            b = b.model_copy(update={'time': b.time.model_copy(update={'event': AT.replace(tzinfo=None)})})
        else:
            b = b.model_copy(update={'origin': 'inferred'})
        forged = result.model_copy(update={'selected': (a, b)})
    with pytest.raises(ValidationError):
        compare_recorded_creatinine(forged)


@pytest.mark.parametrize('update', [{'direction': 'decrease'}, {'earlier_value': Decimal('0')},
    {'later_value': Decimal('NaN')}, {'unit': 'µmol/L'}, {'absolute_delta': '0.3'},
    {'percentage_change': '25'}, {'diagnosis': 'anything'}, {'later_sample_time': AT},
    {'earlier_value': True}])
def test_comparison_rejects_invalid_extra_content(registered, update):
    comparison = compare_recorded_creatinine(pair(registered))
    with pytest.raises(ValidationError):
        replace(comparison, **update)


@pytest.mark.parametrize('path', ['policy', 'quantity', 'unit', 'source', 'binding', 'time', 'reference', 'comparison', 'cutoff'])
def test_nested_contracts_immutable(registered, path):
    selection = pair(registered)
    before = selection.model_dump_json()
    comparison = compare_recorded_creatinine(selection)
    a = selection.selected[0]
    target, field, value = {
        'policy': (selection.policy, 'version', '2'), 'quantity': (a.value.value, 'value', Decimal('5')),
        'unit': (a.value.value.unit, 'raw', 'other'), 'source': (a.provenance.source, 'identifier', 'other'),
        'binding': (a.binding.target, 'patient_id', 'other'), 'time': (a.time, 'event', AT),
        'reference': (comparison.earlier_reference, 'version', '2'),
        'comparison': (comparison, 'direction', 'decrease'), 'cutoff': (selection.cutoff, 'fact_watermark', 0),
    }[path]
    with pytest.raises(ValidationError):
        setattr(target, field, value)
    assert selection.model_dump_json() == before


@pytest.mark.parametrize('update', [{'concept_id': 'other'}, {'unit': 'mg/L'}, {'version': '2'},
    {'window_end': AT}, {'available_at': AT}, {'window_start': AT.replace(tzinfo=None)}])
def test_policy_errors_are_exceptions(update):
    with pytest.raises(ValidationError):
        replace(POLICY, **update)


def test_cutoff_and_scope_errors_stay_exceptions(registered):
    cutoff = save(registered, creatinine('a'))
    with pytest.raises(ScopeMismatch):
        select(registered, replace(cutoff, repository_id='00000000-0000-0000-0000-000000000001'))
    with pytest.raises(PersistenceInputError):
        select(registered, replace(cutoff, fact_watermark=cutoff.fact_watermark + 1))
    with pytest.raises(UnsupportedOperation):
        select(registered, cutoff, target=replace(TARGET, encounter_id=None, longitudinal_context_id='long'))


@pytest.mark.parametrize('damage', ['empty', 'nonfinite', 'inferred', 'unrelated'])
def test_visible_corruption_fails_explicitly(registered, damage):
    a = creatinine('a')
    if damage == 'unrelated':
        a = replace(a, concept_id='other')
    cutoff = save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))
    payload = '{}' if damage in ('empty', 'unrelated') else canonical_payload(a).replace(
        '"1.200"', '"NaN"') if damage == 'nonfinite' else canonical_payload(a).replace('"reported"', '"inferred"')
    with registered.begin() as conn:
        conn.execute(text('UPDATE fact_revision SET payload=:p WHERE fact_id=:id'), {'p': payload, 'id': 'a'})
    with pytest.raises(StorageIntegrityError):
        select(registered, cutoff)


def test_future_corrupt_revision_cannot_influence_original_cutoff(registered):
    a = creatinine('a')
    cutoff = save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))
    before = select(registered, cutoff)
    with transaction(registered) as repo:
        repo.append_revision(revision(a, '2'), target=TARGET)
        current = repo.capture_cutoff()
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='{}' WHERE fact_id='a' AND revision='2'"))
    assert select(registered, cutoff) == before
    with pytest.raises(StorageIntegrityError):
        select(registered, current)


def test_availability_does_not_make_future_insert_visible(registered):
    old = save(registered, creatinine('a'))
    current = save(registered, creatinine('b', at=AT + timedelta(hours=1)))
    assert issues(select(registered, old)) == [(None, 'insufficient_eligible_inputs')]
    assert select(registered, current).successful
    late = replace(POLICY, available_at=POLICY.available_at + timedelta(days=1))
    assert issues(select(registered, old, late)) == [(None, 'insufficient_eligible_inputs')]


def test_readonly_purity_and_exact_reopen(registered):
    cutoff = save(registered, creatinine('b', '1.4000', AT + timedelta(hours=1)), creatinine('a'))
    with transaction(registered) as repo:
        retained = repo.list_history(target=TARGET, cutoff=cutoff)
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().split()[0].upper())
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        result = select(registered, cutoff)
        assert select(registered, cutoff).model_dump_json() == result.model_dump_json()
        statements_before_comparison = len(statements)
        comparison = compare_recorded_creatinine(result)
        assert len(statements) == statements_before_comparison
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    assert not {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'} & set(statements)
    assert CreatinineTrendSelectionResult.model_validate_json(result.model_dump_json()) == result
    registered.dispose()
    reopened = create_database(registered.url.database)
    try:
        replay = select(reopened, cutoff)
        assert replay.model_dump_json() == result.model_dump_json()
        assert compare_recorded_creatinine(replay).model_dump_json() == comparison.model_dump_json()
        with transaction(reopened) as repo:
            assert repo.list_history(target=TARGET, cutoff=cutoff) == retained
            assert repo.capture_cutoff().fact_watermark == cutoff.fact_watermark
    finally:
        reopened.dispose()


@pytest.mark.parametrize('case,expected', [('unit_before_timing', 'unsupported_unit'),
    ('value_before_unit', 'invalid_value'), ('provenance_before_value', 'unacceptable_provenance'),
    ('timing_before_availability', 'invalid_result_timing')])
def test_first_applicable_reason_precedence(registered, case, expected):
    item = creatinine('bad')
    item = replace(item, time=replace(item.time, recorded=None,
        processed=POLICY.available_at + timedelta(microseconds=1)))
    if case != 'timing_before_availability':
        item = changed_unit(item, raw='mg/dl')
    if case in ('value_before_unit', 'provenance_before_value'):
        item = replace(item, value=replace(item.value, value=replace(item.value.value, value=Decimal('0'))))
    if case == 'provenance_before_value':
        item = replace(item, provenance=replace(item.provenance, limitations=('unknown specimen',)))
    result = select(registered, save(registered, item, creatinine('b', at=AT + timedelta(hours=1))))
    assert issues(result) == [('bad', expected), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('case', ['same_family', 'non_observation', 'equal_offset_instant', 'reversed'])
def test_direct_comparison_rejects_forged_identity_or_time(registered, case):
    comparison = compare_recorded_creatinine(pair(registered))
    if case == 'same_family':
        update = {'later_reference': replace(comparison.earlier_reference, version='another')}
    elif case == 'non_observation':
        update = {'later_reference': replace(comparison.later_reference, kind='inference')}
    elif case == 'equal_offset_instant':
        update = {'later_sample_time': comparison.earlier_sample_time.astimezone(timezone.utc)}
    else:
        update = {'earlier_sample_time': comparison.later_sample_time,
                  'later_sample_time': comparison.earlier_sample_time}
    with pytest.raises(ValidationError):
        RecordedCreatinineComparison.model_validate(comparison.model_copy(update=update))


def test_invalid_policy_fails_before_repository_access():
    class UnreadableRepository:
        def list_bounded_history(self, **kwargs):
            pytest.fail('invalid policy must not reach storage')
    forged = POLICY.model_copy(update={'unit': 'µmol/L'})
    with pytest.raises(ValidationError):
        select_creatinine_observations(UnreadableRepository(), target=TARGET, cutoff=None, policy=forged)


def test_precise_duplicate_key_survives_version_and_channel_mismatch(registered):
    a = creatinine('a', sample='same')
    b = creatinine('b', at=AT + timedelta(hours=1), sample='same')
    b = replace(b, provenance=replace(b.provenance, source=replace(b.provenance.source,
        version='2', channel='clinician')))
    result = select(registered, save(registered, a, b))
    assert issues(result) == [('a', 'duplicate_sample_measurement'), ('b', 'unacceptable_provenance'),
        ('b', 'duplicate_sample_measurement'), (None, 'insufficient_eligible_inputs')]


def test_empty_sample_identity_rejected_by_domain():
    with pytest.raises(ValidationError):
        creatinine('a', sample='   ')


def test_imprecise_sample_blocks_but_does_not_fabricate_duplicate_scope(registered):
    a = creatinine('a', sample='same')
    b = creatinine('b', at=AT + timedelta(hours=1), sample='same')
    b = replace(b, time=replace(b.time, uncertainty='unknown collection instant'))
    result = select(registered, save(registered, a, b))
    assert issues(result) == [('b', 'invalid_or_missing_sample_time'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('case,code', [('unverified', 'unverified_input'),
    ('provenance', 'unacceptable_provenance'), ('availability', 'source_unavailable_at_bound')])
def test_review_terminal_ineligible_does_not_resurrect(registered, case, code):
    a = creatinine('a')
    b = creatinine('b', at=AT + timedelta(hours=1))
    old = save(registered, a, b)
    a2 = revision(a, '2')
    if case == 'unverified':
        a2 = replace(a2, verification='unverified')
    elif case == 'provenance':
        a2 = replace(a2, provenance=replace(a2.provenance, limitations=('unknown source',)))
    else:
        a2 = replace(a2, time=replace(a2.time, processed=POLICY.available_at + timedelta(microseconds=1)))
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        new = repo.capture_cutoff()
    assert select(registered, old).selected == (a, b)
    result = select(registered, new)
    assert [(i.reference, i.code) for i in result.issues] == [
        (a2.reference, code), (None, 'insufficient_eligible_inputs')]
    assert result.selected == ()


def test_review_watermark_not_ingestion_or_capture_clock(registered, monkeypatch):
    import app.persistence.repository as repository_module
    monkeypatch.setattr(repository_module, '_now', lambda: AT)
    a, b = creatinine('a'), creatinine('b', at=AT + timedelta(hours=1))
    first = save(registered, a, b)
    a2, a3 = revision(a, '2'), None
    a3 = revision(a2, '3')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        second = repo.capture_cutoff()
        repo.append_revision(a3, target=TARGET)
        third = repo.capture_cutoff()
        history = repo.list_history(target=TARGET, cutoff=third)
    assert {record.ingestion.ingested_at for record in history.records} == {AT}
    for cutoff, expected in ((first, a), (second, a2), (third, a3)):
        for delta in (-1, 0, 1):
            adjusted = replace(cutoff, captured_at=AT + timedelta(microseconds=delta))
            assert select(registered, adjusted).selected == (expected, b)


@pytest.mark.parametrize('concept', ['Synthetic-serum-creatinine', 'synthetic-serum-creatinine-v1',
    'serum-creatinine', 'urine-creatinine', 'creatinine', 'synthetic- serum-creatinine'])
def test_review_concept_aliases_are_unrelated(registered, concept):
    a = replace(creatinine('a'), concept_id=concept)
    result = select(registered, save(registered, a, creatinine('b', at=AT + timedelta(hours=1))))
    assert [(e.reference.id, e.reason) for e in result.exclusions] == [('a', 'unrelated_concept')]
    assert issues(result) == [(None, 'insufficient_eligible_inputs')]


def test_review_concept_whitespace_is_existing_domain_parsing(registered):
    # Text strips whitespace before persistence; the selector never sees the raw spelling.
    a = replace(creatinine('a'), concept_id='  synthetic-serum-creatinine  ')
    assert a.concept_id == 'synthetic-serum-creatinine'
    assert select(registered, save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))).successful


@pytest.mark.parametrize('field,value', [('concept_id', None), ('concept_id', ''),
    ('conflict', 'malformed'), ('provenance', None), ('value', {'status': 'known', 'value': {'value': '1'}})])
def test_review_malformed_domain_data_is_not_ordinary_exclusion(field, value):
    with pytest.raises(ValidationError):
        replace(creatinine('a'), **{field: value})


@pytest.mark.parametrize('raw', ['MG/DL', 'mg / dL', 'mgdl', 'umol/L', 'mmol/L'])
def test_review_other_unit_spellings_rejected(registered, raw):
    result = select(registered, save(registered, changed_unit(creatinine('a'), raw=raw),
        creatinine('b', at=AT + timedelta(hours=1))))
    assert issues(result) == [('a', 'unsupported_unit'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('damage', ['missing_link', 'wrong_predecessor', 'payload_predecessor', 'identity'])
def test_review_corrupt_visible_revision_prefix_raises(registered, damage):
    import json
    a = creatinine('a')
    old = save(registered, a, creatinine('b', at=AT + timedelta(hours=1)))
    a2 = revision(a, '2')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        current = repo.capture_cutoff()
    with registered.begin() as conn:
        if damage == 'missing_link':
            conn.execute(text('DELETE FROM revision_link'))
        elif damage == 'wrong_predecessor':
            conn.execute(text('UPDATE revision_link SET predecessor_sequence=2 WHERE successor_sequence=3'))
        elif damage == 'identity':
            conn.execute(text("UPDATE fact_revision SET revision='different' WHERE ingestion_sequence=3"))
        else:
            payload = json.loads(canonical_payload(a2))
            payload['supersedes']['version'] = 'absent'
            conn.execute(text('UPDATE fact_revision SET payload=:p WHERE ingestion_sequence=3'),
                {'p': json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)})
    assert select(registered, old).selected[0].reference == a.reference
    with pytest.raises(StorageIntegrityError):
        select(registered, current)


def test_review_duplicate_exact_revision_cannot_enter_storage(registered):
    from sqlalchemy.exc import IntegrityError
    cutoff = save(registered, creatinine('a'), creatinine('b', at=AT + timedelta(hours=1)))
    with pytest.raises(IntegrityError), registered.begin() as conn:
        conn.execute(text('''INSERT INTO fact_revision
            (kind, fact_id, revision, patient_id, encounter_id, payload_version, payload, ingested_at)
            SELECT kind, fact_id, revision, patient_id, encounter_id, payload_version, payload, ingested_at
            FROM fact_revision WHERE fact_id='a' '''))
    assert select(registered, cutoff).successful


@pytest.mark.parametrize('case', ['one', 'three', 'concept', 'unit', 'tie'])
def test_review_more_forged_selection_attacks(registered, case):
    result = pair(registered)
    a, b = result.selected
    if case == 'one':
        selected = (a,)
    elif case == 'three':
        selected = (a, b, creatinine('c', at=AT + timedelta(hours=2)))
    elif case == 'concept':
        selected = (a, replace(b, concept_id='creatinine'))
    elif case == 'unit':
        selected = (a, changed_unit(b, raw='mgdl'))
    else:
        selected = (a, replace(b, time=replace(b.time, event=a.time.event)))
    with pytest.raises(ValidationError):
        compare_recorded_creatinine(result.model_copy(update={'selected': selected}))


@pytest.mark.parametrize('target_name', ['result', 'issue', 'exclusion'])
def test_review_remaining_public_contracts_frozen(registered, target_name):
    result = select(registered, save(registered, changed_unit(creatinine('a'), raw='mgdl')))
    target, field, value = {'result': (result, 'issues', ()),
        'issue': (result.issues[0], 'code', 'invalid_value'),
        'exclusion': (result.exclusions[0], 'reason', 'unrelated_concept')}[target_name]
    with pytest.raises(ValidationError):
        setattr(target, field, value)


@pytest.mark.parametrize('a,b,direction', [('1.0', '1.2', 'increase'), ('1.00', '1.0', 'unchanged'),
    ('1.000', '1.000', 'unchanged'), ('1.' + '0' * 80 + '1', '1.' + '0' * 81, 'decrease')])
def test_review_exact_decimal_equality_and_subcontext_precision(registered, a, b, direction):
    result = compare_recorded_creatinine(select(registered, save(registered, creatinine('a', a),
        creatinine('b', b, AT + timedelta(microseconds=1)))))
    assert result.direction == direction
    assert str(result.earlier_value) == a and str(result.later_value) == b


def test_review_terminal_ineligibility_and_old_duplicate_sample(registered):
    a = creatinine('a', sample='same')
    duplicate = creatinine('duplicate', '7.00', AT + timedelta(hours=1), sample='same')
    old = save(registered, a, duplicate)
    with transaction(registered) as repo:
        a2 = revision(a, '2', verification='unverified')
        repo.append_revision(a2, target=TARGET)
        current = repo.capture_cutoff()
    assert issues(select(registered, old)) == [('a', 'duplicate_sample_measurement'),
        ('duplicate', 'duplicate_sample_measurement')]
    assert issues(select(registered, current)) == [('duplicate', 'duplicate_sample_measurement'),
        ('a', 'unverified_input'), ('a', 'duplicate_sample_measurement'), (None, 'insufficient_eligible_inputs')]


@pytest.mark.parametrize('reverse', [False, True])
def test_review_many_candidates_and_exclusion_order(registered, reverse):
    good = [creatinine(str(i), at=AT + timedelta(minutes=i)) for i in range(12)]
    bad = [replace(creatinine('bad-' + str(i)), verification='unverified') for i in range(12)]
    records = good + bad
    if reverse:
        records.reverse()
    result = select(registered, save(registered, *records))
    expected_bad = [f.id for f in records if f.verification == 'unverified']
    assert [e.reference.id for e in result.exclusions] == expected_bad
    assert issues(result) == [(id, 'unverified_input') for id in expected_bad] + [(None, 'ambiguous_eligible_inputs')]
    assert not result.selected


def test_review_hash_seed_does_not_change_canonical_results(registered):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    cutoff = save(registered, creatinine('z', sample='same'),
        replace(creatinine('a', sample='same'), verification='unverified'),
        creatinine('b', at=AT + timedelta(hours=1)))
    expected = select(registered, cutoff).model_dump_json()
    script = '''import sys
from app.persistence.database import create_database
from app.persistence.metadata import RepositoryCutoff
from test_creatinine_trend import select
engine = create_database(sys.argv[1])
try:
    print(select(engine, RepositoryCutoff.model_validate_json(sys.argv[2])).model_dump_json())
finally:
    engine.dispose()
'''
    for seed in ('1', '777'):
        result = subprocess.run([sys.executable, '-c', script, str(registered.url.database), cutoff.model_dump_json()],
            cwd=root, env={**os.environ, 'PYTHONHASHSEED': seed, 'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONPATH': os.pathsep.join((str(root / 'backend'), str(root / 'tests')))},
            capture_output=True, text=True, check=True)
        assert result.stdout.strip() == expected
