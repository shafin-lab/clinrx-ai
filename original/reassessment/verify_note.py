from pathlib import Path
import sqlite3,json,hashlib
m=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6');out=m/'hemodynamics-MAP-63-reassessment'
with sqlite3.connect(out/'before.sqlite3') as a,sqlite3.connect(out/'after.sqlite3') as b:
 assert a.execute('pragma integrity_check').fetchone()[0]=='ok' and b.execute('pragma integrity_check').fetchone()[0]=='ok'
 tables=[r[0] for r in a.execute("select name from sqlite_master where type='table' order by name")];delta={}
 for table in tables:
  q='select * from "'+table.replace('"','""')+'"';old=a.execute(q).fetchall();new=b.execute(q).fetchall();oldset=set(map(repr,old));newset=set(map(repr,new));removed=oldset-newset;added=newset-oldset
  if table=='fact_revision':assert not removed and len(added)==1
  elif table!='sqlite_sequence':assert oldset==newset,table
  else:assert old==[('fact_revision',166)] and new==[('fact_revision',167)]
  delta[table]={'before':len(old),'after':len(new),'added':len(added),'removed':len(removed)}
 row=b.execute('select ingestion_sequence,payload from fact_revision where fact_id=?',('00234d1d-b5ff-47da-a702-e6f50918056f',)).fetchone();assert row[0]==167;fact=json.loads(row[1]);assert fact['supersedes'] is None
 expected={'baseline':{'kind':'circulatory_cardiac','id':'fs-CO-15','version':'1'},'intervention':{'kind':'circulatory_vasoactive','id':'fs-N-CHANGE','version':'1'},'followup':{'kind':'circulatory_pressure','id':'fs-MAP-15','version':'915ae2cb-99f9-47e6-883e-9fc51725a7f0'}}
 for stage,ref in expected.items():
  entry=next(e for e in fact['external_evidence'] if e['namespace']=='clinrx.local.reassessment.'+stage+'/v1');assert json.loads(entry['code'])==ref
  assert sum(x['exact']==ref and x['status']=='resolved' and x['role']=='context' and x['scope']=={'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','longitudinal_context_id':None} for x in fact['associations'])==1
  assert b.execute('select payload from fact_revision where kind=? and fact_id=? and revision=?',(ref['kind'],ref['id'],ref['version'])).fetchone()
 oldnote=json.loads(b.execute('select payload from fact_revision where fact_id=?',('3583c95b-119c-4daf-9642-42845112602e',)).fetchone()[0]);oldref=json.loads(next(e['code'] for e in oldnote['external_evidence'] if e['namespace']=='clinrx.local.reassessment.followup/v1'));assert oldref['version']=='41675deb-aa68-444f-a5fe-6ed8770c2c0c'
 digest=hashlib.sha256(row[1].encode()).hexdigest();assert digest=='1ebc8a36d78781955607c81177a2886038e778087b647806aa34b693f31d9c9e'
 result={'result':'PASS','note':{'id':fact['id'],'revision':fact['revision'],'ingestion':row[0],'digest':digest},'references':expected,'earlier_note_followup':oldref,'all_166_prior_fact_rows_unchanged':True,'both_receipts_unchanged':True,'table_delta':delta}
 (out/'new-note.json').write_text(json.dumps(fact,indent=2)+'\n');(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
