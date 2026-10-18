"""Stdlib data-only verifier; imports no application and executes no logs."""
from pathlib import Path
import base64,hashlib,json,sqlite3
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for name,digest in json.loads((root/'WALKTHROUGH-ORIGINAL-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((root/'walkthrough/original'/name).read_bytes()).hexdigest()==digest
for mirror in json.loads((root/'MIRRORS.json').read_text()):
    data=base64.b64decode(''.join((root/name).read_text().strip() for name in mirror['parts']),validate=True)
    assert data==(root/mirror['path']).read_bytes()
    assert len(data)==mirror['bytes'] and hashlib.sha256(data).hexdigest()==mirror['sha256']
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==mirror['git_blob']
with sqlite3.connect('file:'+str(root/'walkthrough/publication-checkpoint.sqlite3')+'?mode=ro&immutable=1',uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    tables=json.loads((root/'walkthrough/publication-tables.json').read_text());indices=json.loads((root/'readable/TABLES-INDEX.json').read_text())
    for table,obj in tables.items():
        assert [r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]==obj['columns']
        assert [list(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]==obj['rows']
        for row,path in zip(obj['rows'],indices[table]['files'],strict=True):assert json.loads((root/path).read_text())=={'columns':obj['columns'],'row':row}
    baseline=json.loads((root/'walkthrough/baseline-169-rows.json').read_text())
    assert tables['fact_revision']['rows'][:169]==baseline['fact_revision']
    assert len(tables['fact_revision']['rows'])==171
    for table,rows in baseline.items():
        if table not in ('fact_revision','sqlite_sequence'):assert tables[table]['rows']==rows,table
    records=json.loads((root/'walkthrough/original/stored-records.json').read_text());facts={}
    for sequence,kind,id,revision,payload in db.execute('SELECT ingestion_sequence,kind,fact_id,revision,payload FROM fact_revision'):
        facts[kind,id,revision]=(sequence,payload)
    for item in records:
        fact=item['fact'];sequence,payload=facts[fact['kind'],fact['id'],fact['revision']]
        assert sequence==item['ingestion_sequence'] and json.loads(payload)==fact
        assert hashlib.sha256(payload.encode()).hexdigest()==item['payload_sha256']
    gas,note=[r['fact'] for r in records]
    assert gas['result']['quantity']['value']=='7.3300' and gas['sample_type']=='arterial'
    assert gas['blood_gas_context']['fio2']['value']=='40' and gas['blood_gas_context']['peep']['value']=='5'
    assert gas['occurred']['clock']=='unknown' and gas['acquisition']['quality']['status']=='unknown'
    exact={json.dumps(a['exact'],sort_keys=True) for a in note['associations']};assert len(exact)==3
    for stage in ('baseline','intervention','followup'):
        source=next(c for c in note['external_evidence'] if c['namespace']=='clinrx.local.reassessment.'+stage+'/v1');ref=json.loads(source['code'])
        assert json.dumps(ref,sort_keys=True) in exact and (ref['kind'],ref['id'],ref['version']) in facts
        assert stage+': '+json.dumps(ref,separators=(',',':')) in note['description']['raw_display']
    assert 'Patient-level relationship is not established' in note['description']['raw_display']
    for digest,payload in db.execute('SELECT payload_digest,payload FROM circulatory_execution'):assert hashlib.sha256(payload.encode()).hexdigest()==digest
assert (root/'walkthrough/original/saved-reassessment.jpg').read_bytes().startswith(b'\xff\xd8')
print('PASS: publication hashes, nine preserved captures, lossless mirrors, later SQLite export/all tables, prior 169 rows and two receipts, exact records 170/171 and three reassessment references. No corrected-source browser or independent clinical acceptance claimed.')
