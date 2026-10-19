from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
manifest=json.loads((P/'PUBLICATION-SHA256SUMS.json').read_text())
for n,d in manifest.items():assert h((P/n).read_bytes())==d,n
original=json.loads((P/'original/SHA256SUMS.json').read_text())
for n,d in original.items():assert h((P/'original'/n).read_bytes())==d,n
mirrors=json.loads((P/'MIRRORS.json').read_text())
for e in mirrors:
 b=b''.join((P/n).read_bytes() for n in e['parts']);assert b==(P/e['path']).read_bytes() and len(b)==e['bytes'] and h(b)==e['sha256'] and blob(b)==e['git_blob']
s=json.loads((P/'source-correspondence.json').read_text())
assert s['head']=='5cb73212ae6104b02bad361886cd9507795d88bf' and len(s['files'])==5
assert s['source']==json.loads((P/'original/tested-files.json').read_text())
for n,e in s['source'].items():
 b=(P/'original/source'/n).read_bytes();assert h(b)==e['sha256'] and blob(b)==e['git_blob']
b=(P/'original/raw-commit.txt').read_bytes();assert hashlib.sha1(b'commit '+str(len(b)).encode()+b'\0'+b).hexdigest()==s['head']
assert s['backend_tree']==s['parent_backend_tree'] and s['tests_tree']==s['parent_tests_tree']
r=json.loads((P/'hosted/run.json').read_text());assert r['headSha']==s['head'] and r['status']=='completed' and r['conclusion']=='success'
assert all(j['conclusion']=='success' for j in r['jobs']) and {j['name'] for j in r['jobs']}=={'frontend','backend'}
for name in ['backend','frontend']:
 t=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',(P/f'hosted/{name}.log').read_text());assert 'event=workflow_dispatch source_sha='+s['head'] in t
 assert ('4318 passed, 1 warning in 1093.79s' in t) if name=='backend' else ('710 passed' in t and '23 passed' in t)
print(json.dumps({'status':'PASS','publication_hashes':len(manifest),'original_hashes':len(original),'mirrors':len(mirrors),'tested_source_files':len(s['files']),'hosted_checkout':s['head'],'backend':4318,'frontend':710},indent=2))
