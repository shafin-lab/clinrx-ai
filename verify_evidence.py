"""Portable read-only publication checks; no application or harness imports."""
from pathlib import Path
import json,hashlib,re
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
manifest=json.loads((p/'SHA256SUMS.json').read_text())
for name,h in manifest.items():assert sha((p/name).read_bytes())==h,name
identity=json.loads((p/'source-identity.json').read_text())
for name,h in identity['files'].items():assert sha((p/'source'/name).read_bytes())==h,name
for line in (p/'tested-source.sha256').read_text().splitlines():
 h,name=line.split('  ',1);assert identity['files'][name]==h,name
commit=(p/'source-commit.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==identity['source']
assert commit.startswith(('tree '+identity['tree']+'\nparent '+identity['parent']+'\n').encode())
assert '524 passed' in (p/'tests.log').read_text() and '14 passed' in (p/'tests.log').read_text()
assert 'tsc --noEmit && vite build' in (p/'build.log').read_text() and 'built in' in (p/'build.log').read_text()
state=json.loads((p/'reference-data/state-redacted.json').read_text())
assert state['execution_enabled'] is False and sha(canon(state['assembly']))==state['assembly_digest']
items=state['assembly']['snapshot']['items'];assert len(items)==156
by_id={i['fact']['id']:i for i in items}
assert len(by_id)==len(items),'fixture IDs must be unambiguous for this data-only check'
def plotted(name,count,columns):
 dom=(p/'browser'/name).read_text();times=[t.replace(' ','T')+'Z' for t in re.findall(r'columnheader "(2026-10-08 [0-9:]+)"',dom)];assert len(times)==columns
 seen={};cell=-1
 for line in dom.splitlines():
  if re.match(r"^\s*- ['\"]?row ",line):cell=-1
  if re.match(r'^\s*- cell(?: |$)',line):cell+=1
  m=re.search(r'button "Chart source ([^ ]+) revision ([^"]+)"',line)
  if m:
   id,rev=m.groups();assert id not in seen and 0<=cell<len(times)
   item=by_id[id];f=item['fact'];assert f['revision']==rev and item['inclusion']=='in_window'
   t=f.get('collected',f.get('occurred',{}));assert t['source_timestamp'].replace('+00:00','Z')==times[cell]
   seen[id]=times[cell]
 assert len(seen)==count,(name,len(seen));assert 'New execution disabled in this demo' in dom
 for group in ['BP / MAP','Cardiac output / index','Rhythm / heart rate','Infusion events','Fluid records','Perfusion observations']:assert 'rowgroup "'+group+'"' in dom
 return seen
all_times=plotted('all-times-dom.txt',66,12);latest=plotted('default-dom.txt',28,4)
assert set(latest)<=set(all_times)
for id in ['fs-MAP-60','fs-systemic_systolic-60','fs-systemic_diastolic-60','fs-CO-60','fs-CI-60','fs-HR-60','fs-RHYTHM-60','fs-D-CHANGE','fs-BALANCE-TOTAL','fs-LACTATE-60']:assert id in latest
for id in ['m7-CO','m7-FLOTRAC','m7-PICCO-CO','m7-VOLUMEVIEW']:assert id in all_times
assert 'm7-CONTEXT-CO' not in all_times
inspector=(p/'browser/co-inspector-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for text in ['fs-CO-60 / 1','4.60 L/min','suspect','bolus thermodilution','SwanGanz','HemoSphere','3 {injections}']:assert text in inspector
print(json.dumps({'result':'PASS','manifest_entries':len(manifest),'source_files':len(identity['files']),'tested_file_hashes_match_commit':True,'frontend_tests':524,'all_time_controls':len(all_times),'latest_controls':len(latest),'six_groups':True,'source_revision_time_correspondences':len(all_times),'reference_assembly_digest_verified':True,'scope':'Implementation-produced data-only checks; reference API state copied from prior publication; not fresh API/database validation or independent Director review'},indent=2))
