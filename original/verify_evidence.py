"""Portable data-only checks; does not run the application or its tests."""
from pathlib import Path
import json,hashlib,sqlite3
r=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
source=json.loads((r/'source/FILES.json').read_text())
for name,v in source.items():
 b=(r/'source/files'/name).read_bytes();assert sha(b)==v['sha256'] and len(b)==v['bytes'];assert hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()==v['git_blob']
identity=json.loads((r/'source/IDENTITY.json').read_text());b=(r/'source/commit.raw').read_bytes();assert hashlib.sha1(('commit '+str(len(b))+'\0').encode()+b).hexdigest()==identity['application']
def rows(path):
 with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('pragma foreign_key_check').fetchall()
  return {t:db.execute('select * from "'+t+'" order by rowid').fetchall() for t, in db.execute("select name from sqlite_master where type='table' order by name")}
before=rows(r/'runtime-before.sqlite3');after=rows(r/'runtime-after.sqlite3');assert before==after and len(after)==12
assert len(after['fact_revision'])==182 and len(after['circulatory_execution'])==2
for name,value in [('before',before),('after',after)]:assert json.loads((r/f'runtime-{name}-rows.json').read_text())==json.loads(json.dumps(value))
events=json.loads((r/'runtime-events-redacted.json').read_text());assert len(events)==11
for e in events:
 if e['path'].endswith('/history'):
  expected=200 if e['request']['repository']==events[1]['response']['repository'] and e['request']['pins'][0]['repository']==e['request']['repository'] else 409
  assert e['status']==expected
 if e['path'].endswith('/lookup'):
  v=e['response'];assert e['status']==200 and json.loads(v['request_canonical'])==e['request'] and sha(v['request_canonical'].encode())==v['request_digest']
  f=v['evidence']['fact'];row=next(x for x in after['fact_revision'] if (x[1],x[2],x[3])==(f['kind'],f['id'],f['revision']));assert json.loads(row[7])==f and sha(row[7].encode())==v['evidence']['digest']
 if e['path'].endswith('/validate') and e['status']==200:assert e['response']['source_review']
 if e['path'].endswith('/validate') and e['response'].get('code')=='rf2_source_review_changed':assert sha(json.dumps(e['request'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==e['response']['request_digest']
if (r/'SHA256SUMS.json').exists():
 for p,expected in json.loads((r/'SHA256SUMS.json').read_text()).items():assert sha((r/p).read_bytes())==expected,p
print(json.dumps({'status':'PASS','source_files':len(source),'all_12_tables_unchanged':True,'retained_fact_revisions':182,'retained_receipts':2,'http_events':len(events),'browser_claim':False},indent=2))
