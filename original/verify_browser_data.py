from pathlib import Path
import json,sqlite3,hashlib,urllib.request
root=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6');v=root/'hemodynamics-consolidation-validation'
before=json.loads((v/'browser-before-rows.json').read_text())
def rows(path):
 with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
  integrity=db.execute('pragma integrity_check').fetchall()
  result={t:[list(x) for x in db.execute('SELECT * FROM "'+t+'" ORDER BY rowid')] for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 return result,integrity
after,integrity=rows(root/'hemodynamics-consolidation-local-run/synthetic.sqlite3');accepted,accepted_integrity=rows(root/'guided-entry-local-run/synthetic.sqlite3')
assert integrity==[('ok',)] and accepted_integrity==[('ok',)]
assert accepted==before
assert len(before['fact_revision'])==174 and len(after['fact_revision'])==176
assert after['fact_revision'][:174]==before['fact_revision']
assert after['revision_link'][:len(before['revision_link'])]==before['revision_link']
assert len(after['revision_link'])==len(before['revision_link'])+1
for table in before:
 if table not in ('fact_revision','revision_link','sqlite_sequence'):assert after[table]==before[table],table
assert before['sqlite_sequence']==[['fact_revision',174]] and after['sqlite_sequence']==[['fact_revision',176]]
new_rows=after['fact_revision'][-2:];correction,note=[json.loads(r[7]) for r in new_rows]
assert [r[0] for r in new_rows]==[175,176]
assert correction['revision']=='45797d66-cac9-4f83-9d40-45da73366753'
assert correction['supersedes']=={'kind':'circulatory_oxygen','id':'1c1f16d9-33d7-40fb-a94f-013a383c9bfc','version':'aeaca128-a674-4dfa-859a-9ab11d2a9368'}
predecessor=json.loads(next(r[7] for r in before['fact_revision'] if r[2]==correction['id'] and r[3]==correction['supersedes']['version']))
for field in ('occurred','available','blood_gas_context','sample_type','specimen','acquisition','binding','calculation_inputs','calculation_method'):assert correction[field]==predecessor[field],field
assert correction['result']['quantity']['value']=='7.3600'
assert note['id']=='a38d77a7-1aed-4e96-a05d-c467144154a2' and note['revision']=='1' and note['supersedes'] is None
ref={'kind':correction['kind'],'id':correction['id'],'version':correction['revision']}
assert any(a.get('exact')==ref for a in note['associations'])
assert json.dumps(ref,separators=(',',':')) in note['description']['raw_display']
digests=[hashlib.sha256(r[7].encode()).hexdigest() for r in new_rows]
assert digests==['c6cc831bb2061b2ca9213ff27d3a24c071f52e1f897ce087f8e3579711524271','22860c3e45f5d3da355d7ac0217d435815cd93aa2a3ca6d3a772750d57a2bf68']
health=urllib.request.urlopen('http://127.0.0.1:5193/health').read();(v/'health.json').write_bytes(health)
assert json.loads(health)['execution_enabled'] is False
(v/'browser-after-rows.json').write_text(json.dumps(after,indent=2)+'\n')
(v/'browser-new-records.json').write_text(json.dumps({'correction':correction,'note':note},indent=2)+'\n')
(v/'browser-data-verification.json').write_text(json.dumps({'integrity':integrity,'accepted_5191_integrity':accepted_integrity,'accepted_5191_rows_equal_before':True,'before_facts':174,'after_facts':176,'unchanged_prior_facts':174,'retained_receipts_unchanged':len(after['circulatory_execution']),'new_ingestions':[175,176],'new_payload_sha256':digests,'added_revision_links':after['revision_link'][len(before['revision_link']):],'all_other_tables_unchanged':True,'execution_enabled':False},indent=2)+'\n')
with sqlite3.connect('file:'+str(root/'hemodynamics-consolidation-local-run/synthetic.sqlite3')+'?mode=ro',uri=True) as src,sqlite3.connect(v/'browser-after.sqlite3') as dst:src.backup(dst)
print('PASS: 174 prior facts and two receipts unchanged; only correction, separate note, one revision link and sequence advance added. Accepted 5191 unchanged; execution disabled.')
