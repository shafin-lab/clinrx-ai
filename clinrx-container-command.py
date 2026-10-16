import sys,subprocess,time,json,os
from pathlib import Path
out=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/synthetic-container-validation')
name=sys.argv[1];command=sys.argv[2:];env={**os.environ,'DOCKER_CONFIG':str(out/'docker-client')}
start=time.time()
with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
meta={'command':command,'started_unix':start,'duration_seconds':round(time.time()-start,2),'exit_code':r.returncode,'docker_config':'dedicated test configuration; no user credentials'}
(out/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));print((out/(name+'.log')).read_text()[-2500:]);sys.exit(r.returncode)
