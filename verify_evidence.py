"""Portable data-only checks. Does not execute application or harness code."""
import hashlib,json,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parent
identity=json.loads((root/'source-identity.json').read_text())
commit=(root/'source-commit.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==identity['head']
assert commit.startswith(('tree '+identity['tree']+'\n').encode())
for item in identity['files']:
 data=(root/'source'/item['path']).read_bytes()
 assert hashlib.sha256(data).hexdigest()==item['sha256']
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob']
for name in ('backend','frontend','typecheck','build','hosted-build'):
 assert json.loads((root/(name+'.json')).read_text())['exit_code']==0
assert json.loads((root/'frontend.json').read_text())['node']=='v22.13.0'
assert json.loads((root/'frontend.json').read_text())['npm']=='10.9.2'
assert '4243 passed' in (root/'backend.log').read_text()
assert '443 passed' in (root/'frontend.log').read_text()
rows=json.loads((root/'rows-before-browser.json').read_text())
for name in ('rows-after-browser.json','rows-final.json'):assert json.loads((root/name).read_text())==rows
assert len(rows)==12
for name in ('fixture-snapshot.sqlite3','hosted-synthetic.sqlite3'):
 with sqlite3.connect('file:'+str(root/name)+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  actual={table:db.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall() for table in rows}
  assert json.loads(json.dumps(actual))==rows
state=json.loads((root/'state-response.json').read_text())
assert state['execution_enabled'] is False
items=state['assembly']['snapshot']['items'];assert len(items)==26 and len({i['fact']['kind'] for i in items})==15
for name in ('released','withheld'):
 original=(root/(name+'-response.json')).read_bytes()
 assert original==(root/(name+'-after-restart.json')).read_bytes()
 assert json.loads(original)['record']['decision']['outcome']==name
for event in json.loads((root/'http-exchanges.json').read_text()):
 data=(root/(event['name']+'-response.json')).read_bytes()
 assert hashlib.sha256(data).hexdigest()==event['response_sha256']
 if event['name'].startswith('blocked-'):assert event['status']==404
focus=json.loads((root/'final-browser/mobile-source-focus.json').read_text())
assert focus['bodyWidth']==focus['documentWidth']==focus['viewport']['width']==390
assert focus['focusedLabel']=='Selected source evidence'
assert 0<=focus['focusedBounds']['top']<focus['viewport']['height']
assert focus['focusedBounds']['bottom']<=focus['viewport']['height']
assert json.loads((root/'final-browser/console.json').read_text())==[]
checksums=(root/'SHA256SUMS').read_text().splitlines()
for entry in checksums:
 expected,path=entry.split('  ',1);assert hashlib.sha256((root/path).read_bytes()).hexdigest()==expected,path
print('PASS: source identity, final checks, 12-table stability, real reads/blocked routes, retained restart bytes, mobile focus and '+str(len(checksums))+' artifact checksums')
