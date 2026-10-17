import sys,subprocess,time,json,os
from pathlib import Path
out=Path(__file__).resolve().parent
name=sys.argv[1];command=sys.argv[2:];env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')}
start=time.time()
with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
meta={'command':command,'cwd':str(Path.cwd()),'started_unix':start,'duration_seconds':round(time.time()-start,2),'exit_code':r.returncode,'docker_config':'dedicated test configuration; no user registry credentials'}
(out/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));print((out/(name+'.log')).read_text()[-2300:]);sys.exit(r.returncode)
