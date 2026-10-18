from pathlib import Path
import hashlib,json,base64
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert sha((p/n).read_bytes())==h,n
for n,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/n).read_bytes())==h,n
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes'] and sha(raw)==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
meta=json.loads((p/'original/validation.json').read_text());assert meta['source']=='db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5'
for f in meta['source_files']:assert sha((p/'source'/f['path']).read_bytes())==f['sha256']
raw=(p/'SOURCE-COMMIT.txt').read_bytes();assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta['source'];assert raw.startswith(('tree '+meta['tree']+'\nparent '+meta['parent']+'\n').encode())
assert '6 failed' in (p/'original/old-code-negative-control.log').read_text()
assert '49 passed' in (p/'original/focused-tests.log').read_text()
for n in ('default-build.log','authoring-build.log'):
 s=(p/'original'/n).read_text();assert 'tsc --noEmit && vite build' in s and 'built in' in s
print('PASS: original/publication hashes, lossless mirrors, three committed source hashes and raw commit identity, separately attributed negative/final log summaries. Data-only integrity, not execution of application/tests or independent acceptance.')
