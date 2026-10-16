"""Portable read-only verification of published demo evidence; Python stdlib only."""
import json,sqlite3,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
def load(path):return json.loads(path.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def ref(fact):return {'kind':fact['kind'],'id':fact['id'],'version':fact['revision']}
def verify():
 original=ROOT/'original-validation'
 for name,expected in load(original/'SHA256SUMS.json').items():assert sha((original/name).read_bytes())==expected,name
 db=sqlite3.connect('file:'+str(ROOT/'runtime/synthetic-snapshot.sqlite3')+'?mode=ro',uri=True)
 assert db.execute('pragma integrity_check').fetchall()==[('ok',)]
 assert db.execute('select version_num from alembic_version').fetchall()==[('m7_0008',)]
 repo=db.execute('select repository_id from repository_identity').fetchone()[0]
 cursor=db.execute('select * from fact_revision');columns=[v[0] for v in cursor.description];facts=[dict(zip(columns,r)) for r in cursor.fetchall()]
 def row(reference):
  matches=[r for r in facts if (r['kind'],r['fact_id'],r['revision'])==(reference['kind'],reference['id'],reference['version'])];assert len(matches)==1
  return matches[0]
 def metadata(r,m,low,high):
  assert m['repository_id']==repo and low<m['ingestion_sequence']<=high
  assert m['ingestion_sequence']==r['ingestion_sequence'] and m['payload_version']==r['payload_version']
  assert datetime.fromisoformat(m['ingested_at'])==datetime.fromisoformat(r['ingested_at'])
 for state in (load(original/'api-state.json'),load(ROOT/'runtime/current-state.json')):
  assert state['execution_enabled'] is False
  items=state['assembly']['snapshot']['items'];assert len(items)==26 and len({i['fact']['kind'] for i in items})==15
  cutoff=state['assembly']['request']['scope']['repository_cutoff'];assert cutoff['repository_id']==repo
  for item in items:
   r=row(ref(item['fact']));assert json.loads(r['payload'])==item['fact'] and sha(r['payload'].encode())==item['expected_digest']
   metadata(r,item['ingestion'],0,cutoff['fact_watermark'])
 receipts=[]
 assert db.execute('select count(*) from circulatory_execution').fetchone()[0]==2
 for name,outcome in (('released','released'),('withheld','withheld')):
  response=load(original/(name+'-receipt.json'));record=response['record'];request=record['request'];final=record['final_recheck'];evidence=record['evidence'];scope=request['inference_request']['scope']
  payload,payload_digest=db.execute('select payload,payload_digest from circulatory_execution where execution_id=?',(response['execution_id'],)).fetchone()
  assert json.loads(payload)==record and sha(payload.encode())==payload_digest==sha(canonical(record))
  assert record['decision']['outcome']==outcome and (response['statement'] is None)==(outcome=='withheld')
  cutoffs=[scope['repository_cutoff'],request['inference_cutoff'],final['final_cutoff']];a,b,c=[x['fact_watermark'] for x in cutoffs]
  assert all(x['repository_id']==repo for x in cutoffs) and a<b<=c
  assert final['scope']==scope==request['assembly_request']['scope'] and final['inference_cutoff']==request['inference_cutoff'] and evidence['request']==request
  ir=request['inference_request'];pins=[ir['pressure'],ir['lactate'],ir['vasopressor'],*ir['supporting']]
  assert len(pins)==len(final['evidence'])==len(final['terminal_facts'])==len(evidence['facts'])==4
  witnesses=[]
  for pin,w,terminal,fact,item in zip(pins,final['evidence'],final['terminal_facts'],evidence['facts'],evidence['items']):
   consumed=row(w['consumed']);end=row(w['terminal'])
   assert w['consumed']==pin['reference']==ref(fact)==ref(item['fact'])
   assert fact==item['fact']==json.loads(consumed['payload'])
   assert sha(consumed['payload'].encode())==pin['expected_digest']==w['source_digest']==w['item_digest']==item['expected_digest']
   assert w['terminal']==ref(terminal) and terminal==json.loads(end['payload']) and sha(end['payload'].encode())==w['terminal_source_digest']
   latest=max((r for r in facts if (r['kind'],r['fact_id'])==(w['terminal']['kind'],w['terminal']['id']) and r['ingestion_sequence']<=c),key=lambda r:r['ingestion_sequence'])
   assert end==latest
   metadata(consumed,w['original_ingestion'],0,a);metadata(end,w['terminal_ingestion'],0,c);assert item['ingestion']==w['original_ingestion']
   witnesses.append({'consumed':w['consumed'],'terminal':w['terminal'],'source_digest':w['source_digest'],'terminal_digest':w['terminal_source_digest']})
  iw=final['inference'];i=row(iw['reference']);terminal=row(iw['terminal'])
  assert iw['reference']==ref(evidence['inference'])=={'kind':'inference','id':ir['inference_id'],'version':ir['revision']}
  assert json.loads(i['payload'])==evidence['inference']
  assert sha(i['payload'].encode())==iw['expected_digest']==iw['observed_digest']==iw['reconstruction_digest']==request['expected_inference_digest']
  assert sha(terminal['payload'].encode())==iw['terminal_digest']
  assert iw['inputs']==iw['dependencies']==evidence['inference']['inputs'] and iw['declarations']==evidence['inference']['provenance']['upstream']
  metadata(i,iw['ingestion'],a,b);metadata(terminal,iw['terminal_ingestion'],0,c);assert iw['ingestion']==evidence['inference_ingestion']
  assert witnesses[-1]['consumed']=={'kind':'circulatory_monitoring','id':'m7-CAL','version':'1'}
  assert witnesses[-1]['terminal']['version']==('1' if outcome=='released' else '2')
  receipts.append({'execution_id':response['execution_id'],'outcome':outcome,'payload_sha256':payload_digest,'cutoffs':[a,b,c],'witnesses':witnesses})
 before=load(ROOT/'runtime/gate-before-rows.json');after=load(ROOT/'runtime/gate-after-rows.json');assert before['tables']==after['tables']
 old=load(original/'real-api-verification.json')
 for table in ('repository_identity','fact_revision','circulatory_execution'):
  value=before['tables'][table];rows=db.execute('select * from '+table+' order by 1').fetchall();assert [list(r) for r in rows]==value['rows']
  assert sha(repr(rows).encode())==value['repr_rows_sha256']
  if table in old['before']:assert value['repr_rows_sha256']==old['before'][table]==old['after'][table]
 gate=load(ROOT/'runtime/gate-exchange.json');assert gate['status']==422 and gate['tables_unchanged']
 assert sha((ROOT/'runtime/gate-request.json').read_bytes())==gate['request_sha256'] and sha((ROOT/'runtime/gate-response.json').read_bytes())==gate['response_sha256']
 assert load(ROOT/'browser-final/console.json')==[]
 for check in load(ROOT/'checks.json'):assert check['exit_code']==0 and check['source_head']=='8d3ce9cec1aa5c843cb25af385735d358fb02a44'
 db.close()
 return {'status':'PASS','sqlite_integrity':'ok','repository_id':repo,'recorded_items':26,'families':15,'retained_receipts':receipts,'new_execution_enabled':False,'new_preparation_http_status':422,'gate_rows_unchanged':True,'original_gate_commitments_recomputed':True,'original_validation_manifest_verified':True,'final_browser_console_errors':0}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
