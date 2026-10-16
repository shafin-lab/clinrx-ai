"""Generate legitimate HPI/oxygen ID collision states through the gated real API."""
import copy,hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from app.demo.comprehensive import bootstrap,replace
from app.demo.circulatory import facts,TARGET,SIMULATION_AT
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.api.config import APIConfig
from app.main import create_app

def fixture():
    with TemporaryDirectory() as directory:
        path=Path(directory)/'synthetic.sqlite3';engine=create_database(path)
        try:
            manifest=bootstrap(engine)
            hpi=replace(next(f for f in facts() if f.kind=='circulatory_device_prediction'),id='m7-ABG-PH')
            with transaction(engine) as repo:repo.append_fact(hpi,target=TARGET)
            config=APIConfig(database_path=path,environment='test',envelope_signing_key='b7'*32,clock_mode='historical_simulation',simulation_at=SIMULATION_AT)
            with TestClient(create_app(config,engine=engine)) as client:
                response=client.get('/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')});response.raise_for_status();state=response.json()
            assert state['execution_enabled'] is False
            result={}
            for order in ('first','last'):
                raw=copy.deepcopy(state);items=raw['assembly']['snapshot']['items'];hpi=next(i for i in items if i['fact']['kind']=='circulatory_device_prediction');others=[i for i in items if i is not hpi]
                raw['assembly']['snapshot']['items']=[hpi,*others] if order=='first' else [*others,hpi]
                raw['assembly_digest']=hashlib.sha256(json.dumps(raw['assembly'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
                raw['state_context']='fixture.hpi-collision-'+order;result[order]=raw
            return result
        finally:engine.dispose()

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/authoredCaseHpiCollision.json'
    path.write_text(json.dumps(fixture(),indent=2)+'\n')
