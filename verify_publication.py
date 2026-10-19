from pathlib import Path
import hashlib,json,base64,subprocess,sys,re
r=Path(__file__).resolve().parent
def sha(d):return hashlib.sha256(d).hexdigest()
def oid(kind,d):return hashlib.sha1((kind+' '+str(len(d))+'\0').encode()+d).hexdigest()
def manifest(name):
 lines=(r/name).read_text().splitlines()
 for line in lines:
  digest,name=line.split('  ',1);p=(r/name).resolve();assert p.is_relative_to(r.resolve()) and sha(p.read_bytes())==digest,name
 return len(lines)
publication=manifest('SHA256SUMS');originals=manifest('ORIGINAL-SHA256SUMS');index=json.loads((r/'ARTIFACTS.json').read_text())
for item in index:
 d=(r/item['path']).read_bytes();assert len(d)==item['bytes'] and sha(d)==item['sha256'] and oid('blob',d)==item['git_blob'],item['path']
mirrors=json.loads((r/'MIRRORS.json').read_text())
for m in mirrors:
 d=base64.b64decode(''.join((r/p).read_text() for p in m['parts']),validate=True)
 assert d==(r/m['original']).read_bytes() and len(d)==m['bytes'] and sha(d)==m['sha256'] and oid('blob',d)==m['git_blob'],m['original']
 if m['original'].endswith('.jpg'):assert d.startswith(b'\xff\xd8\xff')
source=json.loads((r/'SOURCE.json').read_text());raw=(r/'candidate-commit.txt').read_bytes()
assert oid('commit',raw)==source['source'] and raw.startswith(('tree '+source['tree']+'\nparent '+source['immediate_parent']+'\n').encode())
entries=json.loads((r/'SOURCE-TREE.json').read_text());by_path={e['path']:e for e in entries};tree={}
for e in entries:
 node=tree;parts=e['path'].split('/')
 for part in parts[:-1]:node=node.setdefault(part,{})
 assert parts[-1] not in node;node[parts[-1]]=(e['mode'],e['oid'])
def build(node):
 content=b''
 for name,v in sorted(node.items(),key=lambda item:item[0].encode()+ (b'/' if isinstance(item[1],dict) else b'')):
  mode,h=('40000',build(v)) if isinstance(v,dict) else v
  content+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(h)
 return oid('tree',content)
assert build(tree)==source['tree']
for f in source['source_files']:
 d=(r/f['path']).read_bytes();assert sha(d)==f['sha256'] and oid('blob',d)==f['git_blob']==by_path[f['repository_path']]['oid']
original_source=json.loads((r/'original/source.json').read_text())
for p,h in original_source['tested_source_hashes'].items():assert sha((r/'source'/p).read_bytes())==h
for p,h in original_source['build_files'].items():assert sha((r/'original/authoring-build'/p).read_bytes())==h
ci=json.loads((r/'original/ci-result.json').read_text());assert ci['headSha']==source['source'] and ci['conclusion']=='success' and all(j['conclusion']=='success' for j in ci['jobs'])
log=re.sub(r'\x1b\[[0-9;]*m','',(r/'original/ci-complete.log').read_text(encoding='utf-8-sig'))
assert '4302 passed' in log and '668 passed' in log
for job in ['backend','frontend']:assert any(line.startswith(job+'\tRecord checkout and environment\t') and source['source'] in line for line in log.splitlines())
journey=json.loads(subprocess.check_output([sys.executable,str(r/'original/verify_journey.py')]))
print(json.dumps({'publication_hashes':publication,'original_hashes':originals,'indexed_blobs':len(index),'mirrors':len(mirrors),'mirror_parts':sum(len(m['parts']) for m in mirrors),'source':source['source'],'source_tree_recomputed':True,'ci_exact_candidate':'success','journey':journey,'result':'PASS'},indent=2))
