"""Disposable real-API fixture for F3 transport decoding; not browser evidence."""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from fastapi.testclient import TestClient
from app.demo.patient_state import bootstrap
from app.persistence.database import create_database
from app.demo.renal_fluid_entry_gateway import SyntheticRF2Gateway
from tests.test_renal_fluid_entry import draft,saved,pin,post,ORIGIN
from tests.test_rf2_review_corrections import note,reviewed

def redact(v):
    if isinstance(v,dict):return {k:'TEST_REDACTED_CONTEXT' if k=='state_context' else redact(x) for k,x in v.items()}
    if isinstance(v,list):return [redact(x) for x in v]
    return v

with TemporaryDirectory() as temp:
    root=Path(temp);db=root/'db.sqlite3';engine=create_database(db);bootstrap(engine);engine.dispose();front=root/'frontend';(front/'assets').mkdir(parents=True);(front/'index.html').write_text('synthetic')
    app=SyntheticRF2Gateway(db,front,'ab'*32,ORIGIN)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',1),headers={'Origin':ORIGIN}) as c:
        b=draft(c,'weight');original=saved(c,b);n=note(c,original)
        correction=deepcopy(b);correction.update(revision=str(uuid4()),predecessor=pin(original),reason='Synthetic source correction');correction['chart']['amount']='71.0000';successor=saved(c,correction)
        n=reviewed(c,n,True);validated=post(c,'/validate',n);assert validated.status_code==200,validated.text
        response=post(c,'/save',n);assert response.status_code==200,response.text
        payload=redact({'attribution':'Generated through actual disposable API/storage; not a browser capture; context tokens redacted','draft':n,'validated':validated.json(),'saved':response.json(),'catalog':c.get('/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-rf2').json()})
        out=Path('frontend/tests/fixtures/rf2-reviewed-api.json');out.write_text(json.dumps(payload,indent=2)+'\n');print(out,out.stat().st_size)
