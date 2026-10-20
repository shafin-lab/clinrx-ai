from pathlib import Path
import subprocess,json,time,hashlib,os,shutil,datetime
repo=Path.cwd();out=repo.parent/'rf2-fluid-chart-fc1-validation';evidence=out/'evidence'
changed=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+['frontend/tests/rf2TypedTiming.test.tsx','frontend/tests/fixtures/rf2-fc1-timing.json']
sha={n:hashlib.sha256((repo/n).read_bytes()).hexdigest() for n in sorted(set(changed))}
env={k:v for k,v in os.environ.items() if not k.startswith('VITE_')}
def run(name,args,flags=None):
 assert not (evidence/(name+'.log')).exists();start=time.monotonic();r=subprocess.run(args,env={**env,**(flags or {})},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (evidence/(name+'.log')).write_bytes(r.stdout);(evidence/(name+'.json')).write_text(json.dumps({'command':args,'exit_code':r.returncode,'seconds':time.monotonic()-start,'source_sha256':sha,'vite_flags':flags or {},'node':subprocess.check_output(['node','--version'],text=True).strip(),'npm':subprocess.check_output(['npm','--version'],text=True).strip(),'scope':'frontend/component/build only; no live services/database/browser or installation'},indent=2)+'\n');print(name,r.returncode,r.stdout.decode()[-1200:],flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('final-typecheck',['npm','run','typecheck','--prefix','frontend'])
run('final-focused',['npm','test','--prefix','frontend','--','--configLoader','runner','--no-cache','--maxWorkers=2','tests/rf2TypedTiming.test.tsx','tests/rf2FluidChart.test.tsx','tests/rf2.test.tsx','tests/rf2SourceReview.test.tsx','tests/rf2HandoverRace.test.tsx','tests/rf2.integration.test.tsx'])
run('default-build',['npm','run','build','--prefix','frontend','--','--configLoader','runner']);shutil.copytree(repo/'frontend/dist',out/'default-build')
run('rf2-build',['npm','run','build','--prefix','frontend','--','--configLoader','runner'],{'VITE_SYNTHETIC_HOSTED':'true','VITE_SYNTHETIC_AUTHORING':'true','VITE_SYNTHETIC_RF1':'true','VITE_SYNTHETIC_RF2':'true'});shutil.copytree(repo/'frontend/dist',out/'rf2-build')
for n,h in sha.items():assert hashlib.sha256((repo/n).read_bytes()).hexdigest()==h
print('Final tested source unchanged; no installation.')
