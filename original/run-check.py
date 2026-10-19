from pathlib import Path
import subprocess,sys,time,json,os
root=Path('/Users/mohammedshafiqshajahan/Documents/clinrx-ai')
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/hemodynamics-M1-correction-validation');out.mkdir(exist_ok=True)
name=sys.argv[1];command=sys.argv[2:];start=time.time()
env=os.environ.copy()
if name=='authoring-build':env['VITE_SYNTHETIC_AUTHORING']='true'
with (out/(name+'.log')).open('w') as f:
 p=subprocess.run(command,cwd=root/'frontend',env=env,stdout=f,stderr=subprocess.STDOUT)
result={'command':command,'exit_code':p.returncode,'elapsed_seconds':round(time.time()-start,2)}
(out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print((out/(name+'.log')).read_text()[-2200:]);sys.exit(p.returncode)
