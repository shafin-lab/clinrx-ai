import subprocess,os,json,sqlite3
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-container-validation');env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')};docker=['docker','--host','unix://'+str(Path.home()/'.colima/clinrx-review-28496c4/docker.sock')]
def call(*args):return subprocess.check_output(docker+list(args),env=env)
script="import sqlite3; source=sqlite3.connect('/app/synthetic/synthetic.sqlite3'); target=sqlite3.connect('/tmp/clinrx-final.sqlite3'); source.backup(target); target.close(); source.close()"
call('exec','clinrx-review-28496c4','python','-c',script)
call('cp','clinrx-review-28496c4:/tmp/clinrx-final.sqlite3',str(out/'final-fixture.sqlite3'))
call('create','--name','clinrx-packaged-reference-28496c4','clinrx-synthetic-demo:28496c4-local')
try:call('cp','clinrx-packaged-reference-28496c4:/app/synthetic/synthetic.sqlite3',str(out/'packaged-fixture.sqlite3'))
finally:call('rm','clinrx-packaged-reference-28496c4')
before=json.loads((out/'rows-before.json').read_text())
for name in ('final-fixture.sqlite3','packaged-fixture.sqlite3'):
 with sqlite3.connect(out/name) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  rows={table:db.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall() for table in before}
  assert json.loads(json.dumps(rows))==before
  (out/(name.replace('.sqlite3','')+'-rows.json')).write_text(json.dumps(rows,indent=2)+'\n')
(out/'container-logs.txt').write_bytes(call('logs','clinrx-review-28496c4'))
listener=subprocess.run(['lsof','-nP','-iTCP:5182','-sTCP:LISTEN'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'host-port-listeners.txt').write_bytes(listener.stdout)
(out/'final-results.json').write_text(json.dumps({'status':'PASS','all_12_tables_equal_packaged_never_started_fixture':True,'all_12_tables_unchanged_after_browser':True,'sqlite_integrity_both_snapshots':'ok','browser_console_warnings_errors':json.loads((out/'browser/console.json').read_text()),'test_reference_container_removed':True},indent=2)+'\n')
print('PASS: packaged never-started fixture and final browser/restarted container contain identical rows in all 12 tables')
