"""Data-only captured-content verification; no app or test execution."""
from pathlib import Path
import json,hashlib,base64,re
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for name,h in json.loads((p/'SHA256SUMS.json').read_text()).items():assert sha((p/name).read_bytes())==h,name
for name,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/name).read_bytes())==h,name
mirrors=json.loads((p/'text-mirrors/index.json').read_text())
for name,indexpath in mirrors.items():
 index=json.loads((p/indexpath).read_text());parts=[]
 for part in index['parts']:
  encoded=(p/indexpath).parent.joinpath(part['file']).read_bytes();assert sha(encoded)==part['sha256']
  raw=base64.b64decode(encoded,validate=True);assert len(raw)==part['bytes'] and sha(raw)==part['decoded_sha256'];parts.append(raw)
 raw=b''.join(parts);assert raw==(p/name).read_bytes() and len(raw)==index['bytes'] and sha(raw)==index['sha256']
identity=json.loads((p/'reference-data/source-identity.json').read_text());raw=base64.b64decode(identity['raw_commit_base64'])
assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==identity['head']=='d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982'
assert raw.startswith(('tree '+identity['tree']+'\n').encode())
state=json.loads((p/'reference-data/fresh-state-content.json').read_text());assert state['execution_enabled'] is False and sha(canon(state['assembly']))==state['assembly_digest']
items=state['assembly']['snapshot']['items'];assert len(items)==156
by_id={i['fact']['id']:i for i in items};assert len(by_id)==156
for i in items:assert sha(canon(i['fact']))==i['expected_digest']
dom=(p/'original/patient-summary-dom.txt').read_text()
def check_controls(pattern,expected):
 controls=list(re.finditer(pattern,dom));assert len(controls)==expected
 for n,m in enumerate(controls):
  id=m.group(1).rsplit(' ',1)[1];i=by_id[id];body=dom[m.end():controls[n+1].start() if n+1<len(controls) else len(dom)]
  assert id+' / '+i['fact']['revision'] in body
  time=(i['fact'].get('collected') or i['fact'].get('occurred') or {}).get('source_timestamp')
  if time:assert time in body
  q=i['fact'].get('result',{}).get('quantity')
  if q:assert q['value'] in body and q['unit']['raw'] in body
  finding=i['fact'].get('result',{}).get('finding')
  if finding:assert finding['raw_display'] in body
 return len(controls)
authored=check_controls(r'button "Case source ([^"\n]+)":',42)
summary=check_controls(r'button "Open summary source ([^"\n]+)":',98)
uncertainty=re.findall(r'button "Inspect uncertainty ([^"\n]+)"',dom);assert len(uncertainty)==13
for label in uncertainty:assert label.rsplit(' ',1)[1] in by_id
for text in ['New execution disabled in this demo','156','14 / 15','HPI is optional','Expanded ICU · 156 source records','Possible meaning — unconfirmed','What prevents confirmation','Patient-level relationship: not established','No treatment recommendation','The echo is recorded at 08:00','treatment response remain unconfirmed']:assert text in dom,text
capture=json.loads((p/'capture-correspondence.json').read_text());assert sha((p/'original/patient-summary-dom.txt').read_bytes())==capture['same_summary_sha256']
inspector=(p/'original/noradrenaline-inspector-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
event=by_id['fs-N-CHANGE']['fact'];delivery=event['action']['delivery'];weight=by_id['fs-WEIGHT']['fact'];pump=by_id['fs-PUMP-RATE-N-CHANGE']['fact']
assert event['revision']==weight['revision']==pump['revision']=='1'
assert delivery['dosing_weight']=={'kind':weight['kind'],'id':weight['id'],'version':weight['revision']}
assert any(a['role']=='delivery' and a['status']=='resolved' and a['exact']=={'kind':pump['kind'],'id':pump['id'],'version':pump['revision']} for a in event['associations'])
for text in ['fs-N-CHANGE / 1',event['occurred']['source_timestamp'],delivery['rate']['value']+' '+delivery['rate']['unit']['raw'],delivery['concentration']['value']+' '+delivery['concentration']['unit']['raw'],weight['recorded_amount']['value']+' '+weight['recorded_amount']['unit']['raw']+' · source fs-WEIGHT / 1',pump['recorded_amount']['value']+' '+pump['recorded_amount']['unit']['raw']+' · fs-PUMP-RATE-N-CHANGE / 1',delivery['route']['raw_display'],delivery['pump']['raw_display'],delivery['channel']['raw_display'],delivery['infusion']['raw_display'],'Delivered rate: unresolved · mcg/min','Delivered concentration: unresolved · mg/mL','No continuous exposure, dose conversion or treatment effect is inferred','Orders and preparations do not establish administration']:assert text in inspector,text
assert (p/'original/patient-summary.jpg').read_bytes().startswith(b'\xff\xd8\xff')
print(json.dumps({'result':'PASS','application':identity['head'],'original_captures':3,'reused_reference_fact_digests':156,'authored_controls':authored,'summary_controls':summary,'uncertainty_control_references':13,'noradrenaline_revision_and_recorded_delivery_support':'exact','screenshot_format':'JPEG/.jpg match','lossless_text_mirrors':len(mirrors),'boundary':'Captured DOM/screenshot correspondence with reused earlier API data. No fresh API/DB/network capture, application tests, independent live review or clinical validation.'},indent=2))
