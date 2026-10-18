from pathlib import Path
import json,hashlib,base64
p=Path(__file__).resolve().parent
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
for n,h in json.loads((p/'ORIGINAL-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/'original'/n).read_bytes()).hexdigest()==h,n
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes']
 assert hashlib.sha256(raw).hexdigest()==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
for name in ('original-reference.jpg','corrected-reference.jpg'):assert (p/'original'/name).read_bytes()[:3]==b'\xff\xd8\xff'
dom=(p/'original/both-notes.txt').read_text().replace(chr(92)+chr(34),chr(34))
for ref in ({'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'1'},{'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'aeaca128-a674-4dfa-859a-9ab11d2a9368'}):assert json.dumps(ref,separators=(',',':')) in dom
for value in ('abae4ef7-74c4-48cc-bb50-f50e9fb151cd','90c89b62-1f3a-4903-b10d-eb8c6711e921','7.3300','7.3500','Clinical execution disabled.','Exact revision saved and confirmed. Ingestion sequence 174.'):assert value in dom,value
print('PASS: publication and three original hashes, JPEG signatures, lossless mirrors and captured DOM note/reference correspondence. Data-only integrity; no new persistence or live browser proof.')
