from pathlib import Path
import hashlib,json,sqlite3,re
from datetime import datetime
r=Path(__file__).resolve().parent
j=r/'browser-journey'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def database(path):
 db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 names=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 return db,{name:sorted([dict(row) for row in db.execute('SELECT * FROM "'+name+'"')],key=canonical) for name in names}
a,before=database(j/'before.sqlite3');b,after=database(j/'after.sqlite3')
assert set(before)==set(after) and len(before)==12
for table in before:
 if table not in ['fact_revision','revision_link','sqlite_sequence']:assert before[table]==after[table],table
old={v['ingestion_sequence']:v for v in before['fact_revision']};new={v['ingestion_sequence']:v for v in after['fact_revision']}
assert len(old)==162 and len(new)==165 and all(new[k]==v for k,v in old.items())
assert set(new)-set(old)=={163,164,165}
assert after['sqlite_sequence']==[{'name':'fact_revision','seq':165}]
assert before['sqlite_sequence']==[{'name':'fact_revision','seq':162}]
original_pressure=next(v for v in old.values() if v['kind']=='circulatory_pressure' and v['fact_id']=='fs-MAP-15' and v['revision']=='1')
assert after['revision_link']==sorted(before['revision_link']+[{'successor_sequence':164,'predecessor_sequence':original_pressure['ingestion_sequence']}],key=canonical)
meta=json.loads((j/'journey.json').read_text())
facts={(v['kind'],v['fact_id'],v['revision']):v for v in new.values()}
pa=json.loads(original_pressure['payload']);pc=json.loads(new[164]['payload']);na=json.loads(new[163]['payload']);nb=json.loads(new[165]['payload'])
assert pc['revision']==meta['pressure']['corrected_version'] and pc['supersedes']=={'kind':'circulatory_pressure','id':'fs-MAP-15','version':'1'}
assert pa['result']['quantity']['value']=='61' and pc['result']['quantity']['value']=='62.0000'
expected=json.loads(original_pressure['payload']);expected['result']['quantity']['value']='62.0000'
for key in ['revision','supersedes','correction_reason','provenance']:expected[key]=pc[key]
assert expected==pc,'Correction changed unrelated source content'
assert na['id']==meta['original_note']['id'] and nb['id']==meta['new_note']['id'] and na['supersedes'] is None and nb['supersedes'] is None
for note,follow in [(na,{'kind':'circulatory_pressure','id':'fs-MAP-15','version':'1'}),(nb,{'kind':'circulatory_pressure','id':'fs-MAP-15','version':pc['revision']})]:
 expected_refs={'baseline':meta['baseline'],'intervention':meta['intervention'],'followup':follow}
 for stage,ref in expected_refs.items():
  entries=[e for e in note['external_evidence'] if e['namespace']=='clinrx.local.reassessment.'+stage+'/v1'];assert len(entries)==1 and json.loads(entries[0]['code'])==ref
  matches=[s for s in note['associations'] if s['role']=='context' and s['status']=='resolved' and s['exact']==ref and s['scope']=={'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','longitudinal_context_id':None}];assert len(matches)==1
  assert tuple(ref[k] for k in ['kind','id','version']) in facts
for row in after['circulatory_execution']:assert hashlib.sha256(row['payload'].encode()).hexdigest()==row['payload_digest']
events=sorted([json.loads(x) for x in (j/'events.jsonl').read_text().splitlines()],key=lambda e:e['sequence'])
for e in events:
 for key in ['request','response']:
  if key in e:assert hashlib.sha256((j/e[key]['file']).read_bytes()).hexdigest()==e[key]['sha256']
states=[];saves=[];histories=[]
repository=after['repository_identity'][0]['repository_id']
for e in events:
 if e['path'].endswith('/patient-state-v3') and e['status']==200:
  state=json.loads((j/e['response']['file']).read_text());states.append(state)
  assert state['execution_enabled'] is False and digest(state['assembly'])==state['assembly_digest']
  scope=state['assembly']['request']['scope'];assert scope['patient_id']=='synthetic-p1' and scope['encounter_id']=='synthetic-e1' and scope['repository_cutoff']['repository_id']==repository
  for item in state['assembly']['snapshot']['items']:
   fact=item['fact'];key=(fact['kind'],fact['id'],fact['revision']);row=facts[key]
   assert fact==json.loads(row['payload']) and digest(fact)==item['expected_digest']
   ing=item['ingestion'];assert ing['repository_id']==repository and ing['ingestion_sequence']==row['ingestion_sequence']<=scope['repository_cutoff']['fact_watermark'] and datetime.fromisoformat(ing['ingested_at'])==datetime.fromisoformat(row['ingested_at']) and datetime.fromisoformat(ing['ingested_at'])<=datetime.fromisoformat(scope['repository_cutoff']['captured_at']) and ing['payload_version']==row['payload_version']
 if e['path'].endswith('/synthetic-evidence') and e['status']==200:
  request=json.loads((j/e['request']['file']).read_text());response=json.loads((j/e['response']['file']).read_text());saves.append((request,response))
  assert request['fact']==response['fact'] and request['repository_id']==response['repository_id']==repository
  fact=response['fact'];row=facts[(fact['kind'],fact['id'],fact['revision'])]
  assert fact==json.loads(row['payload']) and response['canonical_fact']==row['payload'] and digest(fact)==response['expected_digest']
  assert response['ingestion']['ingestion_sequence']==row['ingestion_sequence']
  reviewed=[x for x in events if x['sequence']<e['sequence'] and x['path'].endswith('/synthetic-evidence/validate') and x['status']==200 and json.loads((j/x['response']['file']).read_text())['fact']==fact];assert len(reviewed)==1
 if e['path'].endswith('/circulatory-evidence-history') and e['status']==200:
  history=json.loads((j/e['response']['file']).read_text());histories.append(history)
  assert len(history['revisions'])==2
  for item in history['revisions']:
   fact=item['fact'];row=facts[(fact['kind'],fact['id'],fact['revision'])];assert fact==json.loads(row['payload']) and item['ingestion']['ingestion_sequence']==row['ingestion_sequence']
assert len(saves)==3 and {x[1]['ingestion']['ingestion_sequence'] for x in saves}=={163,164,165}
assert len(states)==5 and len(histories)==1 and len(states[-1]['assembly']['snapshot']['items'])==158
assert not any('/circulatory-review-preparations' in e['path'] or '/circulatory-review-reconciliations' in e['path'] for e in events)
executions=[e for e in events if e['path'].endswith('/circulatory-reviews')];assert len(executions)==1 and executions[0]['status']==404
probe=json.loads((j/'gate-probe.json').read_text());assert probe['health']['execution_enabled'] is False and probe['new_execution_route_status']==404
saved=(j/'15-handover-saved.txt').read_text();restored=(j/'16-handover-restored.txt').read_text()
assert 'Saved locally in this browser: 2 selection(s)' in saved and 'Restored saved handover: 2 selection(s)' in restored
cards=lambda text:[p.strip() for p in re.split(r'(?m)^  - article:\n',text)[1:]]
assert len(cards(saved))==2 and cards(saved)==cards(restored)
for value in [pc['revision'],nb['id'],'62.0000','Clinical execution disabled.','No treatment response, causal infusion effect, diagnosis or physiological simultaneity is established.']:assert value in restored,value
source=json.loads((r/'source.json').read_text())
served={e['path']:e.get('served_body_sha256') for e in events if e['path']=='/' or e['path'].startswith('/assets/')}
for path,h in source['build_files'].items():assert served['/' if path=='index.html' else '/'+path]==h,path
layout=json.loads((j/'browser-layout.json').read_text());assert layout['viewport']['width']==390 and layout['documentWidth']==390
summary={'database_tables':12,'original_fact_rows_unchanged':162,'added_fact_rows':3,'retained_receipts_unchanged':2,'original_note_ingestion':163,'pressure_correction_ingestion':164,'new_note_ingestion':165,'state_responses':len(states),'state_item_checks':sum(len(s['assembly']['snapshot']['items']) for s in states),'history_responses':len(histories),'save_responses':len(saves),'restored_handover_selections':2,'gate_probe_status':404,'build_serving_hashes_match':True,'result':'PASS'}
print(json.dumps(summary,indent=2));a.close();b.close()
