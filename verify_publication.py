from pathlib import Path
import hashlib,json,base64,sqlite3
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in json.loads((p/'PUBLICATION-SHA256SUMS.json').read_text()).items():assert sha((p/n).read_bytes())==h,n
for line in (p/'original/SHA256SUMS.txt').read_text().splitlines():
 h,n=line.split('  ',1);assert sha((p/'original'/n).read_bytes())==h,n
for m in json.loads((p/'MIRRORS.json').read_text()):
 b=base64.b64decode(''.join((p/n).read_text().strip() for n in m['parts']),validate=True)
 assert len(b)==m['bytes'] and sha(b)==m['sha256'] and b==(p/m['path']).read_bytes()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==m['git_blob']
meta=json.loads((p/'original/source-identity.json').read_text());raw=(p/'SOURCE-COMMIT.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta['source']
for name,h in json.loads((p/'original/source-hashes.json').read_text()).items():
 b=(p/'source'/name).read_bytes();assert sha(b)==h['sha256'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h['git_blob']
before=json.loads((p/'original/browser-before-rows.json').read_text());after=json.loads((p/'original/browser-after-rows.json').read_text())
assert len(before['fact_revision'])==174 and len(after['fact_revision'])==176 and after['fact_revision'][:174]==before['fact_revision']
assert len(after['circulatory_execution'])==2 and after['circulatory_execution']==before['circulatory_execution']
for t in before:
 if t not in ('fact_revision','revision_link','sqlite_sequence'):assert before[t]==after[t],t
assert after['revision_link'][:-1]==before['revision_link'] and after['revision_link'][-1]==[175,173]
idx=json.loads((p/'TABLES-INDEX.json').read_text())
for phase,rows in [('before',before),('after',after)]:
 for table,entry in idx[phase].items():
  assert [list(json.loads((p/n).read_text())['columns'].values()) for n in entry['rows']]==rows[table]
with sqlite3.connect('file:'+str(p/'original/browser-after.sqlite3')+'?mode=ro',uri=True) as db:
 assert db.execute('pragma integrity_check').fetchall()==[('ok',)]
 for table,rows in after.items():assert [list(x) for x in db.execute('select * from "'+table+'" order by rowid')]==rows,table
assert '639 passed' in (p/'original/frontend-final.log').read_text()
assert '66 passed' in (p/'original/gateway-regressions.log').read_text()
print('PASS: publication/original hashes, mirrors, source identity, readable rows, actual after SQLite integrity/correspondence and bounded result summaries. Data-only integrity, not independent application/test execution or acceptance.')
