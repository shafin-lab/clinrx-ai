from pathlib import Path
import hashlib,json,base64
p=Path(__file__).resolve().parent
sha=lambda x:hashlib.sha256(x).hexdigest()
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert sha((p/n).read_bytes())==h,n
for n,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/n).read_bytes())==h,n
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes'] and sha(raw)==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
u=json.loads((p/'original/update.json').read_text());assert u['source']=='db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5'
for n,h in u['build_files'].items():assert sha((p/'reference/accepted-build'/n).read_bytes())==h,n
html=(p/'reference/accepted-build/index.html').read_text()
for x in json.loads((p/'original/browser-resources.json').read_text()):assert x['path'] in html and x['path'].lstrip('/') in u['build_files']
b=(p/'original/before-rows.json').read_bytes();a=(p/'original/after-rows.json').read_bytes();assert a==b;assert sha(a)=='3269bec045684309a0d532d3a3b22e7dde42eb9b787cd2d7b3a5501697973c35'
rows=json.loads(a);assert len(rows)==12 and len(rows['fact_revision'])==174 and len(rows['circulatory_execution'])==2
index=json.loads((p/'TABLES-INDEX.json').read_text())
for stage in ('before','after'):
 for t,items in rows.items():
  ix=index[stage][t];assert ix['count']==len(items);assert [json.loads((p/f).read_text()) for f in ix['files']]==[{'columns':ix['columns'],'row':r} for r in items]
dom=(p/'original/comparison.txt').read_text();assert 'Clinical execution disabled.' in dom
for note_id,version in (('abae4ef7-74c4-48cc-bb50-f50e9fb151cd','1'),('90c89b62-1f3a-4903-b10d-eb8c6711e921','aeaca128-a674-4dfa-859a-9ab11d2a9368')):
 note=json.loads(next(r[7] for r in rows['fact_revision'] if r[2]==note_id));assert note_id in dom;ref=note['associations'][-1]['exact'];assert ref=={'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':version};assert version in dom
assert (p/'original/comparison.jpg').read_bytes()[:3]==b'\xff\xd8\xff'
print('PASS: original/publication hashes, lossless mirrors, accepted build-byte/path correspondence, identical 12-table exports/readable mirrors, 174 facts/two receipts and captured exact note references. Data-only verification; no live browser, adversarial injection or authenticated network proof.')
