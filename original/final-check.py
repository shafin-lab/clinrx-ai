import subprocess,os,json,sqlite3
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/authored-container-d0f94dc-validation');env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')};docker=['docker','--host','unix://'+str(Path.home()/'.colima/clinrx-review-28496c4/docker.sock')]
def call(*args):return subprocess.check_output(docker+list(args),env=env)
script="import sqlite3; source=sqlite3.connect('/app/synthetic/synthetic.sqlite3'); target=sqlite3.connect('/tmp/clinrx-final.sqlite3'); source.backup(target); target.close(); source.close()"
call('exec','clinrx-expanded-d0f94dc','python','-c',script)
call('cp','clinrx-expanded-d0f94dc:/tmp/clinrx-final.sqlite3',str(out/'final-fixture.sqlite3'))
call('create','--name','clinrx-expanded-reference-d0f94dc','clinrx-expanded-demo:d0f94dc-local')
try:call('cp','clinrx-expanded-reference-d0f94dc:/app/synthetic/synthetic.sqlite3',str(out/'packaged-fixture.sqlite3'))
finally:call('rm','clinrx-expanded-reference-d0f94dc')
before=json.loads((out/'rows-before.json').read_text())
for name in ('final-fixture.sqlite3','packaged-fixture.sqlite3'):
 with sqlite3.connect(out/name) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  rows={table:db.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall() for table in before}
  assert json.loads(json.dumps(rows))==before
  (out/(name.replace('.sqlite3','')+'-rows.json')).write_text(json.dumps(rows,indent=2)+'\n')
(out/'container-logs.txt').write_bytes(call('logs','clinrx-expanded-d0f94dc'))
listener=subprocess.run(['lsof','-nP','-iTCP:5183','-sTCP:LISTEN'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'host-port-listeners.txt').write_bytes(listener.stdout)
(out/'final-results.json').write_text(json.dumps({'status':'PASS','all_12_tables_equal_packaged_never_started_fixture':True,'all_12_tables_unchanged_after_probes_and_restart':True,'sqlite_integrity_both_snapshots':'ok','test_reference_container_removed':True},indent=2)+'\n')
print('PASS: packaged never-started fixture and final restarted container contain identical rows in all 12 tables')

info=json.loads(call('image','inspect','clinrx-expanded-demo:d0f94dc-local'))[0]
(out/'image-inspect.json').write_text(json.dumps(info,indent=2)+'\n')
assert info['Architecture']=='arm64' and info['Os']=='linux'
assert info['Config']['Labels']['org.opencontainers.image.revision']=='d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982'
(out/'docker-version.json').write_bytes(call('version','--format','{{json .}}'))
import hashlib
source=out/'source-context'
expected={str(f.relative_to(source/'backend')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (source/'backend/app').rglob('*.py')}
script="import json,hashlib;from pathlib import Path;p=Path('/app/backend');print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'app').rglob('*.py')}))"
actual=json.loads(call('exec','clinrx-expanded-d0f94dc','python','-c',script))
assert actual==expected
(out/'runtime-source-sha256.json').write_text(json.dumps(actual,indent=2)+'\n')
print('PASS ARM64 image source label and every backend Python file match exact clean Git archive')
