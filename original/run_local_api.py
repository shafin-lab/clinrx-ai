import os,secrets,sqlite3
from pathlib import Path
source=Path('/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/hemodynamics-complete-final-local-run/synthetic.sqlite3')
target=Path('/tmp/clinrx-authored-checks/demo.sqlite3')
assert not target.exists()
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as original,sqlite3.connect(target) as copy:original.backup(copy)
os.environ.update(CLINRX_DATABASE_PATH=str(target),CLINRX_ENVIRONMENT='local_synthetic_demo',CLINRX_API_HOST='127.0.0.1',CLINRX_API_PORT='8766',CLINRX_ALLOWED_DEV_ORIGINS='http://127.0.0.1:5179',CLINRX_ENVELOPE_SIGNING_KEY=secrets.token_hex(32),CLINRX_CLOCK_MODE='historical_simulation',CLINRX_SIMULATION_AT='2026-10-08T12:01:00+00:00')
os.execv('/Users/mohammedshafiqshajahan/Documents/clinrx-ai/backend/venv/bin/python',['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8766'])
