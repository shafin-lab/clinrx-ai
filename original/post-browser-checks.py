from pathlib import Path
import subprocess,os,json,hashlib,re,sqlite3
p=Path(__file__).resolve().parent;env={**os.environ,'DOCKER_CONFIG':str(p/'docker-client')}
cmd=['docker','--host','unix:///Users/mohammedshafiqshajahan/.colima/clinrx-review-28496c4/docker.sock']
def docker(*args):return subprocess.check_output(cmd+list(args),env=env)
script="""import sqlite3,json
with sqlite3.connect('file:/app/synthetic/synthetic.sqlite3?mode=ro',uri=True) as c:
 print(json.dumps({n:c.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n, in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")},sort_keys=True))
"""
raw=docker('exec','clinrx-expanded-d0f94dc','python','-c',script);(p/'rows-after-all-browser-checks.json').write_bytes(raw)
assert json.loads(raw)==json.loads((p/'rows-before.json').read_text())
current=json.loads(docker('inspect','clinrx-expanded-d0f94dc'))[0];old=json.loads(docker('inspect','clinrx-expanded-2539eb6'))[0]
assert current['State']['Running'] and not old['State']['Running']
assert current['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5183'}] and not current['Mounts']
assert current['Config']['User']=='10001:10001' and current['HostConfig']['CapDrop']==['ALL']
assert 'no-new-privileges' in current['HostConfig']['SecurityOpt']
(p/'current-container-inspect.json').write_text(json.dumps(current,indent=2)+'\n')
(p/'previous-container-status.json').write_text(json.dumps({'name':old['Name'],'running':old['State']['Running'],'image':old['Image'],'preserved':True},indent=2)+'\n')
asset_script="""from pathlib import Path
import json,hashlib
p=Path('/app/frontend-dist')
print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}))
"""
assets=json.loads(docker('exec','clinrx-expanded-d0f94dc','python','-c',asset_script));(p/'runtime-frontend-sha256.json').write_text(json.dumps(assets,indent=2)+'\n')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((p/'index-response.bin').read_bytes())==assets['index.html']
urls=re.findall(r'(?:src|href)="(/assets/[^"]+)"',(p/'index-response.bin').read_text())
for n,url in enumerate(urls):assert sha((p/f'asset-{n}-response.bin').read_bytes())==assets[url.lstrip('/')]
state=json.loads((p/'fresh-state-response.bin').read_text());items=state['assembly']['snapshot']['items'];by_id={i['fact']['id']:i for i in items};assert len(items)==156 and state['execution_enabled'] is False
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
assert sha(canon(state['assembly']))==state['assembly_digest']
for item in items:assert sha(canon(item['fact']))==item['expected_digest']
dom=(p/'container-deliverable-summary-dom.txt').read_text()
def controls(prefix,count):
 matches=list(re.finditer(r'button "'+prefix+r' ([^"\n]+)":',dom));assert len(matches)==count
 for n,m in enumerate(matches):
  id=m.group(1).rsplit(' ',1)[1];item=by_id[id];f=item['fact'];block=dom[m.end():matches[n+1].start() if n+1<len(matches) else len(dom)]
  assert id+' / '+f['revision'] in block
  time=(f.get('collected') or f.get('occurred') or {}).get('source_timestamp')
  if time:assert time in block
  q=f.get('result',{}).get('quantity')
  if q:assert q['value'] in block and q['unit']['raw'] in block
  finding=f.get('result',{}).get('finding')
  if finding:assert finding['raw_display'] in block
 return len(matches)
assert controls('Case source',42)==42;assert controls('Open summary source',98)==98
assert len(re.findall(r'button "Inspect uncertainty ',dom))==13
for text in ['Expanded ICU · 156 source records','Patient-level relationship: not established','New execution disabled in this demo','treatment response remain unconfirmed','HPI is optional']:assert text in dom,text
assert not re.search(r'button "(?:Prepare|Execute|Reconcile)',dom)
assert (p/'container-abg-history-dom.txt').read_text().count('1 retained revision at this cutoff')==1
for name,ref in [('container-abg-inspector','fs-PH-60 / 1'),('container-co-inspector','fs-CO-60 / 1'),('container-echo-keyboard-expanded','m7-RVSP / 1'),('container-infusion-inspector','fs-N-CHANGE / 1')]:
 s=(p/(name+'-dom.txt')).read_text().split('complementary "Selected source evidence"')[1];assert ref in s
 if 'abg' in name:
  for text in ['fs-arterial-sample-60','40 %','5 cmH2O','2026-10-08T09:00:00+00:00']:assert text in s
 if 'co-' in name:assert 'suspect' in s and '4.60' in s
 if 'echo-' in name:assert 'Source-reported estimate using TR velocity and estimated RAP 5 mmHg' in s and 'RVOT obstruction not documented' in s
 if 'infusion-' in name:
  for text in ['7 mcg/min','0.08 mg/mL','70 kg · source fs-WEIGHT / 1','5.25 mL/h · fs-PUMP-RATE-N-CHANGE / 1','No continuous exposure, dose conversion or treatment effect is inferred']:assert text in s
assert json.loads((p/'browser-errors-warnings.json').read_text())==[]
result={'result':'PASS','source':'d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982','tree':'384bee3150f0428156549962da1147382f2f03f9','image':current['Image'],'architecture':'linux/arm64','gate_enabled':False,'records':156,'full_pin_matches':156,'authored_controls':42,'summary_controls':98,'uncertainty_controls':13,'inspected_sources':['fs-PH-60/1','fs-CO-60/1','m7-RVSP/1','fs-N-CHANGE/1'],'bounded_history':'selected pH revision 1','all_12_tables_unchanged_after_http_restart_and_browser':True,'retained_receipts':2,'runtime_assets_match_served_bytes':True,'container_running_loopback_only':True,'previous_container_preserved_stopped':True,'browser_console_error_warning_count':0,'clinical_validation':False,'external_hosting':False,'merged':False,'deployed':False}
(p/'post-browser-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
