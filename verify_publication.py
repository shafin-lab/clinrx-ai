"""Data-only stdlib verifier. Never imports/runs the application, tests or logs."""
from pathlib import Path
import base64,hashlib,json,sqlite3
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for mirror in json.loads((root/'MIRRORS.json').read_text()):
    raw=base64.b64decode(''.join((root/part).read_text().strip() for part in mirror['parts']),validate=True)
    assert len(raw)==mirror['bytes'] and hashlib.sha256(raw).hexdigest()==mirror['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==mirror['git_blob']
    assert raw==(root/mirror['path']).read_bytes()
original=json.loads((root/'original/SHA256SUMS.json').read_text());omitted={i['original_path'] for i in json.loads((root/'REDACTIONS.json').read_text())}
for name,digest in original.items():
    if name not in omitted:assert hashlib.sha256((root/'original'/name).read_bytes()).hexdigest()==digest,name
with sqlite3.connect('file:'+str(root/'original/database.sqlite3')+'?mode=ro',uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
    tables=json.loads((root/'original/tables.json').read_text())
    for table,export in tables.items():
        assert [r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]==export['columns']
        assert [list(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]==export['rows']
    facts={}
    for row in db.execute('SELECT kind,fact_id,revision,payload FROM fact_revision'):
        facts[row[:3]]=row[3]
    state=json.loads((root/'redacted/state.json').read_text())
    assert state['execution_enabled'] is False
    for item in state['assembly']['snapshot']['items']:
        f=item['fact'];payload=facts[(f['kind'],f['id'],f['revision'])]
        assert json.loads(payload)==f and hashlib.sha256(payload.encode()).hexdigest()==item['expected_digest']
print('PASS: publication hashes, lossless mirrors, preserved originals, SQLite integrity, all tables and fresh snapshot correspondence')
