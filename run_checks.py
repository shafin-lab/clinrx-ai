import sys,subprocess,os,json,time
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-hosting-validation');out.mkdir(exist_ok=True)
repo=Path('/Users/mohammedshafiqshajahan/Documents/clinrx-ai')
name=sys.argv[1]
commands={'backend':([str(repo/'backend/venv/bin/python'),'-m','pytest','-q'],repo),
 'frontend':(['npm','test'],repo/'frontend'),'typecheck':(['npm','run','typecheck'],repo/'frontend'),
 'build':(['npm','run','build'],repo/'frontend'),
 'hosted-build':(['npm','run','build','--','--outDir',str(out/'hosted-dist'),'--emptyOutDir'],repo/'frontend')}
command,cwd=commands[name];env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(repo/'backend')}
if name=='hosted-build':env['VITE_SYNTHETIC_HOSTED']='true'
start=time.time()
with (out/(name+'.log')).open('w') as log:result=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
meta={'node':subprocess.check_output(['node','--version'],text=True).strip(),'npm':subprocess.check_output(['npm','--version'],text=True).strip(),'command':command,'cwd':str(cwd),'exit_code':result.returncode,'started_unix':start,'duration_seconds':round(time.time()-start,2),'hosted_build':name=='hosted-build'}
(out/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));print((out/(name+'.log')).read_text()[-2000:]);sys.exit(result.returncode)
