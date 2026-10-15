"""Pure Phase 4 contracts; explicit synthetic evidence, no database fixtures."""
from dataclasses import replace as dc_replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.execution.weight_trend import (
    WeightTrendExclusion, WeightTrendSelectionIssue, WeightTrendSelectionResult,
    compare_recorded_weights, select_weight_observations,
)
from app.execution.weight_trend_execution import (
    FINAL_RECHECK_POLICY, WeightTrendExecutionIssue, WeightTrendExecutionRecord,
    WeightTrendFinalRecheck, WeightTrendInferenceTerminalCheck, WeightTrendLineageWitness,
    WeightTrendSelectionManifest, assess_weight_trend_final_recheck,
    weight_trend_lineage_witness, weight_trend_selection_manifest,
)
from app.execution.weight_trend_release import (
    GRANT_TARGET, build_weight_trend_snapshot, build_weight_trend_candidate, render_weight_trend,
)
from app.models.clinical.common import Reference
from app.persistence.errors import StorageIntegrityError
from app.persistence.history import HistoryResult
from app.persistence.lineage import (
    Dependency, LineageAssertion, LineageResult, ProvenanceDisclosure, ResolvedNode, UnresolvedReference,
)
from app.persistence.mapping import StoredFact, canonical_payload
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff
from app.services.governance_service import decide_release
from test_persistence import AT, TARGET, patient, encounter, replace
from test_revision_chains import revision
from test_weight_trend import POLICY, weight
from test_weight_trend_inference import build
from test_weight_trend_release import NOW, run

REPOSITORY = UUID('00000000-0000-4000-8000-000000000001')
EXECUTION = UUID('00000000-0000-4000-8000-000000000002')


def cutoff(watermark):
    return RepositoryCutoff(repository_id=REPOSITORY, fact_watermark=watermark, captured_at=NOW)


def stored(fact, sequence):
    return StoredFact(fact, IngestionMetadata(repository_id=REPOSITORY,
        ingestion_sequence=sequence, ingested_at=NOW))


def pure_case():
    a, b = weight('a', '82.00', label='z'), weight('b', '79.00', AT + timedelta(hours=1), label='0')
    selection = WeightTrendSelectionResult(target=TARGET, policy=POLICY, cutoff=cutoff(2), selected=(a,b))
    comparison = compare_recorded_weights(selection)
    inference = build(selection)
    root = inference.reference
    # Deliberately opposite to event order, as permitted by the repository.
    nodes = tuple(ResolvedNode(stored(f, i), ('evidence',)) for i,f in enumerate((b,a,inference),1))
    graph = LineageResult(reference=root, target=TARGET, cutoff=cutoff(3), nodes=nodes,
        assertions=tuple(LineageAssertion(root,i,e) for i,e in enumerate(inference.provenance.upstream)),
        dependencies=tuple(Dependency(root,i,None,f.reference) for i,f in enumerate((a,b))),
        associations=(), unresolved=(), confirmations=(),
        provenance=tuple(ProvenanceDisclosure(n.stored.fact.reference,n.stored.fact.provenance.lineage,
            n.stored.fact.provenance.limitations) for n in nodes),
        ancestry=((b.reference,frozenset((b.reference,))), (a.reference,frozenset((a.reference,))),
                  (root,frozenset((root,a.reference,b.reference)))),
        coverage='complete_for_declared_visible_graph')
    snapshot = build_weight_trend_snapshot(selection=selection,inference=inference,lineage=graph,
        patient=patient(),encounter=encounter(),at=NOW,id='snapshot')
    candidate = build_weight_trend_candidate(snapshot=snapshot,comparison=comparison,
        inference=inference,at=NOW,id='candidate')
    rendering = render_weight_trend(candidate=candidate,comparison=comparison,target=GRANT_TARGET,
        at=NOW,id='rendering')
    return dict(selection=selection,comparison=comparison,inference=inference,lineage=graph,
        snapshot=snapshot,candidate=candidate,rendering=rendering,target=GRANT_TARGET)


@pytest.fixture
def case():
    return pure_case()


def check(case, final=None, terminal='current'):
    final = replace(case['selection'],cutoff=cutoff(3)) if final is None else final
    consumed = case['inference'].reference
    terminal = consumed if terminal == 'current' else terminal
    return assess_weight_trend_final_recheck(original=case['selection'],final=final,
        inference_terminal=WeightTrendInferenceTerminalCheck(target=TARGET,cutoff=final.cutoff,
            consumed=consumed,terminal=terminal))


def record(case, **changes):
    args = dict(execution_id=EXECUTION,target=GRANT_TARGET,actor='synthetic-orchestrator',
        original=weight_trend_selection_manifest(case['selection']),comparison=case['comparison'],
        inference=case['inference'].reference,lineage=weight_trend_lineage_witness(case['lineage']),
        final_recheck=check(case),decision=run(case),started_at=NOW-timedelta(seconds=1),
        finalized_at=NOW+timedelta(seconds=1))
    args.update(changes)
    return WeightTrendExecutionRecord(**args)


def final_from_terminals(case, *facts):
    """An explicit terminal-reader double; no history or DB behavior is implemented here."""
    class Reader:
        def list_bounded_history(self, *, target, cutoff, latest, budget, family_budget, accounting):
            assert latest is True and budget.max_rows==4096 and accounting is not None
            return HistoryResult(target=target,cutoff=cutoff,
                records=tuple(stored(f,i) for i,f in enumerate(facts,1)),selection='latest_known')
    return select_weight_observations(Reader(),target=TARGET,cutoff=cutoff(8),policy=POLICY)


def withheld_for_context(decision, *, material):
    assessment = decision.assessment
    freshness = replace(assessment.state.freshness,adequate=False,material_change=material)
    assessment = replace(assessment,state=replace(assessment.state,freshness=freshness))
    return decide_release(reference=decision.reference,assessment=assessment,actor=decision.actor,at=decision.at)


def test_unchanged_exact_pair_and_inference_insertion(case):
    result = check(case)
    assert result.policy == Reference(kind='final_recheck_policy',id='WeightTrendFinalRecheckPolicy',version='1')
    assert result.outcome == 'unchanged' and result.reasons == ()
    assert result.original_selected == result.final.selected == (
        Reference(kind='observation',id='a',version='z'),Reference(kind='observation',id='b',version='0'))
    assert result.final.cutoff.fact_watermark == 3 > case['selection'].cutoff.fact_watermark
    assert result.inference_terminal.status == 'current'


@pytest.mark.parametrize('value', ['81.00','82.00'])
def test_new_exact_revision_is_material_even_if_numerically_equal(case,value):
    a,b = case['selection'].selected
    a2 = revision(a,'new',value=replace(a.value,value=replace(a.value.value,value=Decimal(value))))
    result = check(case,final_from_terminals(case,b,a2))
    assert result.outcome == 'materially_changed'
    assert result.reasons == ('selected_exact_references_changed',)
    assert result.final.selected == (a2.reference,b.reference)


@pytest.mark.parametrize('change,expected', [
    ('unit','unsupported_unit'),('zero','invalid_value'),('conflict','unresolved_conflict'),
    ('time','invalid_or_missing_event_time'),('availability','source_unavailable_at_cutoff'),
    ('window','insufficient_eligible_inputs'),('concept','insufficient_eligible_inputs'),
    ('third','ambiguous_eligible_inputs'),
])
def test_relevant_terminal_changes_block(case,change,expected):
    a,b = case['selection'].selected
    a2 = revision(a,'new')
    if change == 'unit':
        a2 = replace(a2,value=replace(a2.value,value=replace(a2.value.value,
            unit=replace(a2.value.value.unit,raw='lb',code='lb'))))
    elif change == 'zero':
        a2 = replace(a2,value=replace(a2.value,value=replace(a2.value.value,value=Decimal(0))))
    elif change == 'conflict':
        a2 = replace(a2,conflict='unresolved')
    elif change == 'time':
        a2 = replace(a2,time=replace(a2.time,event=None,precision='unknown'))
    elif change == 'availability':
        a2 = replace(a2,provenance=replace(a2.provenance,recorded_at=POLICY.available_at+timedelta(microseconds=1)))
    elif change == 'window':
        a2 = replace(a2,time=replace(a2.time,event=POLICY.window_end))
    elif change == 'concept':
        a2 = replace(a2,concept_id='height')
    facts = (a,b,weight('c',at=AT+timedelta(hours=2))) if change == 'third' else (a2,b)
    final = final_from_terminals(case,*facts)
    assert expected in tuple(i.code for i in final.issues)
    result = check(case,final)
    assert result.outcome == 'materially_changed' and result.reasons == ('final_selection_failed',)
    assert result.final.selected == ()


@pytest.mark.parametrize('reason', ['unrelated_fact','unrelated_concept','outside_comparison_window'])
def test_harmless_exclusion_growth_not_material(case,reason):
    final = replace(case['selection'],cutoff=cutoff(10),exclusions=(
        WeightTrendExclusion(reference=Reference(kind='observation',id='other',version='1'),reason=reason),))
    result = check(case,final)
    assert result.outcome == 'unchanged' and result.reasons == ()
    assert len(result.final.exclusions) == 1


def test_exact_window_end_is_harmless_for_an_additional_measurement(case):
    a,b = case['selection'].selected
    final = final_from_terminals(case,a,b,weight('outside',at=POLICY.window_end))
    assert [(e.reference.id,e.reason) for e in final.exclusions] == [('outside','outside_comparison_window')]
    assert check(case,final).outcome == 'unchanged'


def test_inclusive_availability_boundary(case):
    a,b = case['selection'].selected
    # New revision is material, but remains eligible exactly at the source bound.
    a2 = revision(a,'new',provenance=replace(a.provenance,recorded_at=POLICY.available_at))
    final = final_from_terminals(case,a2,b)
    assert final.successful and check(case,final).reasons == ('selected_exact_references_changed',)


@pytest.mark.parametrize('terminal,expected', [('new','materially_changed'),(None,'unavailable')])
def test_inference_terminal_status(case,terminal,expected):
    ref = None if terminal is None else replace(case['inference'].reference,version=terminal)
    result = check(case,terminal=ref)
    assert result.outcome == expected
    assert result.reasons == (('inference_unavailable',) if terminal is None else ('inference_superseded',))


@pytest.mark.parametrize('change', ['value','decimal','offset','uncertainty'])
def test_same_exact_ref_payload_contradiction_is_integrity_failure(case,change):
    a,b = case['selection'].selected
    if change in ('value','decimal'):
        a = replace(a,value=replace(a.value,value=replace(a.value.value,value=Decimal('83' if change=='value' else '82.0'))))
    elif change == 'offset':
        a = replace(a,time=replace(a.time,event=a.time.event.astimezone(timezone.utc)))
    else:
        a = replace(a,uncertainty=('another synthetic uncertainty',))
    final = replace(case['selection'],cutoff=cutoff(3),selected=(a,b))
    with pytest.raises(StorageIntegrityError,match='^contradictory retained weight evidence$'):
        check(case,final)


@pytest.mark.parametrize('field', ['target','policy','repository','backward','terminal_scope','terminal_cutoff'])
def test_recheck_cannot_change_scope_policy_or_prefix(case,field):
    final = replace(case['selection'],cutoff=cutoff(3))
    terminal = WeightTrendInferenceTerminalCheck(target=TARGET,cutoff=cutoff(3),
        consumed=case['inference'].reference,terminal=case['inference'].reference)
    if field == 'target':
        # Failed result isolates scope validation from observation binding validation.
        final = WeightTrendSelectionResult(target=replace(TARGET,encounter_id='other'),policy=POLICY,
            cutoff=cutoff(3),issues=(WeightTrendSelectionIssue(code='insufficient_eligible_inputs'),))
    elif field == 'policy':
        final = replace(final,policy=replace(POLICY,available_at=POLICY.available_at+timedelta(seconds=1)))
    elif field == 'repository':
        final = replace(final,cutoff=replace(cutoff(3),repository_id=EXECUTION))
    elif field == 'backward':
        final = replace(final,cutoff=cutoff(1))
    elif field == 'terminal_scope':
        terminal = replace(terminal,target=replace(TARGET,patient_id='other'))
    else:
        terminal = replace(terminal,cutoff=cutoff(4))
    with pytest.raises(ValueError):
        assess_weight_trend_final_recheck(original=case['selection'],final=final,inference_terminal=terminal)


def test_terminal_different_stable_identity_rejected(case):
    with pytest.raises(ValidationError):
        check(case,terminal=Reference(kind='inference',id='other',version='1'))


def test_recheck_repeats_deterministically_and_serializes_derived_result(case):
    first = check(case)
    assert canonical_payload(first) == canonical_payload(check(case))
    replay = WeightTrendFinalRecheck.model_validate_json(canonical_payload(first))
    assert replay.outcome == 'unchanged' and replay.reasons == ()
    assert 'outcome' not in replay.model_dump()  # Derived, never a contradictory stored status.


@pytest.mark.parametrize('variant,expected', [('released','completed_released'),('withheld','completed_withheld'),('issue','failed_operationally')])
def test_variants(case,variant,expected):
    changes = {}
    if variant == 'withheld':
        changes = dict(actor='synthetic-denied',decision=run(case,actor='synthetic-denied'))
    elif variant == 'issue':
        changes = dict(decision=None,lineage=None,final_recheck=None,
            issue=WeightTrendExecutionIssue(stage='final_recheck',code='integrity_failure'))
    result = record(case,**changes)
    assert result.disposition == expected and result.repository_id == REPOSITORY
    assert (result.decision is None) == (variant == 'issue')
    assert canonical_payload(WeightTrendExecutionRecord.model_validate_json(canonical_payload(result))) == canonical_payload(result)


@pytest.mark.parametrize('both', [False,True])
def test_exactly_one_variant(case,both):
    issue = WeightTrendExecutionIssue(stage='governance',code='internal_failure')
    with pytest.raises(ValidationError,match='exactly one'):
        record(case,decision=run(case) if both else None,issue=issue if both else None)


@pytest.mark.parametrize('version', [0,2,'1',True,1.0])
def test_unsupported_payload_versions(case,version):
    with pytest.raises(ValidationError):
        record(case,payload_version=version)


@pytest.mark.parametrize('field', ['id','time','actor','target','comparison','inference','lineage','recheck','implementation'])
def test_execution_binding_rejections(case,field):
    value = record(case)
    changes = {
        'id':dict(execution_id='not-a-uuid'),'time':dict(finalized_at=NOW-timedelta(seconds=2)),
        'actor':dict(actor='another-actor'),'target':dict(target=replace(GRANT_TARGET,request_id='other')),
        'comparison':dict(comparison=replace(case['comparison'],earlier_kg=Decimal('83'))),
        'inference':dict(inference=replace(case['inference'].reference,version='other')),
        'lineage':dict(lineage=None),'recheck':dict(final_recheck=None),
        'implementation':dict(implementation=replace(value.implementation,version='2')),
    }[field]
    with pytest.raises(ValidationError):
        replace(value,**changes)


@pytest.mark.parametrize('terminal', ['new',None])
def test_changed_or_unavailable_cannot_retain_released_decision(case,terminal):
    check_result = check(case,terminal=None if terminal is None else replace(case['inference'].reference,version=terminal))
    with pytest.raises(ValidationError,match='cannot support release'):
        record(case,final_recheck=check_result)
    withheld = withheld_for_context(run(case),material=terminal is not None)
    value = record(case,final_recheck=check_result,decision=withheld)
    assert value.disposition == 'completed_withheld'
    if terminal is not None:
        with pytest.raises(ValidationError,match='retain the established material change'):
            record(case,final_recheck=check_result,decision=withheld_for_context(run(case),material=False))


def test_immutability_and_copy_escape_revalidation(case):
    value = record(case)
    for obj,field,new in [(value,'actor','other'),(value.original.policy,'version','2'),
        (value.original.cutoff,'fact_watermark',100), (value.lineage.nodes[0].ingestion,'ingestion_sequence',99),
        (value.decision.assessment.review.candidate.claims[0],'action','other'),
        (value.final_recheck.inference_terminal,'terminal',None)]:
        with pytest.raises(ValidationError):
            setattr(obj,field,new)
    forged = value.original.cutoff.model_copy(update={'fact_watermark':-1})
    with pytest.raises(ValidationError):
        replace(value.original,cutoff=forged)
    forged = value.model_copy(update={'decision':None,'issue':None})
    with pytest.raises(ValidationError):
        WeightTrendExecutionRecord.model_validate(forged)


def test_representation_uuid_and_nested_decision_round_trip(case):
    value = record(case)
    payload = canonical_payload(value)
    replay = WeightTrendExecutionRecord.model_validate_json(payload)
    assert replay.model_dump_json() == value.model_dump_json()
    assert '"earlier_kg":"82.00"' in payload and '"later_kg":"79.00"' in payload
    assert '2026-09-25T15:30:00.123456+05:30' in payload
    assert replay.execution_id == EXECUTION
    assert replay.decision.model_dump_json() == value.decision.model_dump_json()
    assert canonical_payload(value) == payload
    assert canonical_payload(replace(value,execution_id=REPOSITORY)) != payload
    assert 'disposition' not in value.model_dump() and 'status' not in value.model_dump()


def test_actual_instant_execution_times_across_dst_fold(case):
    tz = ZoneInfo('America/New_York')
    first = datetime(2026,11,1,1,30,tzinfo=tz,fold=0)
    later = datetime(2026,11,1,1,30,tzinfo=tz,fold=1)
    issue = WeightTrendExecutionIssue(stage='recovery',code='commit_outcome_unknown')
    value = record(case,decision=None,issue=issue,started_at=first,finalized_at=later)
    assert '-04:00' in value.model_dump_json() and '-05:00' in value.model_dump_json()
    with pytest.raises(ValidationError,match='finalization'):
        replace(value,started_at=later,finalized_at=first)


@pytest.mark.parametrize('change', ['duplicate','extra','order','metadata','ancestry','coverage','edge','unresolved'])
def test_malformed_lineage_witness(case,change):
    witness = weight_trend_lineage_witness(case['lineage'])
    if change == 'duplicate':
        changes = dict(nodes=(*witness.nodes,witness.nodes[0]))
    elif change == 'extra':
        changes = dict(root=replace(witness.root,id='other'))
    elif change == 'order':
        changes = dict(nodes=tuple(reversed(witness.nodes)))
    elif change == 'metadata':
        changes = dict(cutoff=replace(witness.cutoff,repository_id=EXECUTION))
    elif change == 'ancestry':
        changes = dict(nodes=(*witness.nodes[:2],replace(witness.nodes[2],ancestry=(witness.root,))))
    elif change == 'coverage':
        changes = dict(coverage='partial')
    elif change == 'edge':
        changes = dict(declarations=tuple(reversed(witness.declarations[:1])))
    else:
        changes = dict(unresolved=(UnresolvedReference(witness.root,witness.direct_dependencies[0],
            'dependency',0,None,'not_resolvable_in_scope_at_cutoff'),))
    with pytest.raises(ValidationError):
        replace(witness,**changes)


def test_lineage_order_is_explicit_and_payload_free(case):
    witness = weight_trend_lineage_witness(case['lineage'])
    assert tuple(n.reference.id for n in witness.nodes) == ('b','a','weight-trend-1')
    assert tuple(r.id for r in witness.nodes[-1].ancestry) == ('weight-trend-1','a','b')
    assert tuple(r.id for r in witness.direct_dependencies) == ('a','b')
    root = replace(witness.nodes[-1],ancestry=tuple(reversed(witness.nodes[-1].ancestry)))
    assert canonical_payload(replace(witness,nodes=(*witness.nodes[:2],root))) == canonical_payload(witness)
    assert 'fact' not in witness.nodes[0].model_dump() and 'value' not in witness.nodes[0].model_dump()


def test_partial_lineage_disclosures_sort_and_round_trip(case):
    witness = weight_trend_lineage_witness(case['lineage'])
    unresolved = tuple(UnresolvedReference(witness.root,r,'dependency',i,None,
        'not_resolvable_in_scope_at_cutoff') for i,r in enumerate(witness.direct_dependencies))
    partial = replace(witness,nodes=(witness.nodes[-1],),coverage='partial',unresolved=unresolved[::-1])
    assert tuple(u.ordinal for u in partial.unresolved) == (0,1)
    assert canonical_payload(partial) == canonical_payload(replace(partial,unresolved=unresolved))
    assert WeightTrendLineageWitness.model_validate_json(canonical_payload(partial)) == partial
    with pytest.raises(ValidationError,match='partial lineage'):
        record(case,lineage=partial)
    value = record(case,lineage=partial,decision=withheld_for_context(run(case),material=False))
    assert value.disposition == 'completed_withheld'


@pytest.mark.parametrize('change', ['empty','duplicate','same_family','digest','blocking','issue','overlap'])
def test_malformed_selection_manifest(case,change):
    manifest = weight_trend_selection_manifest(case['selection'])
    a,b = manifest.selected
    changes = {
        'empty':dict(selected=()),'duplicate':dict(selected=(a,a)),
        'same_family':dict(selected=(a,replace(a,version='other'))),
        'digest':dict(selected_payload_digests=('invalid',manifest.selected_payload_digests[1])),
        'blocking':dict(exclusions=(WeightTrendExclusion(reference=replace(a,id='c'),reason='unresolved_conflict'),)),
        'issue':dict(issues=(WeightTrendSelectionIssue(code='insufficient_eligible_inputs'),)),
        'overlap':dict(exclusions=(WeightTrendExclusion(reference=replace(a,version='other'),reason='outside_comparison_window'),)),
    }[change]
    with pytest.raises(ValidationError):
        replace(manifest,**changes)


@pytest.mark.parametrize('data', [
    dict(stage='governance',code='SQL: SELECT patient values'),
    dict(stage='raw traceback',code='internal_failure'),
    dict(stage='governance',code='internal_failure',message='patient values'),
    dict(stage='governance',code='internal_failure',sql='SELECT *'),
])
def test_failure_contract_cannot_retain_exception_content(data):
    with pytest.raises(ValidationError):
        WeightTrendExecutionIssue(**data)


def test_pure_functions_perform_no_database_access(case,monkeypatch):
    import sqlite3
    import sqlalchemy
    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.orm import Session
    def forbidden(*args,**kwargs):
        pytest.fail('pure execution contract attempted database access')
    monkeypatch.setattr(sqlite3,'connect',forbidden)
    monkeypatch.setattr(sqlalchemy,'create_engine',forbidden)
    for cls in (Connection,Session):
        monkeypatch.setattr(cls,'execute',forbidden)
    monkeypatch.setattr(Engine,'connect',forbidden)
    assert record(case).disposition == 'completed_released'


def test_real_partial_snapshot_withheld_decision_can_be_recorded(case):
    graph = case['lineage']
    missing = case['selection'].selected[0].reference
    partial = dc_replace(graph,nodes=tuple(n for n in graph.nodes if n.stored.fact.reference != missing),
        provenance=tuple(p for p in graph.provenance if p.reference != missing),
        ancestry=tuple(item for item in graph.ancestry if item[0] != missing),coverage='partial',
        unresolved=(UnresolvedReference(graph.reference,missing,'dependency',0,None,'not_resolvable_in_scope_at_cutoff'),))
    snapshot = build_weight_trend_snapshot(selection=case['selection'],inference=case['inference'],
        lineage=partial,patient=patient(),encounter=encounter(),at=NOW,id='snapshot')
    assert tuple(f.reference.id for f in snapshot.facts) == ('b','weight-trend-1')
    candidate = build_weight_trend_candidate(snapshot=snapshot,comparison=case['comparison'],
        inference=case['inference'],at=NOW,id='candidate')
    rendering = render_weight_trend(candidate=candidate,comparison=case['comparison'],target=GRANT_TARGET,at=NOW,id='rendering')
    decision = run({**case,'lineage':partial,'snapshot':snapshot,'candidate':candidate,'rendering':rendering})
    assert decision.outcome == 'withheld' and 'safety_check_unavailable' in decision.reasons
    value = record(case,lineage=weight_trend_lineage_witness(partial),decision=decision)
    assert value.disposition == 'completed_withheld'
    assert WeightTrendExecutionRecord.model_validate_json(canonical_payload(value)) == value


@pytest.mark.parametrize('part', ['assertions','dependencies','ancestry','provenance','roles','scope','payload'])
def test_lineage_projection_rejects_malformed_resolver_result(case,part):
    graph = case['lineage']
    if part in ('assertions','dependencies','ancestry','provenance'):
        graph = dc_replace(graph,**{part:getattr(graph,part)[:-1]})
    elif part == 'roles':
        graph = dc_replace(graph,nodes=(dc_replace(graph.nodes[0],roles=('association',)),*graph.nodes[1:]))
    elif part == 'scope':
        graph = dc_replace(graph,target=replace(TARGET,patient_id='wrong'))
    else:
        root = graph.nodes[-1]
        broken = root.stored.fact.model_copy(update={'inputs':()})
        graph = dc_replace(graph,nodes=(*graph.nodes[:-1],dc_replace(root,stored=dc_replace(root.stored,fact=broken))))
    with pytest.raises(ValueError):
        weight_trend_lineage_witness(graph)


def test_shared_reference_contradiction_is_not_hidden_by_other_revision_change(case):
    a,b = case['selection'].selected
    a2 = revision(a,'new')
    b = replace(b,uncertainty=('different retained payload',))
    with pytest.raises(StorageIntegrityError):
        check(case,replace(case['selection'],cutoff=cutoff(4),selected=(a2,b)))


def test_reversed_manifest_order_is_material_not_silently_sorted(case):
    result = check(case)
    final = replace(result.final,selected=tuple(reversed(result.final.selected)),
        selected_payload_digests=tuple(reversed(result.final.selected_payload_digests)))
    # A manifest has no event bodies; preserving the supplied order detects the mismatch.
    assert replace(result,final=final).outcome == 'materially_changed'
    a,b = case['selection'].selected
    with pytest.raises(ValidationError):
        replace(case['selection'],selected=(b,a))


def test_recheck_rejects_unsupported_policy_and_forged_same_ref_digest(case):
    result = check(case)
    with pytest.raises(ValidationError,match='unsupported final recheck'):
        replace(result,policy=replace(FINAL_RECHECK_POLICY,version='2'))
    final = replace(result.final,selected_payload_digests=('0'*64,result.final.selected_payload_digests[1]))
    with pytest.raises(ValidationError,match='contradictory retained'):
        replace(result,final=final)


@pytest.mark.parametrize('seed', ['1','8675309'])
def test_cross_process_hash_seed_canonicalization(seed):
    import os
    import subprocess
    import sys
    from test_persistence import ROOT
    env = dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=os.pathsep.join((str(ROOT/'backend'),str(ROOT/'tests'))))
    script = 'from test_weight_trend_execution import pure_case, record, canonical_payload; print(canonical_payload(record(pure_case())))'
    result = subprocess.run([sys.executable,'-c',script],env=env,text=True,capture_output=True,check=True,timeout=30)
    assert result.stdout.strip() == canonical_payload(record(pure_case()))


@pytest.mark.parametrize('change', ['incompatible_counts','duplicate_terminal_family'])
def test_impossible_manifest_disclosures_rejected(case,change):
    manifest = weight_trend_selection_manifest(case['selection'])
    if change == 'incompatible_counts':
        updates = dict(selected=(),selected_payload_digests=(),issues=(
            WeightTrendSelectionIssue(code='insufficient_eligible_inputs'),
            WeightTrendSelectionIssue(code='ambiguous_eligible_inputs')))
    else:
        ref = Reference(kind='observation',id='outside',version='1')
        updates = dict(exclusions=tuple(WeightTrendExclusion(reference=r,reason='outside_comparison_window')
            for r in (ref,replace(ref,version='2'))))
    with pytest.raises(ValidationError):
        replace(manifest,**updates)


@pytest.mark.parametrize('variant', ['released','withheld'])
@pytest.mark.parametrize('part', ['root_limits','root_lineage','observation_limits','observation_lineage'])
def test_retained_witness_provenance_must_match_present_fact_bodies(variant,part):
    value = record(pure_case())
    if variant == 'withheld':
        value = replace(value,decision=withheld_for_context(value.decision,material=False))
    nodes = list(value.lineage.nodes)
    index = -1 if part.startswith('root') else 0
    node = nodes[index]
    if part == 'root_limits':
        changes = dict(limitations=())
    elif part == 'observation_limits':
        changes = dict(limitations=('invented witness disclosure',))
    else:
        changes = dict(lineage='unknown',limitations=('unknown retained lineage',))
    nodes[index] = replace(node,**changes)
    witness = replace(value.lineage,nodes=tuple(nodes))
    # These remain individually valid contracts; their contradiction is within
    # the envelope, whose exact snapshot body still has the original provenance.
    assert witness.nodes[index].payload_digest == node.payload_digest
    with pytest.raises(ValidationError,match='provenance'):
        replace(value,lineage=witness)
    encoded = value.model_dump(mode='json')
    encoded['lineage'] = witness.model_dump(mode='json')
    with pytest.raises(ValidationError,match='provenance'):
        WeightTrendExecutionRecord.model_validate(encoded)


@pytest.mark.parametrize('field,value', [('execution_version','2'),('execution_type','generic_workflow')])
def test_execution_identity_versions_rejected(field,value):
    original = record(pure_case())
    with pytest.raises(ValidationError):
        replace(original,**{field:value})


@pytest.mark.parametrize('part', ['outcome','reasons','authorization','safety'])
def test_forged_nested_decision_cannot_change_validated_disposition(part):
    original = record(pure_case())
    decision = original.decision
    assessment = decision.assessment
    if part == 'outcome':
        decision = decision.model_copy(update={'outcome':'withheld'})
    elif part == 'reasons':
        decision = decision.model_copy(update={'reasons':('invented',)})
    elif part == 'authorization':
        auth = assessment.state.authorization.model_copy(update={'outcome':'invented'})
        state = assessment.state.model_copy(update={'authorization':auth})
        decision = decision.model_copy(update={'assessment':assessment.model_copy(update={'state':state})})
    else:
        evaluation = assessment.review.evaluations[0]
        broken = evaluation.checks[0].model_copy(update={'outcome':'invented'})
        evaluation = evaluation.model_copy(update={'checks':(broken,*evaluation.checks[1:])})
        review = assessment.review.model_copy(update={'evaluations':(evaluation,)})
        decision = decision.model_copy(update={'assessment':assessment.model_copy(update={'review':review})})
    with pytest.raises(ValidationError):
        replace(original,decision=decision)
    assert original.disposition == 'completed_released'
    assert WeightTrendExecutionRecord.model_validate_json(canonical_payload(original)).disposition == 'completed_released'
