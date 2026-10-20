"""Generate explicit derived inputs and expected decisions, not observed outcomes."""
import copy
import hashlib
import json
from pathlib import Path
from fixture_support import ROOT, ORIGINAL, run_for, sequential_drain_run, canonical

cases = json.loads((ORIGINAL / 'EXPECTED-DECISIONS.json').read_text())
expected = {
 '01': ('evaluated',1,None), '02': ('evaluated',0,'SAME_REVISION_CONFLICT'),
 '03': ('evaluated',1,None), '04': ('evaluated',0,'SAME_REVISION_CONFLICT'),
 '05': ('evaluated',0,'SAME_REVISION_CONFLICT'), '06': ('evaluated',0,'SAME_REVISION_CONFLICT'),
 '07': ('evaluated',0,'DUPLICATE_UNRESOLVED'), '08': ('evaluated',2,None),
 '09': ('evaluated',0,'DRAIN_LIFECYCLE'), '10': ('evaluated',1,'SUMMARY'),
 '11': ('withheld',0,'SCOPE_UNBOUNDED'), '12': ('evaluated',1,'EFFLUENT'),
 '13': ('evaluated',0,'DUPLICATE_UNRESOLVED'), '14': ('evaluated',0,'TERMINAL_NOT_RECORDED'),
 '15': ('evaluated',0,'TERMINAL_NOT_RECORDED'), '16': ('evaluated',0,'REVISION_BRANCH'),
 '17': ('evaluated',1,None), '18': ('evaluated',0,'AVAILABILITY_UNRESOLVED'),
 '19': ('evaluated',2,None), '20': ('evaluated',1,None),
 '21': ('evaluated',0,'MISSING_QUANTITY'), '22': ('evaluated',0,'AFTER_CLINICAL_AS_OF'),
 '23': ('evaluated',1,None),
}
manifest = []
for case in cases:
    code = case['id'][:2]
    names = case['examples'][:]
    changes = ['Wrap unchanged payloads in strict run schema; add scoped versioned/digested registry snapshots derived from proposed registries; synthetic knowledge sequences only.']
    if code == '22':
        names.insert(0, 'urine-original')
        changes.append('Supply referenced predecessor absent from isolated original scenario so availability is tested independently of missing-lineage withholding.')
    run = run_for(names)
    if 'clinical_as_of' in case:
        run['clinical_as_of'] = case['clinical_as_of']
    if code == '11':
        changes.append('Approved A-C contract refines original vague group exclusion to whole-run withholding because summary membership has no bounded affected set.')
    file = 'fixtures/derived/' + case['id'] + '.json'
    (ROOT / file).write_bytes(canonical(run))
    status, count, reason = expected[code]
    manifest.append({'id':case['id'], 'input':file, 'sha256': hashlib.sha256((ROOT/file).read_bytes()).hexdigest(), 'original_scenario':case['id'], 'original_examples':case['examples'], 'original_expectation':case['conditional_expected_decision'], 'derivation':changes, 'expected':{'run_status':status,'candidate_count':count,'reason':reason}})
(ROOT/'fixtures/DERIVATION-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Added edges are independently named; no changes to original fixture bytes.
edge = sequential_drain_run()
(ROOT/'fixtures/edge/sequential-drain.json').write_bytes(canonical(edge))
print(f'Wrote {len(manifest)} strict derived fixtures and one preserved added-edge fixture.')
