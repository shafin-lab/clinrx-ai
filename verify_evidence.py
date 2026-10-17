"""Portable data-only checks of original/supplementary packaged-browser captures."""
from pathlib import Path
from datetime import datetime
import json,hashlib,base64,re
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
m=json.loads((p/'SHA256SUMS.json').read_text())
for name,h in m.items():assert sha((p/name).read_bytes())==h,name
original=json.loads((p/'original/SHA256SUMS.json').read_text())
for name,h in original.items():assert sha((p/'original'/name).read_bytes())==h,name
mirrors=json.loads((p/'text-mirrors/index.json').read_text())
for name,indexpath in mirrors.items():
 index=json.loads((p/indexpath).read_text());chunks=[]
 for part in index['parts']:
  raw=(p/indexpath).parent.joinpath(part['file']).read_bytes();assert sha(raw)==part['sha256'];chunks.append(base64.b64decode(raw))
 data=b''.join(chunks);assert len(data)==index['bytes'] and sha(data)==index['sha256'] and data==(p/name).read_bytes()
expected=json.loads((p/'original/expected-image.json').read_text())
for name in ['original/container-inspect.json','supplement/container-inspect.json']:
 info=json.loads((p/name).read_text())
 assert info['Image']==expected['image_id'] and info['State']['Running'] is True
 assert info['HostConfig']['PortBindings']['8080/tcp']==[{'HostIp':'127.0.0.1','HostPort':'5183'}]
 assert not info['Mounts']
rows=json.loads((p/'original/rows-before-browser.json').read_text());assert len(rows)==12
for name in ['original/rows-after-browser.json','supplement/rows-after-history.json']:assert json.loads((p/name).read_text())==rows
assert len(rows['fact_revision'])==162 and len(rows['circulatory_execution'])==2
state=json.loads((p/'original/state-response.json').read_text());assert state['execution_enabled'] is False
assert sha(canon(state['assembly']))==state['assembly_digest']
items=state['assembly']['snapshot']['items'];assert len(items)==156
assert len({i['fact']['kind'] for i in items})==14 and all(i['fact']['kind']!='circulatory_device_prediction' for i in items)
scope=state['assembly']['snapshot']['scope'];cutoff=scope['repository_cutoff'];assert rows['repository_identity'][0][1]==cutoff['repository_id']
stored={(r[1],r[2],r[3]):r for r in rows['fact_revision']};by_id={i['fact']['id']:i for i in items};assert len(by_id)==len(items)
for item in items:
 f=item['fact'];r=stored[(f['kind'],f['id'],f['revision'])];meta=item['ingestion']
 assert json.loads(r[7])==f and sha(r[7].encode())==item['expected_digest']
 assert (r[4],r[5])==(scope['patient_id'],scope['encounter_id'])
 assert meta['repository_id']==cutoff['repository_id'] and meta['ingestion_sequence']==r[0]<=cutoff['fact_watermark'] and meta['payload_version']==r[6]
 assert datetime.fromisoformat(meta['ingested_at'])==datetime.fromisoformat(r[8])<=datetime.fromisoformat(cutoff['captured_at'])
for path,count in [('original/current-dom.txt',31),('supplement/ph-history-dom.txt',34)]:
 dom=(p/path).read_text();times=[x.replace(' ','T')+'Z' for x in re.findall(r'columnheader "(2026-10-08 [0-9:]+)"',dom)];assert len(times)==4
 seen=set();cell=-1
 for line in dom.splitlines():
  if re.match(r"^\s*- ['\"]?row ",line):cell=-1
  if re.match(r'^\s*- cell(?: |$)',line):cell+=1
  match=re.search(r'button "Chart source ([^ ]+) revision ([^"]+)"',line)
  if match:
   id,rev=match.groups();assert id not in seen and 0<=cell<4;seen.add(id)
   item=by_id[id];f=item['fact'];assert f['revision']==rev and item['inclusion']=='in_window'
   assert (f.get('collected') or f['occurred'])['source_timestamp'].replace('+00:00','Z')==times[cell]
 assert len(seen)==count,(path,len(seen))
 assert 'New execution disabled in this demo' in dom
history=(p/'supplement/ph-history-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for text in ['fs-PH-60 / 1','7.35 1','2026-10-08T09:00:00+00:00','1 retained revision at this cutoff','Original recorded assertion']:assert text in history,text
f=by_id['fs-PH-60']['fact'];assert f['sample_type']=='arterial' and f['blood_gas_context']['fio2']['value']=='40'
echo=(p/'original/current-dom.txt').read_text()
for text in ['Recorded production tag: source calculated','RVOT obstruction not documented','no invasive confirmation or PAH subtype established']:assert text in echo
for name in ['original/abg.jpg','original/echo.jpg','supplement/ph-history.jpg']:assert (p/name).read_bytes().startswith(b'\xff\xd8\xff')
assert (p/'supplement/browser-url.txt').read_text().startswith('http://127.0.0.1:5183/')
tables=json.loads((p/'readable-tables/index.json').read_text());assert set(tables)==set(rows)
for table,index in tables.items():
 exported=[json.loads((p/name).read_text()) for name in index['rows']]
 assert [x['raw_row'] for x in exported]==rows[table]
 for x in exported:
  assert x['named_columns']==dict(zip(index['columns'],x['raw_row']))
  if 'payload' in x['named_columns']:assert x['parsed_payload']==json.loads(x['named_columns']['payload'])
assert [json.loads((p/'readable-state'/name).read_text()) for name in json.loads((p/'readable-state/items-index.json').read_text())]==items
print(json.dumps({'result':'PASS','publication_manifest_entries':len(m),'original_manifest_entries':len(original),'source':expected['source'],'tree':expected['tree'],'same_image_loopback_only':True,'api_items_payload_digest_ingestion_matches':156,'populated_families':14,'tables_unchanged_before_after_and_supplement':12,'fact_revisions':162,'retained_receipts':2,'original_earlier_controls':31,'supplement_latest_controls':34,'exact_ph_history_visible':True,'screenshots':'JPEG bytes/.jpg match','large_artifact_text_mirrors':len(mirrors),'scope':'Implementation captured browser evidence and data-only recomputation; no complete network trace, fresh-visitor certification or independent Director execution'},indent=2))
