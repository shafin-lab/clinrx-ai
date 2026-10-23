"""Deterministic M10 assessment of explicitly selected reference content.

Never prescribes or activates a hospital protocol. The gateway owns immutable
source resolution/patient binding; this pure function retains the exact supplied
observations and context so synthetic outcomes can be independently reproduced.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import re

from app.services.m10_profiles import VERSION, device_profiles, protocol_profiles, source_catalog

ENGINE_VERSION = 'm10-reference-engine-1.0.0'
_DECIMAL = re.compile(r'^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?$')


def _number(raw):
    if not isinstance(raw,str) or len(raw)>64 or not _DECIMAL.fullmatch(raw):
        return None
    try:
        n=Decimal(raw)
    except InvalidOperation:
        return None
    return n if n.is_finite() and Decimal(0)<=n<=Decimal('1000000') else None


def interpret(payload: dict) -> dict:
    """Return evidence, three-valued decisions and non-actionable reference options.

    No supplied activation/approval field can enable clinical product advice.
    Unknown or incompatible evidence remains visible and cannot satisfy a rule.
    """
    if not isinstance(payload,dict): payload={}
    original=deepcopy(payload)
    context=deepcopy(payload.get('context')) if isinstance(payload.get('context'),dict) else {}
    observations=deepcopy(payload.get('observations')) if isinstance(payload.get('observations'),list) else []
    laboratory=deepcopy(payload.get('laboratory')) if isinstance(payload.get('laboratory'),list) else []
    device=next((x for x in device_profiles() if x['id']==payload.get('device_profile_id')),None)
    profile=next((x for x in protocol_profiles() if x['id']==payload.get('protocol_profile_id')),None)
    result=dict(engine_version=ENGINE_VERSION,registry_version=VERSION,device_profile=device,protocol_profile=profile,
                activation_status='reference_only_not_clinically_activated',context=context,observations=observations,
                laboratory=laboratory,findings=[],options=[],withheld=[],evaluated_rules=[],sources=[],
                evaluated_observation_ids=[],input_digest=sha256(json.dumps(original,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest())
    result['evaluation_id']='m10-evaluation:'+result['input_digest'][:24]
    def hold(code,text,**kwargs): result['withheld'].append(dict(code=code,text=text,**kwargs))
    def finding(code,text,ids=None,**kwargs): result['findings'].append(dict(code=code,text=text,evidence_ids=ids or [],**kwargs))
    if not device:
        hold('unknown_device','Choose an exact supported device and cartridge; original results are retained.')
        return result
    source_ids=set(device['source_ids'])
    if profile: source_ids.update(profile['source_ids'])
    result['sources']=[s for s in source_catalog() if s['id'] in source_ids]
    mask={(c['assay'],p['name']):p['unit'] for c in device['channels'] for p in c['parameters']}
    values={}; valid_observations={}; blocked=False; seen_ids=set(); sample_ids=set(); run_ids=set()
    # A selection resolves a repeated channel only. Unique channels always remain
    # in scope, including contradictory heparinase evidence from the same run.
    selections=payload.get('selected_observation_ids',[])
    selection_valid=isinstance(selections,list) and all(isinstance(x,str) and x for x in selections) and len(set(selections))==len(selections)
    all_ids={o.get('id') for o in observations+laboratory if isinstance(o,dict) and isinstance(o.get('id'),str)}
    if not selection_valid or not set(selections).issubset(all_ids):
        hold('invalid_observation_selection','Select exact observation IDs present in this complete source report.');blocked=True
        selections=[]
    repeated={}
    for o in observations+laboratory:
        if isinstance(o,dict) and isinstance(o.get('assay'),str) and isinstance(o.get('parameter'),str):
            repeated.setdefault((o['assay'],o['parameter']),[]).append(o.get('id'))
    chosen={}
    for k,ids in repeated.items():
        if len(ids)>1:
            explicit=[i for i in ids if i in selections]
            if len(explicit)==1:chosen[k]=explicit[0]
            else:
                hold('ambiguous_repeated_observation','Repeated channel results require exactly one explicitly selected observation for each assay and parameter.');blocked=True
    if ('device_profile_version' in payload and payload['device_profile_version']!=device['version']) or ('protocol_profile_hash' in payload and (not profile or payload['protocol_profile_hash']!=profile['content_hash'])):
        hold('stale_profile','Selected device/protocol version no longer matches the executable reference content.');blocked=True
    for i,o in enumerate(observations+laboratory):
        if not isinstance(o,dict):
            hold('malformed_observation',f'Observation {i+1} is not a structured result.');blocked=True;continue
        if any(not isinstance(o.get(k),str) or not o.get(k) for k in ('assay','parameter')) or any(k in o and o[k] is not None and not isinstance(o[k],str) for k in ('sample_id','run_id','status','qualifier','quality','unit')):
            hold('malformed_observation','Assay, parameter, status, units and source identities must have their expected text types.');blocked=True;continue
        key=(o.get('assay'),o.get('parameter')); oid=o.get('id')
        if not isinstance(oid,str) or not oid or oid in seen_ids:
            hold('conflicting_observation','Every selected observation needs a distinct source observation ID.');blocked=True;continue
        seen_ids.add(oid)
        if key in chosen and oid!=chosen[key]:
            hold('unselected_repeated_observation','Repeated result retained as source evidence; its exact selected counterpart is used for this evaluation.',evidence_ids=[oid,chosen[key]])
            continue
        result['evaluated_observation_ids'].append(oid)
        if key in valid_observations:
            hold('conflicting_observation','Multiple selected values for the same assay/parameter require reconciliation.',evidence_ids=[valid_observations[key]['id'],oid]);blocked=True;continue
        valid_observations[key]=o
        if key[0]!='LAB':
            if key not in mask:
                hold('unmapped_observation',f'{key[0]} {key[1]} is retained as an extra source output; no rule applies.',evidence_ids=[oid]);continue
            if o.get('sample_id'): sample_ids.add(o['sample_id'])
            if o.get('run_id'): run_ids.add(o['run_id'])
        if any(k in o and type(o[k]) is not bool for k in ('mature','source_current','within_cutoff')):
            hold('invalid_boolean_result','Maturity and source eligibility flags must be explicit booleans.',evidence_ids=[oid]);continue
        if o.get('status')=='pending':
            hold('pending_observation',f'{key[0]} {key[1]} is pending; absence of a matured value is not a normal result.',evidence_ids=[oid]);continue
        if o.get('source_current') is False or o.get('within_cutoff') is False:
            hold('stale_observation','Selected source is superseded or outside the review cutoff.',evidence_ids=[oid]);continue
        if o.get('status')!='final' or o.get('quality') in {'invalid','failed','uncertain'}:
            hold('ineligible_observation',f'{key[0]} {key[1]} is not a valid final measurement.',evidence_ids=[oid]);continue
        if o.get('qualifier','eq')!='eq':
            hold('qualified_observation','Comparator/range results are preserved but are not treated as exact values by this reference engine.',evidence_ids=[oid]);continue
        number=_number(o.get('value'))
        if number is None or (o.get('unit') in {'mm','%'} and number>100) or (key[1] in {'R','CT','ACT'} and number==0):
            hold('invalid_numeric_result',f'{key[0]} {key[1]} requires a finite, nonnegative exact decimal within its physical domain.',evidence_ids=[oid]);continue
        if key[0]!='LAB' and o.get('unit')!=mask[key]:
            hold('wrong_unit',f'{key[0]} {key[1]} must use {mask[key]} for this profile. Original units are retained.',evidence_ids=[oid]);continue
        if key[1] in {'LY30','LY60','LI30','LI60','ML'} and (o.get('mature') is False or 'maturation' in o and o.get('maturation')!='mature'):
            hold('pending_observation','Clot breakdown measurement has not matured.',evidence_ids=[oid]);continue
        values[key]=(number,o)
    if len(sample_ids)>1 or len(run_ids)>1:
        hold('discordant_run','Paired results come from different sample/run identities. Select one coherent report.');blocked=True
    hc=profile.get('heparin_comparison') if profile else None
    if hc and device['id'] in profile['device_profile_ids']:
        left=values.get(tuple(hc['left']));right=values.get(tuple(hc['right']))
        if left and right:
            same_pair=bool(left[1].get('sample_id') and left[1].get('run_id') and left[1].get('sample_id')==right[1].get('sample_id') and left[1].get('run_id')==right[1].get('run_id'))
            if not same_pair:
                hold('unverified_pair','Selected heparinase comparison lacks a verified common sample and run.');blocked=True
            else:
                with localcontext() as arithmetic:
                    arithmetic.prec=100
                    threshold=Decimal(hc['threshold'])
                    if hc['kind']=='difference_gt': crossed=left[0]-right[0]>threshold
                    elif hc['kind']=='ratio_gt': crossed=left[0]>threshold*right[0]
                    else: crossed=right[0]<threshold*left[0] and left[0]>Decimal(hc['left_min'])
                if crossed:
                    finding('possible_heparin_effect','The paired initiation measurements cross the selected source protocol’s heparin-effect criterion. Reconcile heparin/protamine context before replacement guidance.',[left[1]['id'],right[1]['id']],source_ids=[hc['source_id']])
                    hold('heparin_evidence_conflict','Observed heparinase comparison requires review even when the context field says heparin was excluded.');blocked=True
    # Explanations describe measured domains; there is no generic high/low threshold.
    if any(a in {'CFF','CFFH','FF','FIBTEM','FIBTEM C','FIBTEM S'} for a,p in values):
        finding('fibrin_domain','The fibrin channel measures the fibrin contribution to clot strength. It is not interchangeable with Clauss fibrinogen concentration.',[o['id'] for (a,p),(v,o) in values.items() if a in {'CFF','CFFH','FF','FIBTEM','FIBTEM C','FIBTEM S'}])
    for a,b,param in [('CK','CKH','R'),('K','KH','R'),('INTEM','HEPTEM','CT'),('INTEM C','HEPTEM C','CT'),('INTEM S','HEPTEM S','CT')]:
        left=values.get((a,param));right=values.get((b,param))
        if left and right and not blocked:
            if left[1].get('sample_id') and left[1].get('sample_id')==right[1].get('sample_id') and left[1].get('run_id') and left[1].get('run_id')==right[1].get('run_id'):
                relation='longer' if left[0]>right[0] else 'not longer'
                finding('heparin_pair',f'{a} {param} is {relation} than the paired {b} measurement. A heparinase comparison can support review of heparin effect; it does not establish a heparin dose or exclude other anticoagulants.',[left[1]['id'],right[1]['id']])
            else:
                hold('unverified_pair','Heparinase comparison requires matching explicit sample and run identities.')
    if '_pm_' in device['id'] or device['id']=='rotem_platelet':
        finding('platelet_function','Agonist-specific results describe platelet response in the tested pathway. Review controls, specimen, medicines and local reference intervals. Inhibition/aggregation does not equal platelet count and does not independently select platelet transfusion.',[o.get('id') for o in observations if isinstance(o,dict)])
        hold('specialist_explanation_only','This profile supports source-report explanation; no platelet-transfusion or antiplatelet-reversal algorithm is activated.')
        return result
    if device['id']=='teg6s_gh':
        finding('lysis_unavailable','This Global Hemostasis parameter mask has no lysis result. Clot stability has not been assessed by this cartridge.')
    if device['id']=='teg6s_gh_hn':
        finding('hn_mapping','HN results retain CK, CKH, CRTH and CFFH identities. Published diagnostic CFFH cutoffs are not a validated transfusion algorithm; any available product option below is explicitly based on concurrent Clauss fibrinogen.')
    if not profile:
        hold('protocol_required','Select an explicit reference protocol to evaluate thresholds; no universal device thresholds are applied.')
        return result
    if device['id'] not in profile['device_profile_ids']:
        hold('wrong_device','The selected protocol does not support this device/cartridge/reagent profile.');blocked=True
    if context.get('population')!=profile['population'] or context.get('setting')!=profile['setting']:
        hold('wrong_context','Population and clinical setting must exactly match the selected protocol.');blocked=True
    if context.get('active_bleeding') is not True or context.get('clinically_significant_bleeding') is not True:
        hold('bleeding_context','Document active clinically significant bleeding before considering a replacement option.');blocked=True
    if context.get('evidence_current') is not True:
        hold('freshness_unconfirmed','Confirm that selected measurements are current and applicable to this assessment.');blocked=True
    if context.get('discordant_evidence') is not False:
        hold('discordance_unresolved','Confirm that conflicting laboratory, device, timing and clinical evidence has been reconciled.');blocked=True
    if context.get('anticoagulant_status')!='none':
        hold('anticoagulant_context','Anticoagulant exposure is present or unconfirmed; this reference replacement algorithm does not resolve its effects.');blocked=True
    if context.get('heparin_status')!='excluded':
        hold('heparin_context','Residual heparin must be assessed and excluded for these replacement options; the engine does not infer this from HN or a single result.');blocked=True
    if profile.get('phases') and context.get('phase') not in profile['phases']:
        hold('phase_required','Document a supported procedure phase: '+', '.join(profile['phases'])+'.');blocked=True
    for key, expected in profile.get('requires_context',{}).items():
        if context.get(key) is not expected:
            hold('profile_context_required','Required context: '+key+'. '+profile.get('context_notes',''));blocked=True
    for key in profile.get('exclusion_keys',[]):
        if context.get(key) is not False:
            hold('profile_exclusion_unresolved','Confirm that this exclusion does not apply: '+key+'.');blocked=True
    if profile['status']=='evidence_gap':
        hold('source_verification_gap','; '.join(profile.get('limitations',[])));blocked=True
    synthetic=payload.get('mode')=='synthetic_reference'
    if not synthetic: hold('clinical_activation_required','Reference content is not a clinically approved hospital protocol. Product options are available only in explicitly selected synthetic reference mode.')
    for rule in profile['rules']:
        ids=[];checks=[];reason=None
        for c in rule['conditions']:
            selected=values.get((c['assay'],c['parameter']))
            if not selected:
                checks.append(None);reason=f"Missing eligible {c['assay']} {c['parameter']} ({c['unit']}).";continue
            n,o=selected;ids.append(o['id'])
            if o.get('unit')!=c['unit']:
                checks.append(None);reason=f"{c['assay']} {c['parameter']} requires {c['unit']}.";continue
            threshold=Decimal(c['value']); op=c['op']
            if op=='ge_other':
                other=values.get(tuple(rule['compare_with']))
                if not other or other[1].get('unit')!=c['unit']:
                    checks.append(None);reason='Missing compatible paired initiation measurement.';continue
                ids.append(other[1]['id']);threshold=other[0];op='ge'
            if op=='difference_lt':
                other=values.get(tuple(rule['difference_with']))
                if not other or other[1].get('unit')!=c['unit']:
                    checks.append(None);reason='Missing compatible paired fibrin measurement.';continue
                ids.append(other[1]['id'])
                with localcontext() as arithmetic:
                    arithmetic.prec=100
                    n=n-other[0]
                op='lt'
            checks.append({'lt':lambda:n<threshold,'le':lambda:n<=threshold,'gt':lambda:n>threshold,'ge':lambda:n>=threshold}[op]())
        requirements=rule.get('requires_context',{})
        if any(context.get(k) is not v if isinstance(v,bool) else context.get(k)!=v for k,v in requirements.items()):
            checks.append(None);reason='Additional required clinical context: '+', '.join(requirements)+'.'
        # Never treat an absent domain as a fully negative assessment.
        state='unknown' if any(c is None for c in checks) or blocked else 'true' if all(checks) else 'false'
        result['evaluated_rules'].append(dict(rule_id=rule['id'],state=state,evidence_ids=ids,conditions=deepcopy(rule['conditions']),source_ids=rule['source_ids']))
        if state=='unknown':
            hold('rule_withheld',reason or 'Required context or source eligibility is unresolved.',rule_id=rule['id']);continue
        if state=='false':continue
        finding('threshold_crossed',rule['text'],ids,rule_id=rule['id'],source_ids=rule['source_ids'],basis=rule.get('basis','viscoelastic'))
        if rule['product'] and synthetic:
            products={'fibrinogen_replacement':['cryoprecipitate','fibrinogen_concentrate']}.get(rule['product'],[rule['product']])
            result['options'].append(dict(product=rule['product'],products=products,text=rule['text'],rule_id=rule['id'],evidence_ids=ids,source_ids=rule['source_ids'],actionable=False,basis=rule.get('basis','viscoelastic'),status='synthetic_reference_option',dose=None,reassessment=profile['reassessment']))
    if result['evaluated_rules'] and all(r['state']=='false' for r in result['evaluated_rules']):
        finding('no_threshold_crossed','None of the evaluated reference thresholds was crossed. This does not establish surgical haemostasis or exclude defects outside the measured domains.')
    return result
