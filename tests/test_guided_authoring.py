"""Generated frontend form records through real admission, serialized append and lookup."""
import copy,json
from pathlib import Path
import pytest
from tests.test_synthetic_authoring import workspace,seeded,ENTRY,rows

VECTORS=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/guidedEntries.json').read_text())

@pytest.mark.parametrize('vector',VECTORS,ids=lambda v:v['fact']['id'])
def test_guided_record_real_admission_append_exact_lookup_and_retained_receipts(workspace,vector):
    client,db,body,*_=workspace
    before=rows(db)
    body.update(fact=vector['fact'],predecessor_digest=None)
    preview=client.post(ENTRY+'/validate',json=body)
    assert preview.status_code==200,preview.text
    assert rows(db)==before
    saved=client.post(ENTRY,json=body)
    assert saved.status_code==200,saved.text
    payload=saved.json()
    assert payload['fact']==preview.json()['fact']
    assert payload['fact']['occurred']['source_timestamp']=='2026-10-08T09:15:00.123456Z'
    assert payload['fact']['binding']['verification']['status']=='unresolved'
    assert payload['fact']['available']['recorded']['status']=='not_recorded'
    after=rows(db)
    assert len(after['fact_revision'])==len(before['fact_revision'])+1
    assert after['fact_revision'][:-1]==before['fact_revision']
    for table in before:
        if table not in ('fact_revision','revision_link','sqlite_sequence'):
            assert after[table]==before[table]
    assert client.post(ENTRY+'/lookup',json=body).json()=={'status':'committed_match','evidence':payload}
    assert client.post(ENTRY,json=body).json()==payload
    assert rows(db)==after

@pytest.mark.parametrize('withdraw',[False,True])
def test_dependency_bearing_correction_and_withdrawal_preserve_inputs(workspace,withdraw):
    client,db,body,*_=workspace
    ref={'kind':'circulatory_pressure','id':'m7-P','version':'1'}
    edge={'target':ref,'relationship':'calculated_from','basis':[],'rationale':'Recorded dependency'}
    body['fact'].update(production='source_calculated',calculation_inputs=[ref])
    body['fact']['provenance'].update(upstream=[edge],lineage='incomplete',limitations=['Synthetic local correction; retained exact dependency'])
    if withdraw:body['fact']['record_status']='withdrawn'
    assert client.post(ENTRY+'/validate',json=body).status_code==200
    saved=client.post(ENTRY,json=body)
    assert saved.status_code==200,saved.text
    assert saved.json()['fact']['calculation_inputs']==[ref]
    assert saved.json()['fact']['provenance']['upstream']==[edge]
    before=rows(db)
    for upstream in ([],[{**edge,'target':{**ref,'version':'foreign'}}]):
        bad=copy.deepcopy(body);bad['fact']['revision']='invalid-dependency';bad['fact']['provenance']['upstream']=upstream
        assert client.post(ENTRY+'/validate',json=bad).status_code==422
        assert client.post(ENTRY,json=bad).status_code==422
        assert rows(db)==before
