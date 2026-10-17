"""Pure D1 evidence contracts. No database fixtures or protected execution."""
from dataclasses import replace as dc_replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.execution.creatinine_trend import (
    CreatinineTrendExclusion, CreatinineTrendSelectionIssue, CreatinineTrendSelectionResult,
    compare_recorded_creatinine, select_creatinine_observations,
)
from app.execution.creatinine_trend_execution import (
    FINAL_CONTEXT_ASSESSOR, FINAL_RECHECK_POLICY, WORKFLOW_ASSESSOR,
    CreatinineTrendExecutionRecord, CreatinineTrendFinalRecheck,
    CreatinineTrendInferenceTerminalCheck, CreatinineTrendLineageWitness,
    CreatinineTrendReviewRequest, CreatinineTrendSampleIdentity, CreatinineTrendSelectionManifest,
    StoredCreatinineTrendExecution, assess_creatinine_trend_final_recheck,
    creatinine_trend_lineage_witness, creatinine_trend_request_projection,
    creatinine_trend_selection_manifest,
)
from app.execution.creatinine_trend_release import GRANT_ACTOR, GRANT_TARGET
from app.models.clinical.common import Reference
from app.persistence.errors import StorageIntegrityError, UnsupportedOperation
from app.persistence.history import HistoryResult
from app.persistence.lineage import Dependency, LineageAssertion, LineageResult, ProvenanceDisclosure, ResolvedNode, UnresolvedReference
from app.persistence.mapping import StoredFact, canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff
from app.services.governance_service import decide_release
from test_persistence import AT, TARGET, patient, encounter, replace
from test_revision_chains import revision
from test_creatinine_trend import POLICY, creatinine, changed_unit
from test_creatinine_trend_inference import build
from test_creatinine_trend_release import NOW, compose, run

REPOSITORY = UUID('00000000-0000-4000-8000-000000000001')
EXECUTION = UUID('00000000-0000-4000-8000-000000000002')


def cutoff(watermark):
    return RepositoryCutoff(repository_id=REPOSITORY, fact_watermark=watermark, captured_at=NOW)


def stored(fact, seq):
    return StoredFact(fact, IngestionMetadata(repository_id=REPOSITORY, ingestion_sequence=seq, ingested_at=NOW))


def pure_case():
    a = creatinine('a', '1.00', label='z')
    b = creatinine('b', '1.200', (AT + timedelta(hours=1)).astimezone(timezone.utc), label='0')
    selection = CreatinineTrendSelectionResult(target=TARGET, policy=POLICY, cutoff=cutoff(2), selected=(a, b))
    inference = build(selection)
    root = inference.reference
    facts = (b, a, inference)  # Deliberately ingestion order, not sample order.
    graph = LineageResult(reference=root, target=TARGET, cutoff=cutoff(3),
        nodes=tuple(ResolvedNode(stored(f, i), ('evidence',)) for i, f in enumerate(facts, 1)),
        assertions=tuple(LineageAssertion(root, i, e) for i, e in enumerate(inference.provenance.upstream)),
        dependencies=tuple(Dependency(root, i, None, f.reference) for i, f in enumerate((a, b))),
        associations=(), unresolved=(), confirmations=(),
        provenance=tuple(ProvenanceDisclosure(f.reference, f.provenance.lineage, f.provenance.limitations) for f in facts),
        ancestry=tuple((f.reference, frozenset((root, a.reference, b.reference)) if f is inference
            else frozenset((f.reference,))) for f in facts), coverage='complete_for_declared_visible_graph')
    return compose(dict(selection=selection, comparison=compare_recorded_creatinine(selection), inference=inference,
        lineage=graph, patient=patient(), encounter=encounter(), target=GRANT_TARGET))


@pytest.fixture
def case():
    return pure_case()


def terminal(case, final_cutoff=None, **updates):
    witness = creatinine_trend_lineage_witness(case['lineage'])
    root = next(n for n in witness.nodes if n.reference == witness.root)
    args = dict(target=TARGET, historical_cutoff=case['lineage'].cutoff, cutoff=final_cutoff or cutoff(3),
        consumed=witness.root, consumed_payload_digest=root.payload_digest, terminal=witness.root,
        terminal_payload_digest=root.payload_digest)
    args.update(updates)
    return CreatinineTrendInferenceTerminalCheck(**args)


def recheck(case, final=None, **updates):
    final = replace(case['selection'], cutoff=cutoff(3)) if final is None else final
    return assess_creatinine_trend_final_recheck(original=case['selection'], final=final,
        inference_terminal=terminal(case, final.cutoff, **updates))


def request_for(case, **updates):
    args = dict(execution_id=EXECUTION, target=GRANT_TARGET, actor=GRANT_ACTOR,
        original=creatinine_trend_selection_manifest(case['selection']), comparison=case['comparison'],
        inference=case['inference'].reference, lineage=creatinine_trend_lineage_witness(case['lineage']),
        requested_at=(NOW - timedelta(seconds=2)).astimezone(AT.tzinfo))
    args.update(updates)
    return CreatinineTrendReviewRequest(**args)


def record(case, check=None, actor=GRANT_ACTOR, **updates):
    check = recheck(case) if check is None else check
    decision = run(case, actor=actor)
    assessment = decision.assessment
    freshness = replace(assessment.state.freshness, assessor=FINAL_CONTEXT_ASSESSOR,
        adequate=assessment.state.freshness.adequate and check.outcome == 'unchanged',
        material_change=check.outcome == 'materially_changed')
    assessment = replace(assessment, assessor=WORKFLOW_ASSESSOR, state=replace(assessment.state, freshness=freshness))
    decision = decide_release(reference=decision.reference, assessment=assessment, actor=actor, at=NOW)
    req = request_for(case, actor=actor)
    args = dict(req.model_dump(), final_recheck=check, decision=decision,
        started_at=NOW - timedelta(seconds=1), finalized_at=NOW + timedelta(seconds=1))
    args.update(updates)
    return CreatinineTrendExecutionRecord(**args)


def final_from(case, *facts):
    class Reader:
        def list_bounded_history(self, *, target, cutoff, latest, budget, family_budget, accounting):
            assert latest is True and budget.max_rows==4096 and accounting is not None
            return HistoryResult(target=target, cutoff=cutoff, selection='latest_known',
                records=tuple(stored(f, i) for i, f in enumerate(facts, 1)))
    return select_creatinine_observations(Reader(), target=TARGET, cutoff=cutoff(10), policy=POLICY)


def test_manifest_independent_expected_fields(case):
    manifest = creatinine_trend_selection_manifest(case['selection'])
    assert manifest.target == TARGET and manifest.policy == POLICY and manifest.cutoff == cutoff(2)
    assert [r.model_dump() for r in manifest.selected] == [
        dict(kind='observation', id='a', version='z'), dict(kind='observation', id='b', version='0')]
    assert manifest.selected_payload_digests == tuple(sha256(canonical_payload(f).encode()).hexdigest() for f in case['selection'].selected)
    assert [s.model_dump() for s in manifest.selected_samples] == [
        dict(namespace='clinrx.synthetic.serum-creatinine', identifier='sample-a'),
        dict(namespace='clinrx.synthetic.serum-creatinine', identifier='sample-b')]
    assert [str(v) for v in manifest.selected_values] == ['1.00', '1.200']
    assert [t.isoformat() for t in manifest.selected_sample_times] == [AT.isoformat(), (AT + timedelta(hours=1)).astimezone(timezone.utc).isoformat()]
    assert canonical_payload(manifest.comparison) == canonical_payload(case['comparison'])
    assert manifest.successful and manifest.exclusions == manifest.issues == ()


@pytest.mark.parametrize('kind', ['duplicate', 'bad_duplicate', 'third', 'zero', 'one'])
def test_failed_manifests_preserve_real_order_without_samples(case, kind):
    a, b = case['selection'].selected
    if kind in ('duplicate', 'bad_duplicate'):
        b = replace(b, provenance=replace(b.provenance, source=a.provenance.source))
        if kind == 'bad_duplicate': b = replace(b, verification='unverified')
        final = final_from(case, b, a)
        expected = [('b', 'unverified_input')] if kind == 'bad_duplicate' else []
        expected += [('b', 'duplicate_sample_measurement'), ('a', 'duplicate_sample_measurement')]
        if kind == 'bad_duplicate': expected += [(None, 'insufficient_eligible_inputs')]
    elif kind == 'third':
        final = final_from(case, a, b, creatinine('c', at=AT + timedelta(hours=2)))
        expected = [(None, 'ambiguous_eligible_inputs')]
    else:
        final = final_from(case, *((a,) if kind == 'one' else ()))
        expected = [(None, 'insufficient_eligible_inputs')]
    manifest = creatinine_trend_selection_manifest(final)
    assert [(i.reference.id if i.reference else None, i.code) for i in manifest.issues] == expected
    assert manifest.exclusions == final.exclusions and manifest.issues == final.issues
    assert manifest.selected == manifest.selected_payload_digests == manifest.selected_samples == ()
    assert manifest.selected_values == manifest.selected_sample_times == () and manifest.comparison is None


@pytest.mark.parametrize('field', ['refs', 'digests', 'samples', 'values', 'times', 'same_sample', 'same_family',
    'cutoff', 'longitudinal', 'window', 'unit', 'version', 'duplicate_exclusion', 'overlap', 'blocking', 'issue'])
def test_manifest_tampering(case, field):
    m = creatinine_trend_selection_manifest(case['selection'])
    if field in ('refs', 'digests', 'samples', 'values', 'times'):
        key = {'refs':'selected', 'digests':'selected_payload_digests', 'samples':'selected_samples',
            'values':'selected_values', 'times':'selected_sample_times'}[field]
        changes = {key:getattr(m, key)[:1]}
    elif field == 'same_sample': changes = dict(selected_samples=(m.selected_samples[0],)*2)
    elif field == 'same_family': changes = dict(selected=(m.selected[0], replace(m.selected[0], version='other')))
    elif field == 'cutoff': changes = dict(cutoff=m.cutoff.model_copy(update={'fact_watermark':-1}))
    elif field == 'longitudinal': changes = dict(target=replace(TARGET, encounter_id=None, longitudinal_context_id='long'))
    elif field == 'window': changes = dict(selected_sample_times=(POLICY.window_start-timedelta(seconds=1), m.selected_sample_times[1]))
    elif field == 'unit': changes = dict(policy=POLICY.model_copy(update={'unit':'kg'}))
    elif field == 'version': changes = dict(version='2')
    elif field == 'duplicate_exclusion':
        e = CreatinineTrendExclusion(reference=Reference(kind='observation', id='other', version='1'), reason='outside_sample_window')
        changes = dict(exclusions=(e, replace(e, reference=replace(e.reference, version='2'))))
    elif field == 'overlap': changes = dict(exclusions=(CreatinineTrendExclusion(reference=m.selected[0], reason='unrelated_concept'),))
    elif field == 'blocking': changes = dict(exclusions=(CreatinineTrendExclusion(reference=m.selected[0], reason='unsupported_unit'),))
    else: changes = dict(issues=(CreatinineTrendSelectionIssue(code='insufficient_eligible_inputs'),))
    with pytest.raises(ValueError): replace(m, **changes)


@pytest.mark.parametrize('kind', ['single_duplicate', 'duplicate_issue', 'global_order', 'two_globals', 'issue_without_exclusion', 'benign_duplicate'])
def test_failed_manifest_issue_consistency(kind):
    ref = Reference(kind='observation', id='a', version='1')
    duplicate = CreatinineTrendSelectionIssue(code='duplicate_sample_measurement', reference=ref)
    cardinality = CreatinineTrendSelectionIssue(code='insufficient_eligible_inputs')
    args = dict(target=TARGET, policy=POLICY, cutoff=cutoff(2))
    if kind == 'single_duplicate': args['issues'] = (duplicate,)
    elif kind == 'duplicate_issue': args['issues'] = (cardinality, cardinality)
    elif kind == 'global_order': args['issues'] = (cardinality, duplicate)
    elif kind == 'two_globals': args['issues'] = (cardinality, CreatinineTrendSelectionIssue(code='ambiguous_eligible_inputs'))
    elif kind == 'issue_without_exclusion': args['issues'] = (CreatinineTrendSelectionIssue(code='unsupported_unit', reference=ref),)
    else:
        args['issues'] = (duplicate, replace(duplicate, reference=replace(ref, id='b')))
        args['exclusions'] = (CreatinineTrendExclusion(reference=ref, reason='outside_sample_window'),)
    with pytest.raises(ValueError): CreatinineTrendSelectionManifest(**args)


@pytest.mark.parametrize('identifier', ['', ' ', ' sample-a', 'sample-a ', 42])
def test_sample_identity_does_not_silently_normalize(identifier):
    with pytest.raises(ValueError): CreatinineTrendSampleIdentity(namespace='clinrx.synthetic.serum-creatinine', identifier=identifier)


def test_lineage_witness_independent_contents(case):
    w = creatinine_trend_lineage_witness(case['lineage'])
    assert w.root == case['inference'].reference and w.target == TARGET and w.cutoff == cutoff(3)
    assert [n.reference.id for n in w.nodes] == ['b', 'a', 'creatinine-i1']
    assert [(e.relationship, e.target.id) for e in w.declarations] == [('derived_from', 'a'), ('derived_from', 'b')]
    assert [n.ingestion.ingestion_sequence for n in w.nodes] == [1, 2, 3]
    assert all(n.roles == ('evidence',) for n in w.nodes)
    assert {r.id for r in w.nodes[-1].ancestry} == {'a', 'b', 'creatinine-i1'}
    assert w.nodes[-1].limitations == ('Synthetic evaluation only; no clinical validity or source-authenticity claim.',)
    assert w.coverage == 'complete_for_declared_visible_graph' and not w.unresolved
    assert w.nodes[0].payload_digest == sha256(canonical_payload(case['selection'].selected[1]).encode()).hexdigest()


@pytest.mark.parametrize('part', ['root', 'scope', 'duplicate', 'order', 'ancestry', 'coverage', 'roles', 'declaration',
    'dependency', 'provenance', 'extra', 'metadata'])
def test_lineage_projection_rejects_contradictions(case, part):
    g = case['lineage']
    if part == 'root': g = dc_replace(g, reference=replace(g.reference, id='absent'))
    elif part == 'scope': g = dc_replace(g, target=replace(TARGET, encounter_id='other'))
    elif part == 'duplicate': g = dc_replace(g, nodes=(*g.nodes, g.nodes[0]))
    elif part == 'order': g = dc_replace(g, nodes=tuple(reversed(g.nodes)))
    elif part == 'ancestry': g = dc_replace(g, ancestry=g.ancestry[:-1])
    elif part == 'coverage': g = dc_replace(g, coverage='partial')
    elif part == 'roles': g = dc_replace(g, nodes=(dc_replace(g.nodes[0], roles=('association',)), *g.nodes[1:]))
    elif part == 'declaration': g = dc_replace(g, assertions=tuple(reversed(g.assertions)))
    elif part == 'dependency': g = dc_replace(g, dependencies=g.dependencies[:1])
    elif part == 'provenance': g = dc_replace(g, provenance=g.provenance[:-1])
    elif part == 'extra': g = dc_replace(g, confirmations=('unsupported',))
    else: g = dc_replace(g, cutoff=replace(g.cutoff, repository_id=EXECUTION))
    with pytest.raises(ValueError): creatinine_trend_lineage_witness(g)


def test_partial_witness_preserves_unresolved_and_cannot_be_completed_record(case):
    g = case['lineage']
    ref = case['selection'].selected[0].reference
    g = dc_replace(g, nodes=tuple(n for n in g.nodes if n.stored.fact.reference != ref),
        ancestry=tuple(p for p in g.ancestry if p[0] != ref), provenance=tuple(p for p in g.provenance if p.reference != ref),
        coverage='partial', unresolved=(UnresolvedReference(g.reference, ref, 'dependency', 0, None, 'not_resolvable_in_scope_at_cutoff'),))
    w = creatinine_trend_lineage_witness(g)
    assert w.coverage == 'partial' and w.unresolved == g.unresolved
    assert CreatinineTrendLineageWitness.model_validate_json(canonical_payload(w)) == w
    req = request_for(case, lineage=w)
    assert req.lineage.coverage == 'partial'
    with pytest.raises(ValueError): record(case, lineage=w)


@pytest.mark.parametrize('state', ['current', 'superseded', 'unavailable'])
def test_terminal_states(case, state):
    changes = {} if state == 'current' else dict(terminal=replace(case['inference'].reference, version='2')) if state == 'superseded' else dict(
        terminal=None, terminal_payload_digest=None, unavailable_reason='reader_unavailable')
    value = terminal(case, **changes)
    assert value.status == state
    check = recheck(case, **changes)
    assert check.outcome == {'current':'unchanged', 'superseded':'materially_changed', 'unavailable':'unavailable'}[state]
    assert record(case, check=check).decision.outcome == ('released' if state == 'current' else 'withheld')


@pytest.mark.parametrize('part', ['family', 'kind', 'digest', 'absence', 'unavailable_digest', 'found_with_reason', 'backward', 'repository'])
def test_terminal_invalid_evidence(case, part):
    changes = {'family':dict(terminal=Reference(kind='inference', id='other', version='1')),
        'kind':dict(terminal=Reference(kind='observation', id='a', version='1')),
        'digest':dict(terminal_payload_digest='0'*64), 'absence':dict(terminal=None, terminal_payload_digest=None),
        'unavailable_digest':dict(terminal=None, unavailable_reason='reader_unavailable'),
        'found_with_reason':dict(unavailable_reason='check_not_performed'),
        'backward':dict(cutoff=cutoff(2)), 'repository':dict(cutoff=replace(cutoff(3), repository_id=EXECUTION))}[part]
    with pytest.raises(ValueError): terminal(case, **changes)


@pytest.mark.parametrize('kind', ['changed_value', 'same_value', 'third', 'duplicate', 'unit', 'verification', 'conflict', 'provenance'])
def test_material_changes_from_real_selector(case, kind):
    a, b = case['selection'].selected
    changed = revision(a, '2')
    if kind == 'changed_value': changed = replace(changed, value=replace(a.value, value=replace(a.value.value, value=Decimal('1.10'))))
    elif kind == 'unit': changed = changed_unit(changed, raw='µmol/L', code='umol/L')
    elif kind == 'verification': changed = replace(changed, verification='unverified')
    elif kind == 'conflict': changed = replace(changed, conflict='unresolved')
    elif kind == 'provenance': changed = replace(changed, provenance=replace(changed.provenance, limitations=('unknown sample',)))
    facts = (changed, b)
    if kind in ('third', 'duplicate'):
        extra = creatinine('c', at=AT + timedelta(hours=2), sample='sample-a' if kind == 'duplicate' else 'sample-c')
        facts = (a, b, extra)
    final = final_from(case, *facts)
    check = recheck(case, final)
    assert check.outcome == 'materially_changed'
    assert check.reasons == (('selected_exact_references_changed',) if kind in ('same_value', 'changed_value') else ('final_selection_failed',))
    retained = record(case, check=check)
    assert retained.decision.outcome == 'withheld' and retained.comparison == case['comparison']
    assert retained.decision.assessment.state.freshness.material_change


@pytest.mark.parametrize('kind', ['unrelated', 'outside', 'inference', 'neutral'])
def test_harmless_growth_unchanged(case, kind):
    a, b = case['selection'].selected
    if kind == 'unrelated': extra = replace(creatinine('other'), concept_id='potassium')
    elif kind == 'outside': extra = creatinine('outside', at=POLICY.window_end)
    else: extra = case['inference']
    final = final_from(case, b, extra, a) if kind != 'neutral' else replace(case['selection'], cutoff=cutoff(3))
    check = recheck(case, final)
    assert check.outcome == 'unchanged' and check.reasons == ()
    assert check.original_manifest_digest == sha256(canonical_payload(check.original).encode()).hexdigest()


@pytest.mark.parametrize('part', ['digest', 'sample', 'decimal', 'offset'])
def test_same_ref_contradiction_never_material(case, part):
    before = creatinine_trend_selection_manifest(case['selection'])
    after = replace(before, cutoff=cutoff(3))
    if part == 'digest': after = replace(after, selected_payload_digests=('0'*64, after.selected_payload_digests[1]))
    elif part == 'sample': after = replace(after, selected_samples=(replace(after.selected_samples[0], identifier='different'), after.selected_samples[1]))
    elif part == 'decimal': after = replace(after, selected_values=(Decimal('1.0'), after.selected_values[1]))
    else: after = replace(after, selected_sample_times=(after.selected_sample_times[0].astimezone(timezone.utc), after.selected_sample_times[1]))
    with pytest.raises(StorageIntegrityError if part == 'digest' else ValueError):
        assess_creatinine_trend_final_recheck(original=before, final=after, inference_terminal=terminal(case))


@pytest.mark.parametrize('part', ['patient', 'encounter', 'policy', 'repository', 'input_prefix', 'output_prefix', 'terminal_cutoff', 'failed_original', 'version'])
def test_recheck_relations(case, part):
    check = recheck(case)
    if part in ('patient', 'encounter'):
        final = replace(check.final, target=replace(TARGET, **{part+'_id':'other'}))
        changes = dict(final=final)
    elif part == 'policy': changes = dict(final=replace(check.final, policy=replace(POLICY, available_at=POLICY.available_at+timedelta(seconds=1))))
    elif part == 'repository': changes = dict(final=replace(check.final, cutoff=replace(cutoff(3), repository_id=EXECUTION)))
    elif part == 'input_prefix': changes = dict(original=replace(check.original, cutoff=cutoff(4)))
    elif part == 'output_prefix': changes = dict(inference_terminal=terminal(case, historical_cutoff=cutoff(2)))
    elif part == 'terminal_cutoff': changes = dict(inference_terminal=terminal(case, cutoff(4)))
    elif part == 'failed_original': changes = dict(original=creatinine_trend_selection_manifest(final_from(case)))
    else: changes = dict(policy=replace(FINAL_RECHECK_POLICY, version='2'))
    with pytest.raises(ValueError): replace(check, **changes)


def test_request_projection_exact_and_generated_fields_excluded(case):
    req = request_for(case)
    value = record(case)
    assert set(json.loads(creatinine_trend_request_projection(req))) == {
        'execution_id', 'target', 'actor', 'original', 'comparison', 'inference', 'lineage', 'requested_at'}
    assert creatinine_trend_request_projection(value) == creatinine_trend_request_projection(req)
    assert req.execution_id == EXECUTION and req.target == GRANT_TARGET and req.actor == GRANT_ACTOR
    assert req.requested_at.isoformat().endswith('+05:30')
    payload = creatinine_trend_request_projection(req)
    assert '"earlier_value":"1.00"' in payload and '"later_value":"1.200"' in payload
    assert req.requested_at.isoformat() in payload
    assert creatinine_trend_request_projection(replace(value, finalized_at=NOW+timedelta(seconds=2))) == payload
    assert canonical_payload(value) != canonical_payload(replace(value, finalized_at=NOW+timedelta(seconds=2)))


@pytest.mark.parametrize('part', ['patient', 'encounter', 'comparison_value', 'comparison_scale', 'comparison_offset',
    'comparison_ref', 'inference', 'lineage', 'policy', 'selected_digest', 'root_sequence', 'extra'])
def test_request_cross_object_tampering(case, part):
    req = request_for(case)
    if part in ('patient', 'encounter'): changes = dict(target=replace(req.target, context=replace(TARGET, **{part+'_id':'other'})))
    elif part.startswith('comparison_'):
        comparison = req.comparison
        update = {'comparison_value':dict(earlier_value=Decimal('1.01')), 'comparison_scale':dict(earlier_value=Decimal('1.0')),
            'comparison_offset':dict(earlier_sample_time=comparison.earlier_sample_time.astimezone(timezone.utc)),
            'comparison_ref':dict(earlier_reference=replace(comparison.earlier_reference, version='2'))}[part]
        changes = dict(comparison=replace(comparison, **update))
    elif part == 'inference': changes = dict(inference=replace(req.inference, version='2'))
    elif part == 'lineage': changes = dict(lineage=replace(req.lineage, target=replace(TARGET, patient_id='other')))
    elif part == 'policy': changes = dict(original=req.original.model_copy(update={'policy':POLICY.model_copy(update={'version':'2'})}))
    elif part == 'selected_digest': changes = dict(original=replace(req.original, selected_payload_digests=('0'*64, req.original.selected_payload_digests[1])))
    elif part == 'root_sequence': changes = dict(original=replace(req.original, cutoff=cutoff(3)), lineage=replace(req.lineage, cutoff=cutoff(4)))
    else: changes = dict(decision={})
    with pytest.raises(ValueError): replace(req, **changes)


@pytest.mark.parametrize('part', ['actor', 'request_id', 'recipient', 'requested_at', 'requested_offset', 'cutoff_metadata', 'exclusions'])
def test_valid_request_changes_are_identity_changes(case, part):
    req = request_for(case)
    if part == 'actor': other = replace(req, actor='other')
    elif part in ('request_id', 'recipient'): other = replace(req, target=replace(req.target, **{part:'other'}))
    elif part == 'requested_at': other = replace(req, requested_at=req.requested_at-timedelta(microseconds=1))
    elif part == 'requested_offset': other = replace(req, requested_at=req.requested_at.astimezone(timezone.utc))
    elif part == 'cutoff_metadata': other = replace(req, original=replace(req.original, cutoff=replace(req.original.cutoff, captured_at=NOW+timedelta(seconds=1))))
    else:
        e = CreatinineTrendExclusion(reference=Reference(kind='observation', id='outside', version='1'), reason='outside_sample_window')
        other = replace(req, original=replace(req.original, exclusions=(e,)))
    assert creatinine_trend_request_projection(other) != creatinine_trend_request_projection(req)


@pytest.mark.parametrize('actor,outcome', [(GRANT_ACTOR, 'released'), ('denied', 'withheld')])
def test_completed_records_roundtrip(case, actor, outcome):
    value = record(case, actor=actor)
    assert value.disposition == 'completed_' + outcome
    assert value.decision.assessment.assessor == 'SyntheticCreatinineProtectedExecution/v1'
    assert value.repository_id == REPOSITORY
    assert CreatinineTrendExecutionRecord.model_validate_json(canonical_payload(value)) == value
    assert 'outcome' not in value.final_recheck.model_dump() and 'reasons' not in value.final_recheck.model_dump()
    assert 'issue' not in value.model_dump()
    wrapped = StoredCreatinineTrendExecution(record=value, ingested_at=NOW)
    assert wrapped.ingested_at.isoformat() == NOW.isoformat()
    assert StoredCreatinineTrendExecution.model_validate_json(canonical_payload(wrapped)) == wrapped


@pytest.mark.parametrize('part', ['workflow', 'final_context', 'actor', 'target', 'lineage_digest', 'lineage_provenance',
    'recheck_original', 'terminal_digest', 'requested', 'started', 'finalized', 'implementation', 'decision', 'issue'])
def test_execution_tampering_rejected(case, part):
    value = record(case)
    if part in ('workflow', 'final_context'):
        a = value.decision.assessment
        if part == 'workflow': a = replace(a, assessor='SyntheticWeightProtectedExecution/v1')
        else: a = replace(a, state=replace(a.state, freshness=replace(a.state.freshness, assessor='historical-only')))
        changes = dict(decision=decide_release(reference=value.decision.reference, assessment=a, actor=value.actor, at=NOW))
    elif part == 'actor': changes = dict(actor='other')
    elif part == 'target': changes = dict(target=replace(value.target, recipient='other'))
    elif part.startswith('lineage_'):
        nodes = value.lineage.nodes
        node = replace(nodes[-1], **({'payload_digest':'0'*64} if part == 'lineage_digest' else {'limitations':()}))
        changes = dict(lineage=replace(value.lineage, nodes=(*nodes[:-1], node)))
    elif part == 'recheck_original': changes = dict(final_recheck=replace(value.final_recheck,
        original=replace(value.original, cutoff=replace(value.original.cutoff, captured_at=NOW+timedelta(seconds=1)))))
    elif part == 'terminal_digest':
        t = replace(value.final_recheck.inference_terminal, consumed_payload_digest='0'*64, terminal_payload_digest='0'*64)
        changes = dict(final_recheck=replace(value.final_recheck, inference_terminal=t))
    elif part == 'requested': changes = dict(requested_at=NOW)
    elif part == 'started': changes = dict(started_at=NOW+timedelta(seconds=1))
    elif part == 'finalized': changes = dict(finalized_at=NOW-timedelta(seconds=1))
    elif part == 'implementation': changes = dict(implementation=replace(value.implementation, version='2'))
    elif part == 'decision': changes = dict(decision=value.decision.model_copy(update={'outcome':'withheld'}))
    else: changes = dict(issue={'code':'internal_failure'})
    with pytest.raises(ValueError): replace(value, **changes)


@pytest.mark.parametrize('version', [0, 2, True, '1', 1.0])
def test_strict_payload_version(case, version):
    with pytest.raises(ValueError): record(case, payload_version=version)


@pytest.mark.parametrize('part', ['manifest', 'sample', 'metadata', 'request', 'record', 'claim', 'witness', 'recheck', 'stored'])
def test_deep_immutability(case, part):
    value = record(case)
    wrapper = StoredCreatinineTrendExecution(record=value, ingested_at=NOW)
    obj, field, new = {'manifest':(value.original, 'selected', ()), 'sample':(value.original.selected_samples[0], 'identifier', 'other'),
        'metadata':(value.lineage.nodes[0].ingestion, 'ingestion_sequence', 999), 'request':(value.request, 'actor', 'other'),
        'record':(value, 'actor', 'other'), 'claim':(value.decision.assessment.review.candidate.claims[0], 'action', 'AKI'),
        'witness':(value.lineage, 'coverage', 'partial'), 'recheck':(value.final_recheck, 'original', None),
        'stored':(wrapper, 'ingested_at', NOW+timedelta(seconds=1))}[part]
    with pytest.raises(ValidationError): setattr(obj, field, new)


def test_valid_inference_revision_metadata_retained_without_extra_ancestry(case):
    old = case['inference']
    revised = replace(old, revision='2', supersedes=old.reference, correction_reason='synthetic correction')
    g = case['lineage']
    g = dc_replace(g, reference=revised.reference,
        nodes=(*g.nodes[:2], ResolvedNode(stored(revised, 3), ('evidence',))),
        assertions=tuple(dc_replace(a, owner=revised.reference) for a in g.assertions),
        dependencies=tuple(dc_replace(d, owner=revised.reference) for d in g.dependencies),
        provenance=(*g.provenance[:2], ProvenanceDisclosure(revised.reference, revised.provenance.lineage, revised.provenance.limitations)),
        ancestry=(*g.ancestry[:2], (revised.reference, frozenset((revised.reference, *revised.inputs)))))
    changed = compose({**case, 'inference':revised, 'lineage':g})
    value = record(changed)
    assert value.decision.outcome == 'released'
    assert old.reference not in value.lineage.nodes[-1].ancestry
    assert value.lineage.direct_dependencies == revised.inputs
    root = value.decision.assessment.review.candidate.snapshot.facts[-1]
    assert root.supersedes == old.reference and root.correction_reason == 'synthetic correction'


def test_changed_recheck_cannot_accompany_released_or_adequate_context(case):
    value = record(case)
    check = recheck(case, terminal=replace(case['inference'].reference, version='2'))
    with pytest.raises(ValueError): replace(value, final_recheck=check)
    withheld = record(case, check=check)
    a = withheld.decision.assessment
    a = replace(a, state=replace(a.state, freshness=replace(a.state.freshness, material_change=False)))
    d = decide_release(reference=withheld.decision.reference, assessment=a, actor=withheld.actor, at=NOW)
    with pytest.raises(ValueError): replace(withheld, decision=d)


@pytest.mark.parametrize('kind', ['naive', 'offset', 'forged_record'])
def test_stored_wrapper_validates_input(case, kind):
    value = record(case)
    changes = dict(record=value, ingested_at=NOW)
    if kind == 'naive': changes['ingested_at'] = NOW.replace(tzinfo=None)
    elif kind == 'offset': changes['ingested_at'] = NOW.astimezone(AT.tzinfo)
    else: changes['record'] = value.model_copy(update={'actor':''})
    with pytest.raises(ValueError): StoredCreatinineTrendExecution(**changes)


def test_recheck_and_projection_no_database_or_clock(case, monkeypatch):
    import sqlite3
    from sqlalchemy.engine import Engine, Connection
    from sqlalchemy.orm import Session
    def forbidden(*args, **kwargs): pytest.fail('pure D1 code performed storage or governance work')
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    monkeypatch.setattr(Engine, 'connect', forbidden)
    monkeypatch.setattr(Connection, 'execute', forbidden)
    monkeypatch.setattr(Session, 'execute', forbidden)
    import app.services.governance_service as governance
    monkeypatch.setattr(governance, 'assess_release', forbidden)
    monkeypatch.setattr(governance, 'decide_release', forbidden)
    assert recheck(case).outcome == 'unchanged'
    assert creatinine_trend_request_projection(request_for(case))


@pytest.mark.parametrize('seed', ['1', '777'])
def test_hash_seed_independence(seed):
    root = Path(__file__).resolve().parents[1]
    script = 'from test_creatinine_trend_execution import pure_case,record,canonical_payload; print(canonical_payload(record(pure_case())))'
    proc = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, check=True, timeout=30,
        env={**os.environ, 'PYTHONHASHSEED':seed, 'PYTHONDONTWRITEBYTECODE':'1',
             'PYTHONPATH':os.pathsep.join((str(root/'backend'), str(root/'tests')))})
    assert proc.stdout.strip() == canonical_payload(record(pure_case()))


def test_no_weight_or_framework_or_runtime_dependencies():
    import ast
    import app.execution.creatinine_trend_execution as module
    source = Path(module.__file__).read_text()
    tree = ast.parse(source)
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any('weight' in name or 'sqlalchemy' in name or 'workflow' in name for name in imports)
    assert not any(name in source for name in ('execute_creatinine', 'reconcile_creatinine', 'datetime.now', 'BEGIN IMMEDIATE'))
    classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    assert classes == {'CreatinineTrendSampleIdentity', 'CreatinineTrendSelectionManifest', 'CreatinineTrendLineageNodeWitness',
        'CreatinineTrendLineageWitness', 'CreatinineTrendInferenceTerminalCheck', 'CreatinineTrendFinalRecheck',
        'CreatinineTrendReviewRequest', 'CreatinineTrendExecutionRecord', 'StoredCreatinineTrendExecution'}


@pytest.mark.parametrize('which', ['assertion', 'dependency'])
def test_boolean_lineage_ordinal_is_not_an_integer_assertion(case, which):
    graph = case['lineage']
    field = 'assertions' if which == 'assertion' else 'dependencies'
    entries = getattr(graph, field)
    altered = dc_replace(graph, **{field:(dc_replace(entries[0], ordinal=False), *entries[1:])})
    with pytest.raises(ValueError): creatinine_trend_lineage_witness(altered)


@pytest.mark.parametrize('part', ['candidate', 'rendering', 'safety', 'fidelity', 'freshness', 'runtime', 'authorization'])
def test_record_requires_governance_evidence_inside_execution_interval(case, part):
    value = record(case)
    a = value.decision.assessment
    # A valid negative decision can disclose stale evidence, but a protected record
    # must not claim those objects were freshly produced by this execution.
    old = value.started_at - timedelta(microseconds=1)
    review = a.review
    with pytest.raises(ValueError):
        if part == 'candidate':
            candidate = replace(review.candidate, created_at=old,
                provenance=replace(review.candidate.provenance, recorded_at=old))
            a = replace(a, review=replace(review, candidate=candidate))
        elif part == 'rendering': a = replace(a, review=replace(review, rendering=replace(review.rendering, rendered_at=old)))
        elif part == 'safety': a = replace(a, review=replace(review, evaluations=(replace(review.evaluations[0], evaluated_at=old),)))
        elif part == 'fidelity': a = replace(a, content_validation=replace(a.content_validation, assessed_at=old))
        elif part == 'freshness': a = replace(a, state=replace(a.state, freshness=replace(a.state.freshness, assessed_at=old)))
        elif part == 'runtime': a = replace(a, state=replace(a.state, observed_at=old))
        else: a = replace(a, state=replace(a.state, authorization=replace(a.state.authorization, issued_at=old)))
        decision = decide_release(reference=value.decision.reference, assessment=a, actor=value.actor, at=NOW)
        replace(value, decision=decision)



@pytest.mark.parametrize('part', ['declarations', 'nodes', 'metadata', 'provenance'])
def test_witness_deep_tampering_rejected_by_record(case, part):
    value = record(case)
    w = value.lineage
    if part == 'declarations': changes = dict(declarations=tuple(reversed(w.declarations)))
    elif part == 'nodes': changes = dict(nodes=tuple(reversed(w.nodes)))
    elif part == 'metadata': changes = dict(cutoff=replace(w.cutoff, repository_id=EXECUTION))
    else: changes = dict(nodes=(replace(w.nodes[0], lineage='unknown', limitations=('unknown',)), *w.nodes[1:]))
    with pytest.raises(ValueError): replace(value, lineage=w.model_copy(update=changes))


def test_recheck_detects_contradiction_even_if_other_ref_changes(case):
    before = creatinine_trend_selection_manifest(case['selection'])
    after = replace(before, cutoff=cutoff(3), selected=(replace(before.selected[0], version='2'), before.selected[1]),
        selected_payload_digests=(before.selected_payload_digests[0], '0'*64))
    with pytest.raises(StorageIntegrityError):
        assess_creatinine_trend_final_recheck(original=before, final=after, inference_terminal=terminal(case))


def test_manifest_exclusion_and_issue_array_order_is_retained(case):
    a, b = case['selection'].selected
    one = replace(creatinine('x'), conflict='unresolved')
    two = changed_unit(creatinine('y'), raw='mgdl')
    final = final_from(case, two, b, one, a)
    m = creatinine_trend_selection_manifest(final)
    assert [e.reference.id for e in m.exclusions] == ['y', 'x']
    assert [(i.reference.id, i.code) for i in m.issues] == [('y', 'unsupported_unit'), ('x', 'unresolved_conflict')]
    with pytest.raises(ValueError): replace(m, issues=tuple(reversed(m.issues)))


def test_array_order_and_ancestry_set_canonicalization(case):
    w = creatinine_trend_lineage_witness(case['lineage'])
    root = replace(w.nodes[-1], ancestry=tuple(reversed(w.nodes[-1].ancestry)))
    assert canonical_payload(replace(w, nodes=(*w.nodes[:-1], root))) == canonical_payload(w)
    assert w.direct_dependencies == case['inference'].inputs
    with pytest.raises(ValueError): replace(w, nodes=tuple(reversed(w.nodes)))


def test_lossy_second_offset_rejected_at_manifest_boundary(case):
    m = creatinine_trend_selection_manifest(case['selection'])
    t = (m.selected_sample_times[0] + timedelta(minutes=1)).replace(tzinfo=timezone(timedelta(hours=5, minutes=30, seconds=1)))
    with pytest.raises(UnsupportedOperation): replace(m, selected_sample_times=(t, m.selected_sample_times[1]))


def test_repeated_pure_evaluation_and_stored_metadata_are_exact(case):
    first = record(case)
    assert canonical_payload(record(case)) == canonical_payload(first)
    original = StoredCreatinineTrendExecution(record=first, ingested_at=NOW-timedelta(days=1))
    assert StoredCreatinineTrendExecution.model_validate_json(canonical_payload(original)).ingested_at == original.ingested_at
    assert creatinine_trend_request_projection(original.record) == creatinine_trend_request_projection(first.request)
