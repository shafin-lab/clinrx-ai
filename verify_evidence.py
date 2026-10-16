"""Data-only verification. No app imports, network, execution or database writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parent
load=lambda p:json.loads((ROOT/p).read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()
if (ROOT/'SHA256SUMS.json').exists():
 manifest=load('SHA256SUMS.json')
 assert set(manifest)=={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'SHA256SUMS.json'}
 for name,h in manifest.items():assert sha((ROOT/name).read_bytes())==h,name
state=load('publication-state.json');items=state['assembly']['snapshot']['items'];scope=state['assembly']['request']['scope'];cutoff=scope['repository_cutoff']
assert state['execution_enabled'] is False and len(items)==41
assert len({i['fact']['kind'] for i in items})==14
assert not any(i['fact']['id']=='m7-HPI' for i in items)
with sqlite3.connect('file:'+str(ROOT/'synthetic.sqlite3')+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 rows={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in names}
 assert json.loads(json.dumps(rows))==load('raw-row-arrays.json')
 exports=load('readable-tables.json')
 for n in names:
  assert exports[n]['columns']==[r[1] for r in db.execute('PRAGMA table_info("'+n+'")')]
  assert exports[n]['rows']==json.loads(json.dumps(rows[n]))
 digest=sha(canonical(rows));assert digest==load('original/database-check.json')['logical_all_table_sha256']=='91ed2b1b40f44294d65788ea26deedfd487b2a552d58de9665d0eb366016773c'
 stored={(r[1],r[2],r[3]):r for r in rows['fact_revision']}
 for i in items:
  f=i['fact'];r=stored[(f['kind'],f['id'],f['revision'])];m=i['ingestion']
  assert f==json.loads(r[7]) and i['expected_digest']==sha(r[7].encode())
  assert f['binding']['target']['patient_id']==scope['patient_id'] and f['binding']['target']['encounter_id']==scope['encounter_id']
  assert m['repository_id']==cutoff['repository_id'] and m['ingestion_sequence']==r[0]<=cutoff['fact_watermark']
  assert datetime.fromisoformat(m['ingested_at'].replace('Z','+00:00'))==datetime.fromisoformat(r[8].replace('Z','+00:00'))
 assert len(rows['circulatory_execution'])==2
 for r in rows['circulatory_execution']:assert sha(r[5].encode())==r[3]
dom=(ROOT/'expanded-explanation-dom.txt').read_text()
controls=list(re.finditer(r'^\s*- button "Explain source ([^"]+)":',dom,re.M))
expected={i['fact']['id']:i for i in items if i['fact']['kind'] in {'circulatory_oxygen','circulatory_cardiac','circulatory_pressure','circulatory_echo'}}
assert len(controls)==len(expected)==30
seen=set()
for n,m in enumerate(controls):
 id=m.group(1).rsplit(' ',1)[-1];assert id in expected and id not in seen;seen.add(id)
 block=dom[m.end():controls[n+1].start() if n+1<len(controls) else len(dom)]
 i=expected[id];f=i['fact'];r=f['result'];q=r.get('quantity')
 assert id+' / '+f['revision'] in block
 if q:assert q['value'] in block and ('(unit: 1)' if q['unit']['raw']=='1' else q['unit']['raw']) in block,id
 elif r['result_type']=='qualitative':assert r['finding']['raw_display'] in block,id
 elif r['result_type']=='missing':assert 'Not established' in block,id
 assert 'Quality: '+f['acquisition']['quality']['status'].replace('_',' ') in block,id
 assert i['inclusion'].replace('_',' ') in block,id
assert seen==set(expected)
for text in ['Patient-level relationship: not established','3 of 3 evidence streams','Recorded quality: unknown','Sample context not recorded','RVOT obstruction not documented','New execution disabled in this demo']:
 assert text in dom,text
abg=(ROOT/'original/abg-source-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for text in ['m7-ABG-PACO2 / 1','48.0 mmHg','synthetic-arterial-sample-1','40 %']:assert text in abg,text
picco=(ROOT/'original/picco-uncertainty-dom.txt').read_text().split('complementary "Selected source evidence"')[1]
for text in ['m7-PICCO-CO / 1','4.60 L/min','definition: unknown']:assert text in picco,text
checks={n:load('original/'+n+'.json')['exit_code'] for n in ['frontend','typecheck','build','hosted-build','diff']};assert all(v==0 for v in checks.values())
assert '461 passed (461)' in (ROOT/'original/frontend.log').read_text()
summary={'scope':'data-only captured-evidence verification, not independent live execution','tables_matched':len(names),'fact_revisions':len(rows['fact_revision']),'api_items_verified':len(items),'explanation_source_controls_verified':len(seen),'retained_receipts':2,'row_commitment':digest,'gate_disabled_in_state_and_dom':True,'local_check_exit_codes':checks,'manifest':'verified when present'}
(ROOT/'verification-results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
