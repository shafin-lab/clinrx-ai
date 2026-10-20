import copy
import hashlib
import itertools
import json
import random
from pathlib import Path
import pytest
from fixture_support import ROOT, run_for, rehash, registry, sequential_drain_run
from rf2_harness import evaluate, canonical, digest, registry_digest, instant, SCHEMA_DIGEST

MANIFEST = json.loads((ROOT/'fixtures/DERIVATION-MANIFEST.json').read_text())


def result(r):
    return evaluate(canonical(r))


def included(o):
    return [d for d in o['decisions'] if d['decision']=='candidate_include']


def all_reasons(o):
    return set(o['run_reasons']) | {r for d in o['decisions'] for r in d['reason_codes']}


@pytest.mark.parametrize('case', MANIFEST, ids=lambda c:c['id'])
def test_preserved_scenario_derived_conformance(case):
    raw=(ROOT/case['input']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==case['sha256']
    o=evaluate(raw); expected=case['expected']
    assert o['run_status']==expected['run_status'], o
    assert len(included(o))==expected['candidate_count'], o
    if expected['reason']:
        assert expected['reason'] in all_reasons(o)
    assert o['synthetic_only'] is True and o['numerical_eligibility_active'] is False
    assert o['completeness']=='unresolved'


def test_original_package_unchanged():
    for name,h in json.loads((ROOT/'original/SHA256SUMS.json').read_text()).items():
        assert hashlib.sha256((ROOT/'original'/name).read_bytes()).hexdigest()==h
    assert len(list((ROOT/'original/examples').glob('*.json')))==24
    assert len(json.loads((ROOT/'original/EXPECTED-DECISIONS.json').read_text()))==23


@pytest.mark.parametrize('raw', [b'{', b'\xff', b'{"x":1,"x":2}', b'NaN', b'1.2', b'"\xed\xa0\x80"'])
def test_malformed_json_rejects(raw):
    o=evaluate(raw); assert o['run_status']=='rejected' and not included(o)


@pytest.mark.parametrize('change', ['unit','extra','missing','bool-sequence','negative','exponent','partial','equal','reverse','mixed','drain','quantity-null','extra-registry','missing-registry-field','number-amount'])
def test_schema_rejects_entire_run(change):
    r=run_for(); e=r['records'][0]['envelope']
    if change=='unit':e['quantity']['unit']='g'
    if change=='extra':e['surprise']=True
    if change=='missing':del e['revision']
    if change=='bool-sequence':r['records'][0]['knowledge_sequence']=True
    if change=='negative':e['quantity']['amount']='-1'
    if change=='exponent':e['quantity']['amount']='1e2'
    if change=='partial':e['time']['start']=None
    if change=='equal':e['time']['end']=e['time']['start']
    if change=='reverse':e['time']['start']='2026-10-08T08:59:00Z'
    if change=='mixed':e['time']['at']='2026-10-08T08:40:00Z'
    if change=='drain':e['category']='output_drain'
    if change=='quantity-null':e['quantity']['amount']=None
    if change=='extra-registry':r['registries'][0]['content']['unexpected']=1
    if change=='missing-registry-field':del r['registries'][0]['available_at']
    if change=='number-amount':e['quantity']['amount']=45
    o=result(r);assert o['run_status']=='rejected' and not included(o),o


def test_unsupported_identifiers_excluded_not_schema_rejected():
    r=run_for();e=r['records'][0]['envelope'];e['producer']['id']='unsupported';e['profile']='future'
    o=result(r);assert o['run_status']=='evaluated' and 'UNSUPPORTED_PROFILE' in all_reasons(o)


def test_canonical_whitespace_and_object_order():
    r=run_for();a=result(r);b=evaluate(json.dumps(r,indent=3,sort_keys=False).encode())
    assert a==b and a['schema_digest']==SCHEMA_DIGEST


@pytest.mark.parametrize('field', ['decimal','timestamp','uncertainty-order','profile'])
def test_changed_canonical_same_revision_conflicts(field):
    r=run_for();w=copy.deepcopy(r['records'][0]);e=w['envelope']
    if field=='decimal':e['quantity']['amount']='45.0'
    if field=='timestamp':e['time']['end']='2026-10-08T08:45:00Z'
    if field=='uncertainty-order':
        r['records'][0]['envelope']['uncertainty']=['A','B'];e['uncertainty']=['B','A']
    if field=='profile':e['profile']='future'
    r['records'].append(w);o=result(r)
    assert not included(o) and 'SAME_REVISION_CONFLICT' in all_reasons(o)


def successor(r,typ='component_aliases',available='2026-10-08T10:00:00Z',sequence=101):
    old=registry(r,typ);new=copy.deepcopy(old)
    new.update(version='registry-r2',available_at=available,knowledge_sequence=sequence,supersedes={'registry_type':typ,'version':old['version'],'digest':old['digest']})
    new['digest']=registry_digest(new);r['registries'].append(new);return new


def test_registry_terminal_unavailable_does_not_fall_back():
    r=run_for();successor(r);r['clinical_as_of']='2026-10-08T09:00:00Z'
    o=result(r);assert o['run_status']=='withheld' and not included(o)
    assert 'REGISTRY_TERMINAL_AFTER_AS_OF' in o['run_reasons']
    assert any(p.get('version')=='registry-r2' for p in o['selected_registries'])


def test_registry_historical_cutoff_before_successor():
    r=run_for();successor(r);r['cutoff']=100;r['clinical_as_of']='2026-10-08T09:00:00Z'
    o=result(r);assert len(included(o))==1 and all(p.get('version')=='registry-r1' for p in o['selected_registries'])


def test_registry_no_asof_uses_new_terminal():
    r=run_for();successor(r);o=result(r)
    assert len(included(o))==1 and any(p.get('version')=='registry-r2' for p in o['selected_registries'])


@pytest.mark.parametrize('change', ['digest','scope','missing','branch','disconnected','cycle','missing-predecessor'])
def test_registry_failures_never_include(change):
    r=run_for();old=registry(r,'component_aliases')
    if change=='digest':old['digest']='a'*64
    if change=='scope':old['scope']['encounter_id']='foreign';rehash(r)
    if change=='missing':r['registries'].remove(old)
    if change=='branch':successor(r);n=successor(r,sequence=102);n['version']='registry-r3';n['digest']=registry_digest(n)
    if change=='disconnected':n=copy.deepcopy(old);n['version']='other-root';n['digest']=registry_digest(n);r['registries'].append(n)
    if change=='cycle':old['supersedes']={'registry_type':'component_aliases','version':'registry-r1','digest':old['digest']};old['digest']=registry_digest(old)
    if change=='missing-predecessor':old['supersedes']={'registry_type':'component_aliases','version':'missing','digest':'a'*64};old['digest']=registry_digest(old)
    o=result(r);assert o['run_status']=='withheld' and not included(o),o


def test_sequential_collections_same_drain_are_independent():
    r=sequential_drain_run();o=result(r)
    assert len(included(o))==2 and not o['conflict_groups']


def test_overlapping_same_drain_excludes_both():
    r=sequential_drain_run();r['records'][1]['envelope']['time']['end']='2026-10-08T08:40:00Z'
    o=result(r);assert not included(o) and 'SAME_STREAM_OVERLAP' in all_reasons(o)


def test_known_summary_is_not_overlap_or_equivalence():
    r=run_for(('urine-original','summary-known'));o=result(r)
    assert len(included(o))==1 and not o['conflict_groups']
    assert {e['type'] for e in o['relationships']}=={'SUMMARY_MEMBER'}


def test_unknown_summary_membership_withholds_scope():
    o=result(run_for(('urine-original','summary-unresolved')))
    assert o['run_status']=='withheld' and not included(o)


def test_missing_summary_member_withholds():
    r=run_for(('summary-known',));o=result(r)
    assert 'DEPENDENCY_MISSING' in o['run_reasons'] and not included(o)


def test_equivalence_overrides_independence():
    r=run_for(('urine-original','distinct-component'))
    registry(r,'quantity_equivalence')['content']['entries']=[{'left_quantity_key':'Q-001','right_quantity_key':'Q-002'}]
    o=result(rehash(r));assert not included(o) and 'DUPLICATE_UNRESOLVED' in all_reasons(o)


def test_distinct_components_without_assertion_excluded():
    r=run_for(('urine-original','distinct-component'));registry(r,'independent_components')['content']['entries']=[]
    o=result(rehash(r));assert not included(o) and 'COMPONENT_INDEPENDENCE_UNRESOLVED' in all_reasons(o)


def test_conflict_closure_does_not_spread_via_summary():
    r=run_for(('urine-original','urine-new-key-same-volume','summary-known','drain-B'))
    o=result(r);assert len(included(o))==1 and included(o)[0]['identity'][-3]=='D-B-C1'
    assert len(o['conflict_groups'])==1 and len(o['conflict_groups'][0]['members'])==2


def test_transitive_conflict_closure():
    r=sequential_drain_run()
    a=r['records'][0]['envelope'];b=r['records'][1]['envelope']
    b['time'].update(start='2026-10-08T08:20:00Z',end='2026-10-08T08:35:00Z')
    c=copy.deepcopy(r['records'][0]);c['envelope'].update(collection_key='D-A-C3',quantity_key='D-A-Q3');c['envelope']['time'].update(start='2026-10-08T08:10:00Z',end='2026-10-08T08:25:00Z');r['records'].append(c)
    o=result(r);assert not included(o) and len(o['conflict_groups'])==1 and len(o['conflict_groups'][0]['members'])==3


@pytest.mark.parametrize('point,expected', [('2026-10-08T08:30:00Z',0),('2026-10-08T08:45:00Z',2)])
def test_point_interval_overlap_halfopen(point,expected):
    r=run_for();w=copy.deepcopy(r['records'][0]);w['envelope'].update(collection_key='P2',quantity_key='PQ2');w['envelope']['time'].update(kind='point',start=None,end=None,at=point);r['records'].append(w)
    o=result(r);assert len(included(o))==expected


@pytest.mark.parametrize('kind', ['interval-end','point-end','crossing','multi-hour'])
def test_period_boundaries(kind):
    r=run_for();e=r['records'][0]['envelope']
    if kind=='interval-end':e['time']['end']=r['period']['end']
    if kind=='point-end':e['time'].update(kind='point',start=None,end=None,at=r['period']['end'])
    if kind=='crossing':e['time']['start']='2026-10-08T07:30:00Z'
    if kind=='multi-hour':r['period']['end']='2026-10-08T12:00:00Z';e['time'].update(start='2026-10-08T08:00:00Z',end='2026-10-08T11:00:00Z')
    o=result(r);assert len(included(o))==(1 if kind in ('interval-end','multi-hour') else 0)


def test_exact_fractional_timestamp_order_not_float():
    assert instant('2026-10-08T08:30:00.0000000000000000001Z')>instant('2026-10-08T08:30:00Z')


@pytest.mark.parametrize('date', ['2026-03-08T02:30:00-05:00','2026-11-01T01:30:00-06:00'])
def test_nonexistent_or_wrong_zone_offset_rejected(date):
    r=run_for();e=r['records'][0]['envelope'];e['time'].update(kind='point',start=None,end=None,at=date,display_timezone='America/New_York')
    assert result(r)['run_status']=='rejected'


def test_resolved_repeated_hour_offsets_are_distinct():
    assert instant('2026-11-01T01:30:00-04:00') < instant('2026-11-01T01:30:00-05:00')


def test_scope_mismatch_withholds_without_inclusions():
    r=run_for();r['records'][0]['envelope']['scope']['patient_id']='foreign'
    o=result(r);assert o['run_status']=='withheld' and not included(o)


@pytest.mark.parametrize('variant',['incomplete','byte-limit','count-limit','nesting'])
def test_input_limits_and_incomplete_never_partial(variant):
    r=run_for()
    if variant=='incomplete':r['input_complete']=False
    if variant=='count-limit':r['records']=r['records']*257
    if variant=='nesting':
        value=[]
        for _ in range(34):value=[value]
        r['extra']=value
    o=evaluate(b' '* (4*1024*1024+1)) if variant=='byte-limit' else result(r)
    assert o['run_status']=='withheld' and not included(o)


def test_historical_revision_selection():
    r=run_for(('urine-original','urine-correction'));r['cutoff']=100
    o=result(r);assert len(included(o))==1 and included(o)[0]['identity'][-1]=='r1'
    r['cutoff']=102;o=result(r);assert len(included(o))==1 and included(o)[0]['identity'][-1]=='r2'


def test_missing_lineage_withholds():
    o=result(run_for(('urine-correction',)));assert o['run_status']=='withheld' and not included(o)


def test_permutations_preserve_decisions_groups_registry_pins():
    r=run_for(('urine-original','urine-new-key-same-volume','summary-known','drain-B'))
    before=result(r)
    for ordering in itertools.permutations(r['records']):
        s=copy.deepcopy(r);s['records']=list(ordering);s['registries'].reverse();after=result(s)
        for k in ('decisions','conflict_groups','relationships','run_status','run_reasons','selected_registries'):
            assert after[k]==before[k],k

