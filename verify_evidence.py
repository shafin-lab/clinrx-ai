"""Portable data-only verification; no application/test/launcher execution."""
from pathlib import Path
import json,hashlib,base64,sqlite3,datetime
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
for name,h in json.loads((p/'SHA256SUMS.json').read_text()).items():assert sha((p/name).read_bytes())==h,name
for name,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/name).read_bytes())==h,name
mirrors=json.loads((p/'text-mirrors/index.json').read_text())
for name,indexpath in mirrors.items():
 index=json.loads((p/indexpath).read_text());parts=[]
 for info in index['parts']:
  encoded=(p/indexpath).parent.joinpath(info['file']).read_bytes();assert sha(encoded)==info['sha256']
  decoded=base64.b64decode(encoded,validate=True);assert len(decoded)==info['bytes'] and sha(decoded)==info['decoded_sha256'];parts.append(decoded)
 raw=b''.join(parts);assert raw==(p/name).read_bytes() and len(raw)==index['bytes'] and sha(raw)==index['sha256']
identity=json.loads((p/'source-identity.json').read_text());raw=base64.b64decode(identity['raw_commit_base64'])
assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==identity['head']
assert raw.startswith(('tree '+identity['tree']+'\nparent '+identity['parent']+'\n').encode())
tested=json.loads((p/'original/tested-source-sha256.json').read_text());assert len(tested)==7
for source in identity['files']:
 b=(p/'source'/source['path']).read_bytes();assert sha(b)==source['sha256']==tested[source['path']] and blob(b)==source['git_blob']
state=json.loads((p/'original/fresh-state-content.json').read_text());assert state['execution_enabled'] is False
assert sha(canon(state['assembly']))==state['assembly_digest'];items=state['assembly']['snapshot']['items'];assert len(items)==156
pins=json.loads((p/'source/frontend/src/demo/expandedICUCasePins.json').read_text())['items']
key=lambda i:(i['fact']['kind'],i['fact']['id'],i['fact']['revision'])
expected={key(i):i for i in pins};assert len(expected)==156
for i in items:
 assert sha(canon(i['fact']))==i['expected_digest']
 assert {k:i[k] for k in ['fact','expected_digest','inclusion','contextual_for','disclosures']}==expected[key(i)]
for info in json.loads((p/'readable-state/items-index.json').read_text()):assert json.loads((p/info['file']).read_text())==next(i for i in items if key(i)==(info['kind'],info['id'],info['revision']))
index=json.loads((p/'readable-tables/index.json').read_text());allrows={}
for label,db in index.items():
 file=p/db['snapshot'];assert len(file.read_bytes())==db['bytes'] and sha(file.read_bytes())==db['sha256']
 with sqlite3.connect('file:'+str(file)+'?mode=ro',uri=True) as c:
  assert c.execute('pragma integrity_check').fetchone()==('ok',);rows={}
  for table,info in db['tables'].items():
   values=c.execute('select * from "'+table+'"').fetchall();values.sort(key=lambda v:canon(v));rows[table]=values
   assert len(values)==info['rows'] and sha(canon(values))==info['rows_sha256']
   assert json.loads((p/info['raw_rows_file']).read_text())=={'columns':info['columns'],'rows':[list(v) for v in values]}
   for n,name in enumerate(info['row_files']):assert json.loads((p/name).read_text())==dict(zip(info['columns'],values[n]))
 allrows[label]=rows
assert allrows['original-demo']==allrows['isolated-demo'] and len(allrows['isolated-demo'])==12
rows=allrows['isolated-demo'];facts={}
for row in rows['fact_revision']:
 d=dict(zip(index['isolated-demo']['tables']['fact_revision']['columns'],row));fact=json.loads(d['payload']);facts[(d['kind'],d['fact_id'],d['revision'])]=(d,fact)
assert len(facts)==162
repo=rows['repository_identity'][0][1]
when=lambda x:datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
for item in items:
 d,f=facts[key(item)];assert f==item['fact'];assert d['patient_id']=='synthetic-p1' and d['encounter_id']=='synthetic-e1'
 ingestion=item['ingestion'];assert ingestion['repository_id']==repo and ingestion['ingestion_sequence']==d['ingestion_sequence'] and ingestion['payload_version']==d['payload_version'] and when(ingestion['ingested_at'])==when(d['ingested_at'])
assert len(rows['circulatory_execution'])==2
for row in rows['circulatory_execution']:
 d=dict(zip(index['isolated-demo']['tables']['circulatory_execution']['columns'],row));assert sha(d['payload'].encode())==d['payload_digest']
controls=json.loads((p/'authored-controls.json').read_text());assert len(controls)==42
by_id={i['fact']['id']:i for i in items}
for control in controls:
 i=by_id[control['fact']['id']];assert control['fact']=={'kind':i['fact']['kind'],'id':i['fact']['id'],'version':i['fact']['revision']} and control['expected_digest']==i['expected_digest']
 assert control['source_timestamp'] in control['captured_dom_block'] and i['fact']['id']+' / '+i['fact']['revision'] in control['captured_dom_block']
 q=i['fact'].get('result',{}).get('quantity')
 if q:assert q['value'] in control['captured_dom_block'] and q['unit']['raw'] in control['captured_dom_block']
 finding=i['fact'].get('result',{}).get('finding')
 if finding:assert finding['raw_display'] in control['captured_dom_block']
dom=(p/'original/stable-summary-dom.txt').read_text()
for text in ['Expanded ICU · 156 source records','Patient-level relationship: not established','New execution disabled in this demo','Possible meaning — unconfirmed','What prevents confirmation','No treatment recommendation']:assert text in dom,text
for f in (p/'original').glob('*.jpg'):assert f.read_bytes().startswith(b'\xff\xd8\xff')
assert '547 passed (547)' in (p/'original/tests.log').read_text()
print(json.dumps({'result':'PASS','original_manifest_entries':22,'tested_source_files':7,'source_commit_identity':identity['head'],'fact_digests_and_exact_pins':156,'api_database_fact_and_ingestion_correspondences':156,'publication_time_database_tables_equal':12,'retained_receipt_payload_hashes':2,'authored_source_control_correspondences':42,'lossless_text_mirrors':len(mirrors),'boundary':'Data-only recomputation of captured evidence and later SQLite snapshots; no app/test rerun, context-signature authentication, live browser review, container/hosted CI or clinical validation.'},indent=2))
