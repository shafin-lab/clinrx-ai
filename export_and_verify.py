"""Read-only export and explicit correspondence audit; stdlib only, portable."""
import json,sqlite3,hashlib,re,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
def digest(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def ref(f):return {'kind':f['kind'],'id':f['id'],'version':f['revision']}
def instant(value):return datetime.fromisoformat(value)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def events(folder):return [json.loads(s) for s in (folder/'events.jsonl').read_text().splitlines()]
exported={};results=[];byte_audit=[]
for group in ('original','supplemental-absent'):
 folder=ROOT/group
 if group=='original':
  manifest=load(folder/'checksums.json')
  for name,expected in manifest.items():assert digest((folder/name).read_bytes())==expected,name
 for path in sorted(folder.glob('*.bin')):
  raw=path.read_bytes()
  try:json.loads(raw);suffix='.json'
  except (ValueError,UnicodeDecodeError):suffix='.txt'
  dest=ROOT/'http-readable'/group/(path.stem+suffix);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 for dbpath in sorted(folder.glob('*.sqlite3')):
  conn=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
  scenario=dbpath.stem;out=ROOT/'row-exports'/group/scenario;tables={}
  for (table,) in conn.execute("select name from sqlite_master where type='table' order by name"):
   assert re.fullmatch(r'[a-z_]+',table)
   cursor=conn.execute('select * from '+table+' order by 1');columns=[c[0] for c in cursor.description];rows=cursor.fetchall()
   value={'database':group+'/'+dbpath.name,'exported_at':datetime.now(timezone.utc).isoformat(),'table':table,'columns':columns,'rows':[list(r) for r in rows]}
   dump(out/(table+'.json'),value);tables[table]=value
  exported[(group,scenario)]=tables
  for row in tables['fact_revision']['rows']:
   r=dict(zip(tables['fact_revision']['columns'],row));fact=json.loads(r['payload']);name=str(r['ingestion_sequence'])+'-'+re.sub(r'[^a-zA-Z0-9_.-]','_',r['fact_id'])+'-v'+r['revision']
   dump(out/'facts'/(name+'.json'),{'row':r,'fact':fact,'payload_sha256':digest(r['payload'].encode())})
  for row in tables['circulatory_execution']['rows']:
   r=dict(zip(tables['circulatory_execution']['columns'],row));dump(out/'receipts'/(r['execution_id']+'.json'),{'row':r,'record':json.loads(r['payload'])})
  es=[e for e in events(folder) if e.get('event')=='http' and e['scenario']==scenario]
  executions=[e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-reviews')]
  if not executions:continue
  baseline=(folder/executions[0]['request']).read_bytes();command=json.loads(baseline)['command']
  for e in es:
   if e['method']=='POST' and (e['path'].endswith('/circulatory-reviews') or e['path'].endswith('/circulatory-review-reconciliations')):
    raw=(folder/e['request']).read_bytes();assert json.loads(raw)==json.loads(baseline) and json.loads(raw)['command']==command
    byte_audit.append({'group':group,'scenario':scenario,'event':e['number'],'baseline_event':executions[0]['number'],'raw_bytes_equal':raw==baseline,'raw_sha256':digest(raw),'command_string_equal':True,'parsed_body_equal':True,'origin':e['origin']})
  repo=conn.execute('select repository_id from repository_identity').fetchone()[0]
  fact_rows=[dict(zip(tables['fact_revision']['columns'],r)) for r in tables['fact_revision']['rows']]
  def exact(reference):
   matches=[r for r in fact_rows if (r['kind'],r['fact_id'],r['revision'])==(reference['kind'],reference['id'],reference['version'])];assert len(matches)==1
   return matches[0]
  def meta(row,metadata,low,high):
   assert metadata['repository_id']==repo and low<metadata['ingestion_sequence']<=high
   assert metadata['ingestion_sequence']==row['ingestion_sequence'] and metadata['payload_version']==row['payload_version']
   assert instant(metadata['ingested_at'])==instant(row['ingested_at'])
  def latest(reference,cutoff):
   return max((r for r in fact_rows if (r['kind'],r['fact_id'])==(reference['kind'],reference['id']) and r['ingestion_sequence']<=cutoff),key=lambda r:r['ingestion_sequence'])
  for row in tables['circulatory_execution']['rows']:
   stored=dict(zip(tables['circulatory_execution']['columns'],row));record=json.loads(stored['payload']);request=record['request'];evidence=record['evidence'];final=record['final_recheck'];ir=request['inference_request'];scope=ir['scope']
   original=scope['repository_cutoff'];inference_cutoff=request['inference_cutoff'];final_cutoff=final['final_cutoff'];prefix=[original['fact_watermark'],inference_cutoff['fact_watermark'],final_cutoff['fact_watermark']]
   assert all(c['repository_id']==repo for c in (original,inference_cutoff,final_cutoff))
   assert prefix[0]<prefix[1]<=prefix[2]<=max(r['ingestion_sequence'] for r in fact_rows)
   assert final['scope']==scope==request['assembly_request']['scope'] and final['inference_cutoff']==inference_cutoff
   assert evidence['request']==request and stored['execution_id']==request['execution_id']
   assert digest(stored['payload'].encode())==stored['payload_digest']==digest(canonical(record))
   pins=[ir['pressure'],ir['lactate'],ir['vasopressor'],*ir['supporting']]
   assert len(pins)==len(final['evidence'])==len(final['terminal_facts'])==len(evidence['items'])==len(evidence['facts'])
   terminal_checks=[]
   for n,(witness,terminal,item,fact,pin) in enumerate(zip(final['evidence'],final['terminal_facts'],evidence['items'],evidence['facts'],pins)):
    original_row=exact(witness['consumed']);terminal_row=exact(witness['terminal'])
    assert witness['consumed']==ref(fact)==ref(item['fact'])==pin['reference']==evidence['inference']['inputs'][n]
    assert json.loads(original_row['payload'])==fact==item['fact']
    assert digest(original_row['payload'].encode())==witness['source_digest']==witness['item_digest']==pin['expected_digest']==item['expected_digest']
    assert witness['terminal']==ref(terminal)==ref(json.loads(terminal_row['payload']))
    assert json.loads(terminal_row['payload'])==terminal and digest(terminal_row['payload'].encode())==witness['terminal_source_digest']
    assert terminal_row==latest(witness['consumed'],prefix[2])
    assert fact['binding']['target']==terminal['binding']['target']=={'patient_id':scope['patient_id'],'encounter_id':scope['encounter_id'],'longitudinal_context_id':None}
    meta(original_row,witness['original_ingestion'],0,prefix[0]);meta(terminal_row,witness['terminal_ingestion'],0,prefix[2]);assert item['ingestion']==witness['original_ingestion']
    if witness['terminal']==witness['consumed']:assert original_row==terminal_row
    else:assert terminal_row['ingestion_sequence']>original_row['ingestion_sequence']
    terminal_checks.append({'consumed':witness['consumed'],'terminal':witness['terminal'],'source_digest':witness['source_digest'],'terminal_digest':witness['terminal_source_digest'],'content_and_metadata_verified':True})
   iw=final['inference'];inference=evidence['inference'];inference_row=exact(iw['reference']);terminal_row=exact(iw['terminal'])
   assert iw['reference']==ref(inference)=={'kind':'inference','id':ir['inference_id'],'version':ir['revision']}
   assert json.loads(inference_row['payload'])==inference
   assert digest(inference_row['payload'].encode())==request['expected_inference_digest']==iw['expected_digest']==iw['observed_digest']==iw['reconstruction_digest']
   assert digest(terminal_row['payload'].encode())==iw['terminal_digest'] and terminal_row==latest(iw['reference'],prefix[2])
   assert iw['inputs']==iw['dependencies']==inference['inputs'] and iw['declarations']==inference['provenance']['upstream'] and iw['method']==inference['method']
   meta(inference_row,iw['ingestion'],prefix[0],prefix[1]);meta(terminal_row,iw['terminal_ingestion'],0,prefix[2]);assert iw['ingestion']==evidence['inference_ingestion']
   for e in es:
    if e['status']!=200:continue
    raw=(folder/e['response']).read_bytes()
    if not raw.startswith(b'{'):continue
    value=json.loads(raw)
    if 'record' in value:assert value['record']==record
    elif value.get('status')=='committed_match':assert value['execution']['record']==record
   results.append({'group':group,'scenario':scenario,'execution_id':stored['execution_id'],'repository_id':repo,'cutoffs':prefix,'outcome':record['decision']['outcome'],'receipt_payload_sha256':stored['payload_digest'],'all_correspondence_checks':'PASS','evidence_witnesses':terminal_checks,'inference_terminal':iw['terminal'],'inference_terminal_digest':iw['terminal_digest']})
  conn.close()
# Original gate commitments: expose the actual row bytes now, without inventing old capture times.
gate=load(ROOT/'original/gate-proof.json');gate_preimages={}
for table in ('fact_revision','circulatory_execution'):
 value=exported[('original','release')][table];rows=[tuple(r) for r in value['rows']];raw=repr(rows).encode();actual=digest(raw)
 assert actual==gate['storage_before'][table]==gate['storage_after'][table]
 dest=ROOT/'gate-row-preimages'/(table+'.repr.txt');dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw)
 gate_preimages[table]={'sha256':actual,'matches_original_before_and_after_commitments':True,'path':str(dest.relative_to(ROOT)),'exported_later_from_unchanged_retained_database':True}
dump(ROOT/'gate-row-preimages/verification.json',gate_preimages)
pending=exported[('original','gate_pending')]
assert pending['circulatory_execution']['rows']==[]
pending_events=[e for e in events(ROOT/'original') if e.get('event')=='http' and e['scenario']=='gate_pending']
blocked=next(e for e in pending_events if e['method']=='POST' and e['path'].endswith('/circulatory-reviews'))
assert blocked['closed'] and blocked['status']==422
absent_event=next(e for e in pending_events if e['method']=='POST' and e['path'].endswith('/circulatory-review-reconciliations'))
assert load(ROOT/'original'/absent_event['response'])=={'status':'absent','execution':None}
# Supplemental absent checkpoint: full empty table is captured before the explicit retry action.
s=ROOT/'supplemental-absent';es=[e for e in events(s) if e.get('event')=='http'];attempts=[e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-reviews')];recon=next(e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-review-reconciliations'))
assert len(attempts)==2 and attempts[0]['status']==502 and attempts[1]['status']==200
empty=load(s/(recon['response'].replace('-response.bin','-after-rows.json')));assert empty['tables']['circulatory_execution']['rows']==[]
before_retry=load(s/(attempts[1]['request'].replace('-request.bin','-before-rows.json')));assert before_retry['tables']['circulatory_execution']['rows']==[]
actions=[json.loads(x) for x in (s/'browser-actions.jsonl').read_text().splitlines()];click=next(a for a in actions if a['action'].startswith('EXPLICIT USER-STYLE ACTION'))
assert recon['time']<click['time']<before_retry['captured_at']<attempts[1]['time']
assert (s/attempts[0]['request']).read_bytes()==(s/recon['request']).read_bytes()==(s/attempts[1]['request']).read_bytes()
assert len(exported[('supplemental-absent','absent')]['circulatory_execution']['rows'])==1
dump(ROOT/'supplemental-absent/explicit-retry-correspondence.json',{'reconciliation_event':recon['number'],'receipt_count_before_retry':0,'explicit_click':click,'retry_event':attempts[1]['number'],'raw_request_bytes_identical':True,'receipt_count_after_retry':1})
dump(ROOT/'correspondence-verification.json',{'status':'PASS','receipt_cases_checked':len(results),'cases':results,'raw_request_byte_audit':byte_audit,'gate_preimages':gate_preimages,'note':'Gate diagnostic requests use JSON whitespace distinct from browser bodies. Their parsed bodies and command strings match; raw byte equality is NOT claimed for those requests.'})
print('PASS:',len(results),'retained receipts; complete repository/cutoff/terminal/content/ingestion checks; raw byte audit; gate preimages; explicit retry checkpoint.')
