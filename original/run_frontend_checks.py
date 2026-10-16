from pathlib import Path
import os,subprocess,json,time
root=Path('/Users/mohammedshafiqshajahan/Documents/clinrx-ai');out=Path(__file__).resolve().parent
env={**os.environ,'PATH':'/Users/mohammedshafiqshajahan/.npm/_npx/cd797643f5f2e392/node_modules/.bin:'+os.environ['PATH']}
for name,command,hosted in [('frontend',['npm','--prefix','frontend','test'],False),('typecheck',['npm','--prefix','frontend','run','typecheck'],False),('build',['npm','--prefix','frontend','run','build'],False),('hosted-build',['npm','--prefix','frontend','run','build'],True),('diff',['git','diff','--check'],False)]:
 settings={**env};settings.pop('VITE_SYNTHETIC_HOSTED',None)
 if hosted:settings['VITE_SYNTHETIC_HOSTED']='true'
 start=time.time()
 with (out/(name+'.log')).open('w') as log:result=subprocess.run(command,cwd=root,env=settings,stdout=log,stderr=subprocess.STDOUT)
 meta={'command':command,'cwd':str(root),'exit_code':result.returncode,'duration_seconds':round(time.time()-start,2),'hosted_build':hosted,'node':subprocess.check_output(['node','--version'],env=env,text=True).strip()}
 (out/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta),flush=True)
 if result.returncode:raise SystemExit(result.returncode)
