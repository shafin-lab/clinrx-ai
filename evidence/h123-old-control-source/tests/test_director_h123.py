"""Focused Director findings; old-source controls precede production fixes."""
import copy
import itertools
from fixture_support import run_for, registry, rehash
from rf2_harness import evaluate, canonical, digest


def result(run):
    return evaluate(canonical(run))


def includes(output):
    return [x for x in output['decisions'] if x['decision']=='candidate_include']


def alias_registry(run, entries):
    registry(run,'component_aliases')['content']['entries']=entries
    return rehash(run)


def test_h1_canonical_target_quantity_mismatch_is_excluded():
    run=run_for();run['records'][0]['envelope']['quantity_key']='CONTRADICTS-TARGET'
    out=result(run)
    assert not includes(out)
    assert 'ALIAS_UNRESOLVED' in out['decisions'][0]['reason_codes']


def test_h1_contradictory_alias_chain_withholds():
    run=run_for();run['records'][0]['envelope']['component_key']='outer'
    alias_registry(run,[
        {'collection_key':'C-001','alias':'outer','canonical':'inner','quantity_key':'Q-001'},
        {'collection_key':'C-001','alias':'inner','canonical':'volume','quantity_key':'Q-CONTRADICTORY'},
    ])
    out=result(run)
    assert out['run_status']=='withheld' and not includes(out)
    assert 'ALIAS_UNRESOLVED' in out['run_reasons']


def test_h1_converging_aliases_cannot_assign_two_quantities_to_target():
    run=run_for();alias_registry(run,[
        {'collection_key':'C-001','alias':'left','canonical':'volume','quantity_key':'Q-001'},
        {'collection_key':'C-001','alias':'right','canonical':'volume','quantity_key':'Q-OTHER'},
    ])
    out=result(run)
    assert out['run_status']=='withheld' and not includes(out)


def test_h1_valid_chain_accepts_alias_and_canonical_separately():
    run=run_for();alias_registry(run,[
        {'collection_key':'C-001','alias':'outer','canonical':'inner','quantity_key':'Q-001'},
        {'collection_key':'C-001','alias':'inner','canonical':'volume','quantity_key':'Q-001'},
    ])
    for component in ('outer','inner','volume'):
        run['records'][0]['envelope']['component_key']=component
        out=result(run)
        assert out['run_status']=='evaluated' and len(includes(out))==1
        assert includes(out)[0]['identity'][-2]=='volume'


def test_h2_lineage_edge_is_predecessor_to_successor_not_digest_order():
    run=run_for(('urine-original','urine-correction'))
    a,b=[w['envelope'] for w in run['records']]
    # Ensure an unordered/sorted implementation must reverse the causal direction.
    for n in range(100):
        a['uncertainty']=[f'Predecessor provenance fixture {n}']
        if digest(a)>digest(b):break
    assert digest(a)>digest(b)
    out=result(run)
    edge=next(e for e in out['relationships'] if e['type']=='LINEAGE')
    assert edge['members']==[digest(a),digest(b)]
    assert len(includes(out))==1


def test_h2_summary_edge_is_summary_to_member_not_digest_order():
    run=run_for(('urine-original','summary-known'))
    member,summary=[w['envelope'] for w in run['records']]
    for n in range(100):
        summary['uncertainty']=[f'Summary provenance fixture {n}']
        if digest(summary)>digest(member):break
    assert digest(summary)>digest(member)
    out=result(run)
    edge=next(e for e in out['relationships'] if e['type']=='SUMMARY_MEMBER')
    assert edge['members']==[digest(summary),digest(member)]
    assert len(includes(out))==1 and not out['conflict_groups']


def test_h3_singleton_cycle_group_has_causal_reasons_and_self_edge():
    run=run_for();e=run['records'][0]['envelope']
    e['supersedes']={k:e[k] for k in ('identity_namespace','collection_key','component_key','revision')}
    out=result(run);h=digest(e)
    assert not includes(out) and len(out['conflict_groups'])==1
    group=out['conflict_groups'][0]
    assert 'REVISION_CYCLE' in group['reason_codes']
    assert any(edge['members']==[h,h] and edge['type']=='LINEAGE' for edge in group['typed_edges'])
    assert any(edge['members']==[h,h] and edge['reason']=='REVISION_CYCLE' for edge in group['typed_edges'])


def test_h123_permutations_preserve_directed_provenance():
    run=run_for(('urine-original','urine-correction','summary-known','drain-B'))
    before=result(run)
    for records in itertools.permutations(run['records']):
        varied=copy.deepcopy(run);varied['records']=list(records);varied['registries'].reverse()
        after=result(varied)
        for key in ('relationships','conflict_groups','decisions','run_status','run_reasons'):
            assert before[key]==after[key]
