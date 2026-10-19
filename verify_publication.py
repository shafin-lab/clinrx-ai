"""Portable stdlib, data-only verification; no application or test execution."""
from pathlib import Path
import json,hashlib,base64
PUB=Path(__file__).resolve().parent
for name,digest in json.loads((PUB/'PUBLICATION-SHA256SUMS.json').read_text()).items():
 assert hashlib.sha256((PUB/name).read_bytes()).hexdigest()==digest,name
for entry in json.loads((PUB/'MIRRORS.json').read_text()):
 raw=base64.b64decode(''.join((PUB/part).read_text().strip() for part in entry['parts']),validate=True)
 assert raw==(PUB/entry['path']).read_bytes()
 assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob']
for name,digest in json.loads((PUB/'original/SHA256SUMS.json').read_text()).items():
 assert hashlib.sha256((PUB/'original'/name).read_bytes()).hexdigest()==digest,name
"""Data-only verification; no application or captured script execution."""
from pathlib import Path
from hashlib import sha256
import sqlite3,json
PUB=Path(__file__).resolve().parent
ROOT=PUB/'original'
E=ROOT/'evidence'
def db_rows(path):
 with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
  assert db.execute('pragma integrity_check').fetchone()==('ok',)
  assert db.execute('pragma foreign_key_check').fetchall()==[]
  return {t:db.execute('select * from "'+t+'" order by rowid').fetchall() for t, in db.execute("select name from sqlite_master where type='table' order by name")}
before,after=db_rows(E/'before.sqlite3'),db_rows(E/'after.sqlite3')
assert before==after==db_rows(E/'final.sqlite3')
assert json.loads((E/'before-rows.json').read_text())==json.loads((E/'after-rows.json').read_text())
for name,rows in after.items():assert json.loads((E/'after-rows.json').read_text())[name]==[list(r) for r in rows]
records={(r[1],r[2],r[3]):r for r in after['fact_revision']}
count=0
final_count=0
responses=[]
for event in map(json.loads,(E/'events.jsonl').read_text().splitlines()):
 if event.get('status')!=200 or not event.get('response'):continue
 value=json.loads((E/event['response']).read_text())
 if 'laboratory' in value:
  scope=value['context']['scope'];cutoff=scope['repository_cutoff']
  assert scope==value['laboratory']['scope']==value['circulatory']['assembly']['request']['scope']
  assert value['execution_enabled'] is False and value['circulatory']['execution_enabled'] is False
  for key,digest,model in [('canonical_assembly',value['context']['circulatory_digest'],value['circulatory']['assembly']),('canonical_laboratory',value['context']['observations_digest'],value['laboratory'])]:
   assert sha256(value[key].encode()).hexdigest()==digest
   assert json.loads(value[key])==model
  responses.append(value)
  selected=[*value['laboratory']['observations'],*value['circulatory']['assembly']['snapshot']['items']]
 elif 'revisions' in value:
  scope=value['context'].get('scope',value['context'].get('assembly_request',{}).get('scope'));cutoff=scope['repository_cutoff'];selected=value['revisions']
  request=json.loads((E/event['request']).read_text());assert request['reference']==value['reference']
 else:continue
 for item in selected:
  fact=item['fact'];r=records[(fact['kind'],fact['id'],fact['revision'])]
  assert json.loads(r[7])==fact
  assert (r[4],r[5])==(scope['patient_id'],scope['encounter_id'])
  assert item['ingestion']['repository_id']==cutoff['repository_id']
  assert item['ingestion']['ingestion_sequence']==r[0]<=cutoff['fact_watermark']
  if 'expected_digest' in item:assert sha256(r[7].encode()).hexdigest()==item['expected_digest']
  count+=1
  if event['number']>=10:final_count+=1
assert responses
for row in after['circulatory_execution']:assert sha256(row[5].encode()).hexdigest()==row[3]
# Keep the existing assisted MAP/note journey and every prior source row untouched.
original=json.loads((PUB/'baseline-rows-publication-copy.json').read_text())
original={name:[tuple(row) for row in rows] for name,rows in original.items()}
assert len(original['fact_revision'])==167
assert after['fact_revision'][:167]==original['fact_revision']
assert after['circulatory_execution']==original['circulatory_execution']
result={'status':'PASS','tables_unchanged':len(after),'fact_revisions_unchanged':len(after['fact_revision']),'retained_receipts_unchanged':len(after['circulatory_execution']),'captured_fact_correspondences':count,'final_build_fact_correspondences':final_count,'prior_167_facts_and_receipts_preserved':True,'context_redaction':'Signed state-context fields are redacted. No signature authentication or complete browser network trace claimed.'}
# Verification does not modify the published original evidence.
assert result==json.loads((E/'readonly-verification.json').read_text())
print(json.dumps(result,indent=2))

indices=json.loads((PUB/'readable/tables-index.json').read_text())
for table,entry in indices.items():
 actual=[json.loads((PUB/path).read_text())['row'] for path in entry['files']]
 assert actual==[list(row) for row in after[table]],table
selected=responses[-1]['laboratory']['observations']+responses[-1]['circulatory']['assembly']['snapshot']['items']
for item,entry in zip(selected,json.loads((PUB/'readable/api-index.json').read_text()),strict=True):
 assert json.loads((PUB/entry['path']).read_text())==item
raw=(PUB/'original/validation/source-commit.raw').read_bytes()
assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='c2d58e4c8d52d2ceeddd57881365cc5f76cdf74f'
for name,meta in json.loads((PUB/'original/validation/tested-files.json').read_text()).items():
 raw=(PUB/'original/source'/name).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==meta['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta['git_blob']
for name,digest in json.loads((PUB/'original/validation/build-hashes.json').read_text()).items():
 assert hashlib.sha256((PUB/'final-build'/name).read_bytes()).hexdigest()==digest
print('PASS: original/publication checksums, lossless mirrors, raw source identity, tested bytes/build, three SQLite checkpoints/all rows, API scope/digests/references, baseline preservation and closed read-only results.')
