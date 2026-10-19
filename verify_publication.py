from pathlib import Path
import hashlib,json,base64
r=Path(__file__).resolve().parent
def sha(d):return hashlib.sha256(d).hexdigest()
def oid(kind,d):return hashlib.sha1((kind+' '+str(len(d))+'\0').encode()+d).hexdigest()
def manifest(path,base):
 lines=(r/path).read_text().splitlines()
 for line in lines:
  h,name=line.split('  ',1);p=(base/name).resolve();assert p.is_relative_to(base.resolve()) and sha(p.read_bytes())==h,name
 return len(lines)
publication=manifest('SHA256SUMS',r);original=manifest('original/SHA256SUMS',r/'original')
for f in json.loads((r/'ARTIFACTS.json').read_text()):
 d=(r/f['path']).read_bytes();assert len(d)==f['bytes'] and oid('blob',d)==f['git_blob'],f['path']
mirrors=json.loads((r/'MIRRORS.json').read_text())
for m in mirrors:
 d=base64.b64decode(''.join((r/p).read_text() for p in m['parts']),validate=True);assert d==(r/m['original']).read_bytes() and sha(d)==m['sha256'] and oid('blob',d)==m['git_blob'] and len(d)==m['bytes']
s=json.loads((r/'SOURCE.json').read_text());raw=(r/'source-commit.txt').read_bytes();assert oid('commit',raw)==s['source'] and raw.startswith(('tree '+s['tree']+'\nparent '+s['parent']+'\n').encode())
entries=json.loads((r/'SOURCE-TREE.json').read_text());tree={};by_path={e['path']:e for e in entries}
for e in entries:
 node=tree;parts=e['path'].split('/')
 for p in parts[:-1]:node=node.setdefault(p,{})
 assert parts[-1] not in node;node[parts[-1]]=(e['mode'],e['oid'])
def build(node):
 d=b''
 for name,v in sorted(node.items(),key=lambda kv:kv[0].encode()+(b'/' if isinstance(kv[1],dict) else b'')):
  mode,h=('40000',build(v)) if isinstance(v,dict) else v
  d+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(h)
 return oid('tree',d)
assert build(tree)==s['tree']
for f in s['files']:
 d=(r/f['path']).read_bytes();assert sha(d)==f['sha256'] and oid('blob',d)==f['git_blob']==by_path[f['repository_path']]['oid']
for name in ['focused-final','full-frontend','typecheck','default-build','authoring-build']:assert json.loads((r/('original/'+name+'.json')).read_text())['exit_code']==0
assert '675 passed' in (r/'original/full-frontend.log').read_text() and '119 passed' in (r/'original/focused-final.log').read_text()
print(json.dumps({'result':'PASS','publication_hashes':publication,'original_hashes':original,'mirrors':len(mirrors),'mirror_parts':sum(len(m['parts']) for m in mirrors),'source':s['source'],'source_tree_recomputed':True,'tested_source_files':len(s['files'])},indent=2))
