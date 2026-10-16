"""Export the expanded synthetic read-only state via the actual API, without secrets."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from app.demo.comprehensive import bootstrap
from app.demo.circulatory import SIMULATION_AT
from app.api.config import APIConfig
from app.main import create_app
from app.persistence.database import create_database


def fixture():
    with TemporaryDirectory() as directory:
        path=Path(directory)/'synthetic.sqlite3'
        engine=create_database(path)
        try:
            manifest=bootstrap(engine)
            config=APIConfig(database_path=path,environment='test',envelope_signing_key='b7'*32,
                clock_mode='historical_simulation',simulation_at=SIMULATION_AT)
            with TestClient(create_app(config,engine=engine)) as client:
                reply=client.get('/api/v1/patients/synthetic-p1/encounters/synthetic-e1/patient-state-v3',
                    params={k:manifest[k] for k in ('review_start','review_end')})
                reply.raise_for_status()
                result=reply.json()
                result['state_context']='fixture.expanded-read-only-state'
                return result
        finally:engine.dispose()

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/comprehensive.json'
    path.write_text(json.dumps(fixture(),indent=2)+'\n')
