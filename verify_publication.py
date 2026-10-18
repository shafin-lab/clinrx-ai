from pathlib import Path
import json,hashlib,base64
p=Path(__file__).resolve().parent
for name,digest in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes']
 assert hashlib.sha256(raw).hexdigest()==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
 assert raw[:3]==b'\xff\xd8\xff' and m['path'].endswith('.jpg')
print('PASS: publication hashes, original JPEG and lossless mirror correspondence. Data-only integrity; no live application verification.')
