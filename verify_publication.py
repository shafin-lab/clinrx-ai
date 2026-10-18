from pathlib import Path
import json,hashlib,base64,sqlite3
P=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,digest in json.loads((P/'PUBLICATION-SHA256SUMS.json').read_text()).items(): assert sha((P/name).read_bytes())==digest,name
for name,digest in json.loads((P/'original/SHA256SUMS.json').read_text()).items(): assert sha((P/'original'/name).read_bytes())==digest,name
for m in json.loads((P/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((P/p).read_text().strip() for p in m['parts']),validate=True)
 assert raw==(P/m['path']).read_bytes() and len(raw)==m['bytes'] and sha(raw)==m['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob']
index=json.loads((P/'TABLES-INDEX.json').read_text()); snapshots={}
for stage in ('before','after'):
 rows=json.loads((P/'original'/(stage+'-rows.json')).read_text()); snapshots[stage]=rows
 with sqlite3.connect('file:'+str(P/'original'/(stage+'.sqlite3'))+'?mode=ro&immutable=1',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
  assert set(rows)=={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  for table,items in rows.items():
   cols=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
   assert [list(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]==items
   ix=index[stage][table]; assert ix['columns']==cols and ix['count']==len(items)
   assert [json.loads((P/f).read_text()) for f in ix['files']]==[{'columns':cols,'row':r} for r in items]
b,a=snapshots['before'],snapshots['after']
assert len(b['fact_revision'])==173 and len(a['fact_revision'])==174
assert a['fact_revision'][:-1]==b['fact_revision']
for table in b:
 if table not in ('fact_revision','sqlite_sequence'): assert a[table]==b[table],table
assert len(a['circulatory_execution'])==2
notes=json.loads((P/'original/note-comparison.json').read_text())
old,new=notes['original_note'],notes['new_note']
assert new['id']=='90c89b62-1f3a-4903-b10d-eb8c6711e921' and new['revision']=='1' and new['supersedes'] is None
for obj in (old,new):
 row=next(r for r in a['fact_revision'] if r[1]==obj['kind'] and r[2]==obj['id'] and r[3]==obj['revision'])
 assert json.loads(row[7])==obj
 if obj is new:
  assert row[0]==174
  assert sha(row[7].encode())=='b0073215bcb9e38a35a8b24d5d3b50bbb7e7b9ce2aea114f6c185dd2d5ec3b87'
expected=[{'kind':'circulatory_oxygen','id':'a02f88e1-db04-48a0-89e6-f236016a38a8','version':'1'},{'kind':'circulatory_vasoactive','id':'99a26724-026c-4ccc-ac63-c22ddada2664','version':'1'},{'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'aeaca128-a674-4dfa-859a-9ab11d2a9368'}]
assert [x['exact'] for x in new['associations']]==expected
assert [json.loads(x['code']) for x in new['external_evidence']]==expected
assert [x['namespace'] for x in new['external_evidence']]==['clinrx.local.reassessment.'+x+'/v1' for x in ('baseline','intervention','followup')]
assert old['id']=='abae4ef7-74c4-48cc-bb50-f50e9fb151cd'
assert old['associations'][-1]['exact']==dict(expected[-1],version='1')
for ref in expected:
 row=next(r for r in a['fact_revision'] if r[1]==ref['kind'] and r[2]==ref['id'] and r[3]==ref['version'])
 assert row[4:6]==['synthetic-p1','synthetic-e1'] and row[0]<174
form=(P/'original/form.txt').read_text();review=(P/'original/review-ready.txt').read_text()
for ref in expected:
 assert ref['id'] in form and ref['version'] in form
 assert json.dumps(ref,separators=(',',':')) in review.replace(chr(92)+chr(34),chr(34))
assert 'Exact revision saved and confirmed. Ingestion sequence 174.' in (P/'original/saved.txt').read_text()
assert (P/'original/saved.txt').read_bytes()==(P/'original/final.txt').read_bytes()
assert sha((P/'original/before.sqlite3').read_bytes())=='5b9c25415bdb21313771ddf0ab07084623f6f053dc4797d892feb86862b82f72'
print('PASS: originals/publication/mirrors; both SQLite integrity checks and all-table/readable correspondence; 173 unchanged fact rows and two receipts; new note exact associations/stages/source scope/digest; original note references preserved; captured confirmation at 174. Data-only, not independent live execution.')
