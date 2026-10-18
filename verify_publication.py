"""Portable stdlib, data-only verification; never runs application, tests or logs."""
from pathlib import Path
import base64,hashlib,json,sqlite3
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text())
for path,digest in manifest.items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
for entry in json.loads((root/'MIRRORS.json').read_text()):
    raw=base64.b64decode(''.join((root/path).read_text().strip() for path in entry['parts']),validate=True)
    assert raw==(root/entry['path']).read_bytes()
    assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob']
omitted={r['original_path'] for r in json.loads((root/'REDACTIONS.json').read_text())}
for line in (root/'original/SHA256SUMS').read_text().splitlines():
    digest,path=line.split('  ',1)
    if path not in omitted:assert hashlib.sha256((root/'original'/path).read_bytes()).hexdigest()==digest,path
before=json.loads((root/'original/before-rows.json').read_text());after=json.loads((root/'original/after-rows.json').read_text())
assert after['fact_revision'][:len(before['fact_revision'])]==before['fact_revision']
assert len(after['fact_revision'])==len(before['fact_revision'])+7
for table in before:
    if table not in ('fact_revision','sqlite_sequence'):assert after[table]==before[table],table
indices=json.loads((root/'readable/tables-index.json').read_text());states=json.loads((root/'readable/state-index.json').read_text())
for checkpoint in ('before','after'):
    exports=json.loads((root/'original'/(checkpoint+'-rows.json')).read_text())
    with sqlite3.connect('file:'+str(root/'original'/(checkpoint+'.sqlite3'))+'?mode=ro&immutable=1',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        for table,rows in exports.items():
            columns=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
            assert columns==indices[checkpoint][table]['columns']
            assert [list(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]==rows
            for expected,path in zip(rows,indices[checkpoint][table]['files'],strict=True):
                row=json.loads((root/path).read_text());assert row=={'table':table,'columns':columns,'row':expected}
        facts={r[:3]:r[3:] for r in db.execute('SELECT kind,fact_id,revision,payload,ingestion_sequence FROM fact_revision')}
        state=json.loads((root/'redacted'/(checkpoint+'-state.json')).read_text());assert state['execution_enabled'] is False
        assert state['state_context']=='REDACTED_TEMPORARY_SIGNED_STATE_CONTEXT'
        for item,index in zip(state['assembly']['snapshot']['items'],states[checkpoint],strict=True):
            f=item['fact'];payload,sequence=facts[f['kind'],f['id'],f['revision']]
            assert json.loads(payload)==f and hashlib.sha256(payload.encode()).hexdigest()==item['expected_digest']
            assert sequence==item['ingestion']['ingestion_sequence']
            assert json.loads((root/index['path']).read_text())==item
        for digest,payload in db.execute('SELECT payload_digest,payload FROM circulatory_execution'):
            assert hashlib.sha256(payload.encode()).hexdigest()==digest
        if checkpoint=='after':
            notes=[json.loads(payload) for payload,sequence in facts.values() if sequence==169];assert len(notes)==1
            note=notes[0];assert note['kind']=='circulatory_event'
            exact={json.dumps(a['exact'],sort_keys=True) for a in note['associations']};assert len(exact)==3
            for stage in ('baseline','intervention','followup'):
                code=next(c for c in note['external_evidence'] if c['namespace']=='clinrx.local.reassessment.'+stage+'/v1')
                ref=json.loads(code['code']);assert json.dumps(ref,sort_keys=True) in exact
                assert (ref['kind'],ref['id'],ref['version']) in facts
print('PASS: publication/original hashes, exact-byte mirrors, both SQLite checkpoints/all tables, retained rows/receipts, both API snapshots and three exact reassessment links. Tokens withheld; no application execution or clinical acceptance claimed.')
