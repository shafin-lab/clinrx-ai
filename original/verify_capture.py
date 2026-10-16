"""Read-only captured flowsheet correspondence checks; no application imports."""
from pathlib import Path
import json,re,hashlib,sqlite3
p=Path(__file__).resolve().parent
state=json.loads((p/'live-state-redacted.json').read_text());items=state['assembly']['snapshot']['items'];assert state['execution_enabled'] is False
with sqlite3.connect('file:'+str(p/'synthetic.sqlite3')+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 rows=db.execute('SELECT * FROM fact_revision ORDER BY rowid').fetchall();stored={(r[1],r[2],r[3]):r for r in rows}
 for i in items:
  f=i['fact'];r=stored[(f['kind'],f['id'],f['revision'])]
  assert json.loads(r[7])==f and hashlib.sha256(r[7].encode()).hexdigest()==i['expected_digest']
dom=(p/'flowsheet-dom.txt').read_text();times=re.findall(r'columnheader "(2026-10-08 [0-9:]+)"',dom);times=[t.replace(' ','T')+'Z' for t in times];assert len(times)==12
by_id={i['fact']['id']:i for i in items};seen={};cell=-1
for line in dom.splitlines():
 if re.match(r"^\s*- ['\"]?row ",line):cell=-1
 if re.match(r'^\s*- cell(?: |$)',line):cell+=1
 m=re.search(r'button "Chart source ([^ ]+) revision ([^"]+)"',line)
 if m:
  id,rev=m.groups();assert id not in seen and 0<=cell<len(times)
  i=by_id[id];f=i['fact'];assert f['revision']==rev and i['inclusion']=='in_window'
  t=f.get('collected',f.get('occurred',{}));assert t['source_timestamp'].replace('+00:00','Z')==times[cell]
  seen[id]=times[cell]
assert len(seen)==150
for id in ['m7-CONTEXT-CO','m7-UNPLACED']:assert id not in seen and id in dom
assert 'New execution disabled in this demo' in dom
history=(p/'urine-history-dom.txt').read_text();assert '1 retained revision at this cutoff' in history and 'fs-IO-output_urine-15 / 1' in history
co=(p/'suspect-co-dom.txt').read_text().split('complementary "Selected source evidence"')[1];assert 'code: fs-CO-60 / 1' in co and 'definition: suspect' in co
assessment=(p/'assessment-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
assert 'code: fs-FLUID-ASSESSMENT / 1' in assessment and 'definition: unknown' in assessment
for id in ('m7-CO / 1','fs-FLUID-CHALLENGE / 1','fs-CO-15 / 1'):assert id in assessment
assert 'No response, change percentage or causal conclusion is calculated' in assessment
for name,sample in [('scvo2','central venous'),('svo2','mixed venous')]:
 assert 'definition: '+sample in (p/(name+'-dom.txt')).read_text().split('complementary "Selected source evidence"')[1]
ci=(p/'ci-context-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
assert 'definition: source calculated' in ci and '1.73 m2' in ci
infusion=(p/'dobutamine-inspector-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for value in ('3.0 mcg/kg/min','70 kg','2.52 mL/h','5 mg/mL','fs-D-CHANGE / 1'):assert value in infusion
assert 'previous possibilities are withheld' in (p/'summary-dom.txt').read_text()
result={'api_items_and_payload_digests':len(items),'placed_controls_with_exact_revision_and_source_column':len(seen),'source_time_columns':len(times),'off_axis_contextual_and_unplaced_records':2,'matching_interval_urine_history':True,'suspect_co_preserved':True,'execution_enabled':False,'scope':'implementation-produced captured-data verification, not independent browser or clinical acceptance'}
(p/'capture-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
