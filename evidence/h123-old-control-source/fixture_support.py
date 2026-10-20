"""Strict synthetic fixtures derived from, never replacing, approved design examples."""
import copy
import json
from pathlib import Path
from rf2_harness import CONTRACT, canonical, registry_digest
ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'original'


def example(name):
    return json.loads((ORIGINAL / 'examples' / (name + '.json')).read_text())


def run_for(names=('urine-original',)):
    records = [example(n) for n in names]
    b = example('urine-original')
    s = {**b['scope'], 'issuer': b['issuer'], 'identity_namespace': b['identity_namespace']}
    proposed = json.loads((ORIGINAL / 'PROPOSED-REGISTRIES.json').read_text())
    contents = {
        'component_aliases': {'entries': [{k: v for k, v in a.items() if k != 'issuer'} for a in proposed['component_aliases']]},
        'quantity_equivalence': {'entries': []},
        'drain_lifecycle': {'entries': [{**d, 'replaces': d.get('replaces')} for d in proposed['drain_lifecycle']]},
        'independent_components': {'entries': [{'collection_key': 'C-001', 'components': [{'component_key': c, 'quantity_key': q} for c, q in zip(proposed['distinct_component_assertion']['components'], proposed['distinct_component_assertion']['quantity_keys'])]}]},
    }
    regs = []
    for typ, content in sorted(contents.items()):
        r = {'registry_type': typ, 'schema_version': 'rf2-registry/v1-proposal.1', 'scope': b['scope'], 'issuer': b['issuer'], 'identity_namespace': b['identity_namespace'], 'version': 'registry-r1', 'available_at': '2026-10-08T07:00:00+00:00', 'knowledge_sequence': 1, 'supersedes': None, 'content': content}
        r['digest'] = registry_digest(r)
        regs.append(r)
    return {'contract_version': CONTRACT, 'expected_scope': s, 'period': {'start': '2026-10-08T08:00:00+00:00', 'end': '2026-10-08T09:00:00+00:00', 'display_timezone': 'UTC'}, 'cutoff': 102, 'clinical_as_of': None, 'input_complete': True, 'records': [{'envelope': e, 'knowledge_sequence': 102 if e['supersedes'] else 100} for e in records], 'registries': regs}


def rehash(run):
    for r in run['registries']:
        r['digest'] = registry_digest(r)
    return run


def registry(run, typ):
    return next(r for r in run['registries'] if r['registry_type'] == typ)


def sequential_drain_run():
    r = run_for(('drain-A',))
    second = copy.deepcopy(r['records'][0])
    e = second['envelope']
    e.update(collection_key='D-A-C2', quantity_key='D-A-Q2')
    e['time'].update(start='2026-10-08T08:15:00+00:00', end='2026-10-08T08:30:00+00:00')
    r['records'].append(second)
    return r
