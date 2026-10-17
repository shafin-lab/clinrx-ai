"""Recompute captured local packaging evidence without running the application."""
from pathlib import Path
import json,hashlib,sqlite3
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
manifest=json.loads((p/'SHA256SUMS.json').read_text())
for name,h in manifest.items():assert sha((p/name).read_bytes())==h,name
identity=json.loads((p/'source-identity.json').read_text());commit=(p/'source-commit.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==identity['source']
assert commit.startswith(('tree '+identity['tree']+'\n').encode())
for line in (p/'tested-source.sha256').read_text().splitlines():
 h,f=line.split('  ',1);assert sha((p/'source-context'/f).read_bytes())==h,f
for name in ['build','run','probes','final-checks','stop-container','stop-runtime']:
 assert json.loads((p/(name+'.json')).read_text())['exit_code']==0,name
assert '56 passed' in (p/'focused-backend.log').read_text()
rows=json.loads((p/'rows-before.json').read_text());assert len(rows)==12
assert len(rows['fact_revision'])==162 and len(rows['circulatory_execution'])==2
for name in ['rows-after-probes','rows-after-restart']:
 assert json.loads((p/(name+'.json')).read_text())==rows
for name in ['packaged-fixture.sqlite3','final-fixture.sqlite3']:
 with sqlite3.connect('file:'+str(p/name)+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  actual={t:db.execute('SELECT * FROM "'+t+'" ORDER BY rowid').fetchall() for t in rows}
  assert json.loads(json.dumps(actual))==rows
state=json.loads((p/'state-response.bin').read_bytes());items=state['assembly']['snapshot']['items']
assert state['execution_enabled'] is False and len(items)==156 and len({i['fact']['kind'] for i in items})==14
assert not any(i['fact']['kind']=='circulatory_device_prediction' for i in items)
assert sha(canon(state['assembly']))==state['assembly_digest']
by_ref={(r[1],r[2],r[3]):r for r in rows['fact_revision']}
for item in items:
 f=item['fact'];r=by_ref[(f['kind'],f['id'],f['revision'])]
 assert json.loads(r[7])==f and sha(r[7].encode())==item['expected_digest']
for name in ['released','withheld']:
 raw=(p/(name+'-response.bin')).read_bytes();assert raw==(p/(name+'-after-restart-response.bin')).read_bytes()
 record=json.loads(raw)['record'];assert record['decision']['outcome']==name
 assert any(isinstance(v,str) and v.startswith('{') and json.loads(v)==record for r in rows['circulatory_execution'] for v in r)
 for f in record['evidence']['facts']:assert json.loads(by_ref[(f['kind'],f['id'],f['revision'])][7])==f
 assert len(record['final_recheck']['evidence'])==4
 for w in record['final_recheck']['evidence']:
  for a,b in [('consumed','source_digest'),('terminal','terminal_source_digest')]:
   ref=w[a];assert sha(by_ref[(ref['kind'],ref['id'],ref['version'])][7].encode())==w[b]
image=json.loads((p/'image-inspect.json').read_text());assert image['Architecture']=='arm64' and image['Os']=='linux'
assert image['Config']['Labels']['org.opencontainers.image.revision']==identity['source']
actual=json.loads((p/'runtime-source-sha256.json').read_text())
expected={str(f.relative_to(p/'source-context/backend')):sha(f.read_bytes()) for f in (p/'source-context/backend/app').rglob('*.py')}
assert actual==expected
for e in json.loads((p/'http-events.json').read_text()):
 assert sha((p/(e['name']+'-response.bin')).read_bytes())==e['sha256']
 if e['name'].startswith('blocked-'):assert e['status']==404
 if e['name'] in ['malformed-state','malformed-history','stale-context']:assert e['status']==422
assert json.loads((p/'stale-context-response.bin').read_text())['code']=='invalid_state_context'
print(json.dumps({'result':'PASS','source':identity['source'],'tree':identity['tree'],'manifest_entries':len(manifest),'focused_backend_tests':56,'records':156,'populated_families':14,'hpi_present':False,'sqlite_tables_unchanged':12,'fact_revisions':162,'receipts_byte_identical_after_restart':2,'terminal_witnesses_verified':8,'backend_python_files_match_image':len(expected),'architecture':'linux/arm64','scope':'Implementation-produced local gateway/container execution and data-only recomputation; not independent Director acceptance, hosted CI or external hosting'},indent=2))
