"""Data-only container evidence verification; never starts Docker or the application."""
import json,sqlite3,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
identity=json.loads((root/'source-identity.json').read_text())
commit=(root/'source-commit.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==identity['head']
assert commit.startswith(('tree '+identity['tree']+'\n').encode())
for name in ('build','run','probes','final-checks','stop-container','colima-start','colima-stop'):
 assert json.loads((root/(name+'.json')).read_text())['exit_code']==0
image=json.loads((root/'image-inspect.json').read_text())
assert image['Config']['Labels']['org.opencontainers.image.revision']==identity['head']
assert image['Architecture']=='arm64' and image['Os']=='linux'
assert image['Config']['User']=='10001:10001'
container=json.loads((root/'container-inspect.json').read_text())[0]
assert container['Config']['User']=='10001:10001' and not container['Mounts']
assert container['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5182'}]
rows=json.loads((root/'rows-before.json').read_text());assert len(rows)==12 and rows['alembic_version']==[['m7_0008']]
for name in ('rows-after-probes.json','rows-after-restart.json','final-fixture-rows.json','packaged-fixture-rows.json'):
 assert json.loads((root/name).read_text())==rows
for name in ('packaged-fixture.sqlite3','final-fixture.sqlite3'):
 with sqlite3.connect('file:'+str(root/name)+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  actual={table:db.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall() for table in rows}
  assert json.loads(json.dumps(actual))==rows
state=json.loads((root/'state-response.bin').read_bytes());assert state['execution_enabled'] is False
items=state['assembly']['snapshot']['items'];assert len(items)==26 and len({i['fact']['kind'] for i in items})==15
for name in ('released','withheld'):
 raw=(root/(name+'-response.bin')).read_bytes()
 assert raw==(root/(name+'-after-restart-response.bin')).read_bytes()
 assert json.loads(raw)['record']['decision']['outcome']==name
for event in json.loads((root/'http-events.json').read_text()):
 raw=(root/(event['name']+'-response.bin')).read_bytes();assert hashlib.sha256(raw).hexdigest()==event['sha256']
 if event['name'].startswith('blocked-'):assert event['status']==404
assert json.loads((root/'stale-context-response.bin').read_bytes())['code']=='invalid_state_context'
focus=json.loads((root/'browser/mobile.json').read_text())
assert focus['viewport']=={'width':390,'height':844} and focus['bodyWidth']==focus['documentWidth']==390
assert focus['focusedLabel']=='Selected source evidence' and 0<=focus['focusedBounds']['top']<focus['focusedBounds']['bottom']<=844
assert json.loads((root/'browser/console.json').read_text())==[]
stop=json.loads((root/'stopped-container.json').read_text())
assert stop['State']['Status']=='exited' and stop['State']['ExitCode']==0
assert json.loads((root/'cleanup-check.json').read_text())['test_port_5182_no_longer_listening']
manifest=(root/'SHA256SUMS').read_text().splitlines()
for entry in manifest:
 expected,path=entry.split('  ',1);assert hashlib.sha256((root/path).read_bytes()).hexdigest()==expected,path
print('PASS: exact source/image identity, real container reads/blocks, all 12 tables, packaged/final fixture integrity, restart, browser/mobile and '+str(len(manifest))+' checksums')
