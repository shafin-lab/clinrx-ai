import subprocess,os,json,time,sys,hashlib
from pathlib import Path
ROOT=Path('/Users/mohammedshafiqshajahan/Documents/clinrx-ai')
OUT=Path(__file__).resolve().parent
ENV={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'PYTHONDONTWRITEBYTECODE':'1'}
PY=str(ROOT/'backend/venv/bin/python')
checks={
 'backend':[(PY,'-m','pytest','-q','-p','no:cacheprovider','tests')],
 'frontend':[('npm','--prefix','frontend','test'),('npm','--prefix','frontend','run','typecheck'),('npm','--prefix','frontend','run','build')],
 'static':[(PY,'-m','pip','check'),(str(ROOT/'backend/venv/bin/alembic'),'-c','backend/alembic.ini','heads'),('git','diff','--check')]
}
name=sys.argv[1]
if name=='frontend-pinned':
 checks[name]=checks['frontend']+[('npm','--prefix','frontend','run','build')]
 ENV['PATH']='/Users/mohammedshafiqshajahan/.npm/_npx/cd797643f5f2e392/node_modules/.bin:'+ENV['PATH']
for n,command in enumerate(checks[name]):
 if name=='frontend-pinned' and n==3:ENV['VITE_SYNTHETIC_HOSTED']='true'
 start=time.time()
 with (OUT/f'{name}-{n}.log').open('w') as log:
  result=subprocess.run(command,cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT)
 metadata={'command':command,'cwd':str(ROOT),'exit_code':result.returncode,'duration_seconds':round(time.time()-start,2)}
 (OUT/f'{name}-{n}.json').write_text(json.dumps(metadata,indent=2)+'\n')
 print(json.dumps(metadata),flush=True)
 if result.returncode:sys.exit(result.returncode)
