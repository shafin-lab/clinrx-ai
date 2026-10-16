"""Portable data-only checks for the overview publication; no application imports."""
from pathlib import Path
from datetime import datetime
import json,hashlib,re
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for name,h in json.loads((p/'SHA256SUMS.json').read_text()).items():assert sha((p/name).read_bytes())==h,name
for name,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/name).read_bytes())==h,name
identity=json.loads((p/'source-identity.json').read_text())
for name,h in identity['increment_files_sha256'].items():assert sha((p/'original/source'/name).read_bytes())==h,name
commands=json.loads((p/'final-validation/commands.json').read_text());assert len(commands)==4
assert all(r['exit_code']==0 and r['source']==identity['source'] and r['source_tree']==identity['tree'] for r in commands)
assert '523 passed' in (p/'final-validation/frontend-full.log').read_text()
rows=json.loads((p/'current-data/all-table-rows.json').read_text());assert len(rows)==12
assert sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())=='273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc'
assert len(rows['fact_revision'])==162 and len(rows['circulatory_execution'])==2
state=json.loads((p/'current-data/state-redacted.json').read_text());assert state['execution_enabled'] is False
scope=state['assembly_request']['scope'];cutoff=scope['repository_cutoff'];assert state['assembly']['request']==state['assembly_request'] and state['assembly']['snapshot']['scope']==scope
assert sha(canon(state['assembly']))==state['assembly_digest'];assert rows['repository_identity'][0][1]==cutoff['repository_id']
items=state['assembly']['snapshot']['items'];assert len(items)==156
stored={(r[1],r[2],r[3]):r for r in rows['fact_revision']};by_id={i['fact']['id']:i for i in items}
for item in items:
 f=item['fact'];r=stored[(f['kind'],f['id'],f['revision'])];meta=item['ingestion']
 assert json.loads(r[7])==f and sha(r[7].encode())==item['expected_digest']
 assert (r[4],r[5])==(scope['patient_id'],scope['encounter_id'])
 assert meta['repository_id']==cutoff['repository_id'] and meta['ingestion_sequence']==r[0]<=cutoff['fact_watermark'] and meta['payload_version']==r[6]
 assert datetime.fromisoformat(meta['ingested_at'])==datetime.fromisoformat(r[8])<=datetime.fromisoformat(cutoff['captured_at'])

def plotted(name,count,columns):
 dom=(p/'current-browser'/name).read_text();times=[t.replace(' ','T')+'Z' for t in re.findall(r'columnheader "(2026-10-08 [0-9:]+)"',dom)];assert len(times)==columns
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
 assert len(seen)==count;assert 'New execution disabled in this demo' in dom
 return seen
full=plotted('all-details-dom.txt',150,12);overview=plotted('all-overview-times-dom.txt',31,12);latest=plotted('combined-dom.txt',14,4)
assert set(latest)<=set(overview)<=set(full)
for id in ('fs-D-CHANGE','fs-D-PAUSE','fs-D-RESTART','fs-V-STOP','fs-BALANCE-TOTAL','fs-IO-output_urine-60','fs-LACTATE-60'):assert id in latest
layout=json.loads((p/'current-browser/layout.json').read_text());assert layout['documentWidth']==layout['viewport']['width']
assert len(layout['groups'])==3 and all(0<=g['top']<g['bottom']<=layout['viewport']['height'] for g in layout['groups'])
inspector=(p/'current-browser/source-inspector-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for text in ('fs-N-CHANGE / 1','7 mcg/min','70 kg','5.25 mL/h','Delivered rate: unresolved'):assert text in inspector
history=(p/'current-browser/source-history-dom.txt').read_text();assert '1 retained revision at this cutoff' in history and 'fs-N-CHANGE / 1' in history
print(json.dumps({'increment_source_files':len(identity['increment_files_sha256']),'frontend_tests':523,'api_payloads_and_ingestion_correspondences':len(items),'full_chart_controls':len(full),'all_time_overview_controls':len(overview),'latest_overview_controls':len(latest),'all_table_rows_unchanged':True,'three_groups_fit_observed_viewport':True,'execution_enabled':False,'result':'PASS','scope':'Implementation data-only checks; selected browser captures, not independent review or a complete action trace'},indent=2))
