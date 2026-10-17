"""Portable read-only verification of captured evidence, chunks and readable exports."""
from pathlib import Path
import json,hashlib,base64,subprocess,sys
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((p/'SHA256SUMS.json').read_text())
for name,h in m.items():assert sha((p/name).read_bytes())==h,name
r=subprocess.run([sys.executable,str(p/'original/verify_evidence.py')],capture_output=True,text=True)
assert r.returncode==0,r.stderr
original=json.loads(r.stdout);assert original['result']=='PASS'
mirrors=json.loads((p/'text-mirrors/index.json').read_text())
for name,indexpath in mirrors.items():
 index=json.loads((p/indexpath).read_text());chunks=[]
 for part in index['parts']:
  data=(p/indexpath).parent.joinpath(part['file']).read_bytes();assert sha(data)==part['sha256'];chunks.append(base64.b64decode(data,validate=False))
 raw=b''.join(chunks);assert len(raw)==index['bytes'] and sha(raw)==index['sha256']
 assert raw==(p/index['artifact']).read_bytes()
rows=json.loads((p/'original/rows-before.json').read_text());tables=json.loads((p/'readable-tables/index.json').read_text())
assert set(tables)==set(rows)
for table,index in tables.items():
 records=[json.loads((p/name).read_text()) for name in index['rows']]
 assert [x['raw_row'] for x in records]==rows[table]
 for x in records:
  assert x['named_columns']==dict(zip(index['columns'],x['raw_row']))
  if 'payload' in x['named_columns']:assert x['parsed_payload']==json.loads(x['named_columns']['payload'])
state=json.loads((p/'original/state-response.bin').read_bytes());names=json.loads((p/'readable-state/items-index.json').read_text())
assert [json.loads((p/'readable-state'/name).read_text()) for name in names]==state['assembly']['snapshot']['items']
print(json.dumps({'result':'PASS','publication_manifest_entries':len(m),'original_manifest_entries':original['manifest_entries'],'lossless_large_artifact_mirrors':len(mirrors),'readable_tables':len(tables),'readable_rows':sum(len(x['rows']) for x in tables.values()),'readable_api_items':len(names),'original_checks':original,'scope':'Implementation data-only recomputation of published raw captures; not independent Director review or new live execution'},indent=2))
