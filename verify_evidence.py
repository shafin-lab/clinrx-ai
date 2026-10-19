from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def oid(kind,data):return hashlib.sha1((kind+' '+str(len(data))+'\0').encode()+data).hexdigest()
def check_manifest(base):
 lines=(base/'SHA256SUMS').read_text().splitlines()
 for line in lines:
  expected,name=line.split('  ',1)
  p=(base/name).resolve();assert p.is_relative_to(base.resolve()),name
  assert digest(p.read_bytes())==expected,name
 return len(lines)
n=check_manifest(root);original=check_manifest(root/'original')
index=json.loads((root/'ARTIFACTS.json').read_text())
for item in index:
 data=(root/item['path']).read_bytes()
 assert len(data)==item['bytes'] and digest(data)==item['sha256'] and oid('blob',data)==item['git_blob'],item['path']
m=json.loads((root/'SOURCE.json').read_text())
raw=(root/'source/commit.txt').read_bytes()
assert oid('commit',raw)==m['source']
assert raw.startswith(('tree '+m['tree']+'\nparent '+m['parent']+'\n').encode())
assert oid('commit',(root/'source/parent-commit.txt').read_bytes())==m['parent']
for key in ['source_file','parent_file']:
 item=m[key];assert oid('blob',(root/item['path']).read_bytes())==item['git_blob']
assert digest((root/m['source_file']['path']).read_bytes())==(root/'original/tested-file.sha256').read_text().split()[0]
print(json.dumps({'publication_hashes':n,'original_hashes':original,'artifact_blob_identities':len(index),'source':m['source'],'result':'PASS'},indent=2))
