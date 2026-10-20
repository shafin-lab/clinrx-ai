"""Run only this isolated harness's tests and retain raw exit/timing/source attribution."""
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import importlib.metadata
ROOT=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'final-focused'
folder=ROOT/'evidence'
if (folder/(name+'.log')).exists():raise SystemExit('Refusing to overwrite existing run evidence')
command=[sys.executable,'-m','pytest','tests','-q',f'--junitxml=evidence/{name}-junit.xml']
source={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and (p.suffix=='.py' or p.name=='schema.json') and 'evidence' not in p.parts and '__pycache__' not in p.parts}
env=dict(os.environ,RF2_HARNESS_CAPTURE_DIR=str(folder/(name+'-captures')))
start=time.monotonic()
with (folder/(name+'.log')).open('wb') as log:
 r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
meta={'command':command,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'python':sys.version,'platform':platform.platform(),'pytest':importlib.metadata.version('pytest'),'source_sha256':source,'scope':'isolated harness only; no application suite or live service','captures':'evidence/'+name+'-captures'}
(folder/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
print((folder/(name+'.log')).read_text())
raise SystemExit(r.returncode)
