import subprocess,os,json,sqlite3
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/expanded-packaging-validation');env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')};docker=['docker','--host','unix://'+str(Path.home()/'.colima/clinrx-review-28496c4/docker.sock')]
def call(*args):return subprocess.check_output(docker+list(args),env=env)
script="import sqlite3; source=sqlite3.connect('/app/synthetic/synthetic.sqlite3'); target=sqlite3.connect('/tmp/clinrx-final.sqlite3'); source.backup(target); target.close(); source.close()"
call('exec','clinrx-expanded-2539eb6','python','-c',script)
call('cp','clinrx-expanded-2539eb6:/tmp/clinrx-final.sqlite3',str(out/'final-fixture.sqlite3'))
call('create','--name','clinrx-expanded-reference-2539eb6','clinrx-expanded-demo:2539eb6-local')
try:call('cp','clinrx-expanded-reference-2539eb6:/app/synthetic/synthetic.sqlite3',str(out/'packaged-fixture.sqlite3'))
finally:call('rm','clinrx-expanded-reference-2539eb6')
before=json.loads((out/'rows-before.json').read_text())
for name in ('final-fixture.sqlite3','packaged-fixture.sqlite3'):
 with sqlite3.connect(out/name) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  rows={table:db.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall() for table in before}
  assert json.loads(json.dumps(rows))==before
  (out/(name.replace('.sqlite3','')+'-rows.json')).write_text(json.dumps(rows,indent=2)+'\n')
(out/'container-logs.txt').write_bytes(call('logs','clinrx-expanded-2539eb6'))
listener=subprocess.run(['lsof','-nP','-iTCP:5183','-sTCP:LISTEN'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'host-port-listeners.txt').write_bytes(listener.stdout)
(out/'final-results.json').write_text(json.dumps({'status':'PASS','all_12_tables_equal_packaged_never_started_fixture':True,'all_12_tables_unchanged_after_probes_and_restart':True,'sqlite_integrity_both_snapshots':'ok','test_reference_container_removed':True},indent=2)+'\n')
print('PASS: packaged never-started fixture and final restarted container contain identical rows in all 12 tables')

info=json.loads(call('image','inspect','clinrx-expanded-demo:2539eb6-local'))[0]
(out/'image-inspect.json').write_text(json.dumps(info,indent=2)+'\n')
assert info['Architecture']=='arm64' and info['Os']=='linux'
assert info['Config']['Labels']['org.opencontainers.image.revision']=='2539eb61292456706b3c358443a8fdb7a6ece144'
(out/'docker-version.json').write_bytes(call('version','--format','{{json .}}'))
import hashlib
source=out/'source-context'
expected={str(f.relative_to(source/'backend')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (source/'backend/app').rglob('*.py')}
script="import json,hashlib;from pathlib import Path;p=Path('/app/backend');print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'app').rglob('*.py')}))"
actual=json.loads(call('exec','clinrx-expanded-2539eb6','python','-c',script))
assert actual==expected
(out/'runtime-source-sha256.json').write_text(json.dumps(actual,indent=2)+'\n')
print('PASS ARM64 image source label and every backend Python file match exact clean Git archive')
