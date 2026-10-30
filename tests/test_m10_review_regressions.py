"""Independent review regressions for canonical ownership and interpretation provenance."""
from copy import deepcopy
from uuid import uuid4
from test_m10_backend import case,catalog,draft,save,post,pin,correction


def pcc(repository):
    b=draft(repository,'haemostatic_medication_course')
    b['data'].update(product={'family':'pcc','preparation':'Four factor PCC','label':'Synthetic PCC','factor_basis':'factor IX'},amounts=[{'dimension':'dose','value':'1000','unit':'IU','basis':'factor IX'}],status='completed',promote_to_medication=True)
    return b


def test_promoted_course_cannot_be_unlinked_into_another_exposure(case):
    c,_=case;b=pcc(catalog(c)['repository']);s=save(c,b)
    changed=correction(b,s,promote_to_medication=False,completed_as=None,amounts=[{'dimension':'dose','value':'1500','unit':'IU','basis':'factor IX'}])
    assert post(c,'save',changed).status_code==409
    assert len(catalog(c)['medication_exposures'])==1
    changed['data']['promote_to_medication']=True
    corrected=save(c,changed)
    exposures=catalog(c)['medication_exposures'];assert len(exposures)==1
    assert exposures[0]['item']['fact']['administered_dose']['amount']['value']=='1500'
    assert corrected['fact']['data']['completed_as']['reference']['id']==s['fact']['data']['completed_as']['reference']['id']


def test_course_cannot_pin_another_delivery_as_its_completion(case):
    c,_=case;repo=catalog(c)['repository'];a=pcc(repo);first=save(c,a)
    b=pcc(repo);b['data'].update(promote_to_medication=False,completed_as=first['fact']['data']['completed_as'])
    assert post(c,'save',b).status_code==409


def test_preview_signing_key_survives_restart(tmp_path):
    from app.demo.transfusion_gateway import retained_signing_key
    path=tmp_path/'synthetic.sqlite3'
    a=retained_signing_key(path);b=retained_signing_key(path)
    assert a==b and len(a)>=32
    assert path.with_suffix('.m10-signing.key').stat().st_mode&0o077==0


def test_clauss_gate_requires_explicit_assay_and_fibrinogen_mapping(case):
    from test_laboratory_contract import report,component
    from app.persistence.repository import transaction
    from app.services.transfusion_service import digest
    from app.services.m10_profiles import device_profiles
    c,app=case;repo_id=catalog(c)['repository'];device=next(d for d in device_profiles() if d['id']=='teg6s_gh_hn')
    vet=draft(repo_id,'viscoelastic_report',{'title':'HN source','device':device['device'],'profile_id':device['id'],'profile_version':device['version'],'cartridge':device['configuration'],'run_id':'hn-1','specimen_id':'s1','report_status':'final','observations':[{'id':'cffh','assay':'CFFH','parameter':'MA','value':'10','unit':'mm','state':'final'}]});v=save(c,vet)
    raw=component('not-clauss-derived','Derived fibrinogen','1.4',unit='g/L',mapping='unknown').model_dump()
    raw.update(mapping_status='mapped',mapped_concept='fibrinogen',mapping_version='clinrx-shared-labs/2',assay={'namespace':'source.assay','code':'derived','raw_display':'Derived fibrinogen'})
    lab=report((raw,),fact_id='derived-fibrinogen')
    with transaction(app.core.state.dependencies.engine) as repository:repository.append_fact(lab,target=lab.binding.target)
    request={'repository':repo_id,'patient_id':'synthetic-p1','encounter_id':'synthetic-e1','cutoff':catalog(c)['cutoff']['fact_watermark'],'review_end':'2026-10-08T10:00:00Z','device_profile_id':device['id'],'protocol_profile_id':'teg6s_hn_cardiac_reference','context':{},'observations':[{'id':'cffh','source_ref':{**pin(v)['reference'],'digest':v['digest']}}],'laboratory':[{'id':'derived-fibrinogen/not-clauss-derived','parameter':'fibrinogen_clauss','component_id':'not-clauss-derived','source_ref':{**lab.reference.model_dump(),'digest':digest(lab)}}]}
    assert post(c,'evaluate',request).status_code==409


def test_completed_course_source_availability_does_not_become_transcription_time(case):
    c,_=case;b=pcc(catalog(c)['repository']);b['recorded_at']='2026-10-23T09:00:00Z'
    save(c,b)
    view=catalog(c);assert len(view['medication_exposures'])==1
    assert view['totals']['groups'][0]['known_subtotal']=='1000'


def test_promoted_course_can_retract_false_completion_without_second_exposure(case):
    c,_=case;b=pcc(catalog(c)['repository']);s=save(c,b)
    changed=correction(b,s,status='not_given',promote_to_medication=False,completed_as=None,amounts=[],missing_amount_reason='Original entry was made against wrong bag',reason='No dose was delivered')
    result=save(c,changed)
    assert result['fact']['data']['retracted_medication']['reference']['kind']=='medication_administration'
    view=catalog(c);assert view['medication_exposures']==[];assert view['totals']['groups']==[]
    assert len(view['retracted_medication_exposures'])==1
    assert view['retracted_medication_exposures'][0]['item']['fact']['conflict']=='unresolved'
    # A subsequent corrected actual delivery restores the same canonical owner.
    restored=correction(changed,result,status='completed',promote_to_medication=True,amounts=[{'dimension':'dose','value':'500','unit':'IU','basis':'factor IX'}],missing_amount_reason=None)
    restored_result=save(c,restored)
    assert restored_result['fact']['data']['completed_as']['reference']['id']==s['fact']['data']['completed_as']['reference']['id']
    assert len(catalog(c)['medication_exposures'])==1


def test_unknown_source_availability_cannot_promote_to_a_known_exposure(case):
    c,_=case;b=pcc(catalog(c)['repository']);b['available_at']=None
    assert post(c,'save',b).status_code==409
    b['data']['promote_to_medication']=False
    save(c,b);view=catalog(c)
    assert view['items']==[] and len(view['unknown_availability'])==1
    assert view['medication_exposures']==[]


def test_unknown_retraction_is_excluded_from_every_current_exposure_summary(case):
    c,app=case;b=pcc(catalog(c)['repository']);s=save(c,b)
    before=catalog(c)['cutoff']['fact_watermark']
    changed=correction(b,s,status='not_given',promote_to_medication=False,completed_as=None,amounts=[],missing_amount_reason='Incorrect original claim')
    changed['available_at']=None;save(c,changed)
    view=catalog(c);assert view['medication_exposures']==[]
    assert view['totals']['groups']==[]
    assert len(view['unknown_availability'])==1
    for summary in view['summaries'].values():assert summary['complete'] is False
    from app.persistence.repository import transaction
    from app.services.transfusion_service import TransfusionService
    with transaction(app.core.state.dependencies.engine) as repo:
        historical=TransfusionService(app.core.state.dependencies).catalog(repo,'2026-10-08T08:00:00Z','2026-10-08T10:00:00Z',before)
    assert len(historical['medication_exposures'])==1
    assert historical['totals']['groups'][0]['known_subtotal']=='1000'
    assert view['fluid_reconciliation']['complete'] is False


def test_unknown_delivery_cannot_make_other_periods_look_complete(case):
    c,_=case;b=draft(catalog(c)['repository']);b['available_at']=None;save(c,b)
    view=catalog(c)
    for summary in view['summaries'].values():
        assert summary['complete'] is False
        assert any('Availability unknown' in e['reason'] for e in summary['excluded'])

def test_explicit_cutoff_keeps_unknown_terminal_retraction_visible_and_holds_old_positive(case):
    from app.persistence.repository import transaction
    from app.services.transfusion_service import TransfusionService
    c,app=case;b=pcc(catalog(c)['repository']);s=save(c,b)
    changed=correction(b,s,status='not_given',promote_to_medication=False,completed_as=None,amounts=[],missing_amount_reason='Incorrect original claim')
    changed['available_at']=None;save(c,changed);cutoff=catalog(c)['cutoff']['fact_watermark']
    with transaction(app.core.state.dependencies.engine) as repo:
        view=TransfusionService(app.core.state.dependencies).catalog(repo,'2026-10-08T08:00:00Z','2026-10-08T10:00:00Z',cutoff)
    assert view['medication_exposures']==[]
    assert view['totals']['groups']==[]
    assert view['unknown_availability'][0]['fact']['revision']==changed['revision']
    for summary in view['summaries'].values():assert summary['complete'] is False
