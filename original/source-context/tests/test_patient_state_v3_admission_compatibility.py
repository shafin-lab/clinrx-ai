"""Actual historical producers, current consumers, exact identities and receipts."""
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import pytest
from sqlalchemy import text
from app.persistence.database import create_database
from app.persistence.errors import StorageIntegrityError
from app.execution import patient_state_v3_execution as c, patient_state_v3_workflow as w
from test_patient_state_v3_workflow import clock, forbidden

ROOT=Path(__file__).resolve().parents[1]
VERSIONS=('a1680c455939099cec94c369a191da8ba0f6a211','fe3cb12933179153142df201dbdf0e9917fae6ed')


@pytest.fixture(scope='session',params=VERSIONS)
def historical_source(request,tmp_path_factory):
    root=tmp_path_factory.mktemp('historical-'+request.param[:7])
    fixtures=ROOT/'tests/fixtures/m7_timestamp_producers'
    archive=(fixtures/(request.param+'.tar.gz')).read_bytes()
    expected=json.loads((fixtures/'manifest.json').read_text())[request.param]
    assert hashlib.sha256(archive).hexdigest()==expected['sha256']
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        assert tar.pax_headers['comment']==request.param
        assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and not m.issym() for m in tar.getmembers())
        tar.extractall(root,filter='data')
    return root,request.param


PRODUCER=r'''
import json,sys
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
from sqlalchemy import event,text
from app.persistence.database import create_database
from test_persistence import migrate
from app.persistence.repository import transaction
from app.persistence.errors import TransactionCompletionUnknown
from app.execution import patient_state_v3_execution as c, patient_state_v3_workflow as w
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference
from test_persistence import patient,encounter
from test_patient_state_v3 import h,change,PROV,TARGET
from test_patient_state_v3_inference import inputs,selected
from test_patient_state_v3_persistence import save,revised
from test_patient_state_v3_workflow import clock
path,output,kind,phase=sys.argv[1:]
engine=create_database(path);migrate(engine)
with transaction(engine) as repo:
 repo.register_patient(patient());repo.register_encounter(encounter())
p,l,v=inputs()
def stamp(value):return h.ClinicalInstant(recorded={'status':'known','precision':'instant','value':value},clock='verified',clock_basis=PROV)
if kind=='iso':
 p=change(p,occurred=stamp(p.occurred.recorded.value.isoformat()))
 l=change(l,collected=stamp(l.collected.recorded.value.isoformat()))
 v=change(v,occurred=stamp(v.occurred.recorded.value.isoformat()))
elif kind=='bytes':
 p=change(p,occurred=stamp(b'2026-10-08T08:00:00.1234561+05:30'))
 v=change(v,occurred=stamp(b'2026-10-08T08:00:00.1234569+05:30'))
elif kind=='numeric':
 def number(token):
  raw='{"recorded":{"status":"known","precision":"instant","value":'+token+'},"clock":"verified","clock_basis":'+PROV.model_dump_json()+'}'
  return h.ClinicalInstant.model_validate_json(raw)
 p=change(p,occurred=number('1791426600.12345601'))
 v=change(v,occurred=number('1791426600.12345604'))
a,r=selected(engine,(p,l,v));i=build_circulatory_timing_inference(assembly=a,request=r)
cutoff=save(engine,i)
req=c.CirculatoryExecutionRequest(execution_id=uuid4(),target=c.GRANT_TARGET,actor=c.GRANT_ACTOR,
 inference_request=r,assembly_request=a.request,inference_cutoff=cutoff,
 expected_inference_digest=c.digest(i),requested_at=c.GRANT_WINDOW.start)
unknown=False
if phase=='withheld':save(engine,revised(p))
if phase=='uncertain_absent':
 def fail(conn):raise RuntimeError('synthetic commit failure')
 event.listen(engine,'commit',fail)
if phase=='uncertain_committed':
 owner=w.execution_transaction
 @contextmanager
 def uncertain(engine):
  with owner(engine) as tx:yield tx
  raise TransactionCompletionUnknown('synthetic response lost')
 w.execution_transaction=uncertain
if phase!='pending':
 try:w.execute_circulatory_review(engine,req,clock=clock)
 except TransactionCompletionUnknown:unknown=True
 finally:
  if phase=='uncertain_absent':event.remove(engine,'commit',fail)
with engine.connect() as conn:
 payload=conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one_or_none()
 facts=conn.execute(text('SELECT payload FROM fact_revision ORDER BY ingestion_sequence')).scalars().all()
Path(output).write_text(json.dumps({'request':req.model_dump(mode='json'),'receipt':payload,'facts':facts,'unknown':unknown,'statement':i.statement,'producer_module':h.__file__}))
engine.dispose()
'''


CASES=[('iso','pending'),('unknown','pending'),('numeric','pending'),('bytes','pending'),
 ('unknown','released'),('numeric','released'),('bytes','released'),('unknown','withheld'),('numeric','withheld'),
 ('numeric','uncertain_committed'),('unknown','uncertain_absent'),('iso','uncertain_absent')]


@pytest.mark.parametrize('kind,phase',CASES)
def test_actual_producer_current_consumer(historical_source,tmp_path,monkeypatch,kind,phase):
    source,sha=historical_source;database=tmp_path/'old.sqlite3';output=tmp_path/'old.json'
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(source/'backend')+os.pathsep+str(source/'tests')}
    result=subprocess.run([sys.executable,'-c',PRODUCER,str(database),str(output),kind,phase],cwd=source,env=env,text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    data=json.loads(output.read_text());assert str(source) in data['producer_module']
    if kind in ('numeric','bytes'):assert 'Pressure acquisition occurred at the initiation event.' in data['statement']
    request=c.CirculatoryExecutionRequest.model_validate(data['request']);original_request=request.model_dump_json()
    engine=create_database(database)
    try:
        def contents():
            with engine.connect() as conn:
                return conn.execute(text('SELECT payload FROM circulatory_execution')).scalar_one_or_none(),conn.execute(text('SELECT payload FROM fact_revision ORDER BY ingestion_sequence')).scalars().all()
        assert contents()==(data['receipt'],data['facts'])
        if data['receipt'] is not None:
            for name in ('_new_execution','_assemble','build_circulatory_timing_inference','_utc_now','assess_release','decide_release'):
                monkeypatch.setattr(w,name,forbidden)
            receipt=w.reconcile_circulatory_execution(engine,request).stored
            assert receipt is not None
            assert receipt.record.decision.outcome==('withheld' if phase=='withheld' else 'released')
            assert w.execute_circulatory_review(engine,request,clock=forbidden)==receipt
            engine.dispose()
            assert w.reconcile_circulatory_execution(engine,request).stored==receipt
        else:
            assert w.reconcile_circulatory_execution(engine,request).status=='absent'
            # Absence performs no retry. Only this explicit same-command call may execute.
            assert contents()[0] is None
            # These pre-policy producers have no approved eligibility version or
            # acquisition-specific applicability evidence. Even exact ISO pending
            # preparations require explicit source-backed re-preparation now.
            with pytest.raises(StorageIntegrityError) as caught:w.execute_circulatory_review(engine,request,clock=clock)
            assert str(caught.value)=='circulatory execution integrity failure'
            assert contents()[0] is None
        assert request.model_dump_json()==original_request
        assert contents()[1]==data['facts']
        if data['receipt'] is not None:assert contents()[0]==data['receipt']
        assert data['unknown']==phase.startswith('uncertain_')
    finally:engine.dispose()
