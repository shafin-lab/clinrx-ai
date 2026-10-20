from pathlib import Path
import base64,hashlib,json
p=Path(__file__).resolve().parent
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
for f in json.loads((p/'SOURCE-MANIFEST.json').read_text()):
 b=(p/'source'/f['path']).read_bytes();assert len(b)==f['bytes'];assert hashlib.sha256(b).hexdigest()==f['sha256'];assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['git_blob']
b=(p/'source-commit.raw').read_bytes();assert hashlib.sha1(f'commit {len(b)}\0'.encode()+b).hexdigest()=='780112139c2a6f0224df5331600f3874e8b714c7'
for n,h in json.loads((p/'source/original/SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/'source/original'/n).read_bytes()).hexdigest()==h
for n,h in json.loads((p/'evidence/corrected-focused.json').read_text())['source_sha256'].items():assert hashlib.sha256((p/'source'/n).read_bytes()).hexdigest()==h
calls=0
for idx in (p/'evidence/corrected-focused-captures').glob('*.index.json'):
 for c in json.loads(idx.read_text())['calls']:
  for kind in ('input','output'):assert hashlib.sha256((idx.parent/c[kind]).read_bytes()).hexdigest()==c[kind+'_sha256']
  o=json.loads((idx.parent/c['output']).read_text());assert o['numerical_eligibility_active'] is False
  if o['run_status'] in ('withheld','rejected'):assert not any(d['decision']=='candidate_include' for d in o['decisions'])
  calls+=1
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=''.join((p/n).read_text() for n in m['parts']);b=base64.b64decode(raw) if m['encoding']=='base64' else raw.encode();assert b==(p/m['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['sha256']
assert calls==135
print(json.dumps({'data_integrity':'PASS','source_files':70,'captured_calls':calls,'application_tests_executed':False}))
