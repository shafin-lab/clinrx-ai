"""Run the comprehensive synthetic demo on loopback with new execution gated."""
import argparse,json,os,secrets,socket,subprocess,sys,tempfile,time,urllib.request,urllib.parse
from pathlib import Path
from app.demo.comprehensive import bootstrap
from app.persistence.database import create_database

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--api-port',type=int,default=8766)
    parser.add_argument('--web-port',type=int,default=5179)
    parser.add_argument('--flowsheet',action='store_true',help='use an opt-in fictional ICU sequence in a fresh database')
    args=parser.parse_args()
    if args.api_port==args.web_port or any(p<1024 or p>65535 for p in (args.api_port,args.web_port)):
        parser.error('choose two distinct unprivileged local ports')
    for port in (args.api_port,args.web_port):
        try:
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        except OSError:parser.error('requested port is occupied; choose another port')
    directory=args.directory or Path(tempfile.mkdtemp(prefix='clinrx-comprehensive-'))
    if not directory.is_absolute():parser.error('directory must be absolute')
    directory.mkdir(parents=True,exist_ok=True);database=directory/'synthetic.sqlite3'
    if database.exists():parser.error('database already exists; choose a fresh directory (no files are overwritten)')
    engine=create_database(database)
    try:
        if args.flowsheet:
            from app.demo.icu_flowsheet import bootstrap as flowsheet_bootstrap
            manifest=flowsheet_bootstrap(engine)
        else:manifest=bootstrap(engine)
    finally:engine.dispose()
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    repo=Path(__file__).resolve().parents[1];origin=f'http://127.0.0.1:{args.web_port}';base=f'http://127.0.0.1:{args.api_port}'
    env={**os.environ,'PYTHONPATH':str(repo/'backend'),'PYTHONDONTWRITEBYTECODE':'1',
        'CLINRX_DATABASE_PATH':str(database),'CLINRX_ENVIRONMENT':'local_synthetic_demo',
        'CLINRX_API_HOST':'127.0.0.1','CLINRX_API_PORT':str(args.api_port),'CLINRX_ALLOWED_DEV_ORIGINS':origin,
        'CLINRX_ENVELOPE_SIGNING_KEY':secrets.token_hex(32),'CLINRX_CLOCK_MODE':'historical_simulation',
        'CLINRX_SIMULATION_AT':manifest['simulation_at']}
    processes=[];logs=[]
    try:
        for name,command,cwd,settings in (
            ('api',[sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(args.api_port)],repo,env),
            ('frontend',['npm','run','dev','--','--host','127.0.0.1','--port',str(args.web_port),'--strictPort'],repo/'frontend',
                {**os.environ,'VITE_API_BASE_URL':base,'VITE_REVIEW_START':manifest['review_start'],'VITE_REVIEW_END':manifest['review_end'],
                 'VITE_RELEASED_EXAMPLE':manifest['released_example'],'VITE_WITHHELD_EXAMPLE':manifest['withheld_example']})):
            log=(directory/(name+'.log')).open('w');logs.append(log)
            process=subprocess.Popen(command,cwd=cwd,env=settings,stdout=log,stderr=subprocess.STDOUT);processes.append(process)
            url=base+'/health' if name=='api' else origin
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError(name+' stopped; inspect its local log')
                try:
                    with urllib.request.urlopen(url,timeout=1) as response:
                        if response.status==200:break
                except OSError:time.sleep(.1)
            else:raise RuntimeError(name+' did not become ready')
        query=urllib.parse.urlencode({k:manifest[k] for k in ('review_start','review_end')})
        with urllib.request.urlopen(base+'/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3?'+query) as response:
            if json.load(response)['execution_enabled'] is not False:raise RuntimeError('expected closed execution gate')
        print('Comprehensive synthetic demo: '+origin+'\nNew execution gate: CLOSED\nDisposable data and logs: '+str(directory)+'\nPress Ctrl+C to stop both local servers.',flush=True)
        while all(p.poll() is None for p in processes):time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for log in logs:log.close()
if __name__=='__main__':main()
