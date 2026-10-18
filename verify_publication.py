from pathlib import Path
import json,hashlib,base64
p=Path(__file__).resolve().parent
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
for n,h in json.loads((p/'ORIGINAL-SHA256SUMS.json').read_text()).items():assert hashlib.sha256((p/'original'/n).read_bytes()).hexdigest()==h,n
for m in json.loads((p/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((p/f).read_text().strip() for f in m['parts']),validate=True)
 assert raw==(p/m['path']).read_bytes() and len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
assert (p/'original/reference-table.jpg').read_bytes()[:3]==b'\xff\xd8\xff'
raw=(p/'reference/persisted-notes.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='9f2a68a88c2fa3609f0126b9c429ed2c4ee09f88c9d737c01d75098876e3d5fc'
notes=json.loads(raw)
for name in ('expanded-notes.txt','final.txt'):
 dom=(p/'original'/name).read_text().split('  - region "Recorded evidence":')[0].replace(chr(92)+chr(34),chr(34));normalized=' '.join(dom.split())
 assert 'Clinical execution disabled.' in dom
 for label,key in (('A','original_note'),('B','new_note')):
  note=notes[key];assert note['id'] in dom
  narrative=' '.join(note['description']['raw_display'].split());assert narrative in normalized
  for assoc in note['associations']:
   ref=assoc['exact'];assert json.dumps({k:ref[k] for k in ('kind','id','version')},separators=(',',':')) in dom
  assert 'Note '+label+' uncertainty and provenance' in dom
  for caveat in note['uncertainty']:assert ' '.join(caveat.split()) in normalized
print('PASS: original/publication hashes and lossless mirrors; reused persisted-note byte identity; both captured authored narratives, exact references and uncertainty correspondence. Data-only checks; no new execution or persistence evidence.')
