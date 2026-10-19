from pathlib import Path
import base64,hashlib,json,sqlite3,re
r=Path(__file__).resolve().parent
def sha(d):return hashlib.sha256(d).hexdigest()
def oid(k,d):return hashlib.sha1((k+' '+str(len(d))+'\0').encode()+d).hexdigest()
def manifest(name):
 lines=(r/name).read_text().splitlines()
 for line in lines:
  h,p=line.split('  ',1);path=(r/p).resolve();assert path.is_relative_to(r) and sha(path.read_bytes())==h,p
 return len(lines)
count=manifest('SHA256SUMS');originals=manifest('ORIGINAL-SHA256SUMS');index=json.loads((r/'ARTIFACTS.json').read_text())
for f in index:
 d=(r/f['path']).read_bytes();assert len(d)==f['bytes'] and oid('blob',d)==f['git_blob'],f['path']
mirrors=json.loads((r/'MIRRORS.json').read_text())
for m in mirrors:
 d=base64.b64decode(''.join((r/p).read_text() for p in m['parts']),validate=True);assert d==(r/m['original']).read_bytes() and sha(d)==m['sha256'] and len(d)==m['bytes'] and oid('blob',d)==m['git_blob']
 if m['original'].endswith('.jpg'):assert d.startswith(b'\xff\xd8\xff')
s=json.loads((r/'application-SOURCE.json').read_text());raw=(r/'application-source-commit.txt').read_bytes();assert oid('commit',raw)==s['source'] and raw.startswith(('tree '+s['tree']+'\nparent '+s['parent']+'\n').encode())
entries=json.loads((r/'application-SOURCE-TREE.json').read_text());tree={};by_path={e['path']:e for e in entries}
for e in entries:
 node=tree;parts=e['path'].split('/')
 for part in parts[:-1]:node=node.setdefault(part,{})
 assert parts[-1] not in node;node[parts[-1]]=(e['mode'],e['oid'])
def build(node):
 d=b''
 for name,v in sorted(node.items(),key=lambda kv:kv[0].encode()+(b'/' if isinstance(kv[1],dict) else b'')):
  mode,h=('40000',build(v)) if isinstance(v,dict) else v;d+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(h)
 return oid('tree',d)
assert build(tree)==s['tree']
for f in s['files']:
 d=(r/f['path']).read_bytes();assert sha(d)==f['sha256'] and oid('blob',d)==f['git_blob']==by_path[f['repository_path']]['oid']
buildref=json.loads((r/'reference/local-update/final-installed-build.json').read_text());assert buildref['source']==s['source']
for p,h in buildref['files'].items():assert sha((r/'reference/authoring-build'/p).read_bytes())==h
assert buildref['settings']=={'VITE_SYNTHETIC_HOSTED':'true','VITE_SYNTHETIC_AUTHORING':'true'}
def database(path):
 with sqlite3.connect('file:'+str(r/path)+'?mode=ro',uri=True) as db:
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok';data={}
  for (t,) in db.execute("select name from sqlite_master where type='table' order by name"):
   q='select * from "'+t.replace('"','""')+'"';c=db.execute(q);data[t]={'columns':[x[0] for x in c.description],'rows':[list(x) for x in c.fetchall()]}
  return data
exports=json.loads((r/'EXPORTS.json').read_text());databases={}
for e in exports:
 d=database(e['database']);assert d==json.loads((r/e['export']).read_text());databases[e['database']]=d
before=databases['original/map-correction/before.sqlite3'];mapafter=databases['original/map-correction/after.sqlite3'];notebefore=databases['original/reassessment/before.sqlite3'];after=databases['original/reassessment/after.sqlite3'];assert mapafter==notebefore
for a,b,link in [(before,mapafter,1),(notebefore,after,0)]:
 assert len(a)==len(b)==12
 for t in a:
  assert a[t]['columns']==b[t]['columns'];old=set(map(repr,a[t]['rows']));new=set(map(repr,b[t]['rows']))
  if t=='fact_revision':assert not old-new and len(new-old)==1
  elif t=='revision_link':assert not old-new and len(new-old)==link
  elif t=='sqlite_sequence':assert b[t]['rows'][0][1]==a[t]['rows'][0][1]+1
  else:assert old==new,t
assert len(before['fact_revision']['rows'])==165 and len(after['fact_revision']['rows'])==167 and len(after['circulatory_execution']['rows'])==2
facts={};payloads={}
for row in after['fact_revision']['rows']:
 rec=dict(zip(after['fact_revision']['columns'],row));f=json.loads(rec['payload']);assert rec['patient_id']=='synthetic-p1' and rec['encounter_id']=='synthetic-e1';facts[(rec['kind'],rec['fact_id'],rec['revision'])]=f;payloads[(rec['kind'],rec['fact_id'],rec['revision'])]=rec
mapkind='circulatory_pressure';mapid='fs-MAP-15';oldver='41675deb-aa68-444f-a5fe-6ed8770c2c0c';newver='915ae2cb-99f9-47e6-883e-9fc51725a7f0'
old=facts[(mapkind,mapid,oldver)];new=facts[(mapkind,mapid,newver)];assert old['result']['quantity']['value']=='62.0000' and new['result']['quantity']['value']=='63.0000'
assert {k for k in old if old[k]!=new.get(k)}=={'revision','supersedes','result','provenance','correction_reason'}
assert new['supersedes']=={'kind':mapkind,'id':mapid,'version':oldver}
assert {k:v for k,v in old['result']['quantity'].items() if k!='value'}=={k:v for k,v in new['result']['quantity'].items() if k!='value'}
assert payloads[(mapkind,mapid,newver)]['ingestion_sequence']==166
noteid='00234d1d-b5ff-47da-a702-e6f50918056f';oldid='3583c95b-119c-4daf-9642-42845112602e';note=facts[('circulatory_event',noteid,'1')];older=facts[('circulatory_event',oldid,'1')]
assert note==json.loads((r/'original/reassessment/new-note.json').read_text()) and note['supersedes'] is None
assert payloads[('circulatory_event',noteid,'1')]['ingestion_sequence']==167
assert sha(payloads[('circulatory_event',noteid,'1')]['payload'].encode())=='1ebc8a36d78781955607c81177a2886038e778087b647806aa34b693f31d9c9e'
def refs(f):return {e['namespace'].split('.')[-1].split('/')[0]:json.loads(e['code']) for e in f['external_evidence'] if e['namespace'].startswith('clinrx.local.reassessment.')}
nrefs=refs(note);orefs=refs(older);assert nrefs['baseline']==orefs['baseline']=={'kind':'circulatory_cardiac','id':'fs-CO-15','version':'1'}
assert nrefs['intervention']==orefs['intervention']=={'kind':'circulatory_vasoactive','id':'fs-N-CHANGE','version':'1'}
assert nrefs['followup']=={'kind':mapkind,'id':mapid,'version':newver} and orefs['followup']['version']==oldver
for stage,ref in nrefs.items():
 assert (ref['kind'],ref['id'],ref['version']) in facts
 assert sum(a['exact']==ref and a['role']=='context' and a['status']=='resolved' and a['scope']=={'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','longitudinal_context_id':None} for a in note['associations'])==1
history=(r/'original/map-correction/history.txt').read_text();assert all('Recorded result: '+v+' mmHg' in history for v in ['61','62.0000','63.0000'])
comparison=(r/'original/comparison/comparison.txt').read_text();assert all(x in comparison for x in [oldid,noteid,oldver,newver,'2026-10-08T09:25:00Z','2026-10-08T09:30:00Z'])
for label,fact in [('A',older),('B',note)]:
 match=re.search(r'generic "Note '+label+r' full authored narrative"\n  - term: raw display\n  - definition: (.+)',comparison);assert match
 assert ' '.join(json.loads(match.group(1)).split())==' '.join(fact['description']['raw_display'].split())
saved4=(r/'original/handover-four/saved.txt').read_text();restored4=(r/'original/handover-four/restored.txt').read_text();assert 'Saved locally in this browser: 4 selection(s)' in saved4 and 'Restored saved handover: 4 selection(s)' in restored4 and 'Saved reference unavailable in the current snapshot' in restored4
final=(r/'original/handover-final-two/restored.txt').read_text();assert 'Restored saved handover: 2 selection(s)' in final and 'Clinical execution disabled.' in final
identities=re.findall(r'^    - paragraph: (circulatory_\w+) / ([^ ]+) / ([^\n]+)$',final,re.M)
assert set(identities)=={('circulatory_event',noteid,'1'),(mapkind,mapid,newver)}
assert 'cutoff 167 · ingestion 167' in final and 'cutoff 167 · ingestion 166' in final and 'Recorded result: 63.0000 mmHg' in final
assert 'Saved reference unavailable in the current snapshot' not in final
print(json.dumps({'result':'PASS','publication_hashes':count,'original_artifacts':originals,'indexed_blobs':len(index),'mirrors':len(mirrors),'mirror_parts':sum(len(m['parts']) for m in mirrors),'application':s['source'],'source_tree_recomputed':True,'sqlite_integrity_and_exports':len(databases),'tables_per_database':12,'original_fact_rows_unchanged':165,'fact_additions':2,'retained_receipts_unchanged':2,'final_handover_exact_selections':2,'scope':'data/hash/DOM correspondence; not live browser or storage-byte proof'},indent=2))
