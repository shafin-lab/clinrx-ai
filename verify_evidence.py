"""Portable data-only evidence checks; no app execution, API access or DB writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parent
load=lambda path:json.loads((ROOT/path).read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':')).encode()
if (ROOT/'SHA256SUMS.json').exists():
 entries=load('SHA256SUMS.json')
 assert set(entries)=={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'SHA256SUMS.json'}
 for name,expected in entries.items():assert sha((ROOT/name).read_bytes())==expected,name
for name,expected in load('original/SHA256SUMS.json').items():assert sha((ROOT/'original'/name).read_bytes())==expected,name
state=load('publication-state.json');scope=state['assembly']['request']['scope'];cutoff=scope['repository_cutoff'];items=state['assembly']['snapshot']['items']
assert state['execution_enabled'] is False and len(items)==41
assert len({i['fact']['kind'] for i in items})==14 and not any(i['fact']['id']=='m7-HPI' for i in items)
with sqlite3.connect('file:'+str(ROOT/'synthetic.sqlite3')+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 rows={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in names}
 assert json.loads(json.dumps(rows))==load('raw-row-arrays.json')
 exports=load('readable-tables.json')
 for name in names:
  assert exports[name]['columns']==[r[1] for r in db.execute('PRAGMA table_info("'+name+'")')]
  assert exports[name]['rows']==json.loads(json.dumps(rows[name]))
 row_digest=sha(canonical(rows));assert row_digest==load('original/live-check.json')['rows_sha256']
 stored={(r[1],r[2],r[3]):r for r in rows['fact_revision']}
 for item in items:
  f=item['fact'];r=stored[(f['kind'],f['id'],f['revision'])]
  assert f==json.loads(r[7]) and item['expected_digest']==sha(r[7].encode())
  assert f['binding']['target']['patient_id']==scope['patient_id'] and f['binding']['target']['encounter_id']==scope['encounter_id']
  m=item['ingestion'];assert m['repository_id']==cutoff['repository_id'] and m['ingestion_sequence']==r[0]<=cutoff['fact_watermark']
  assert datetime.fromisoformat(m['ingested_at'].replace('Z','+00:00'))==datetime.fromisoformat(r[8].replace('Z','+00:00'))
 assert len(rows['circulatory_execution'])==2
 for row in rows['circulatory_execution']:assert sha(row[5].encode())==row[3]
# DOM is a captured browser representation, not an executable test or live action trace.
dom=(ROOT/'original/summary-dom.txt').read_text()
pattern=re.compile(r'^\s*- button "Open summary source ([^"]+)":',re.M)
controls=list(pattern.finditer(dom));assert len(controls)==33
kinds={'circulatory_oxygen','circulatory_cardiac','circulatory_pressure','circulatory_echo','circulatory_lactate','circulatory_perfusion','circulatory_vasoactive','circulatory_device_prediction'}
expected={i['fact']['id']:i for i in items if i['fact']['kind'] in kinds};assert len(expected)==33
captured=[]
for n,match in enumerate(controls):
 id=match.group(1).rsplit(' ',1)[-1];assert id in expected and id not in captured
 end=controls[n+1].start() if n+1<len(controls) else len(dom)
 block=dom[match.end():end];item=expected[id];fact=item['fact'];result=fact.get('result',{});quantity=result.get('quantity')
 assert fact['id']+' / '+fact['revision'] in block
 if quantity:
  # Verify exact value token inside the source button, separately from units.
  button=block.split('Inspect source ↗',1)[0]
  tokens=[]
  for line in button.splitlines():
   m=re.search(r'- (?:text|generic|strong): (.+)$',line)
   if m:
    raw=m.group(1)
    try:tokens.append(json.loads(raw) if raw.startswith('"') else raw)
    except json.JSONDecodeError:tokens.append(raw)
  assert quantity['value'] in tokens,(id,quantity['value'],tokens)
  unit=quantity['unit']['raw'];assert (('(unit: 1)' if unit=='1' else unit) in tokens),id
 elif result.get('result_type')=='qualitative':
  assert result['finding']['raw_display'] in block,id
 status=fact.get('acquisition',{}).get('quality',{}).get('status','not_recorded').replace('_',' ')
 assert 'Quality: '+status in block,id
 assert item['inclusion'].replace('_',' ') in block,id
 captured.append(id)
assert set(captured)==set(expected)
assert 'No combined diagnosis, score, treatment recommendation or new inference is generated.' in dom
assert 'Qualitative echo findings are source-report assertions, not directly measured diagnoses.' in dom
assert 'Recorded production tag: direct measurement.' in dom
assert 'Sample-time FiO₂: Not recorded' in dom and 'Sample-time FiO₂: 40 %' in dom
summary={'manifest':'verified when present','original_manifest':'passed','sqlite_integrity':'ok','readable_tables_matched':len(names),'api_facts_and_digests_matched':len(items),'captured_summary_sources_matched':len(captured),'summary_values_units_quality_and_placement':'matched captured DOM','source_revisions_matched':True,'retained_receipts':2,'execution_enabled':False,'row_digest_matches_original_check':row_digest,'scope':'captured-evidence verification, not independent live browser execution'}
(ROOT/'verification-results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
