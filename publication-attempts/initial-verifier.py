"""Portable data-only verification. Does not execute Docker, the app, tests or captured helpers."""
from pathlib import Path
import json,hashlib,base64,sqlite3,tarfile,re,datetime
p=Path(__file__).resolve().parent;o=p/'original'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def load(path):return json.loads((p/path).read_bytes())
def original(name):return json.loads((o/name).read_bytes())
def git_hash(kind,data):return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()
for name,h in load('SHA256SUMS.json').items():assert sha((p/name).read_bytes())==h,name
for name,h in original('SHA256SUMS.json').items():assert sha((o/name).read_bytes())==h,name
mirror_index=load('text-mirrors/index.json')
for name,indexpath in mirror_index.items():
 index=load(indexpath);parts=[]
 for part in index['parts']:
  encoded=(p/indexpath).parent.joinpath(part['file']).read_bytes();assert sha(encoded)==part['sha256']
  raw=base64.b64decode(encoded,validate=True);assert len(raw)==part['bytes'] and sha(raw)==part['decoded_sha256'];parts.append(raw)
 raw=b''.join(parts);assert raw==(p/name).read_bytes() and len(raw)==index['bytes'] and sha(raw)==index['sha256']
identity=load('source-git-identity.json');source=original('source-identity.json');head=identity['source'];tree=identity['tree']
assert head==source['source']=='d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982' and tree==source['tree']=='384bee3150f0428156549962da1147382f2f03f9'
commit=base64.b64decode(identity['raw_commit_base64']);assert git_hash('commit',commit)==head and commit.startswith(('tree '+tree+'\n').encode())
files=[e for e in identity['entries'] if e['type']=='blob'];assert len(files)==len(source['context_file_sha256'])==328
for e in files:
 b=(o/'source-context'/e['path']).read_bytes();assert git_hash('blob',b)==e['oid'] and sha(b)==source['context_file_sha256'][e['path']]
# Reconstruct every Git tree, including Git's directory sort convention.
entries={e['path']:e for e in identity['entries']}
def check_tree(directory):
 children=[e for e in identity['entries'] if e['path'].rsplit('/',1)[0]==directory] if directory else [e for e in identity['entries'] if '/' not in e['path']]
 children.sort(key=lambda e:(e['path'].rsplit('/',1)[-1]+('/' if e['type']=='tree' else '')).encode())
 data=b''
 for e in children:
  oid=check_tree(e['path']) if e['type']=='tree' else e['oid'];assert oid==e['oid']
  name=e['path'].rsplit('/',1)[-1];mode='40000' if e['type']=='tree' else e['mode'];data+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid)
 result=git_hash('tree',data)
 if directory:assert result==entries[directory]['oid']
 return result
assert check_tree('')==tree
assert sha((o/'source.tar').read_bytes())==source['clean_git_archive_sha256']
with tarfile.open(o/'source.tar') as tar:
 members=[m for m in tar.getmembers() if m.isfile()];assert len(members)==len({m.name for m in members})==328
 for m in members:assert tar.extractfile(m).read()==(o/'source-context'/m.name).read_bytes()
assert {m.name for m in members}==set(source['context_file_sha256'])
backend={name.removeprefix('backend/'):h for name,h in source['context_file_sha256'].items() if name.startswith('backend/app/') and name.endswith('.py')}
assert original('runtime-source-sha256.json')==backend
image=original('image-inspect.json');container=original('current-container-inspect.json');image_id='sha256:ce30c75d0d7ea1ba9cdba43d6c060270449e864a9e30b511f953fb6f17537a78'
assert image['Id']==container['Image']==image_id and image['Architecture']=='arm64' and image['Os']=='linux'
assert image['Config']['Labels']['org.opencontainers.image.revision']==head and image['Config']['Labels']['org.opencontainers.image.source-tree']==tree
assert container['State']['Running'] and container['Config']['User']=='10001:10001' and not container['Mounts']
assert container['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5183'}]
assert container['HostConfig']['CapDrop']==['ALL'] and 'no-new-privileges' in container['HostConfig']['SecurityOpt']
assert '--workers' in container['Config']['Cmd'] and container['Config']['Cmd'][container['Config']['Cmd'].index('--workers')+1]=='1'
assert original('previous-container-status.json')['running'] is False
for name in ['build','run','gateway-checks','final-container-checks','post-browser-checks']:assert original(name+'.json')['exit_code']==0
assert 'VITE_SYNTHETIC_HOSTED=true npm run build' in (o/'build.log').read_text() and 'tsc --noEmit && vite build' in (o/'build.log').read_text()
assets=original('runtime-frontend-sha256.json');assert sha((o/'index-response.bin').read_bytes())==assets['index.html']
for n,url in enumerate(re.findall(r'(?:src|href)="(/assets/[^\"]+)"',(o/'index-response.bin').read_text())):assert sha((o/f'asset-{n}-response.bin').read_bytes())==assets[url.lstrip('/')]
base_rows=original('rows-before.json');assert len(base_rows)==12 and len(base_rows['fact_revision'])==162 and len(base_rows['circulatory_execution'])==2
for name in ['rows-after-probes.json','rows-after-restart.json','rows-after-all-browser-checks.json','packaged-fixture-rows.json','final-fixture-rows.json']:assert original(name)==base_rows,name
for name,db in load('readable-tables/index.json').items():
 file=p/db['snapshot'];assert len(file.read_bytes())==db['bytes'] and sha(file.read_bytes())==db['sha256']
 with sqlite3.connect('file:'+str(file)+'?mode=ro',uri=True) as c:
  assert c.execute('pragma integrity_check').fetchone()==('ok',)
  for table,info in db['tables'].items():
   columns=[v[1] for v in c.execute('pragma table_info("'+table+'")')];rows=c.execute('select * from "'+table+'" ORDER BY rowid').fetchall()
   assert json.loads(json.dumps(rows))==base_rows[table] and len(rows)==info['rows'] and columns==info['columns']
   assert load(info['raw_rows_file'])=={'columns':columns,'rows':[list(row) for row in rows]}
   for n,path in enumerate(info['row_files']):assert load(path)==dict(zip(columns,rows[n]))
by_ref={(row[1],row[2],row[3]):row for row in base_rows['fact_revision']}
state=original('fresh-state-response.bin');first=original('state-response.bin')
key=lambda i:(i['fact']['kind'],i['fact']['id'],i['fact']['revision'])
pins=json.loads((o/'source-context/frontend/src/demo/expandedICUCasePins.json').read_text())['items'];pin_map={key(i):i for i in pins};assert len(pin_map)==156
for snapshot in [first,state]:
 assert snapshot['execution_enabled'] is False and sha(canon(snapshot['assembly']))==snapshot['assembly_digest']
 items=snapshot['assembly']['snapshot']['items'];assert len(items)==156 and len({i['fact']['kind'] for i in items})==14
 assert all(i['fact']['kind']!='circulatory_device_prediction' for i in items)
 for item in items:
  assert {k:item[k] for k in ['fact','expected_digest','inclusion','contextual_for','disclosures']}==pin_map[key(item)]
  row=by_ref[key(item)];assert json.loads(row[7])==item['fact'] and sha(row[7].encode())==item['expected_digest']
  ingestion=item['ingestion'];assert ingestion['repository_id']==base_rows['repository_identity'][0][1] and ingestion['ingestion_sequence']==row[0] and ingestion['payload_version']==row[6]
  instant=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
  assert instant(ingestion['ingested_at'])==instant(row[8])
for item in load('readable-state/items-index.json'):assert load(item['file'])==next(i for i in items if key(i)==(item['kind'],item['id'],item['revision']))
events=original('http-events.json');by_name={e['name']:e for e in events}
for e in events:assert sha((o/(e['name']+'-response.bin')).read_bytes())==e['sha256']
for e in events:
 if e['name'].startswith('blocked-'):assert e['status']==404
for name in ['malformed-history','malformed-state']:assert by_name[name]['status']==422
assert original('stale-context-response.bin')['code']=='invalid_state_context'
assert original('history-request.json')['state_context']==original('stale-context-request.json')['state_context']
assert original('fresh-history-request.json')['state_context']==state['state_context']!=first['state_context']
for path in ['history-response.bin','fresh-history-response.bin']:assert [v['fact']['revision'] for v in original(path)['revisions']]==['1','2']
for name in ['released','withheld']:
 raw=(o/(name+'-response.bin')).read_bytes();assert raw==(o/(name+'-after-restart-response.bin')).read_bytes()
 receipt=json.loads(raw);record=receipt['record'];assert record['decision']['outcome']==name
 row=next(r for r in base_rows['circulatory_execution'] if r[0]==receipt['execution_id']);payload=row[5];assert json.loads(payload)==record and sha(payload.encode())==row[3]
 for f in record['evidence']['facts']:assert json.loads(by_ref[(f['kind'],f['id'],f['revision'])][7])==f
 for witness in record['final_recheck']['evidence']:
  for field,digest in [('consumed','source_digest'),('terminal','terminal_source_digest')]:
   ref=witness[field];assert sha(by_ref[(ref['kind'],ref['id'],ref['version'])][7].encode())==witness[digest]
for info in load('readable-http/index.json'):assert json.loads((p/info['original']).read_bytes())==load(info['readable']) and sha((p/info['original']).read_bytes())==info['original_sha256']
dom=(o/'container-deliverable-summary-dom.txt').read_text();by_id={i['fact']['id']:i for i in items}
def controls(prefix,count):
 matches=list(re.finditer(r'button "'+prefix+r' ([^"\n]+)":',dom));assert len(matches)==count
 for n,m in enumerate(matches):
  id=m.group(1).rsplit(' ',1)[1];item=by_id[id];f=item['fact'];block=dom[m.end():matches[n+1].start() if n+1<len(matches) else len(dom)]
  assert id+' / '+f['revision'] in block
  time=(f.get('collected') or f.get('occurred') or {}).get('source_timestamp')
  if time:assert time in block
  q=f.get('result',{}).get('quantity')
  if q:assert q['value'] in block and q['unit']['raw'] in block
  finding=f.get('result',{}).get('finding')
  if finding:assert finding['raw_display'] in block
 return len(matches)
authored=controls('Case source',42);summary=controls('Open summary source',98)
assert len(re.findall(r'button "Inspect uncertainty ',dom))==13
for text in ['Expanded ICU · 156 source records','Patient-level relationship: not established','New execution disabled in this demo','treatment response remain unconfirmed','HPI is optional']:assert text in dom
assert not re.search(r'button "(?:Prepare|Execute|Reconcile)',dom)
assert '1 retained revision at this cutoff' in (o/'container-abg-history-dom.txt').read_text()
for name,reference in [('container-abg-inspector','fs-PH-60 / 1'),('container-co-inspector','fs-CO-60 / 1'),('container-echo-keyboard-expanded','m7-RVSP / 1'),('container-infusion-inspector','fs-N-CHANGE / 1')]:
 s=(o/(name+'-dom.txt')).read_text().split('complementary "Selected source evidence"')[1];assert reference in s
 if 'abg' in name:
  for text in ['fs-arterial-sample-60','40 %','5 cmH2O','2026-10-08T09:00:00+00:00']:assert text in s
 if 'co-' in name:assert 'suspect' in s and '4.60' in s
 if 'echo-' in name:assert 'Source-reported estimate using TR velocity and estimated RAP 5 mmHg' in s and 'RVOT obstruction not documented' in s
 if 'infusion-' in name:
  for text in ['7 mcg/min','0.08 mg/mL','70 kg · source fs-WEIGHT / 1','5.25 mL/h · fs-PUMP-RATE-N-CHANGE / 1','No continuous exposure, dose conversion or treatment effect is inferred']:assert text in s
assert original('browser-errors-warnings.json')==[]
for f in o.glob('*.jpg'):assert f.read_bytes().startswith(b'\xff\xd8\xff')
print(json.dumps({'result':'PASS','original_manifest_entries':432,'source':head,'source_tree':tree,'source_files':len(files),'runtime_backend_files':len(backend),'image':image_id,'architecture':'linux/arm64','fresh_container_facts_and_exact_pins':156,'all_tables_unchanged':12,'fact_revisions':162,'retained_receipts_byte_identical_after_restart':2,'http_exchanges':len(events),'authored_controls':authored,'summary_controls':summary,'uncertainty_controls':13,'lossless_text_mirrors':len(mirror_index),'boundary':'Independent recomputation is possible from captured source/build/HTTP/DB/browser artifacts. This implementer verifier executes no app, tests, Docker or live browser and authenticates no hidden signing key. No clinical/hosting approval.'},indent=2))
