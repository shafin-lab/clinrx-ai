"""Check captured real HTTP exchanges against disposable persisted receipts."""
import json,sqlite3,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
def body(e,side='response'):return json.loads((root/e[side]).read_bytes())
names=('release','same_value','provenance','withdrawn','pressure','malformed','post_commit','timeout','absent','gate_pending')
results=[]
for name in names:
 es=[e for e in events if e.get('event')=='http' and e['scenario']==name]
 preparations=[e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-review-preparations') and e['status']==200]
 executions=[e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-reviews')]
 assert preparations and executions,name
 prepared=body(preparations[-1]);identity=prepared['execution_id'];command={'command':prepared['command']}
 assert len(prepared['inference']['inputs'])==4
 assert prepared['inference']['inputs'][-1]=={'kind':'circulatory_monitoring','id':'m7-CAL','version':'1'}
 for e in executions:assert body(e,'request')==command
 reconciliations=[e for e in es if e['method']=='POST' and e['path'].endswith('/circulatory-review-reconciliations')]
 for e in reconciliations:assert body(e,'request')==command
 db=sqlite3.connect(root/(name+'.sqlite3'))
 rows=db.execute('select execution_id,payload,payload_digest from circulatory_execution').fetchall()
 if name=='gate_pending':
  assert not rows and executions[0]['status']==422 and executions[0]['closed']
  assert body(reconciliations[0])=={'status':'absent','execution':None}
  results.append({'scenario':name,'status':'PASS','execution_id':identity,'receipt_count':0,'execution_http_status':422});continue
 assert len(rows)==1 and rows[0][0]==identity
 saved=json.loads(rows[0][1]);assert hashlib.sha256(rows[0][1].encode()).hexdigest()==rows[0][2]
 successful=next(e for e in executions if e['status']==200)
 receipt=body(successful);assert receipt['record']==saved and receipt['execution_id']==identity
 assert receipt['record']['evidence']['inference']==prepared['inference']
 assert [f['revision'] for f in saved['evidence']['facts']]==['2','1','1','1']
 assert [f['id'] for f in saved['evidence']['facts']]==['m7-P','m7-L','m7-V','m7-CAL']
 state_event=next(e for e in reversed(es) if e['number']<preparations[-1]['number'] and e['path'].endswith('/patient-state-v3'))
 selected_items=body(state_event)['assembly']['snapshot']['items']
 for fact in saved['evidence']['facts']:
  assert fact==next(i['fact'] for i in selected_items if i['fact']['id']==fact['id'])
  raw=db.execute('select payload from fact_revision where kind=? and fact_id=? and revision=?',(fact['kind'],fact['id'],fact['revision'])).fetchone()[0]
  assert json.loads(raw)==fact
 outcome='withheld' if name in ('same_value','provenance','withdrawn','pressure') else 'released'
 assert saved['decision']['outcome']==outcome
 assert (receipt['statement'] is None)==(outcome=='withheld')
 witness=saved['final_recheck']['evidence'][-1]
 assert witness['consumed']=={'kind':'circulatory_monitoring','id':'m7-CAL','version':'1'}
 assert witness['terminal']['version']==('2' if name in ('same_value','provenance','withdrawn') else '1')
 if name=='withdrawn':assert saved['final_recheck']['terminal_facts'][-1]['record_status']=='withdrawn'
 if name=='provenance':assert saved['final_recheck']['terminal_facts'][-1]['provenance']['actor']=='Isolated corrected source'
 if name=='pressure':assert saved['final_recheck']['evidence'][0]['terminal']['version']=='3'
 for e in es:
  if e['method']=='GET' and '/circulatory-reviews/' in e['path']:assert body(e)==receipt
 for e in reconciliations:
  if name=='absent':assert body(e)=={'status':'absent','execution':None}
  else:assert body(e)=={'status':'committed_match','execution':receipt}
 if name in ('malformed','post_commit','timeout'):assert len(executions)==1 and len(preparations)==1
 if name=='malformed':
  delivered=json.loads((root/(successful['response'].replace('-response.bin','-delivered.bin'))).read_bytes())
  assert delivered['record']['final_recheck']['inference']['reference']['id']=='foreign'
  assert saved['final_recheck']['inference']['reference']['id']!='foreign'
 if name=='timeout':assert reconciliations[0]['time']-successful['time']>=29
 if name=='absent':
  assert len(executions)==2 and executions[0]['status']==502 and executions[0]['time']<reconciliations[0]['time']<executions[1]['time']
 results.append({'scenario':name,'status':'PASS','execution_id':identity,'outcome':outcome,'receipt_count':1,'execution_attempts':len(executions),'payload_sha256':rows[0][2],'original_support_retained':True,'terminal_support_revision':witness['terminal']['version']})
repo=Path('/Users/mohammedshafiqshajahan/Documents/clinrx-ai')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=repo,text=True).strip()
assert head=='17e2064c3f1a1761876e9a42c5c7a131646d465c'
assert tree=='3723885d26a9ba62ff271361a1c8a6a7351de63c'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
summary={'source_head':head,'source_tree':tree,'working_tree_clean':True,'cases':results}
(root/'verified-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
