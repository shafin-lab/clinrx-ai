"""Build and run a separate disposable evidence-entry workspace on IPv4 loopback."""
import argparse,json,os,secrets,socket,subprocess,sys,tempfile
from pathlib import Path
from app.demo.icu_flowsheet import bootstrap
from app.persistence.database import create_database

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--port',type=int,default=5185)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('choose an unprivileged local port')
    with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
    root=args.directory or Path(tempfile.mkdtemp(prefix='clinrx-evidence-entry-'))
    if not root.is_absolute():parser.error('absolute directory required')
    root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):parser.error('fresh empty directory required; no evidence is overwritten')
    database=root/'synthetic.sqlite3';engine=create_database(database)
    try:manifest=bootstrap(engine)
    finally:engine.dispose()
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    repo=Path(__file__).resolve().parents[1];origin=f'http://127.0.0.1:{args.port}'
    env={**os.environ,'PYTHONPATH':str(repo/'backend'),'PYTHONDONTWRITEBYTECODE':'1',
        'VITE_SYNTHETIC_HOSTED':'true','VITE_SYNTHETIC_AUTHORING':'true',
        'VITE_PATIENT_ID':'synthetic-p1','VITE_ENCOUNTER_ID':'synthetic-e1',
        'VITE_REVIEW_START':manifest['review_start'],'VITE_REVIEW_END':manifest['review_end'],
        'CLINRX_AUTHORING_DATABASE':str(database),'CLINRX_AUTHORING_FRONTEND':str(root/'frontend'),
        'CLINRX_AUTHORING_ORIGIN':origin}
    with (root/'build.log').open('w') as log:
        subprocess.run(['npm','run','build','--','--outDir',str(root/'frontend')],cwd=repo/'frontend',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(f'Local consolidated patient workspace: {origin}\nClinical execution: DISABLED\nDisposable database and logs: {root}\nAccepted read-only Docker demo is unchanged.',flush=True)
    subprocess.run([sys.executable,'-m','uvicorn','app.demo.authoring:from_environment','--factory','--host','127.0.0.1','--port',str(args.port),'--workers','1'],cwd=repo,env=env,check=True)
if __name__=='__main__':main()
