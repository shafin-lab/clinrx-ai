from pathlib import Path
import json,hashlib,base64
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PUBLICATION-SHA256SUMS.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==h,rel
for rel,h in json.loads((root/'original/SHA256SUMS.json').read_text()).items():assert hashlib.sha256((root/'original'/rel).read_bytes()).hexdigest()==h,rel
for m in json.loads((root/'MIRRORS.json').read_text()):
 s=''.join((root/p).read_text() for p in m['parts']);b=base64.b64decode(s) if m['encoding']=='base64-concatenation' else s.encode()
 assert b==(root/m['path']).read_bytes();assert len(b)==m['bytes'];assert hashlib.sha256(b).hexdigest()==m['sha256']
for f in json.loads((root/'original/source/FILES.json').read_text()):
 b=(root/'original/source'/f['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==f['sha256'];assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['git_blob']
raw=(root/'source-identity/commit.raw').read_bytes();assert hashlib.sha1(f'commit {len(raw)}\0'.encode()+raw).hexdigest()=='d608ce8655a024cf7c9e4d78dbeb85b50d20fdc5'
before=(root/'original/database-before-rows.json').read_bytes();after=(root/'original/database-after-rows.json').read_bytes();assert before==after
rows=json.loads(before);assert len(rows)==12 and len(rows['fact_revision'])==186 and len(rows['circulatory_execution'])==2
print(json.dumps({'status':'PASS','publication_checksums':len(manifest),'source_files':2,'all_12_exports_byte_identical':True,'facts':186,'receipts':2,'browser_claim':False},indent=2))
