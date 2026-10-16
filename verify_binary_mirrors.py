"""Reconstruct the exact existing artifacts from text chunks; no application imports."""
from pathlib import Path
import base64,hashlib,json,sqlite3,tempfile
p=Path(__file__).resolve().parent
results={}
for folder in sorted((p/'binary-mirrors').iterdir()):
 index=json.loads((folder/'index.json').read_text());parts=[]
 for entry in index['chunks']:
  raw=(folder/entry['file']).read_bytes();assert len(raw)==entry['bytes'];assert hashlib.sha256(raw).hexdigest()==entry['sha256'];parts.append(raw.strip())
 data=base64.b64decode(b''.join(parts),validate=True);assert len(data)==index['original_bytes'];assert hashlib.sha256(data).hexdigest()==index['original_sha256']
 result={'bytes':len(data),'sha256':index['original_sha256'],'chunks':len(parts),'exact_original_identity':True}
 if folder.name=='expanded-database':
  with tempfile.TemporaryDirectory() as directory:
   dbpath=Path(directory)/'reconstructed.sqlite3';dbpath.write_bytes(data)
   with sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    rows={name:[list(r) for r in db.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}
   assert rows==json.loads((p/'database-reference/raw-row-arrays.json').read_text())
   assert rows=={name:t['rows'] for name,t in json.loads((p/'database-reference/readable-tables.json').read_text()).items()}
   commitment=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert commitment=='273acbe17d027b1836fa893ebb980dcc333fa6d920defdd60f1b4096fbdc02cc'
   result.update(integrity='ok',tables=len(rows),fact_revisions=len(rows['fact_revision']),retained_receipts=len(rows['circulatory_execution']),exports_equal=True,row_commitment=commitment)
 else:
  assert data.startswith(b'\xff\xd8\xff');result['detected_format']='JPEG; original .png filename retained unchanged'
 results[folder.name]=result
print(json.dumps(results,indent=2))
