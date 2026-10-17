"""Synthetic adversarial cases for cutoff-bounded declared lineage, not clinical truth."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys
import traceback
from uuid import uuid4
import warnings

import pytest
from sqlalchemy import text

from app.models.clinical.common import LineageEdge, Reference
from app.persistence.database import create_database
from app.persistence.errors import (PersistenceInputError, QueryLimitExceeded, RecordNotFound,
    ScopeMismatch, StorageIntegrityError, TransactionAborted)
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.repository import transaction
from test_persistence import AT, ROOT, TARGET, database, registered, fact, replace
from test_revision_chains import revision

LIMITS = LineageLimits()
SECRET = 'CONFIDENTIAL-LINEAGE-SENTINEL'


def ref(id, kind='observation', version='1'):
    return Reference(kind=kind, id=id, version=version)


def node(id, *parents, kind='observation', edges=None, at=AT, target=TARGET):
    base = fact(kind, id=id)
    edges = tuple(LineageEdge(target=p, relationship='derived_from') for p in parents) if edges is None else edges
    updates = dict(provenance=replace(base.provenance, upstream=edges, recorded_at=at,
                                      lineage='complete', limitations=()),
                   binding=replace(base.binding, target=target))
    if kind == 'inference':
        updates['inputs'] = tuple(dict.fromkeys(p for e in edges for p in e.dependencies))
    return replace(base, **updates)


def save(engine, *facts):
    with transaction(engine) as repo:
        for item in facts:
            repo.append_fact(item, target=item.binding.target)
        return repo.capture_cutoff()


def resolve(engine, root, cutoff=None, target=TARGET, limits=LIMITS):
    with transaction(engine) as repo:
        return repo.resolve_lineage(root, target=target,
            cutoff=cutoff if cutoff is not None else repo.capture_cutoff(), limits=limits)


def refs(result):
    return tuple(item.stored.fact.reference for item in result.nodes)


def corrupt(engine, reference, mutate):
    with engine.begin() as conn:
        row = conn.execute(text('SELECT payload FROM fact_revision WHERE kind=:k AND fact_id=:i AND revision=:v'),
                           dict(k=reference.kind, i=reference.id, v=reference.version)).scalar_one()
        payload = json.loads(row)
        mutate(payload)
        conn.execute(text('UPDATE fact_revision SET payload=:p WHERE kind=:k AND fact_id=:i AND revision=:v'),
                     dict(p=json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False),
                          k=reference.kind, i=reference.id, v=reference.version))


def sanitized(call, error):
    with pytest.raises(error) as caught:
        call()
    value = caught.value
    assert SECRET not in str(value) + repr(value) + ''.join(traceback.format_exception(value))
    assert value.__cause__ is None
    return value


def test_exact_ancestor_stays_old_revision_and_revision_is_not_evidence(registered):
    a = node('a')
    b = node('b', a.reference, kind='inference')
    cutoff = save(registered, a, b)
    before = resolve(registered, b.reference, cutoff)
    a2 = revision(a, 'opaque-earlier-label')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
        current = repo.capture_cutoff()
    assert resolve(registered, b.reference, cutoff) == before
    after = resolve(registered, b.reference, current)
    assert refs(after) == (a.reference, b.reference)
    assert after.dependencies[0].source == a.reference
    assert refs(resolve(registered, a2.reference)) == (a2.reference,)
    assert not resolve(registered, a2.reference).dependencies


@pytest.mark.parametrize('damage', ['payload', 'lineage', 'link'])
def test_future_corruption_invisible_visible_corruption_fails(registered, damage):
    a = node('a')
    cutoff = save(registered, a)
    before = resolve(registered, a.reference, cutoff)
    a2 = revision(a)
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
    if damage == 'link':
        with registered.begin() as conn:
            conn.execute(text('DELETE FROM revision_link'))
    else:
        def mutate(payload):
            if damage == 'payload':
                payload['value'] = SECRET
            else:
                payload['provenance']['upstream'] = [dict(target=ref(SECRET).model_dump(), relationship=SECRET)]
        corrupt(registered, a2.reference, mutate)
    assert resolve(registered, a.reference, cutoff) == before
    sanitized(lambda: resolve(registered, a.reference), StorageIntegrityError)


def test_late_ancestor_and_old_prefix_replay(registered):
    a, b = node('a'), node('b', ref('a'))
    early = save(registered, b)
    first = resolve(registered, b.reference, early)
    assert first.coverage == 'partial'
    assert first.unresolved[0].reason == 'not_resolvable_in_scope_at_cutoff'
    later = save(registered, a)
    assert refs(resolve(registered, b.reference, later)) == (b.reference, a.reference)
    assert resolve(registered, b.reference, early) == first


@pytest.mark.parametrize('missing', [ref('missing'), ref('external', 'source_record'),
    ref('a', version='absent'), ref('model', 'model'), ref('derived', 'derived_value')])
def test_unresolved_reason_exactness_and_no_fallback(registered, missing):
    a = node('a')
    b = node('b', missing, kind='inference')
    save(registered, a, b)
    result = resolve(registered, b.reference)
    assert refs(result) == (b.reference,)
    assert result.unresolved[0].reference == missing
    assert result.unresolved[0].reason == ('not_resolvable_in_scope_at_cutoff'
        if missing.kind == 'observation' else 'unsupported_reference_kind')


@pytest.mark.parametrize('target', [replace(TARGET, encounter_id='synthetic-e2'),
    replace(TARGET, patient_id='synthetic-p2', encounter_id='synthetic-e3')])
def test_other_context_indistinguishable_from_missing_even_if_malformed(registered, target):
    a, b = node(SECRET, target=target), node('b', ref(SECRET))
    cutoff = save(registered, b)
    before = resolve(registered, b.reference, cutoff)
    current = save(registered, a)
    corrupt(registered, a.reference, lambda p: p.update(value=SECRET))
    result = resolve(registered, b.reference, current)
    assert result.unresolved == before.unresolved
    assert refs(result) == (b.reference,)
    sanitized(lambda: resolve(registered, a.reference), RecordNotFound)


@pytest.mark.parametrize('root', [None, {}, {'kind': SECRET, 'id': SECRET, 'version': None}])
def test_invalid_root_does_not_broaden_and_is_private(registered, root):
    save(registered, node('a'), node('b'))
    sanitized(lambda: resolve(registered, root), PersistenceInputError)


def test_missing_root_and_future_root_fail(registered):
    c1 = save(registered, node('a'))
    save(registered, node('b'))
    sanitized(lambda: resolve(registered, ref(SECRET)), RecordNotFound)
    sanitized(lambda: resolve(registered, ref('b'), c1), RecordNotFound)


@pytest.mark.parametrize('case', ['uuid', 'watermark', 'forged', 'target'])
def test_cutoff_and_parent_boundary(registered, case):
    root = node('a')
    cutoff = save(registered, root)
    error, target = PersistenceInputError, TARGET
    if case == 'uuid':
        cutoff = replace(cutoff, repository_id=uuid4())
        error = ScopeMismatch
    elif case == 'watermark':
        cutoff = replace(cutoff, fact_watermark=100)
    elif case == 'forged':
        cutoff = cutoff.model_copy(update={'fact_watermark': SECRET})
    else:
        target = None
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter('always')
        sanitized(lambda: resolve(registered, root.reference, cutoff, target), error)
        assert not seen
    with pytest.warns(UserWarning, match='useful warning'):
        warnings.warn('useful warning')


@pytest.mark.parametrize('table', ['patient', 'encounter'])
def test_malformed_parent_fails_private(registered, table):
    root = node('a')
    save(registered, root)
    with registered.begin() as conn:
        conn.execute(text(f'UPDATE {table} SET payload=:payload'), {'payload': SECRET})
    sanitized(lambda: resolve(registered, root.reference), StorageIntegrityError)


@pytest.mark.parametrize('length', [1, 2, 5])
def test_self_and_transitive_cycle(registered, length):
    items = [node(str(i), ref(str((i+1) % length))) for i in range(length)] if length > 1 else [node('0')]
    save(registered, *items)
    if length == 1:
        corrupt(registered, items[0].reference, lambda p: p['provenance'].update(
            upstream=[LineageEdge(target=items[0].reference, relationship='derived_from').model_dump()]))
    sanitized(lambda: resolve(registered, items[0].reference), StorageIntegrityError)


def test_diamond_repeated_ancestor_assertions_and_dependence(registered):
    a = node('a')
    b, c = node('b', a.reference), node('c', a.reference)
    d = node('d', edges=(LineageEdge(target=b.reference, relationship='derived_from'),
                        LineageEdge(target=c.reference, relationship='derived_from'),
                        LineageEdge(target=b.reference, relationship='copied_from')))
    save(registered, d, c, a, b)
    result = resolve(registered, d.reference)
    assert refs(result) == (d.reference, c.reference, a.reference, b.reference)
    assert len(result.assertions) == len(result.dependencies) == 5
    assert len(set(item.identity for item in result.assertions)) == 5
    assert result.support_relationship(b.reference, c.reference) == 'dependent'
    assert set(dict(result.ancestry)[d.reference]) == {a.reference, b.reference, c.reference, d.reference}
    assert all(item.roles == ('evidence',) for item in result.nodes)


def test_disjoint_ancestry_unknown_and_family_overlap_dependent(registered):
    a, other = node('a'), node('other')
    save(registered, a, other)
    a2 = revision(a, '2')
    with transaction(registered) as repo:
        repo.append_revision(a2, target=TARGET)
    root = node('root', a.reference, a2.reference, other.reference)
    save(registered, root)
    result = resolve(registered, root.reference)
    assert result.support_relationship(a.reference, a2.reference) == 'dependent'
    assert result.support_relationship(a.reference, other.reference) == 'unknown'
    assert dict(result.ancestry)[a2.reference] == frozenset((a2.reference,))
    sanitized(lambda: result.support_relationship(ref(SECRET), root.reference), PersistenceInputError)
    sanitized(lambda: result.support_relationship(None, root.reference), PersistenceInputError)


@pytest.mark.parametrize('budget', ['max_records', 'max_nodes', 'max_assertions', 'max_width',
                                   'max_depth', 'max_ancestry_entries'])
def test_resource_limits(registered, budget):
    a, b = node('a'), node('b', ref('a'))
    root = node('root', a.reference, b.reference)
    save(registered, a, b, root)
    limits = LineageLimits(**{budget: 1})
    sanitized(lambda: resolve(registered, root.reference, limits=limits), QueryLimitExceeded)


@pytest.mark.parametrize('value', [None, {'max_nodes': True}, {'max_nodes': 0},
    {'max_depth': -1}, {'max_nodes': 1001}, {'max_width': SECRET}])
def test_invalid_limits_sanitized(registered, value):
    root = node('root')
    save(registered, root)
    sanitized(lambda: resolve(registered, root.reference, limits=value), PersistenceInputError)


def test_longest_path_depth_in_diamond_not_shortest_visit(registered):
    a = node('a')
    b = node('b', a.reference)
    c = node('c', b.reference)
    root = node('root', a.reference, c.reference)
    save(registered, root, a, b, c)
    sanitized(lambda: resolve(registered, root.reference, limits=LineageLimits(max_depth=2)), QueryLimitExceeded)
    assert len(resolve(registered, root.reference, limits=LineageLimits(max_depth=3)).nodes) == 4


def test_inferred_copy_origin_and_transitive_dependencies_preserved(registered):
    a = node('a')
    b = node('b', a.reference, kind='inference')
    c = node('c', kind='inference', edges=(LineageEdge(target=b.reference, relationship='copied_from'),))
    d = node('d', c.reference, kind='inference')
    save(registered, a, b, c, d)
    result = resolve(registered, d.reference)
    assert tuple(n.stored.fact.origin for n in result.nodes) == ('reported', 'inferred', 'inferred', 'inferred')
    assert result.support_relationship(b.reference, d.reference) == 'dependent'


@pytest.mark.parametrize('relationship', ['copied_from', 'derived_from', 'calculated_from'])
def test_origin_laundering_retained_corruption_rejected(registered, relationship):
    a = node('a')
    b = node('b', a.reference, kind='inference')
    c = node('c')
    d = node('d', c.reference)
    save(registered, a, b, c, d)
    corrupt(registered, c.reference, lambda p: p['provenance'].update(upstream=[
        LineageEdge(target=b.reference, relationship=relationship, rationale=SECRET).model_dump()]))
    sanitized(lambda: resolve(registered, d.reference), StorageIntegrityError)


def confirmation(id='confirmation', target=ref('prediction', 'inference'), bases=(ref('new'),), at=AT+timedelta(hours=1)):
    return node(id, at=at, edges=(LineageEdge(target=target, relationship='independent_confirmation',
                                           basis=bases, rationale=SECRET),))


def confirmation_facts():
    old, new = node('old'), node('new')
    prediction = node('prediction', old.reference, kind='inference')
    return old, new, prediction


def test_confirmation_target_is_validation_only_basis_is_evidence(registered):
    old, new, prediction = confirmation_facts()
    owner = confirmation()
    save(registered, old, new, prediction, owner)
    result = resolve(registered, owner.reference)
    roles = {n.stored.fact.reference: n.roles for n in result.nodes}
    assert roles[prediction.reference] == roles[old.reference] == ('confirmation_validation',)
    assert roles[new.reference] == roles[owner.reference] == ('evidence',)
    assert dict(result.ancestry)[owner.reference] == frozenset((owner.reference, new.reference))
    assert result.assertions[-1].edge.rationale == SECRET
    assert result.confirmations[0].relationship == 'unknown'
    assert result.confirmations[0].limitations == ('independence_not_established',)


@pytest.mark.parametrize('case', ['exact', 'family', 'transitive', 'circular'])
def test_confirmation_shared_ancestry_rejected(registered, case):
    old, new, prediction = confirmation_facts()
    save(registered, old, new)
    if case == 'exact':
        owner = confirmation(bases=(old.reference,))
    elif case == 'family':
        old2 = revision(old, 'new')
        with transaction(registered) as repo:
            repo.append_revision(old2, target=TARGET)
        owner = confirmation(bases=(old2.reference,))
    elif case == 'transitive':
        dependent = node('dependent', old.reference)
        save(registered, dependent)
        owner = confirmation(bases=(dependent.reference,))
    else:
        prediction = node('prediction', ref('confirmation'), kind='inference')
        owner = confirmation()
    save(registered, prediction, owner)
    sanitized(lambda: resolve(registered, owner.reference), StorageIntegrityError)


@pytest.mark.parametrize('case', ['target', 'basis', 'ancestor', 'disclosure'])
def test_confirmation_incomplete_ancestry_stays_explicit_unknown(registered, case):
    old, new, prediction = confirmation_facts()
    if case == 'ancestor':
        prediction = node('prediction', ref('external', 'source_record'), kind='inference')
    if case == 'disclosure':
        new = replace(new, provenance=replace(new.provenance, lineage='unknown', limitations=(SECRET,)))
    save(registered, old)
    if case != 'target':
        save(registered, prediction)
    if case != 'basis':
        save(registered, new)
    owner = confirmation()
    save(registered, owner)
    result = resolve(registered, owner.reference)
    assessment = result.confirmations[0]
    assert assessment.relationship == 'unknown'
    assert ('limited_declared_provenance' if case == 'disclosure' else 'unresolved_confirmation_ancestry') in assessment.limitations
    assert result.coverage == ('complete_for_declared_visible_graph' if case == 'disclosure' else 'partial')


@pytest.mark.parametrize('case', ['equal_target', 'earlier_target', 'late_basis'])
def test_confirmation_temporal_failures(registered, case):
    old, new, prediction = confirmation_facts()
    at = AT if case == 'equal_target' else AT-timedelta(hours=1)
    if case == 'late_basis':
        at = AT+timedelta(hours=1)
        new = replace(new, provenance=replace(new.provenance, recorded_at=AT+timedelta(hours=2)))
    owner = confirmation(at=at)
    save(registered, old, new, prediction, owner)
    sanitized(lambda: resolve(registered, owner.reference), StorageIntegrityError)


@pytest.mark.parametrize('year,offset', [(1, 330), (9999, -330)])
def test_confirmation_boundary_instants(registered, year, offset):
    dt = datetime(year, 1 if year == 1 else 12, 1 if year == 1 else 31,
                  0 if year == 1 else 23, tzinfo=timezone(timedelta(minutes=offset)))
    old, new, prediction = confirmation_facts()
    old = replace(old, provenance=replace(old.provenance, recorded_at=dt))
    new = replace(new, provenance=replace(new.provenance, recorded_at=dt))
    prediction = replace(prediction, provenance=replace(prediction.provenance, recorded_at=dt))
    owner = confirmation(at=dt+timedelta(minutes=1))
    save(registered, old, new, prediction, owner)
    assert resolve(registered, owner.reference).confirmations[0].relationship == 'unknown'


def test_associations_never_expand_evidence_or_associated_lineage(registered):
    ancestor = node('a')
    order = node('order', ancestor.reference, kind='medication_order')
    admin = node('admin', kind='medication_administration', edges=(
        LineageEdge(target=order.reference, relationship='fulfills_order'),))
    admin = replace(admin, order=order.reference)
    save(registered, ancestor, order, admin)
    result = resolve(registered, admin.reference)
    assert refs(result) == (order.reference, admin.reference)
    assert not result.dependencies
    assert len(result.associations) == 2
    assert dict(result.ancestry)[admin.reference] == frozenset((admin.reference,))
    assert result.nodes[0].roles == ('association',)


def test_missing_association_reason_and_retained_provenance(registered):
    item = fact('medication_administration')
    save(registered, item)
    result = resolve(registered, item.reference)
    assert result.unresolved[0].role == 'association'
    assert result.provenance[0].limitations == item.provenance.limitations
    assert result.provenance[0].lineage == 'unknown'


def test_sequence_gaps_clocks_determinism_immutability_and_reopen(registered):
    a, b = node('a'), node('b', ref('a'))
    save(registered, a)
    with registered.begin() as conn:
        conn.execute(text("UPDATE sqlite_sequence SET seq=7 WHERE name='fact_revision'"))
    cutoff = save(registered, b)
    with registered.begin() as conn:
        conn.execute(text('UPDATE fact_revision SET ingested_at=:at WHERE fact_id=:id'),
                     [{'at': (AT+timedelta(days=1)).isoformat(), 'id': 'a'}, {'at': AT.isoformat(), 'id': 'b'}])
    first = resolve(registered, b.reference, cutoff)
    assert [n.stored.ingestion.ingestion_sequence for n in first.nodes] == [1, 8]
    assert resolve(registered, b.reference, cutoff) == first
    with pytest.raises(FrozenInstanceError):
        first.coverage = 'partial'
    with pytest.raises(FrozenInstanceError):
        first.nodes[0].roles = ()
    registered.dispose()
    assert resolve(registered, b.reference, cutoff) == first
    # A separate interpreter resolves the same persisted prefix after reopening.
    code = '''import json, sys
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.metadata import RepositoryCutoff
from app.persistence.lineage import LineageLimits
from app.models.clinical.common import Reference, ContextTarget
engine=create_database(sys.argv[1])
with transaction(engine) as repo:
 r=repo.resolve_lineage(Reference.model_validate_json(sys.argv[2]), target=ContextTarget.model_validate_json(sys.argv[3]), cutoff=RepositoryCutoff.model_validate_json(sys.argv[4]), limits=LineageLimits())
 print(json.dumps([[(n.stored.fact.id,n.stored.ingestion.ingestion_sequence) for n in r.nodes],r.coverage]))
engine.dispose()
'''
    completed = subprocess.run([sys.executable, '-c', code, registered.url.database, b.reference.model_dump_json(),
        TARGET.model_dump_json(), cutoff.model_dump_json()], env={**os.environ, 'PYTHONPATH': str(ROOT/'backend'),
        'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [[['a', 1], ['b', 8]], first.coverage]


def test_read_only_payload_metadata_schema_and_retry_preservation(registered):
    a, b = node('a'), node('b', ref('a'))
    cutoff = save(registered, a, b)
    with registered.connect() as conn:
        before = conn.execute(text('SELECT * FROM fact_revision ORDER BY ingestion_sequence')).all()
        schema = conn.execute(text("SELECT sql FROM sqlite_master ORDER BY name")).all()
    resolve(registered, b.reference, cutoff)
    with transaction(registered) as repo:
        assert canonical_payload(repo.append_fact(b, target=TARGET).fact) == canonical_payload(b)
    with registered.connect() as conn:
        assert conn.execute(text('SELECT * FROM fact_revision ORDER BY ingestion_sequence')).all() == before
        assert conn.execute(text('SELECT sql FROM sqlite_master ORDER BY name')).all() == schema


def test_caught_failure_aborts_prior_writes_and_closed_handle(registered):
    a = node('a', ref('missing'))
    with pytest.raises(TransactionAborted), transaction(registered) as repo:
        repo.append_fact(a, target=TARGET)
        with pytest.raises(QueryLimitExceeded):
            repo.resolve_lineage(a.reference, target=TARGET, cutoff=repo.capture_cutoff(),
                                 limits=LineageLimits(max_depth=0))
    with registered.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM fact_revision')).scalar_one() == 0
    sanitized(lambda: repo.resolve_lineage(a.reference, target=TARGET, cutoff=None, limits=LIMITS), TransactionAborted)


def test_deep_iterative_traversal_and_explicit_depth_boundary(registered):
    items = [node('n0')]
    for index in range(1, 130):
        items.append(node(f'n{index}', items[-1].reference))
    save(registered, *items)
    sanitized(lambda: resolve(registered, items[-1].reference), QueryLimitExceeded)
    result = resolve(registered, items[-1].reference, limits=LineageLimits(max_depth=129))
    assert len(result.nodes) == 130
    assert len(dict(result.ancestry)[items[-1].reference]) == 130


def test_shared_unknown_source_establishes_declared_dependence(registered):
    shared = ref('external', 'source_record')
    a, b = node('a', shared), node('b', shared)
    root = node('root', a.reference, b.reference)
    save(registered, a, b, root)
    result = resolve(registered, root.reference)
    assert result.coverage == 'partial'
    assert result.support_relationship(a.reference, b.reference) == 'dependent'
    assert len(result.unresolved) == 2  # Preserve assertion owners, not just endpoint.


def test_multi_basis_confirmation_order_and_repeated_assertions(registered):
    old, new, prediction = confirmation_facts()
    other = node('other')
    owner = confirmation(bases=(other.reference, new.reference))
    save(registered, old, new, other, prediction, owner)
    result = resolve(registered, owner.reference)
    basis = [d for d in result.dependencies if d.owner == owner.reference]
    assert [(d.basis_ordinal, d.source) for d in basis] == [(0, other.reference), (1, new.reference)]
    assert result.confirmations[0].relationship == 'unknown'


@pytest.mark.parametrize('damage', ['rationale', 'basis', 'origin', 'reference', 'duplicate'])
def test_malformed_confirmation_privacy(registered, damage):
    old, new, prediction = confirmation_facts()
    owner = confirmation()
    save(registered, old, new, prediction, owner)
    def mutate(payload):
        edge = payload['provenance']['upstream'][0]
        if damage == 'rationale':
            edge['rationale'] = {SECRET: SECRET}
        elif damage == 'basis':
            edge['basis'] = [ref(SECRET, 'inference').model_dump()]
        elif damage == 'origin':
            payload['origin'] = SECRET
        elif damage == 'reference':
            edge['target']['version'] = {SECRET: SECRET}
        else:
            payload['provenance']['upstream'].append(edge)
    corrupt(registered, owner.reference, mutate)
    sanitized(lambda: resolve(registered, owner.reference), StorageIntegrityError)


def test_limit_failure_without_future_records_affecting_budget(registered):
    a = node('a')
    cutoff = save(registered, a)
    limited = LineageLimits(max_records=1, max_nodes=1, max_depth=0)
    before = resolve(registered, a.reference, cutoff, limits=limited)
    save(registered, node('future1'), node('future2'))
    assert resolve(registered, a.reference, cutoff, limits=limited) == before
    sanitized(lambda: resolve(registered, a.reference, limits=limited), QueryLimitExceeded)


@pytest.mark.parametrize('same_clock', [True, False])
def test_watermark_over_clock_including_late_backdated_ancestor(registered, same_clock):
    b = node('b', ref('a'))
    cutoff = save(registered, b)
    with registered.begin() as conn:
        conn.execute(text('UPDATE fact_revision SET ingested_at=:at'), {'at': AT.isoformat()})
    before = resolve(registered, b.reference, cutoff)
    save(registered, node('a'))
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET ingested_at=:at WHERE fact_id='a'"),
                     {'at': (AT if same_clock else AT-timedelta(days=1)).isoformat()})
    assert resolve(registered, b.reference, cutoff) == before
    assert refs(resolve(registered, b.reference)) == (b.reference, ref('a'))


def test_visible_unrelated_corruption_is_scope_validation_failure(registered):
    root, bad = node('root'), node(SECRET)
    save(registered, root, bad)
    corrupt(registered, bad.reference, lambda p: p.update(value=SECRET))
    sanitized(lambda: resolve(registered, root.reference), StorageIntegrityError)


def test_origin_limits_remain_explicit_for_unsupported_intermediary(registered):
    item = node('copy', ref('outside-record', 'source_record'))
    item = replace(item, provenance=replace(item.provenance, lineage='incomplete', limitations=(SECRET,)))
    save(registered, item)
    result = resolve(registered, item.reference)
    assert result.nodes[0].stored.fact.origin == 'reported'
    assert result.coverage == 'partial'
    assert result.provenance[0].limitations == (SECRET,)
    # No claim to infer missing external origin from a source identifier.
    assert result.unresolved[0].reason == 'unsupported_reference_kind'


def test_confirmation_equal_instants_across_offsets_rejected(registered):
    old, new, prediction = confirmation_facts()
    owner = confirmation(at=AT.astimezone(timezone.utc))
    save(registered, old, new, prediction, owner)
    sanitized(lambda: resolve(registered, owner.reference), StorageIntegrityError)


@pytest.mark.parametrize('budget,boundary', [
    ('max_records', 3), ('max_nodes', 3), ('max_assertions', 3),
    ('max_width', 2), ('max_depth', 2), ('max_ancestry_entries', 6),
])
def test_review_exact_budget_boundary_and_one_below(registered, budget, boundary):
    a = node('a')
    b = node('b', a.reference)
    root = node('root', a.reference, b.reference)
    cutoff = save(registered, root, b, a)
    result = resolve(registered, root.reference, cutoff, limits=LineageLimits(**{budget: boundary}))
    assert result.coverage == 'complete_for_declared_visible_graph'
    assert set(refs(result)) == {root.reference, b.reference, a.reference}
    sanitized(lambda: resolve(registered, root.reference, cutoff,
        limits=LineageLimits(**{budget: boundary-1})), QueryLimitExceeded)
    # Failed reads leave no transaction/lock state that poisons the next query.
    assert resolve(registered, root.reference, cutoff) == result


@pytest.mark.parametrize('reverse', [False, True])
def test_review_association_then_evidence_reaches_same_node(registered, reverse):
    a = node('a')
    order = node('order', a.reference, kind='medication_order')
    bridge = node('bridge', order.reference)
    edges = (LineageEdge(target=order.reference, relationship='fulfills_order'),
             LineageEdge(target=bridge.reference, relationship='derived_from'))
    root = node('root', edges=tuple(reversed(edges)) if reverse else edges)
    cutoff = save(registered, root, bridge, order, a)
    result = resolve(registered, root.reference, cutoff)
    assert set(dict(result.ancestry)[root.reference]) == set(refs(result))
    assert {n.stored.fact.reference: n.roles for n in result.nodes}[order.reference] == ('association', 'evidence')
    assert len(result.dependencies) == 3
    assert resolve(registered, root.reference, cutoff) == result


def test_review_association_only_cycle_is_not_traversed(registered):
    order = node('order', ref('other', 'medication_order'), kind='medication_order')
    other = node('other', order.reference, kind='medication_order')
    root = node('root', edges=(LineageEdge(target=order.reference, relationship='fulfills_order'),))
    save(registered, root, order, other)
    result = resolve(registered, root.reference, limits=LineageLimits(max_depth=0))
    assert refs(result) == (root.reference, order.reference)
    assert not result.dependencies
    assert result.coverage == 'complete_for_declared_visible_graph'
    sanitized(lambda: resolve(registered, order.reference), StorageIntegrityError)


def test_review_nested_result_mutations_are_rejected(registered):
    from pydantic import ValidationError
    a = node('a')
    root = node('root', a.reference)
    cutoff = save(registered, a, root)
    result = resolve(registered, root.reference, cutoff)
    attempts = [
        (result.nodes[0].stored, 'fact', root, FrozenInstanceError),
        (result.nodes[0].stored.fact, 'origin', 'inferred', ValidationError),
        (result.nodes[0].stored.fact.provenance, 'upstream', (), ValidationError),
        (result.nodes[0].stored.ingestion, 'ingestion_sequence', 999, ValidationError),
        (result.assertions[0].edge, 'target', ref('replacement'), ValidationError),
        (result.dependencies[0], 'source', ref('replacement'), FrozenInstanceError),
        (result.cutoff, 'fact_watermark', 0, ValidationError),
        (result.target, 'patient_id', 'replacement', ValidationError),
    ]
    for value, field, replacement, error in attempts:
        with pytest.raises(error):
            setattr(value, field, replacement)
    with pytest.raises(AttributeError):
        dict(result.ancestry)[root.reference].add(ref('replacement'))
    assert resolve(registered, root.reference, cutoff) == result


@pytest.mark.parametrize('failure', ['cycle', 'confirmation', 'limit'])
def test_review_structural_failure_returns_nothing_and_rolls_back(registered, failure):
    if failure == 'cycle':
        items = (node('a', ref('b')), node('b', ref('a')))
        error, limits = StorageIntegrityError, LIMITS
    elif failure == 'confirmation':
        old, new, prediction = confirmation_facts()
        items = (old, new, prediction, confirmation(bases=(old.reference,)))
        error, limits = StorageIntegrityError, LIMITS
    else:
        items = (node('a'), node('b', ref('a')))
        error, limits = QueryLimitExceeded, LineageLimits(max_nodes=1)
    results = []
    with pytest.raises(TransactionAborted), transaction(registered) as repo:
        for item in items:
            repo.append_fact(item, target=TARGET)
        with pytest.raises(error):
            results.append(repo.resolve_lineage(items[-1].reference, target=TARGET,
                           cutoff=repo.capture_cutoff(), limits=limits))
        with pytest.raises(TransactionAborted):
            repo.capture_cutoff()
    assert results == []
    with transaction(registered) as repo:
        assert repo.capture_cutoff().fact_watermark == 0


def test_review_resolver_emits_no_write_statements(registered):
    from sqlalchemy import event
    root = node('root', ref('missing'))
    cutoff = save(registered, root)
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split()[0].upper())
    event.listen(registered, 'before_cursor_execute', record)
    try:
        assert resolve(registered, root.reference, cutoff).coverage == 'partial'
    finally:
        event.remove(registered, 'before_cursor_execute', record)
    assert set(statements) <= {'BEGIN', 'SELECT'}


@pytest.mark.parametrize('target_fold,owner_fold,succeeds', [(0, 1, True), (1, 0, False)])
def test_review_confirmation_dst_fold_orders_actual_instants(registered, target_fold, owner_fold, succeeds):
    from zoneinfo import ZoneInfo
    zone = ZoneInfo('America/New_York')
    target_time = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=target_fold)
    owner_time = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=owner_fold)
    old, new, prediction = confirmation_facts()
    prediction = replace(prediction, provenance=replace(prediction.provenance, recorded_at=target_time))
    owner = confirmation(at=owner_time)
    save(registered, old, new, prediction, owner)
    if succeeds:
        assert resolve(registered, owner.reference).confirmations[0].relationship == 'unknown'
    else:
        sanitized(lambda: resolve(registered, owner.reference), StorageIntegrityError)


def test_review_endpoint_work_counts_distinct_assertions_not_unique_nodes(registered):
    leaf = node('leaf')
    root = node('root', edges=tuple(LineageEdge(target=leaf.reference,
        relationship='derived_from', rationale=f'synthetic reason {i}') for i in range(6)))
    save(registered, leaf, root)
    result = resolve(registered, root.reference, limits=LineageLimits(max_assertions=6, max_nodes=2))
    assert len(result.dependencies) == 6 and len(result.nodes) == 2
    sanitized(lambda: resolve(registered, root.reference,
        limits=LineageLimits(max_assertions=5)), QueryLimitExceeded)


def test_review_record_budget_precedes_payload_decoding(registered):
    root, unrelated = node('root'), node('unrelated')
    save(registered, root, unrelated)
    corrupt(registered, unrelated.reference, lambda p: p.update(value=SECRET))
    sanitized(lambda: resolve(registered, root.reference,
        limits=LineageLimits(max_records=1)), QueryLimitExceeded)
    sanitized(lambda: resolve(registered, root.reference,
        limits=LineageLimits(max_records=2)), StorageIntegrityError)
