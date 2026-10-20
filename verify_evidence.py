from pathlib import Path
import hashlib,json,base64
p=Path(__file__).resolve().parent
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
for f in json.loads((p/'SOURCE-MANIFEST.json').read_text()):
 b=(p/'source'/f['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==f['sha256'];assert len(b)==f['bytes'];assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['git_blob']
i=json.loads((p/'IDENTITY.json').read_text())
for label in ('source','parent'):
 b=(p/(label+'-commit.raw')).read_bytes();assert hashlib.sha1(f'commit {len(b)}\0'.encode()+b).hexdigest()==i[label]
for label in ('final-focused','final-typecheck','default-build','rf2-build'):
 m=json.loads((p/'evidence'/f'{label}.json').read_text());assert m['exit_code']==0
 for n,h in m['source_sha256'].items():assert hashlib.sha256((p/'source'/n).read_bytes()).hexdigest()==h
for mode,files in json.loads((p/'BUILD-SHA256SUMS.json').read_text()).items():
 for n,h in files.items():assert hashlib.sha256((p/mode/n).read_bytes()).hexdigest()==h
for m in json.loads((p/'MIRRORS.json').read_text()):
 s=''.join((p/n).read_text() for n in m['parts']);b=base64.b64decode(s) if m['encoding']=='base64' else s.encode();assert b==(p/m['path']).read_bytes()
b=(p/'old-control-source/frontend/src/demo/RF2FluidChart.tsx').read_bytes();assert b in (p/'changes.diff').read_bytes() or hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()=='7258d54f0be3c2b1dbbf131bb7a8f06d93124f96'
print('Publication/source/build integrity PASS; no application tests rerun.')
