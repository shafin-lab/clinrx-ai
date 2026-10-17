"""Synthetic Phase B: independent grammar oracles and unchanged durable lineage."""
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text

from app.execution.creatinine_trend import (
    RECORDED_CREATININE_TREND_METHOD, CreatinineTrendSelectionIssue,
    build_creatinine_trend_inference, compare_recorded_creatinine,
)
from app.models.clinical.common import LineageEdge, Reference
from app.models.clinical.facts import ClinicalInference
from app.persistence.database import create_database
from app.persistence.errors import QueryLimitExceeded, RecordConflict, RecordNotFound, StorageIntegrityError
from app.persistence.history import FactIdentity
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import PatientRepository, transaction
from test_persistence import AT, TARGET, database, registered, replace
from test_revision_chains import revision
from test_creatinine_trend import POLICY, changed_unit, creatinine, save, select

EXECUTED = POLICY.available_at


def selected_pair(engine, earlier='1.00', later='1.20'):
    a = creatinine('a', earlier, label='z')
    b = creatinine('b', later, (AT + timedelta(hours=1)).astimezone(timezone.utc), label='0')
    return select(engine, save(engine, b, a)), (a, b)


def build(selection, comparison=None, **changes):
    return build_creatinine_trend_inference(selection=selection,
        comparison=compare_recorded_creatinine(selection) if comparison is None else comparison,
        inference_id=changes.pop('inference_id', 'creatinine-i1'),
        executed_at=changes.pop('executed_at', EXECUTED), **changes)


def persist(engine, inference):
    with transaction(engine) as repo:
        stored = repo.append_fact(inference, target=TARGET)
    with transaction(engine) as repo:
        cutoff = repo.capture_cutoff()
    return stored, cutoff


def resolve(engine, reference, cutoff, limits=None):
    with transaction(engine) as repo:
        return repo.resolve_lineage(reference, target=TARGET, cutoff=cutoff,
            limits=LineageLimits() if limits is None else limits)


def assert_exact_graph(graph, inference, earlier, later):
    expected_inputs = (earlier.reference, later.reference)
    assert graph.reference == inference.reference and graph.target == TARGET
    assert graph.coverage == 'complete_for_declared_visible_graph'
    assert graph.unresolved == graph.associations == graph.confirmations == ()
    assert [(d.owner, d.ordinal, d.source, d.basis_ordinal) for d in graph.dependencies] == [
        (inference.reference, 0, earlier.reference, None),
        (inference.reference, 1, later.reference, None)]
    assert [(a.owner, a.ordinal, a.edge.target, a.edge.relationship, a.edge.basis, a.edge.rationale)
            for a in graph.assertions] == [
        (inference.reference, 0, earlier.reference, 'derived_from', (), None),
        (inference.reference, 1, later.reference, 'derived_from', (), None)]
    assert {n.stored.fact.reference for n in graph.nodes} == {*expected_inputs, inference.reference}
    assert all(n.roles == ('evidence',) for n in graph.nodes)
    assert [n.stored.ingestion.ingestion_sequence for n in graph.nodes] == sorted(
        n.stored.ingestion.ingestion_sequence for n in graph.nodes)
    assert dict(graph.ancestry) == {earlier.reference: frozenset((earlier.reference,)),
        later.reference: frozenset((later.reference,)),
        inference.reference: frozenset((*expected_inputs, inference.reference))}
    assert graph.support_relationship(*expected_inputs) == 'unknown'
    assert graph.support_relationship(inference.reference, earlier.reference) == 'dependent'
    disclosures = {p.reference: p for p in graph.provenance}
    assert disclosures[inference.reference].lineage == 'complete'
    assert disclosures[inference.reference].limitations == (
        'Synthetic evaluation only; no clinical validity or source-authenticity claim.',)
    assert disclosures[earlier.reference].limitations == disclosures[later.reference].limitations == ()


@pytest.mark.parametrize('a,b,statement', [
    ('1.0', '1.20', 'Recorded serum creatinine increased from 1.0 mg/dL to 1.20 mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.'),
    ('1.20', '1.0', 'Recorded serum creatinine decreased from 1.20 mg/dL to 1.0 mg/dL between the selected samples. Synthetic evaluation only; bounded historical comparison.'),
    ('1.00', '1.0', 'Recorded serum creatinine was unchanged between the selected samples (1.00 mg/dL then 1.0 mg/dL). Synthetic evaluation only; bounded historical comparison.'),
])
def test_exact_specification_grammar_and_complete_contract(registered, a, b, statement):
    selection, (earlier, later) = selected_pair(registered, a, b)
    inference = build(selection)
    assert type(inference) is ClinicalInference
    assert inference.statement == statement
    assert inference.method == Reference(kind='inference_method', id='RecordedCreatinineTrend', version='1')
    assert inference.method == RECORDED_CREATININE_TREND_METHOD
    assert inference.origin == 'inferred' and inference.verification == 'unverified'
    assert inference.conflict == inference.temporal_status == 'unknown'
    assert inference.binding == earlier.binding and inference.binding.target == TARGET
    assert inference.inputs == (earlier.reference, later.reference)
    assert [(e.relationship, e.target, e.basis, e.rationale) for e in inference.provenance.upstream] == [
        ('derived_from', earlier.reference, (), None), ('derived_from', later.reference, (), None)]
    assert inference.provenance.dependencies == (earlier.reference, later.reference)
    assert inference.target is None and inference.horizon is None
    assert inference.validation_references == ()
    assert inference.applicability == 'Synthetic serum-creatinine comparison within the selected patient/encounter and sample-time window only.'
    assert inference.validation_limitations == 'Not clinically validated; recorded values and synthetic sample identity only.'
    assert inference.uncertainty == (
        'Recorded comparison does not establish clinical significance or cause.',
        'Synthetic evaluation only; specimen identity and input authenticity are assumed.',
        'synthetic uncertainty',)
    assert inference.provenance.source.model_dump() == {'namespace': 'clinrx.synthetic',
        'identifier': 'RecordedCreatinineTrend', 'version': '1', 'channel': 'system'}
    assert inference.provenance.actor == 'RecordedCreatinineTrend/v1'
    assert inference.provenance.recorded_at == EXECUTED
    assert inference.provenance.lineage == 'complete'
    assert inference.provenance.limitations == ('Synthetic evaluation only; no clinical validity or source-authenticity claim.',)
    assert inference.time.event == inference.time.recorded == inference.time.processed == EXECUTED
    assert inference.time.retrieved is None and inference.time.effective_start is None and inference.time.effective_end is None
    assert inference.time.precision == 'instant' and inference.time.uncertainty is None
    assert ClinicalInference.model_validate_json(inference.model_dump_json()) == inference
    assert all(word not in inference.statement.lower() for word in (
        'aki', 'egfr', 'worsened', 'improved', 'abnormal', 'elevated', 'renal dysfunction',
        'significant', 'percent', '%', 'delta', 'recommendation', 'prognosis'))


@pytest.mark.parametrize('a,b', [('1E-1000', '1E+1000'), ('1.' + '0' * 100 + '1', '1.' + '0' * 101)])
def test_extreme_decimal_representation_without_arithmetic_rounding(registered, a, b):
    selection, _ = selected_pair(registered, a, b)
    inference = build(selection)
    verb = 'increased' if a == '1E-1000' else 'decreased'
    assert inference.statement == (f'Recorded serum creatinine {verb} from {a} mg/dL to {b} mg/dL '
        'between the selected samples. Synthetic evaluation only; bounded historical comparison.')
    stored, cutoff = persist(registered, inference)
    assert resolve(registered, inference.reference, cutoff).nodes[-1].stored == stored


@pytest.mark.parametrize('change', ['earlier_ref', 'later_ref', 'earlier_value', 'later_value',
    'scale', 'unit', 'earlier_time', 'later_time', 'offset', 'direction', 'reverse', 'duplicate'])
def test_forged_comparison_rejected(registered, change):
    selection, _ = selected_pair(registered)
    comparison = compare_recorded_creatinine(selection)
    changes = {
        'earlier_ref': {'earlier_reference': replace(comparison.earlier_reference, version='new')},
        'later_ref': {'later_reference': replace(comparison.later_reference, id='other')},
        'earlier_value': {'earlier_value': Decimal('1.01')},
        'later_value': {'later_value': Decimal('1.21')},
        'scale': {'earlier_value': Decimal('1.0')},
        'unit': {'unit': 'umol/L'},
        'earlier_time': {'earlier_sample_time': comparison.earlier_sample_time + timedelta(microseconds=1)},
        'later_time': {'later_sample_time': comparison.later_sample_time + timedelta(microseconds=1)},
        'offset': {'earlier_sample_time': comparison.earlier_sample_time.astimezone(timezone.utc)},
        'direction': {'direction': 'decrease'},
        'reverse': {'earlier_reference': comparison.later_reference, 'later_reference': comparison.earlier_reference,
            'earlier_sample_time': comparison.later_sample_time, 'later_sample_time': comparison.earlier_sample_time},
        'duplicate': {'later_reference': comparison.earlier_reference},
    }[change]
    with pytest.raises(ValueError):
        build(selection, comparison.model_copy(update=changes))


@pytest.mark.parametrize('case', ['one', 'three', 'reverse', 'same_family', 'same_sample', 'patient',
    'encounter', 'concept', 'unit', 'equal_instants', 'unverified', 'uncertainty'])
def test_selection_is_revalidated_independently_of_comparison(registered, case):
    selection, (a, b) = selected_pair(registered)
    comparison = compare_recorded_creatinine(selection)
    if case == 'one':
        selected = (a,)
    elif case == 'three':
        selected = (a, b, creatinine('c', at=AT + timedelta(hours=2)))
    elif case == 'reverse':
        selected = (b, a)
    else:
        if case == 'same_family':
            b = replace(b, id=a.id, revision='another')
        elif case == 'same_sample':
            b = replace(b, provenance=replace(b.provenance, source=a.provenance.source))
        elif case in ('patient', 'encounter'):
            target = replace(TARGET, **({'patient_id': 'other'} if case == 'patient' else {'encounter_id': 'other'}))
            b = replace(b, binding=replace(b.binding, target=target))
        elif case == 'concept':
            b = replace(b, concept_id='other')
        elif case == 'unit':
            b = changed_unit(b, raw='mg/dl')
        elif case == 'equal_instants':
            b = replace(b, time=replace(b.time, event=a.time.event.astimezone(timezone.utc)))
        elif case == 'unverified':
            b = replace(b, verification='unverified')
        else:
            b = replace(b, uncertainty=('unsupported interpretation',))
        selected = (a, b)
    with pytest.raises(ValidationError):
        build(selection.model_copy(update={'selected': selected}), comparison)


@pytest.mark.parametrize('count', [0, 1, 3])
def test_failed_selection_rejected_without_inference(registered, count):
    selection = select(registered, save(registered, *(creatinine(str(i), at=AT + timedelta(minutes=i))
        for i in range(count))))
    with pytest.raises(ValueError, match='successful creatinine selection'):
        build(selection)


def test_issue_cannot_stand_in_for_successful_comparison(registered):
    selection, _ = selected_pair(registered)
    with pytest.raises(ValidationError):
        build(selection, CreatinineTrendSelectionIssue(code='insufficient_eligible_inputs'))


@pytest.mark.parametrize('at', [EXECUTED - timedelta(microseconds=1), EXECUTED.replace(tzinfo=None)])
def test_invalid_execution_time_rejected(registered, at):
    selection, _ = selected_pair(registered)
    with pytest.raises(ValueError):
        build(selection, executed_at=at)


@pytest.mark.parametrize('microseconds', [0, 1])
def test_inclusive_execution_bound_preserves_offset(registered, microseconds):
    selection, _ = selected_pair(registered)
    at = (EXECUTED + timedelta(microseconds=microseconds)).astimezone(timezone(timedelta(hours=-7)))
    inference = build(selection, executed_at=at)
    assert inference.time.event.isoformat() == inference.time.recorded.isoformat() == at.isoformat()
    assert inference.time.processed.isoformat() == inference.provenance.recorded_at.isoformat() == at.isoformat()
    stored, _ = persist(registered, inference)
    assert canonical_payload(stored.fact) == canonical_payload(inference)


@pytest.mark.parametrize('empty', [False, True])
def test_permitted_input_uncertainty_deduplicated_after_required_disclosures(registered, empty):
    a, b = creatinine('a'), creatinine('b', at=AT + timedelta(hours=1))
    if empty:
        a, b = replace(a, uncertainty=()), replace(b, uncertainty=())
    inference = build(select(registered, save(registered, a, b)))
    expected = ('Recorded comparison does not establish clinical significance or cause.',
        'Synthetic evaluation only; specimen identity and input authenticity are assumed.')
    assert inference.uncertainty == expected + (() if empty else ('synthetic uncertainty',))


@pytest.mark.parametrize('earlier,later', [('1.0', '1.20'), ('1.20', '1.0'), ('1.00', '1.0')])
def test_persist_reopen_complete_exact_lineage(registered, earlier, later):
    selection, (a, b) = selected_pair(registered, earlier, later)
    comparison = compare_recorded_creatinine(selection)
    inference = build(selection, comparison)
    stored, output = persist(registered, inference)
    assert output.fact_watermark > selection.cutoff.fact_watermark
    assert output.repository_id == selection.cutoff.repository_id
    with pytest.raises(RecordNotFound):
        resolve(registered, inference.reference, selection.cutoff)
    registered.dispose()
    reopened = create_database(registered.url.database)
    try:
        with transaction(reopened) as repo:
            loaded = repo.load_fact(inference.reference, target=TARGET)
        assert loaded == stored
        assert canonical_payload(loaded.fact) == canonical_payload(inference)
        graph = resolve(reopened, inference.reference, output)
        assert_exact_graph(graph, inference, a, b)
        assert graph.cutoff == output
        retained = {n.stored.fact.reference: n.stored.fact for n in graph.nodes}
        assert str(retained[a.reference].value.value.value) == earlier
        assert str(retained[b.reference].value.value.value) == later
        assert retained[a.reference].time.event.isoformat() == comparison.earlier_sample_time.isoformat()
        assert retained[b.reference].time.event.isoformat() == comparison.later_sample_time.isoformat()
        assert [n.stored.fact.reference for n in graph.nodes] == [b.reference, a.reference, inference.reference]
        with reopened.connect() as conn:
            assert set(inspect(conn).get_table_names()) == {'patient', 'encounter', 'fact_revision',
                'revision_link', 'repository_identity', 'weight_trend_execution', 'creatinine_trend_execution', 'patient_state_temporal_execution', 'micro_antimicrobial_execution', 'circulatory_execution', 'alembic_version'}
    finally:
        reopened.dispose()


@pytest.mark.parametrize('case', ['a', 'b', 'both', 'same_value', 'ineligible', 'unit'])
def test_later_corrections_do_not_substitute_historical_evidence(registered, case):
    selection, (a, b) = selected_pair(registered)
    inference = build(selection)
    stored, output = persist(registered, inference)
    old_graph = resolve(registered, inference.reference, output)
    a2 = revision(a, 'a-new', value=replace(a.value, value=replace(a.value.value,
        value=Decimal('1.00') if case == 'same_value' else Decimal('1.10'))))
    b2 = revision(b, 'b-new', value=replace(b.value, value=replace(b.value.value, value=Decimal('1.30'))))
    if case == 'ineligible':
        a2 = replace(a2, verification='unverified')
    elif case == 'unit':
        a2 = changed_unit(a2, raw='µmol/L', code='umol/L')
    with transaction(registered) as repo:
        if case != 'b':
            repo.append_revision(a2, target=TARGET)
        if case in ('b', 'both'):
            repo.append_revision(b2, target=TARGET)
        later = repo.capture_cutoff()
    graph = resolve(registered, inference.reference, later)
    assert_exact_graph(graph, inference, a, b)
    assert resolve(registered, inference.reference, output) == old_graph
    assert select(registered, selection.cutoff) == selection
    # Pure replay does not consult latest state after a correction, even with the same numeric value.
    assert canonical_payload(build(selection)) == canonical_payload(inference)
    current = select(registered, later)
    if case in ('ineligible', 'unit'):
        assert not current.successful
    else:
        expected = (a.reference if case == 'b' else a2.reference,
                    b2.reference if case in ('b', 'both') else b.reference)
        fresh = build(current, inference_id='creatinine-new')
        assert fresh.inputs == expected
        assert fresh.inputs != inference.inputs
    with transaction(registered) as repo:
        assert repo.load_fact(inference.reference, target=TARGET) == stored


def test_generic_inference_revision_uses_own_exact_inputs_and_cutoff(registered):
    selection, (a, b) = selected_pair(registered)
    i1 = build(selection)
    _, first_output = persist(registered, i1)
    a2 = revision(a, '2')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        changed = repo.capture_cutoff()
    i2 = build(select(registered, changed), revision='2')
    i2 = replace(i2, supersedes=i1.reference, correction_reason='synthetic evidence revision')
    with transaction(registered) as repo:
        repo.append_revision(i2, target=TARGET)
        second_output = repo.capture_cutoff()
        identity = FactIdentity(kind='inference', id=i1.id)
        assert repo.load_latest_known(identity, target=TARGET, cutoff=first_output).records[0].fact.reference == i1.reference
        assert repo.load_latest_known(identity, target=TARGET, cutoff=second_output).records[0].fact.reference == i2.reference
    with pytest.raises(RecordNotFound):
        resolve(registered, i2.reference, first_output)
    assert_exact_graph(resolve(registered, i1.reference, second_output), i1, a, b)
    second_graph = resolve(registered, i2.reference, second_output)
    assert_exact_graph(second_graph, i2, a2, b)
    assert i1.reference not in dict(second_graph.ancestry)[i2.reference]
    assert a.reference not in dict(second_graph.ancestry)[i2.reference]


def test_retries_preserve_original_ingestion_and_content_conflicts(registered):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    stored, output = persist(registered, inference)
    retried, retry_cutoff = persist(registered, build(selection))
    assert retried == stored and retry_cutoff.fact_watermark == output.fact_watermark
    with pytest.raises(RecordConflict):
        persist(registered, replace(inference, statement='different retained statement'))
    with transaction(registered) as repo:
        assert repo.load_fact(inference.reference, target=TARGET) == stored


@pytest.mark.parametrize('case,reason', [('missing', 'not_resolvable_in_scope_at_cutoff'),
    ('wrong_revision', 'not_resolvable_in_scope_at_cutoff'), ('wrong_patient', 'not_resolvable_in_scope_at_cutoff'),
    ('wrong_encounter', 'not_resolvable_in_scope_at_cutoff'), ('unsupported', 'unsupported_reference_kind'),
    ('future', 'not_resolvable_in_scope_at_cutoff')])
def test_unresolved_ancestry_remains_partial_not_exception(registered, case, reason):
    selection, (a, b) = selected_pair(registered)
    inference = build(selection)
    ref = Reference(kind='observation', id='absent', version='1')
    if case == 'wrong_revision':
        ref = replace(a.reference, version='absent')
    elif case == 'unsupported':
        ref = Reference(kind='source_record', id='external', version='1')
    elif case in ('wrong_patient', 'wrong_encounter', 'future'):
        other = creatinine('foreign', at=AT + timedelta(hours=2))
        if case != 'future':
            target = (replace(TARGET, encounter_id='synthetic-e2') if case == 'wrong_encounter' else
                replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3'))
            other = replace(other, binding=replace(other.binding, target=target))
            save(registered, other)
        ref = other.reference
    # Generic facts may declare unresolved ancestry; this deliberately does not come from the builder.
    inputs = (a.reference, ref)
    inference = replace(inference, inputs=inputs, provenance=replace(inference.provenance,
        upstream=tuple(LineageEdge(target=r, relationship='derived_from') for r in inputs)))
    _, output = persist(registered, inference)
    graph = resolve(registered, inference.reference, output)
    assert graph.coverage == 'partial'
    assert [(u.owner, u.reference, u.role, u.ordinal, u.reason) for u in graph.unresolved] == [
        (inference.reference, ref, 'dependency', 1, reason)]
    assert tuple(d.source for d in graph.dependencies) == inputs
    assert {n.stored.fact.reference for n in graph.nodes} == {inference.reference, a.reference}
    if case == 'future':
        later = save(registered, other)
        assert resolve(registered, inference.reference, output) == graph
        assert resolve(registered, inference.reference, later).unresolved == ()


@pytest.mark.parametrize('case', ['edge', 'missing_edge', 'origin', 'time', 'prefix'])
def test_malformed_visible_storage_remains_exception(registered, case):
    selection, (a, _) = selected_pair(registered)
    inference = build(selection)
    _, output = persist(registered, inference)
    payload = json.loads(canonical_payload(inference))
    if case == 'edge':
        payload['provenance']['upstream'][0]['relationship'] = 'malformed'
    elif case == 'missing_edge':
        payload['provenance']['upstream'] = payload['provenance']['upstream'][:1]
    elif case == 'origin':
        payload['origin'] = 'observed'
    elif case == 'time':
        payload['time']['event'] = 'bad'
    else:
        with transaction(registered) as repo:
            repo.append_revision(revision(a, '2'), target=TARGET)
            output = repo.capture_cutoff()
    with registered.begin() as conn:
        if case == 'prefix':
            conn.execute(text('DELETE FROM revision_link'))
        else:
            conn.execute(text('UPDATE fact_revision SET payload=:p WHERE fact_id=:id'),
                {'p': json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False), 'id': inference.id})
    with pytest.raises(StorageIntegrityError):
        resolve(registered, inference.reference, output)


def test_generic_cycle_remains_exception(registered):
    selection, _ = selected_pair(registered)
    i1 = build(selection)
    i2 = build(selection, inference_id='creatinine-i2')
    def with_dependency(inference, reference):
        return replace(inference, inputs=(*inference.inputs, reference),
            provenance=replace(inference.provenance, upstream=(*inference.provenance.upstream,
                LineageEdge(target=reference, relationship='derived_from'))))
    i1, i2 = with_dependency(i1, i2.reference), with_dependency(i2, i1.reference)
    persist(registered, i1)
    _, output = persist(registered, i2)
    with pytest.raises(StorageIntegrityError):
        resolve(registered, i1.reference, output)


@pytest.mark.parametrize('limits', [LineageLimits(max_records=2), LineageLimits(max_nodes=2),
    LineageLimits(max_assertions=1), LineageLimits(max_width=1), LineageLimits(max_depth=0),
    LineageLimits(max_ancestry_entries=4)])
def test_budget_exhaustion_is_exception_not_truncated_graph(registered, limits):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    _, output = persist(registered, inference)
    with pytest.raises(QueryLimitExceeded):
        resolve(registered, inference.reference, output, limits)


def test_generic_extra_dependencies_are_visible_not_silently_pruned(registered):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    extra = creatinine('extra', at=AT + timedelta(hours=2))
    save(registered, extra)
    inference = replace(inference, inputs=(*inference.inputs, extra.reference),
        provenance=replace(inference.provenance, upstream=(*inference.provenance.upstream,
            LineageEdge(target=extra.reference, relationship='derived_from'))))
    _, output = persist(registered, inference)
    graph = resolve(registered, inference.reference, output)
    assert len(graph.nodes) == 4 and len(graph.dependencies) == 3
    assert graph.dependencies[-1].source == extra.reference
    # Generic completeness cannot certify the capability's two-input contract.
    assert graph.coverage == 'complete_for_declared_visible_graph'


def test_builder_pure_deterministic_and_lineage_readonly(registered, monkeypatch):
    import app.execution.creatinine_trend as module
    selection, _ = selected_pair(registered)
    before = selection.model_dump_json()
    def forbidden(*args, **kwargs):
        pytest.fail('pure builder accessed storage or sampled a clock')
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().split()[0].upper())
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        with monkeypatch.context() as patch:
            for name in ('append_fact', 'append_revision', 'load_fact', 'list_latest_known',
                    'list_current_latest_known', 'capture_cutoff', 'resolve_lineage'):
                patch.setattr(PatientRepository, name, forbidden)
            patch.setattr(module, 'datetime', type('ForbiddenClock', (), {'now': forbidden, 'utcnow': forbidden}))
            inference = build(selection)
            assert canonical_payload(build(selection)) == canonical_payload(inference)
            assert statements == [] and selection.model_dump_json() == before
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    _, output = persist(registered, inference)
    statements.clear()
    event.listen(registered, 'before_cursor_execute', capture)
    try:
        graph = resolve(registered, inference.reference, output)
        assert resolve(registered, inference.reference, output) == graph
    finally:
        event.remove(registered, 'before_cursor_execute', capture)
    assert not {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'} & set(statements)


@pytest.mark.parametrize('part', ['statement', 'method', 'binding', 'inputs', 'source', 'edge', 'uncertainty'])
def test_returned_inference_nested_contracts_frozen(registered, part):
    selection, _ = selected_pair(registered)
    inference = build(selection)
    stored, output = persist(registered, inference)
    graph = resolve(registered, inference.reference, output)
    retained = next(n.stored.fact for n in graph.nodes if n.stored.fact.reference == inference.reference)
    obj, field, value = {
        'statement': (retained, 'statement', 'changed'), 'method': (retained.method, 'version', '2'),
        'binding': (retained.binding.target, 'patient_id', 'other'), 'inputs': (retained, 'inputs', ()),
        'source': (retained.provenance.source, 'identifier', 'other'),
        'edge': (retained.provenance.upstream[0], 'target', retained.inputs[1]),
        'uncertainty': (retained, 'uncertainty', ()),
    }[part]
    with pytest.raises(ValidationError):
        setattr(obj, field, value)
    with pytest.raises(FrozenInstanceError):
        graph.coverage = 'partial'
    with transaction(registered) as repo:
        assert repo.load_fact(inference.reference, target=TARGET) == stored


def test_seconds_offset_cannot_hide_behind_json_time_encoding(registered):
    selection, _ = selected_pair(registered)
    comparison = compare_recorded_creatinine(selection)
    shifted = comparison.earlier_sample_time.replace(
        tzinfo=timezone(timedelta(hours=5, minutes=30, seconds=1)))
    forged = replace(comparison, earlier_sample_time=shifted)
    with pytest.raises(ValueError, match='exact selected observations'):
        build(selection, forged)


def test_visible_malformed_inference_after_old_prefix_does_not_change_old_lineage(registered):
    selection, (a, b) = selected_pair(registered)
    i1 = build(selection)
    _, old = persist(registered, i1)
    i2 = replace(build(selection, revision='2'), supersedes=i1.reference,
        correction_reason='synthetic correction')
    with transaction(registered) as repo:
        repo.append_revision(i2, target=TARGET)
        current = repo.capture_cutoff()
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='{}' WHERE fact_id=:id AND revision='2'"), {'id': i1.id})
    assert_exact_graph(resolve(registered, i1.reference, old), i1, a, b)
    with pytest.raises(StorageIntegrityError):
        resolve(registered, i1.reference, current)


@pytest.mark.parametrize('field,value', [('inference_id', ''), ('revision', '')])
def test_invalid_inference_identity_rejected(registered, field, value):
    selection, _ = selected_pair(registered)
    with pytest.raises(ValidationError):
        build(selection, **{field: value})
