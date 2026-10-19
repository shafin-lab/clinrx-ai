from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi.testclient import TestClient
from app.demo.patient_state import bootstrap
from app.persistence.database import create_database
from app.demo.renal_fluid_entry_gateway import SyntheticRF2Gateway,RF2
from tests.test_renal_fluid_entry import draft,saved,pin,ORIGIN,post

def redact(v):
 if isinstance(v,dict):return {k:'TEST_REDACTED_CONTEXT' if k=='state_context' else redact(x) for k,x in v.items()}
 if isinstance(v,list):return [redact(x) for x in v]
 return v
with TemporaryDirectory() as t:
 p=Path(t);db=p/'db.sqlite3';e=create_database(db);bootstrap(e);e.dispose();f=p/'front';(f/'assets').mkdir(parents=True);(f/'index.html').write_text('synthetic')
 app=SyntheticRF2Gateway(db,f,'ac'*32,ORIGIN)
 with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',5000),headers={'Origin':ORIGIN}) as c:
  b=draft(c,'weight');w=saved(c,b);urine=draft(c);u=saved(c,urine);cat=c.get(RF2).json()
  note=draft(c);note['chart']=None;note['note']={'question':'Review kidney and fluid evidence','findings':'Recorded observations only','possibilities':'Patient-level relationship not established','gaps':'Source quality remains unknown','plan':'Unscheduled review','pins':[pin(w),pin(u)]};n=saved(c,note)
  cat=c.get(RF2).json();data=redact({'attribution':'Small synthetic real-API fixture for client/component tests, not a runtime acceptance capture; signed contexts redacted','catalog':cat,'weight_draft':b,'weight':w,'urine_draft':urine,'urine':u,'note_draft':note,'note':n})
  from copy import deepcopy
  from uuid import uuid4
  correction=deepcopy(b);correction.update(revision=str(uuid4()),predecessor=pin(w),reason='Weight transcription correction, not a new measurement');correction['chart']['amount']='71.0000';cw=saved(c,correction)
  note2=deepcopy(note);note2.update(id=str(uuid4()),revision=str(uuid4()));note2['note']['question']='Review corrected weight';note2['note']['pins']=[pin(cw),pin(u)];nn=saved(c,note2)
  data.update(redact({'corrected_weight':cw,'new_note':nn,'comparison_catalog':c.get(RF2).json()}))
  out=Path('frontend/tests/fixtures/rf2-api.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(data,indent=2)+'\n');print(out, out.stat().st_size)
