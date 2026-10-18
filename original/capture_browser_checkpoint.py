import json,sqlite3,hashlib,sys,urllib.request
from pathlib import Path
root=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6')
label=sys.argv[1];out=root/'guided-entry-validation'
with sqlite3.connect(root/'guided-entry-local-run/synthetic.sqlite3') as db:
    with sqlite3.connect(out/(label+'.sqlite3')) as dest:db.backup(dest)
    tables={row[0]:db.execute('SELECT * FROM "'+row[0]+'" ORDER BY rowid').fetchall() for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}
(out/(label+'-rows.json')).write_text(json.dumps(tables,indent=2)+'\n')
url='http://127.0.0.1:5191/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3?review_start=2026-10-08T08:00:00Z&review_end=2026-10-08T10:00:00Z'
raw=urllib.request.urlopen(url).read();(out/(label+'-state.json')).write_bytes(raw)
state=json.loads(raw)
print(json.dumps({'checkpoint':label,'execution_enabled':state['execution_enabled'],'items':len(state['assembly']['snapshot']['items']),'rows':{k:len(v) for k,v in tables.items()}}))
