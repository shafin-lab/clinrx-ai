"""Portable, data-only validation. No app imports, API calls, or database writes."""
import hashlib,json,sqlite3
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
load=lambda name:json.loads((ROOT/name).read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':')).encode()
ref=lambda fact:(fact['kind'],fact['id'],fact['revision'])
pin=lambda value:(value['kind'],value['id'],value['version'])
manifest=ROOT/'SHA256SUMS.json'
if manifest.exists():
 entries=load('SHA256SUMS.json')
 for name,expected in entries.items():assert sha((ROOT/name).read_bytes())==expected,name
 actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
 assert actual==set(entries),'missing or extra published files'
state=load('original/live-state.json');scope=state['assembly']['request']['scope'];cutoff=scope['repository_cutoff'];repository=cutoff['repository_id']
assert state['execution_enabled'] is False
with sqlite3.connect('file:'+str(ROOT/'synthetic.sqlite3')+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 arrays={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in names}
 assert json.loads(json.dumps(arrays))==load('raw-row-arrays.json')
 exported=load('readable-tables.json')
 for name in names:
  assert exported[name]['columns']==[r[1] for r in db.execute('PRAGMA table_info("'+name+'")')]
  assert exported[name]['rows']==json.loads(json.dumps(arrays[name]))
 row_digest=sha(canonical(arrays));original=load('original/live-verification.json')
 assert row_digest==original['rows_sha256_before']==original['rows_sha256_after']
 stored={}
 for seq,kind,id,revision,patient,encounter,version,payload,ingested in arrays['fact_revision']:
  f=json.loads(payload);assert ref(f)==(kind,id,revision)
  stored[(kind,id,revision)]={'fact':f,'sha':sha(payload.encode()),'sequence':seq,'ingested':ingested,'version':version}
  assert f==load(f'fact-payloads/{kind}--{id}--{revision}.json')
 def metadata(meta,entry,limit):
  assert meta['repository_id']==repository
  assert meta['ingestion_sequence']==entry['sequence']<=limit
  assert datetime.fromisoformat(meta['ingested_at'].replace('Z','+00:00'))==datetime.fromisoformat(entry['ingested'].replace('Z','+00:00'))
  if 'payload_version' in meta:assert meta['payload_version']==entry['version']
 items=state['assembly']['snapshot']['items'];assert len(items)==41
 assert len({i['fact']['kind'] for i in items})==14 and not any(i['fact']['id']=='m7-HPI' for i in items)
 for item in items:
  f=item['fact'];entry=stored[ref(f)]
  assert f==entry['fact'] and item['expected_digest']==entry['sha']
  assert f['binding']['target']['patient_id']==scope['patient_id'] and f['binding']['target']['encounter_id']==scope['encounter_id']
  metadata(item['ingestion'],entry,cutoff['fact_watermark'])
 assert len(arrays['circulatory_execution'])==2
 witnesses=0
 for label,outcome in [('released','released'),('withheld','withheld')]:
  response=load('original/'+label+'_example.json');record=response['record'];request=record['request'];recheck=record['final_recheck'];evidence=record['evidence']
  row=next(r for r in arrays['circulatory_execution'] if r[0]==response['execution_id'])
  assert sha(row[5].encode())==row[3] and json.loads(row[5])==record
  assert request['execution_id']==response['execution_id'] and record['decision']['outcome']==outcome
  assert (response['statement'] is None)==(outcome=='withheld')
  original_cutoff=request['inference_request']['scope']['repository_cutoff'];inference_cutoff=request['inference_cutoff'];final_cutoff=recheck['final_cutoff']
  assert all(c['repository_id']==repository for c in [original_cutoff,inference_cutoff,final_cutoff])
  assert original_cutoff['fact_watermark']<inference_cutoff['fact_watermark']<=final_cutoff['fact_watermark']
  assert recheck['scope']==request['inference_request']['scope']
  assert request['assembly_request']['scope']==recheck['scope']
  original_facts={ref(f):f for f in evidence['facts']};terminals={ref(f):f for f in recheck['terminal_facts']}
  for witness in recheck['evidence']:
   consumed=pin(witness['consumed']);terminal=pin(witness['terminal']);old=stored[consumed];last=stored[terminal]
   assert original_facts[consumed]==old['fact'] and terminals[terminal]==last['fact']
   assert witness['item_digest']==witness['source_digest']==old['sha']
   assert witness['terminal_source_digest']==last['sha']
   metadata(witness['original_ingestion'],old,original_cutoff['fact_watermark']);metadata(witness['terminal_ingestion'],last,final_cutoff['fact_watermark'])
   latest=max((e for key,e in stored.items() if key[:2]==terminal[:2] and e['sequence']<=final_cutoff['fact_watermark']),key=lambda e:e['sequence'])
   assert latest==last;witnesses+=1
  inf=evidence['inference'];entry=stored[ref(inf)];iw=recheck['inference']
  assert inf==entry['fact'] and pin(iw['reference'])==ref(inf)
  assert iw['expected_digest']==iw['observed_digest']==iw['reconstruction_digest']==entry['sha']==request['expected_inference_digest']
  assert iw['inputs']==inf['inputs'] and iw['declarations']==inf['provenance']['upstream']
  metadata(iw['ingestion'],entry,inference_cutoff['fact_watermark'])
summary={'database_integrity':'ok','readable_tables_matched':len(names),'state_facts_matched':len(items),'source_payloads_matched':len(stored),
 'full_original_terminal_witnesses_matched':witnesses,'retained_receipts_matched':2,'hpi_absent':True,'execution_enabled':False,
 'rows_match_original_before_after_commitments':True,'row_digest':row_digest}
(ROOT/'verification-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
