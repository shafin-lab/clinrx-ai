"""Generate synthetic browser test fixtures via the actual scoped HTTP lifecycle."""
import json
import tempfile
from pathlib import Path
from uuid import UUID
from fastapi.testclient import TestClient
from app.main import create_app
from app.api.config import APIConfig
from app.demo.circulatory import bootstrap,correct,manifest,SIMULATION_AT
from app.persistence.database import create_database

def fixtures():
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'synthetic.sqlite3';engine=create_database(path);bootstrap(engine)
        config=APIConfig(database_path=path,environment='test',envelope_signing_key='a9'*32,
            clock_mode='historical_simulation',simulation_at=SIMULATION_AT,circulatory_execution_enabled=True)
        p='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
        with TestClient(create_app(config,engine=engine)) as client:
            def check(response):
                if response.status_code!=200:raise RuntimeError('fixture HTTP operation failed')
                return response.json()
            state=check(client.get(p+'/patient-state-v3',params={k:manifest()[k] for k in ('review_start','review_end')}))
            body={'execution_id':str(UUID(int=77)),'state_context':state['state_context']}
            for field,id in [('pressure','m7-P'),('lactate','m7-L'),('vasopressor','m7-V')]:
                item=next(i for i in state['assembly']['snapshot']['items'] if i['fact']['id']==id);f=item['fact']
                body[field]={'reference':{'kind':f['kind'],'id':f['id'],'version':f['revision']},'expected_digest':item['expected_digest']}
            prepared=check(client.post(p+'/circulatory-review-preparations',json=body))
            released=check(client.post(p+'/circulatory-reviews',json={'command':prepared['command']}))
            body['execution_id']=str(UUID(int=78))
            prepared2=check(client.post(p+'/circulatory-review-preparations',json=body))
            correct(engine)
            withheld=check(client.post(p+'/circulatory-reviews',json={'command':prepared2['command']}))
            current=check(client.get(p+'/patient-state-v3',params={k:manifest()[k] for k in ('review_start','review_end')}))
            history=check(client.post(p+'/circulatory-evidence-history',json={'state_context':current['state_context'],'reference':body['pressure']['reference']}))
        engine.dispose()
    # Opaque placeholders, not retained signed commands or usable server contexts.
    state['state_context']='fixture.m7-state';prepared['command']='fixture.m7-command';prepared2['command']='fixture.m7-command-2'
    return dict(state=state,prepared=prepared,prepared2=prepared2,released=released,withheld=withheld,history=history)
if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/circulatory.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(fixtures(),indent=2)+'\n')
    print('Wrote synthetic M7 lifecycle fixtures with opaque command placeholders')
