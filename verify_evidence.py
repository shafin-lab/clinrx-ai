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

publication_count=n
import re
names=['before-two-selections.txt','three-unsaved.txt','three-saved.txt','three-restored.txt']
docs={name:(r/'original'/name).read_text() for name in names}
cards={name:[p.strip() for p in re.split(r'(?m)^  - article:\n',text)[1:]] for name,text in docs.items()}
assert [len(cards[n]) for n in names]==[2,3,3,3]
for name in names[1:]:assert cards[name][:2]==cards[names[0]],name
assert cards['three-unsaved.txt']==cards['three-saved.txt']==cards['three-restored.txt']
assert 'Restored saved handover: 2 selection(s).' in docs[names[0]]
assert 'Unsaved handover changes. Save locally before reloading.' in docs[names[1]]
assert 'Saved locally in this browser: 3 selection(s). They will be restored after reload.' in docs[names[2]]
assert 'Restored saved handover: 3 selection(s). Saved 2026-10-19T05:02:22.319Z.' in docs[names[3]]
for text in docs.values():assert 'Clinical execution disabled.' in text
meta=json.loads((r/'original/walkthrough.json').read_text())
assert meta['selectionCountBefore']==2 and meta['selectionCountAfter']==3
for key,n,expected in [('retained',0,'Recorded result: 7.3700 1'),('retained',1,'Patient-level relationship is not established.'),('added',2,'Recorded result: 7.3400 1')]:
 item=meta[key][n] if key=='retained' else meta[key];card=cards['three-restored.txt'][n]
 for v in [item['kind'],item['id'],item['revision'],expected,'ingestion '+str(item['ingestion']),'cutoff 178']:assert v in card,(key,v)
flat=cards['three-restored.txt'][1].replace('\\"','"')
follow=meta['retained'][0]
assert 'followup: {"kind":"'+follow['kind']+'","id":"'+follow['id']+'","version":"'+follow['revision']+'"}' in flat
inspector=(r/'original/baseline-inspector.txt').read_text()
for v in ['a02f88e1-db04-48a0-89e6-f236016a38a8','2026-10-08T09:20:00.123456Z','7.3400 1','guided-arterial-sample','arterial','40 %','5 cmH2O']:assert v in inspector,v
print(json.dumps({'publication_hashes':publication_count,'original_hashes':o,'indexed_git_blobs':len(a),'reconstructed_images':len(mirrors),'mirror_parts':sum(len(m['parts']) for m in mirrors),'card_counts':[len(cards[x]) for x in names],'prior_card_text_unchanged':True,'saved_restored_card_text_equal':True,'result':'PASS'},indent=2))
