"""Portable stdlib data-only verifier; does not execute application, bundles or logs."""
from pathlib import Path
import base64,hashlib,json,sqlite3
root=Path(__file__).resolve().parent
for name,digest in json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
original=json.loads((root/'original/SHA256SUMS.json').read_text());assert len(original)==15
for name,digest in original.items():assert hashlib.sha256((root/'original'/name).read_bytes()).hexdigest()==digest,name
for mirror in json.loads((root/'MIRRORS.json').read_text()):
    raw=base64.b64decode(''.join((root/name).read_text().strip() for name in mirror['parts']),validate=True)
    assert raw==(root/mirror['path']).read_bytes() and len(raw)==mirror['bytes']
    assert hashlib.sha256(raw).hexdigest()==mirror['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==mirror['git_blob']
update=json.loads((root/'original/update.json').read_text());assert update['source']=='008034ea12275406d8f5aede8ceb3aa5142570b6';assert update['health']['execution_enabled'] is False
for name,digest in update['files'].items():assert hashlib.sha256((root/'build-reference'/name).read_bytes()).hexdigest()==digest
for name in json.loads((root/'original/browser-script-paths.json').read_text()):assert name.lstrip('/') in update['files']
indices=json.loads((root/'TABLES-INDEX.json').read_text());exports={}
for checkpoint in ('before','after'):
    exports[checkpoint]=json.loads((root/'original'/(checkpoint+'-rows.json')).read_text())
    with sqlite3.connect('file:'+str(root/'original'/(checkpoint+'.sqlite3'))+'?mode=ro&immutable=1',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        for table,rows in exports[checkpoint].items():
            columns=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
            assert columns==indices[checkpoint][table]['columns']
            assert [list(row) for row in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]==rows
            for row,path in zip(rows,indices[checkpoint][table]['files'],strict=True):assert json.loads((root/path).read_text())=={'columns':columns,'row':row}
before,after=exports['before'],exports['after'];assert len(before['fact_revision'])==171 and len(after['fact_revision'])==172
assert before['fact_revision']==after['fact_revision'][:-1]
for table,rows in before.items():
    if table not in ('fact_revision','sqlite_sequence'):assert after[table]==rows,table
with sqlite3.connect('file:'+str(root/'original/after.sqlite3')+'?mode=ro&immutable=1',uri=True) as db:
    facts={r[:3]:r[3:] for r in db.execute('SELECT kind,fact_id,revision,payload,ingestion_sequence FROM fact_revision')}
    fact=json.loads((root/'original/stored-reassessment.json').read_text());payload,sequence=facts[fact['kind'],fact['id'],fact['revision']]
    assert sequence==172 and json.loads(payload)==fact
    assert hashlib.sha256(payload.encode()).hexdigest()=='7e91409555cf2fc9693c8baece95a1d5253b1df3b70697525ff7e55927d2948d'
    tuples=[json.loads(item['value']) for item in json.loads((root/'original/selected-options.json').read_text())]
    expected=[{'kind':kind,'id':id,'version':version} for kind,id,version in tuples]
    assert [a['exact'] for a in fact['associations']]==expected
    for stage,ref in zip(('baseline','intervention','followup'),expected,strict=True):
        assert (ref['kind'],ref['id'],ref['version']) in facts
        assert stage+': '+json.dumps(ref,separators=(',',':')) in fact['description']['raw_display']
        code=next(c for c in fact['external_evidence'] if c['namespace']=='clinrx.local.reassessment.'+stage+'/v1');assert json.loads(code['code'])==ref
    assert 'Patient-level relationship is not established' in fact['description']['raw_display']
    for digest,payload in db.execute('SELECT payload_digest,payload FROM circulatory_execution'):assert hashlib.sha256(payload.encode()).hexdigest()==digest
assert (root/'original/saved-reassessment.jpg').read_bytes().startswith(b'\xff\xd8')
print('PASS: publication/original hashes, exact-byte mirrors, build-reference bytes, both captured databases/all tables, unchanged 171 rows/two receipts, note 172 and three exact selected references. Normal-flow capture only; no live collision or clinical acceptance claimed.')
