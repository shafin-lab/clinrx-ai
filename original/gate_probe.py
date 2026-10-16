import json,urllib.request,urllib.error,sqlite3,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
base='http://127.0.0.1:8765/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
prep=next(e for e in events if e.get('scenario')=='release' and e.get('method')=='POST' and e['path'].endswith('/circulatory-review-preparations'))
original=next(e for e in events if e.get('scenario')=='release' and e.get('method')=='POST' and e['path'].endswith('/circulatory-reviews'))
prepared=json.loads((root/prep['response']).read_bytes());command={'command':prepared['command']}
root.joinpath('control.json').write_text(json.dumps({'scenario':'release','closed':True}))
def snapshot():
 with sqlite3.connect(root/'release.sqlite3') as c:
  return {table:hashlib.sha256(repr(c.execute('select * from '+table+' order by 1').fetchall()).encode()).hexdigest() for table in ('fact_revision','circulatory_execution')}
def request(name,path,body):
 data=json.dumps(body).encode()
 try:
  r=urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'}),timeout=10);status=r.status;raw=r.read()
 except urllib.error.HTTPError as e:status=e.code;raw=e.read()
 (root/('gate-'+name+'.json')).write_bytes(raw)
 return status,raw
before=snapshot()
status,retry=request('retained-retry','/circulatory-reviews',command)
assert status==200 and retry==(root/original['response']).read_bytes()
status,reconciliation=request('retained-reconciliation','/circulatory-review-reconciliations',command)
assert status==200 and json.loads(reconciliation)=={'status':'committed_match','execution':json.loads(retry)}
status,rejected=request('prepare-rejected','/circulatory-review-preparations',json.loads((root/prep['request']).read_bytes()))
assert status==422
after=snapshot();assert before==after
with sqlite3.connect(root/'gate_pending.sqlite3') as c:assert c.execute('select count(*) from circulatory_execution').fetchone()[0]==0
summary={'gate':False,'preparation_status':422,'retained_retry_status':200,'retained_retry_bytes_identical':True,'reconciliation_status':'committed_match','storage_before':before,'storage_after':after,'blocked_pending_receipts':0}
(root/'gate-proof.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
