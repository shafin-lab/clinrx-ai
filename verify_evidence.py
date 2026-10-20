from pathlib import Path
import json,hashlib,base64
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==h,rel
mirrors=json.loads((root/'MIRRORS.json').read_text())
for m in mirrors:
 raw=''.join((root/p).read_text() for p in m['parts']);b=base64.b64decode(raw) if m['encoding']=='base64-concatenation' else raw.encode()
 assert b==(root/m['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['sha256']
for folder in ['usability-8186bb7','feedback-195f452']:
 p=root/'original'/folder
 for rel,h in json.loads((p/'SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/rel).read_bytes()).hexdigest()==h
 before=json.loads((p/'database-before-rows.json').read_text());after=json.loads((p/'database-after-rows.json').read_text())
 assert before==after;assert len(after)==12 and len(after['fact_revision'])==186 and len(after['circulatory_execution'])==2
for f in json.loads((root/'candidate-source/FILES.json').read_text()):
 b=(root/'candidate-source/files'/f['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==f['sha256'];assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['git_blob']
print(json.dumps({'status':'PASS','publication_hashes':len(manifest),'mirrors':len(mirrors),'source_files':6,'both_installations_all_12_tables_unchanged':True,'facts':186,'receipts':2,'browser_claim':False},indent=2))
