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
b,a=snapshots['before'],snapshots['after']; assert len(b['fact_revision'])==172 and len(a['fact_revision'])==173
assert a['fact_revision'][:-1]==b['fact_revision']; assert a['revision_link'][:-1]==b['revision_link']; assert a['revision_link'][-1]==[173,170]
for table in b:
 if table not in ('fact_revision','revision_link','sqlite_sequence'): assert a[table]==b[table],table
assert len(a['circulatory_execution'])==2
records=json.loads((P/'original/correction-records.json').read_text()); print('Record labels:',list(records))
for r in a['fact_revision']:
 if r[0] in (170,173):
  obj=json.loads(r[7]); expected=records['original' if r[0]==170 else 'correction']; assert obj==expected
  if r[0]==173: assert sha(r[7].encode())=='ef4c7c9855eb53c874373a7e7472b1c0bb10b58c7465d56f4a08fb826d65eb09'
orig,cor=records['original'],records['correction']
for field in ('occurred','available','blood_gas_context','acquisition','calculation_inputs'): assert orig[field]==cor[field],field
assert cor['supersedes']=={'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'1'}
display=json.loads((P/'original/displayed-history-comparison.json').read_text()); assert [x['value'] for x in display]==['7.3300','7.3500']; assert [x['ingestion'] for x in display]==['170','173']
for field in ('source_time','sample','specimen','fio2','peep','unit'): assert display[0][field]==display[1][field]
print('PASS: publication/original hashes; lossless mirrors; both SQLite integrity checks and all table/readable exports; unchanged 172 facts and receipts; exact successor/link/context; displayed history correspondence. Data-only verification, not live browser execution.')
