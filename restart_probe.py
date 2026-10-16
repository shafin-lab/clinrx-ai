import json,urllib.request,urllib.error,hashlib,sqlite3
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-hosting-validation')
base='http://127.0.0.1:5181';prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1';proof=[]
for name,ending in [('released','c901'),('withheld','c902')]:
 with urllib.request.urlopen(base+prefix+'/circulatory-reviews/00000000-0000-4000-8000-00000000'+ending) as response:
  body=response.read();assert response.status==200 and body==(out/(name+'-response.json')).read_bytes()
  (out/(name+'-after-restart.json')).write_bytes(body)
  proof.append({'receipt':ending,'byte_identical_after_restart':True,'sha256':hashlib.sha256(body).hexdigest()})
raw=(out/'history-request.json').read_bytes()
request=urllib.request.Request(base+prefix+'/circulatory-evidence-history',data=raw,headers={'Content-Type':'application/json'})
try:response=urllib.request.urlopen(request)
except urllib.error.HTTPError as error:response=error
body=response.read();(out/'stale-context-after-restart.json').write_bytes(body)
assert response.status>=400 and json.loads(body)['code']=='invalid_state_context'
proof.append({'stale_state_context_rejected':True,'status':response.status,'code':'invalid_state_context'})
with sqlite3.connect(out/'hosted-synthetic.sqlite3') as db:
 tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
 rows={name:db.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall() for name, in tables}
assert json.loads(json.dumps(rows))==json.loads((out/'rows-before-browser.json').read_text())
(out/'restart-check.json').write_text(json.dumps({'checks':proof,'all_12_tables_unchanged':True},indent=2)+'\n')
print('PASS: both receipts byte-identical after restart; old context rejected; all 12 tables unchanged')
