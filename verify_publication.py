from pathlib import Path
import json,hashlib,base64
p=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
for name,digest in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert sha((p/name).read_bytes())==digest,name
for name,digest in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/name).read_bytes())==digest,name
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes'] and sha(raw)==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
source=json.loads((p/'original/source.json').read_text());assert source['source']=='ebbab2955109884169ae7ceef4a87d0f12af4ebf'
for f in source['files']:assert sha((p/'source'/f['path']).read_bytes())==f['sha256']
raw=(p/'SOURCE-COMMIT.txt').read_bytes();assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['source'];assert raw.startswith(('tree '+source['tree']+'\nparent 008034ea12275406d8f5aede8ceb3aa5142570b6\n').encode())
b=json.loads((p/'original/before-view-rows.json').read_text());a=json.loads((p/'original/after-view-rows.json').read_text());assert a==b;assert len(a)==12 and len(a['fact_revision'])==174 and len(a['circulatory_execution'])==2
index=json.loads((p/'TABLES-INDEX.json').read_text())
for stage in ('before','after'):
 for table,items in a.items():
  ix=index[stage][table];assert ix['count']==len(items)
  assert [json.loads((p/f).read_text()) for f in ix['files']]==[{'columns':ix['columns'],'row':row} for row in items]
notes={r[2]:json.loads(r[7]) for r in a['fact_revision'] if r[2] in ('abae4ef7-74c4-48cc-bb50-f50e9fb151cd','90c89b62-1f3a-4903-b10d-eb8c6711e921')}
old=notes['abae4ef7-74c4-48cc-bb50-f50e9fb151cd'];new=notes['90c89b62-1f3a-4903-b10d-eb8c6711e921']
assert old['associations'][-1]['exact']=={'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'1'}
assert new['associations'][-1]['exact']==dict(old['associations'][-1]['exact'],version='aeaca128-a674-4dfa-859a-9ab11d2a9368')
dom=(p/'original/comparison.txt').read_text();assert 'Clinical execution disabled.' in dom
for note in (old,new):
 assert note['id'] in dom
 for assoc in note['associations']:assert assoc['exact']['id'] in dom and assoc['exact']['version'] in dom
assert (p/'original/comparison.jpg').read_bytes()[:3]==b'\xff\xd8\xff'
assert '602 passed' in (p/'original/frontend-tests.log').read_text()
print('PASS: all original/publication hashes, lossless mirrors, four committed source-file hashes and raw commit identity; identical all-table exports/readable rows; 174 facts/two receipts; retained note ABG references and captured DOM correspondence. Data-only verification, not application/test execution or independent browser witnessing.')
