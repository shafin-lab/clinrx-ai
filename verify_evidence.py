from pathlib import Path
import hashlib,json,base64
r=Path(__file__).resolve().parent
def sha(d):return hashlib.sha256(d).hexdigest()
def oid(kind,d):return hashlib.sha1((kind+' '+str(len(d))+'\0').encode()+d).hexdigest()
def manifest(name):
 lines=(r/name).read_text().splitlines()
 for line in lines:
  digest,name=line.split('  ',1);p=(r/name).resolve();assert p.is_relative_to(r.resolve())
  assert sha(p.read_bytes())==digest,name
 return len(lines)
n=manifest('SHA256SUMS');o=manifest('ORIGINAL-SHA256SUMS')
a=json.loads((r/'ARTIFACTS.json').read_text())
for f in a:
 d=(r/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256'] and oid('blob',d)==f['git_blob'],f['path']
mirrors=json.loads((r/'MIRRORS.json').read_text())
for m in mirrors:
 d=base64.b64decode(''.join((r/p).read_text() for p in m['parts']),validate=True)
 assert d==(r/m['original']).read_bytes() and sha(d)==m['sha256'] and len(d)==m['bytes'] and oid('blob',d)==m['git_blob']
 assert d.startswith(b'\xff\xd8\xff') and m['original'].endswith('.jpg')
s=json.loads((r/'SOURCE.json').read_text());assert oid('commit',(r/'reference/source-commit.txt').read_bytes())==s['application_reference']
before=(r/'original/before.txt').read_bytes();after=(r/'original/after-reload.txt').read_bytes();assert before==after
text=after.decode();meta=json.loads((r/'original/walkthrough.json').read_text())
for v in [meta['abg']['id'],meta['abg']['revision'],meta['note']['id'],'Recorded result: 7.3700 1','Restored saved handover: 2 selection(s).','Clinical execution disabled.','ingestion 177','ingestion 178','cutoff 178','Patient-level relationship is not established.','not a new sample or evidence of physiological improvement']:
 assert v in text,v
assert meta['abg']['revision']==meta['note']['followupRevision']
assert 'followup: {\"kind\":\"circulatory_oxygen\",\"id\":\"'+meta['abg']['id']+'\",\"version\":\"'+meta['abg']['revision']+'\"}' in text.replace('\\"','"')
print(json.dumps({'publication_hashes':n,'original_hashes':o,'indexed_git_blobs':len(a),'reconstructed_images':len(mirrors),'mirror_parts':sum(len(m['parts']) for m in mirrors),'same_dom_bytes':True,'result':'PASS'},indent=2))
