from pathlib import Path
import hashlib,json,base64
p=Path(__file__).resolve().parent
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
for f in json.loads((p/'SOURCE-MANIFEST.json').read_text()):
 b=(p/'source'/f['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==f['sha256'];assert len(b)==f['bytes'];assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['git_blob']
for f,h in [('source-commit.raw','5830cdceb12f5adc48ce1867429ac7fd1b5a53f2'),('parent-commit.raw','780112139c2a6f0224df5331600f3874e8b714c7')]:
 b=(p/f).read_bytes();assert hashlib.sha1(f'commit {len(b)}\0'.encode()+b).hexdigest()==h
for n,h in json.loads((p/'source/original/SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/'source/original'/n).read_bytes()).hexdigest()==h
for label,count,exitcode in [('h123-old-control',34,1),('h123-corrected-focused',169,0)]:
 meta=json.loads((p/'evidence'/f'{label}.json').read_text());assert meta['exit_code']==exitcode
 base=p/'evidence/h123-old-control-source' if exitcode else p/'source'
 for n,h in meta['source_sha256'].items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h
 folder=p/'evidence'/f'{label}-captures';calls=0
 for index in folder.glob('*.index.json'):
  for c in json.loads(index.read_text())['calls']:
   for kind in ('input','output'):assert hashlib.sha256((folder/c[kind]).read_bytes()).hexdigest()==c[kind+'_sha256']
   o=json.loads((folder/c['output']).read_text());assert o['numerical_eligibility_active'] is False
   if o['run_status'] in ('withheld','rejected'):assert not any(d['decision']=='candidate_include' for d in o['decisions'])
   calls+=1
 assert calls==count
for m in json.loads((p/'MIRRORS.json').read_text()):
 s=''.join((p/n).read_text() for n in m['parts']);b=base64.b64decode(s) if m['encoding']=='base64' else s.encode();assert b==(p/m['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['sha256']
print(json.dumps({'data_integrity':'PASS','source_files':71,'old_control_calls':34,'corrected_calls':169,'tests_executed_by_verifier':False}))
