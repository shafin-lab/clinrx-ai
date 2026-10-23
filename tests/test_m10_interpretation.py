from copy import deepcopy
import pytest
from app.services.m10_profiles import device_profiles, protocol_profiles
from app.services.m10_interpretation import interpret


def observation(assay, parameter, value, unit='mm', **kw):
    return dict(id=f'{assay}:{parameter}', assay=assay, parameter=parameter, value=value,
                unit=unit, status='final', qualifier='eq', sample_id='sample-1', run_id='run-1', **kw)


def payload():
    return dict(device_profile_id='teg6s_gh_lysis', protocol_profile_id='teg6s_trauma_reference',
                mode='synthetic_reference', context=dict(population='adult', setting='trauma',
                active_bleeding=True, clinically_significant_bleeding=True, evidence_current=True,
                discordant_evidence=False, anticoagulant_status='none', heparin_status='excluded'),
                observations=[observation('CK','R','11','min'), observation('CRT','MA','40'),
                observation('CFF','MA','10'), observation('CK','LY30','0','%')])


def test_registry_exact_cartridges():
    ds={p['id']:p for p in device_profiles()}
    assert len(ds)>=14
    def mask(pid): return {(c['assay'],p['name']) for c in ds[pid]['channels'] for p in c['parameters']}
    assert ('CK','LY30') not in mask('teg6s_gh')
    assert ('CK','LY30') in mask('teg6s_gh_lysis')
    assert ('CKH','LY30') in mask('teg6s_gh_hn')
    assert ('CK','LY30') not in mask('teg6s_gh_hn')
    assert ('CFFH','MA') in mask('teg6s_gh_hn')
    assert not any(a=='AA' for a,p in mask('teg6s_pm_adp'))
    assert any(a=='APTEM C' for a,p in mask('rotem_sigma_complete'))
    assert not any(a=='HEPTEM C' for a,p in mask('rotem_sigma_complete'))


def test_supported_products_and_no_wrong_platelet_inference():
    r=interpret(payload())
    assert {x['product'] for x in r['options']}=={'plasma','fibrinogen_replacement'}
    assert all(x['actionable'] is False for x in r['options'])
    assert r['input_digest'] and r['protocol_profile']['content_hash']
    p=payload(); p['observations'][2]['value']='20'
    assert 'platelets' in {x['product'] for x in interpret(p)['options']}


def test_no_option_normal_and_boundary():
    p=payload()
    for o in p['observations']: o['value']={'R':'10','MA':'50','LY30':'2.6'}[o['parameter']]
    p['observations'][2]['value']='14'
    r=interpret(p)
    assert r['options']==[]
    assert any(f['code']=='no_threshold_crossed' for f in r['findings'])


@pytest.mark.parametrize('field,value', [('active_bleeding',False),('population','paediatric'),
    ('evidence_current',False),('discordant_evidence',True),('heparin_status','unknown'),
    ('anticoagulant_status','unknown'),('active_bleeding','true')])
def test_context_gates(field,value):
    p=payload();p['context'][field]=value
    assert interpret(p)['options']==[]


def test_clinical_mode_never_activates_reference_rule():
    p=payload();p['mode']='clinical'
    r=interpret(p);assert not r['options']
    assert any(x['code']=='clinical_activation_required' for x in r['withheld'])


@pytest.mark.parametrize('value', ['NaN','Infinity','-1','1e9999',None,True])
def test_bad_numeric_input_cannot_trigger(value):
    p=payload();p['observations'][0]['value']=value
    r=interpret(p)
    assert 'plasma' not in {x['product'] for x in r['options']}


def test_pending_lysis_unknown_extra_and_qualified_results():
    p=payload();p['observations'][3].update(status='pending',value=None)
    p['observations'][2]['qualifier']='lt'
    p['observations'].append(observation('EXTRA','custom','7','widgets'))
    r=interpret(p)
    assert len(r['observations'])==5
    assert 'fibrinogen_replacement' not in {x['product'] for x in r['options']}
    assert any(x['code']=='pending_observation' for x in r['withheld'])
    assert any(x['code']=='unmapped_observation' for x in r['withheld'])


def test_conflicting_duplicate_and_wrong_device_withhold():
    p=payload();p['observations'].append(observation('CFF','MA','20'))
    assert not interpret(p)['options']
    p=payload();p['device_profile_id']='teg6s_gh_hn'
    assert not interpret(p)['options']


def test_missing_fibrin_cannot_select_platelets_and_sample_pair_must_match():
    p=payload();p['observations']=p['observations'][:2]
    assert 'platelets' not in {x['product'] for x in interpret(p)['options']}
    p=payload();p['observations'][2].update(value='20',sample_id='other')
    assert not interpret(p)['options']


def test_registry_return_is_detached():
    ds=device_profiles();ds[0]['label']='changed'
    assert device_profiles()[0]['label']!='changed'
    assert all(p['status'] in {'reference_only','evidence_gap'} for p in protocol_profiles())

# Independent examples transcribed from named source branches. No doses are implied.
CASES=[
 ('teg5000_kaolin','teg5000_cardiac_reference','cardiac','post_protamine', [('K','MA','30','mm'),('KH','R','13','min'),('FF','MA','7','mm')], {'plasma','fibrinogen_replacement'}, [('K','MA','50','mm'),('KH','R','10','min'),('FF','MA','15','mm')]),
 ('teg5000_rapid','teg5000_trauma_reference','trauma',None,[('RapidTEG','MA','70','mm'),('RapidTEG','ACT','121','s'),('RapidTEG','LY30','0','%'),('FF','MA','19','mm')], {'plasma','fibrinogen_replacement'}, [('RapidTEG','MA','70','mm'),('RapidTEG','ACT','120','s'),('RapidTEG','LY30','0','%'),('FF','MA','20','mm')]),
 ('teg6s_gh','teg6s_cardiac_reference','cardiac','post_protamine',[('CK','R','10','min'),('CRT','MA','40','mm'),('CFF','MA','14','mm')], {'plasma','fibrinogen_replacement'}, [('CK','R','9','min'),('CRT','MA','50','mm'),('CFF','MA','15','mm')]),
 ('teg6s_gh_lysis','teg6s_trauma_reference','trauma',None,[('CK','R','11','min'),('CRT','MA','40','mm'),('CFF','MA','14','mm'),('CK','LY30','0','%')], {'plasma','platelets'}, [('CK','R','10','min'),('CRT','MA','50','mm'),('CFF','MA','14','mm'),('CK','LY30','2.6','%')]),
 ('teg6s_gh_hn','teg6s_hn_cardiac_reference','cardiac','post_protamine',[('LAB','fibrinogen_clauss','1.4','g/L'),('CFFH','MA','12','mm')], {'fibrinogen_concentrate'}, [('LAB','fibrinogen_clauss','1.5','g/L'),('CFFH','MA','25','mm')]),
 ('rotem_delta_liquid','rotem_delta_perioperative_reference','cardiac','post_protamine',[('FIBTEM','A10','9','mm'),('EXTEM','A10','30','mm'),('EXTEM','CT','110','s'),('INTEM','CT','250','s')], {'fibrinogen_replacement','plasma'}, [('FIBTEM','A10','15','mm'),('EXTEM','A10','50','mm'),('EXTEM','CT','100','s'),('INTEM','CT','240','s')]),
 ('rotem_delta_single_use','rotem_delta_trauma_reference','trauma',None,[('FIBTEM S','A5','10','mm'),('EXTEM S','CT','90','s')], {'fibrinogen_replacement'}, [('FIBTEM S','A5','11','mm'),('EXTEM S','CT','80','s')]),
 ('rotem_sigma_complete','rotem_sigma_trauma_reference','trauma',None,[('FIBTEM C','A5','10','mm')], {'fibrinogen_replacement'}, [('FIBTEM C','A5','11','mm')]),
 ('rotem_sigma_complete_hep','rotem_sigma_cardiac_reference','cardiac','post_protamine',[('FIBTEM C','MCF','10','mm'),('EXTEM C','A10','39','mm'),('EXTEM C','CT','91','s')], {'platelets','plasma'}, [('FIBTEM C','MCF','10','mm'),('EXTEM C','A10','40','mm'),('EXTEM C','CT','90','s')]),
 ('rotem_delta_liquid','rotem_delta_obstetric_reference','obstetric','postpartum',[('FIBTEM','A5','11.999','mm')], {'fibrinogen_concentrate'}, [('FIBTEM','A5','12','mm')]),
 ('rotem_delta_liquid','rotem_delta_liver_reference','liver_transplant','reperfusion',[('EXTEM','A5','24','mm'),('FIBTEM','A10','9','mm'),('INTEM','CT','250','s'),('HEPTEM','CT','250','s')], {'fibrinogen_replacement','plasma'}, [('EXTEM','A5','30','mm'),('FIBTEM','A10','12','mm'),('INTEM','CT','240','s'),('HEPTEM','CT','240','s')]),
]


def case_payload(case, rows):
    device,profile,setting,phase,*_=case
    p=payload();p.update(device_profile_id=device,protocol_profile_id=profile)
    p['context'].update(setting=setting,phase=phase,persistent_non_surgical_bleeding=True,
       diffuse_bleeding=True,physiological_conditions_met=True,acute_liver_failure=False,
       combined_organ_transplant=False,retransplant_within_30_days=False)
    p['observations']=[observation(*row) for row in rows if row[0]!='LAB']
    p['laboratory']=[observation(*row) for row in rows if row[0]=='LAB']
    return p


@pytest.mark.parametrize('case',CASES,ids=[c[1] for c in CASES])
def test_every_reference_target_positive_negative_missing_and_wrong_setting(case):
    p=case_payload(case,case[4]);r=interpret(p)
    assert {x['product'] for x in r['options']}==case[5]
    assert all(x['source_ids'] for x in r['options'])
    assert not interpret(case_payload(case,case[6]))['options']
    p['context']['setting']='unverified'
    assert not interpret(p)['options']
    p=case_payload(case,[])
    assert not interpret(p)['options']
    assert any(x['state']=='unknown' for x in interpret(p)['evaluated_rules'])


@pytest.mark.parametrize('changes',[{'assay':[]},{'parameter':{}},{'sample_id':[]},{'run_id':{}},{'id':[]}])
def test_malformed_observation_fields_do_not_raise(changes):
    p=payload();p['observations'][0].update(changes)
    r=interpret(p)
    assert not r['options']


def test_hn_does_not_borrow_cff_trigger():
    p=case_payload(CASES[4],[('CFFH','MA','1','mm')])
    r=interpret(p);assert not r['options']
    assert any(x['code']=='hn_mapping' for x in r['findings'])
    p=case_payload(CASES[4],CASES[4][4]);r=interpret(p)
    assert all(x['basis']=='laboratory' for x in r['options'])


def test_unmatured_lysis_does_not_cancel_other_valid_domains():
    p=payload();p['observations'][3]['mature']=False
    r=interpret(p)
    assert {x['product'] for x in r['options']}=={'plasma','fibrinogen_replacement'}
    assert next(x for x in r['evaluated_rules'] if x['rule_id']=='lysis')['state']=='unknown'


def test_sigma_heptem_mask_excludes_lysis_but_preserves_strength():
    d=next(x for x in device_profiles() if x['id']=='rotem_sigma_complete_hep')
    mask={c['assay']:{p['name'] for p in c['parameters']} for c in d['channels']}
    assert mask['HEPTEM C']=={'CT','A5','A10','A20','MCF'}
    assert mask['FIBTEM C']=={'A5','A10','A20','MCF'}


def test_early_and_maximum_amplitude_never_substitute():
    p=payload();p['observations'][2]['parameter']='A10'
    assert 'fibrinogen_replacement' not in {x['product'] for x in interpret(p)['options']}


def test_source_heparin_comparison_overrides_excluded_checkbox():
    case=CASES[2]
    p=case_payload(case, [('CK','R','15','min'),('CKH','R','5','min'),('CRT','MA','40','mm'),('CFF','MA','10','mm')])
    r=interpret(p)
    assert not r['options']
    assert any(x['code']=='possible_heparin_effect' for x in r['findings'])


def test_heparin_pair_missing_identity_is_not_trusted():
    p=case_payload(CASES[2],[('CK','R','15','min'),('CKH','R','5','min'),('CRT','MA','40','mm'),('CFF','MA','10','mm')])
    del p['observations'][0]['sample_id']
    r=interpret(p)
    assert any(x['code']=='unverified_pair' for x in r['withheld'])
    assert not r['options']


def test_patient_source_invalidity_not_overridden_by_freshness_checkbox():
    p=payload();p['observations'][2]['source_current']=False
    r=interpret(p)
    assert 'fibrinogen_replacement' not in {x['product'] for x in r['options']}
    assert 'platelets' not in {x['product'] for x in r['options']}


CORE_CHANNELS={
 'teg5000_kaolin':{'K','KH','FF'}, 'teg5000_rapid':{'RapidTEG','FF'},'teg5000_native':{'Native'},
 'teg5000_pm_adp_aa':{'Control','Fibrin','ADP','AA'},'teg5000_pm_adp':{'Control','Fibrin','ADP'},'teg5000_pm_aa':{'Control','Fibrin','AA'},
 'teg6s_gh':{'CK','CKH','CRT','CFF'},'teg6s_gh_lysis':{'CK','CRT','CFF'},'teg6s_gh_hn':{'CK','CKH','CRTH','CFFH'},
 'teg6s_pm_adp_aa':{'Control','Fibrin','ADP','AA'},'teg6s_pm_adp':{'Control','Fibrin','ADP'},
 'rotem_delta_liquid':{'INTEM','EXTEM','FIBTEM','HEPTEM','APTEM','NATEM'},
 'rotem_delta_single_use':{'INTEM S','EXTEM S','FIBTEM S','HEPTEM S','APTEM S'},
 'rotem_sigma_complete':{'INTEM C','EXTEM C','FIBTEM C','APTEM C'},
 'rotem_sigma_complete_hep':{'INTEM C','EXTEM C','FIBTEM C','HEPTEM C'},
 'rotem_platelet':{'ADPTEM','ARATEM','TRAPTEM'},
}


@pytest.mark.parametrize('profile_id',list(CORE_CHANNELS))
def test_each_capture_configuration_preserves_all_source_values_and_extras(profile_id):
    d=next(x for x in device_profiles() if x['id']==profile_id)
    assert {c['assay'] for c in d['channels']}==CORE_CHANNELS[profile_id]
    original=[observation(c['assay'],p['name'],'12',p['unit']) for c in d['channels'] for p in c['parameters']]
    original.append(observation('Original custom assay','manufacturer extension','7.000001','source unit'))
    r=interpret(dict(device_profile_id=profile_id,observations=original))
    assert r['observations']==original
    assert not r['options']
    assert r['device_profile']['content_hash']


def test_exact_decimal_decision_does_not_round_at_threshold():
    p=payload();p['observations'][0]['value']='10.0000000000000000000000000000000001'
    assert 'plasma' in {x['product'] for x in interpret(p)['options']}
    p['observations'][0]['value']='9.9999999999999999999999999999999999'
    assert 'plasma' not in {x['product'] for x in interpret(p)['options']}


def test_liver_phase_and_study_exclusions():
    p=case_payload(CASES[-1],CASES[-1][4]);p['context']['acute_liver_failure']=True
    assert not interpret(p)['options']
    p=case_payload(CASES[-1],CASES[-1][4]);p['context']['phase']='pre_bypass'
    assert not interpret(p)['options']
    p=case_payload(CASES[-1],CASES[-1][4]);p['context']['physiological_conditions_met']=None
    assert not interpret(p)['options']


def test_stale_profile_version_and_untrusted_maturity_withhold():
    p=payload();p['device_profile_version']='obsolete'
    assert not interpret(p)['options']
    p=payload();p['protocol_profile_hash']='0'*64
    assert not interpret(p)['options']
    p=payload();p['observations'][3].update(value='10',mature='true')
    assert not any(f.get('rule_id')=='lysis' for f in interpret(p)['findings'])


def test_timed_repeated_results_require_explicit_observation_selection():
    p=payload()
    early={**p['observations'][2],'id':'cff-early','value':'8','elapsed_seconds':'60','timing_origin':'run_start','observed_at':'2026-10-08T09:01:00Z'}
    final={**p['observations'][2],'id':'cff-final','value':'20','elapsed_seconds':'1200','timing_origin':'run_start','observed_at':'2026-10-08T09:20:00Z'}
    p['observations']=[*p['observations'][:2],early,final,p['observations'][3]]
    assert not interpret(p)['options']
    p['selected_observation_ids']=['cff-final']
    r=interpret(p)
    assert {x['product'] for x in r['options']}=={'plasma','platelets'}
    assert len(r['observations'])==5
    assert 'cff-final' in r['evaluated_observation_ids']
    assert 'cff-early' not in r['evaluated_observation_ids']
    assert any(w['code']=='unselected_repeated_observation' for w in r['withheld'])


def test_selection_resolves_repeats_without_omitting_unique_heparin_evidence():
    p=case_payload(CASES[2],[('CK','R','15','min'),('CKH','R','5','min'),('CRT','MA','40','mm'),('CFF','MA','10','mm')])
    p['observations'].append({**p['observations'][3],'id':'cff-later','value':'12','elapsed_seconds':'1200'})
    p['selected_observation_ids']=['cff-later']
    r=interpret(p)
    assert not r['options']
    assert any(f['code']=='possible_heparin_effect' for f in r['findings'])
    assert 'CKH:R' in r['evaluated_observation_ids']


@pytest.mark.parametrize('selection',[['missing'],['CFF:MA','later'],['later','later'],'later',None])
def test_invalid_repeat_selection_fails_closed(selection):
    p=payload();p['observations'].append({**p['observations'][2],'id':'later','value':'20'})
    p['selected_observation_ids']=selection
    assert not interpret(p)['options']
