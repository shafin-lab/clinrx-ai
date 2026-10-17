"""Portable read-only verification; does not execute the application."""
from pathlib import Path
import json,hashlib,base64,re
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
m=json.loads((p/'SHA256SUMS.json').read_text())
for name,h in m.items():assert sha((p/name).read_bytes())==h,name
for name,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/name).read_bytes())==h,name
mirrors=json.loads((p/'text-mirrors/index.json').read_text())
for name,indexpath in mirrors.items():
 index=json.loads((p/indexpath).read_text());parts=[]
 for part in index['parts']:
  raw=(p/indexpath).parent.joinpath(part['file']).read_bytes();assert sha(raw)==part['sha256'];parts.append(base64.b64decode(raw))
 raw=b''.join(parts);assert raw==(p/name).read_bytes() and len(raw)==index['bytes'] and sha(raw)==index['sha256']
expected=json.loads((p/'reference-data/expected-image.json').read_text());info=json.loads((p/'publication-time-container-inspect.json').read_text())
assert info['Image']==expected['image_id'] and info['State']['Running']
assert info['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5183'}]
state=json.loads((p/'reference-data/state-response.json').read_text());assert state['execution_enabled'] is False
assert sha(canon(state['assembly']))==state['assembly_digest']
items=state['assembly']['snapshot']['items'];assert len(items)==156
by_id={i['fact']['id']:i for i in items};assert len(by_id)==len(items)
for item in items:assert sha(canon(item['fact']))==item['expected_digest']
dom=(p/'original/current-dom.txt').read_text()
controls=list(re.finditer(r'button "Open summary source ([^"]+)":',dom));assert len(controls)==98
for n,match in enumerate(controls):
 id=match.group(1).rsplit(' ',1)[1];item=by_id[id];f=item['fact']
 body=dom[match.end():controls[n+1].start() if n+1<len(controls) else len(dom)]
 assert id+' / '+f['revision'] in body
 time=(f.get('collected') or f.get('occurred') or {}).get('source_timestamp') or 'Time not established'
 assert 'Source time: '+time in body
 assert item['inclusion'].replace('_',' ') in body
 quantity=(f.get('result') or {}).get('quantity')
 if quantity:assert quantity['value'] in body and quantity['unit']['raw'] in body
 finding=(f.get('result') or {}).get('finding')
 if finding:assert finding['raw_display'] in body
uncertainty=re.findall(r'button "Inspect uncertainty ([^"]+)"',dom);assert len(uncertainty)==13
for label in uncertainty:assert label.rsplit(' ',1)[1] in by_id
for text in ['Patient summary','156','14 / 15','New execution disabled in this demo','Patient-level relationship: not established','The previous possibilities are withheld','Nothing is automatically regenerated','9 cardiac-output records are present','Recorded quality: suspect','Recorded quality: unknown','no invasive confirmation or PAH subtype established','No cardiac output is calculated from VTI']:assert text in dom,text
assert (p/'original/explanation.jpg').read_bytes().startswith(b'\xff\xd8\xff')
print(json.dumps({'result':'PASS','publication_manifest_entries':len(m),'original_capture_files':2,'reference_api_items_digest_verified':156,'summary_controls_source_revision_time_value_correspondence':98,'uncertainty_controls_correspondence':13,'same_image_loopback_only':True,'withheld_authored_interpretation_visible':True,'combined_relationship_not_established':True,'screenshot_format':'JPEG/.jpg match','large_artifact_text_mirrors':len(mirrors),'scope':'Captured summary and reused reference API; not fresh API/database/network verification or independent Director execution'},indent=2))
