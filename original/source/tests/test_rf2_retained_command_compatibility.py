"""Actual archived service producer against the corrected consumer, on isolated databases."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import hashlib
import pytest
from tests.test_renal_fluid_entry import ws, seed, draft, pin, post, saved
from tests.test_synthetic_hosting import rows


def old_service():
    source=Path(__file__).with_name('fixtures')/'rf2/producer_4429401.py.txt'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='9a2af0f641c4ac7e91ad36a8493816582344b60564b094eb8f94cc61bc3ec207'
    namespace={'__name__':'archived_rf2_4429401'}
    exec(compile(source.read_bytes(),str(source),'exec'),namespace)
    return namespace['RF2Service']


@pytest.mark.parametrize('changed_bound',[None,'end'])
def test_actual_old_interval_correction_lookup_retry_and_no_resurrection(ws,changed_bound):
    from app.demo.renal_fluid_entry_gateway import service
    c,db,app=ws
    original=draft(c)
    app.core.dependency_overrides[service]=lambda:old_service()(app.core.state.dependencies)
    first=saved(c,original)
    correction=deepcopy(original);correction.update(revision=str(uuid4()),actor='Different correcting clinician',recorded_at='2026-10-08T10:10:00Z',predecessor=pin(first),reason='Historical amount correction')
    correction['chart']['amount']='36.0000'
    if changed_bound:correction['chart'][changed_bound]='2026-10-08T09:46:00Z'
    retained=saved(c,correction)
    assert retained['fact']['recorded_interval']['provenance']['actor']==correction['actor']
    app.core.dependency_overrides.pop(service)
    # A new correction is constructed by the current consumer and remains current.
    next_body=deepcopy(correction);next_body.update(revision=str(uuid4()),actor='Current clinician',recorded_at='2026-10-08T10:20:00Z',predecessor=pin(retained));next_body['chart']['amount']='37.0000'
    terminal=saved(c,next_body);before=rows(db)
    for action in ('/lookup','/save'):
        response=post(c,action,correction);assert response.status_code==200,response.text
        value=response.json();assert value['evidence']['fact']==retained['fact']
        assert value['evidence']['superseded'] is True
        assert value['evidence']['terminal_reference']['version']==terminal['fact']['revision']
        assert rows(db)==before
    for field,value in [('actor','Wrong actor'),('recorded_at','2026-10-08T10:11:00Z'),('reason','Different reason')]:
        altered=deepcopy(correction);altered[field]=value
        for action in ('/lookup','/save'):assert post(c,action,altered).status_code==409
    altered=deepcopy(correction);altered['chart']['amount']='99'
    assert post(c,'/lookup',altered).status_code==409
    assert rows(db)==before
