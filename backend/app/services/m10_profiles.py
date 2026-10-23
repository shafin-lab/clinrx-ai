"""Versioned source-backed M10 capture profiles and reference algorithms.

These are reference content, not clinically activated hospital protocols. Parameter
masks describe the cited configuration; unlisted source output is retained as extra.
"""
from copy import deepcopy
from hashlib import sha256
import json

VERSION = '2026-10-23.1'
SOURCES = {
 'teg5000': ('Haemonetics TEG 5000 reagent catalogue', 'https://hospital.haemonetics.com/hemostasis-management/teg-5000', 'Reagents and PlateletMapping configurations'),
 'teg6s': ('Haemonetics TEG 6s catalogue', 'https://hospital.haemonetics.com/hemostasis-management/teg-6s', 'Cartridge inventory'),
 'gh': ('Manufacturer FDA K243858', 'https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243858.pdf', 'Table 2, reported parameter mask'),
 'lysis': ('Manufacturer FDA K183160', 'https://www.accessdata.fda.gov/cdrh_docs/pdf18/K183160.pdf', 'Indications and assay parameters'),
 'hn': ('Manufacturer FDA K232018', 'https://www.accessdata.fda.gov/cdrh_docs/pdf23/K232018.pdf', 'Assays and clinical assessment set'),
 'rotem': ('Manufacturer FDA K201440', 'https://www.accessdata.fda.gov/cdrh_docs/pdf20/k201440.pdf', 'Reported parameters and assay-specific reportable ranges'),
 'sigma': ('Werfen ROTEM sigma', 'https://www.werfen.com/de/de/rotem-sigma-ivdr', 'Complete and Complete + HEP cartridges'),
 'delta': ('Manufacturer ROTEM delta manual', 'https://imda.moh.gov.vn/documents/10182/57924129/upload_00053884_1725101751240.pdf?fileId=57939148&version=1.0', 'Liquid and single-use reagent identities'),
 'teg6s_trauma': ('TEG 6s adult trauma Delphi consensus, 2025', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC12105950/', 'Table 4 and Figure 2; CK R >10 min, CFF MA <14 mm, CRT MA <50 mm with adequate CFF; CK LY30 >2.6%'),
 'moh_cardiac': ('Malaysia MOH Patient Blood Management consensus, 2024', 'https://www.moh.gov.my/images/04-penerbitan/garis-panduan-kkm/Consensus%20Statement%20on%20Patient%20Blood%20Management%20MOH_digital%20preview.pdf', 'Table 5.5 intraoperative cardiac algorithm; TEG kaolin/heparinase and functional fibrinogen'),
 'aagbi_trauma': ('Association of Anaesthetists blood component guideline, 2025', 'https://associationofanaesthetists-publications.onlinelibrary.wiley.com/doi/10.1111/anae.16542', 'Table 3 suggested VHA algorithms based on ITACTIC; rapid TEG and functional fibrinogen'),
 'gh_cardiac': ('TEG-guided management in thoracic aortic surgery', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11708463/', 'Institutional TEG6s protocol; post-CPB CFF MA <14 mm: plasma'),
 'hn_diagnostic': ('CFFH clinical decision points, 2025 primary study', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC12509440/', 'Diagnostic correlation, not validated treatment trigger; prospective algorithm validation still needed'),
 'cardiac_clauss': ('TEG6s in cardiothoracic surgery, primary study', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6301661/', 'Perioperative management: persistent non-surgical bleeding after CPB and neutralization, Clauss fibrinogen <1.5 g/L'),
 'sigma_cardiac': ('Fiameni et al cardiac surgery centre protocol, 2024', 'https://onlinelibrary.wiley.com/doi/full/10.1111/tme.13063', 'Table 1B, ROTEM sigma EXTEM/INTEM/HEPTEM/FIBTEM; MCF FIBTEM <9; adequate fibrin with EXTEM A10 <40 or CT >90'),
 'sigma_trauma': ('FEISTY primary trial protocol', 'https://link.springer.com/article/10.1186/s13063-017-1980-x', 'Intervention and blood sampling; ROTEM sigma FIBTEM A5 <=10 mm, significant traumatic haemorrhage'),
 'delta_trauma': ('SCGH Blood Transfusion Committee critical bleeding protocol, 2017', 'https://scghed.com/wp-content/uploads/2017/05/Massive-Transfusion-Protocol-2017.pdf', 'ROTEM EXTEM S/FIBTEM S critical bleeding algorithm'),
 'obstetric': ('Tampere ROTEM delta postpartum haemorrhage randomized pilot trial', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9900729/', 'Methods and ROTEM arm: ongoing postpartum bleeding; FIBTEM A5 <12 mm triggers fibrinogen concentrate'),
 'liver': ('Zamper et al liver transplantation primary before-after study', 'https://link.springer.com/article/10.1186/s12871-018-0664-8', 'Figure 1: EXTEM A5 <25 and FIBTEM A10 <10: fibrinogen; FIBTEM >10: platelets; prolonged INTEM with HEPTEM >=INTEM: plasma; adults with diffuse surgical bleeding'),
 'ruh': ('Royal United Hospitals Bath TEG6 SOP/POCT/61/2', 'https://www.ruh.nhs.uk/pathology/documents/poct/TEG6_SOP_inc_algorithms.pdf', 'Appendix 4, page 25: non-obstetric TEG6 algorithm, effective 10 November 2022; selected cardiac subset after heparin assessment'),
 'platelet': ('Haemonetics PlateletMapping', 'https://hospital.haemonetics.com/hemostasis-management/teg-6s', 'Agonist-specific platelet function; local IFU required for complete output mask'),
}


def source_catalog():
    return [dict(id=k,title=v[0],url=v[1],section=v[2],checked_on='2026-10-23') for k,v in SOURCES.items()]


def _params(names):
    units={'R':'min','K':'min','ACT':'s','CT':'s','CFT':'s','LOT':'s','alpha':'deg',
           'LY30':'%','LY60':'%','LI30':'%','LI60':'%','ML':'%','inhibition':'%',
           'aggregation':'%','FLEV':'mg/dL','G':'dyn/cm2','CI':'1','AUC':'ohm*min',
           'A6':'ohm','MS':'ohm/min'}
    return [{'name':n,'unit':units.get(n,'mm')} for n in names.split()]


def _device(id, label, channels, sources, status='source_verified_core', note=''):
    return dict(id=id,label=label,device=label.split(' — ')[0],manufacturer='Haemonetics' if id.startswith('teg') else 'Werfen',
                configuration=label,version=VERSION,channels=[dict(assay=a,label=a,parameters=_params(p)) for a,p in channels.items()],
                source_ids=sources,mapping_status=status,notes=note,
                extra_outputs='preserved_unmapped',clinical_activation='not_activated',
                availability_states=['final','preliminary','pending','not_reported','invalid','aborted','no_clot','unavailable'])


_DEVICES = [
 _device('teg5000_kaolin','TEG 5000 — Kaolin + functional fibrinogen',{'K':'R K alpha MA LY30 LY60 G CI','KH':'R K alpha MA LY30 LY60','FF':'MA FLEV'},['teg5000'], 'source_defined_capture', 'Cup-and-pin reagents, with optional matched heparinase channel. Local output mask requires IFU verification.'),
 _device('teg5000_rapid','TEG 5000 — RapidTEG + functional fibrinogen',{'RapidTEG':'ACT K alpha MA LY30 LY60','FF':'MA FLEV'},['teg5000'],'source_defined_capture'),
 _device('teg5000_native','TEG 5000 — Native / recalcified',{'Native':'R K alpha MA LY30 LY60'},['teg5000'],'capture_only', 'No kaolin algorithm applies to native results.'),
 _device('teg6s_gh','TEG 6s — Global Hemostasis',{'CK':'R K alpha MA','CKH':'R','CRT':'MA','CFF':'MA FLEV'},['gh']),
 _device('teg6s_gh_lysis','TEG 6s — Global Hemostasis with Lysis',{'CK':'R LY30','CRT':'MA','CFF':'MA'},['lysis']),
 _device('teg6s_gh_hn','TEG 6s — Global Hemostasis–HN',{'CK':'R MA','CKH':'R LY30','CRTH':'MA','CFFH':'MA'},['hn']),
]
for machine in ('teg5000','teg6s'):
    for variant in ('adp_aa','adp','aa'):
        if machine=='teg6s' and variant=='aa': continue
        channels={'Control':'MA','Fibrin':'MA'}
        channels.update({agonist:'MA inhibition aggregation' for agonist in variant.upper().split('_')})
        _DEVICES.append(_device(f'{machine}_pm_{variant}',f'{"TEG 5000" if machine=="teg5000" else "TEG 6s"} — PlateletMapping {variant.upper().replace("_", " & ")}',channels,['platelet','teg5000' if machine=='teg5000' else 'teg6s'],'capture_only','Source control/channel names are retained verbatim; this is a capture vocabulary, not a verified regional export mask.'))
for variant,suffix in [('liquid',''),('single_use',' S')]:
    ch={a+suffix:'CT CFT alpha A5 A10 A20 MCF LI30 LI60 ML LOT' for a in ('INTEM','EXTEM','APTEM','HEPTEM','NATEM')}
    if variant=='single_use': ch.pop('NATEM S')
    ch['FIBTEM'+suffix]='CT A5 A10 A20 MCF LI30 LI60 ML'
    _DEVICES.append(_device('rotem_delta_'+variant,'ROTEM delta — '+variant.replace('_',' '),ch,['rotem','delta'],'source_defined_capture','Assay-specific local outputs require current IFU; source-only extra parameters remain available.'))
# The FDA sigma profile does not report every parameter in every assay.
for variant,fourth in [('complete','APTEM C'),('complete_hep','HEPTEM C')]:
    ch={'INTEM C':'CT A5 A10 A20 MCF LI60 ML','EXTEM C':'CT A5 A10 A20 MCF LI60 ML','FIBTEM C':'A5 A10 A20 MCF'}
    ch[fourth]='CT A5 A10 A20 MCF' if fourth=='HEPTEM C' else 'CT A5 A10 A20 MCF LI60 ML'
    _DEVICES.append(_device('rotem_sigma_'+variant,'ROTEM sigma — '+variant.replace('_hep',' + HEP').title(),ch,['rotem','sigma'],'source_verified_core' if fourth=='HEPTEM C' else 'source_defined_capture', 'Complete APTEM C regional mask requires local verification.' if fourth=='APTEM C' else 'FDA K201440 assay-specific US reportable outputs.'))
_DEVICES.append(_device('rotem_platelet','ROTEM platelet — aggregation', {a:'A6 MS AUC' for a in ('ARATEM','ADPTEM','TRAPTEM')},['sigma'],'capture_only','Platelet aggregation domain; no clot-strength or transfusion rule applied.'))


for _entry in _DEVICES:
    _entry['content_hash']=sha256(json.dumps(_entry,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _condition(assay, parameter, op, value, unit='mm'):
    return dict(assay=assay,parameter=parameter,op=op,value=value,unit=unit)


def _rule(id, conditions, product, text, sources, **kw):
    return dict(id=id,conditions=conditions,product=product,text=text,source_ids=sources,**kw)


C=_condition
R=_rule
FIB='Fibrinogen replacement may be considered within this reference protocol; choose cryoprecipitate or the specified fibrinogen concentrate with the clinician and blood service.'
PLT='Reduced overall strength with adequate measured fibrin contribution supports reviewing platelet replacement in this reference protocol.'
PLASMA='Delayed clot initiation supports considering plasma after reviewing anticoagulants and the clinical/laboratory findings.'


def _profile(id,label,devices,setting,rules,sources,**kw):
    obj=dict(id=id,label=label,version=VERSION,status='reference_only',population='adult',setting=setting,
             device_profile_ids=devices,rules=rules,source_ids=sources,reviewer_approval=None,
             quantitative_dosing='not_activated',clinical_activation='site_approval_required',
             reassessment='Reassess bleeding and repeat the relevant laboratory/VET measurements after intervention according to the selected local protocol.',**kw)
    heparin={
        'teg5000_cardiac_reference': dict(left=['K','R'],right=['KH','R'],kind='ratio_gt',threshold='1.25',source_id='moh_cardiac'),
        'teg6s_cardiac_reference': dict(left=['CK','R'],right=['CKH','R'],kind='difference_gt',threshold='2',source_id='ruh'),
        'rotem_delta_perioperative_reference': dict(left=['INTEM','CT'],right=['HEPTEM','CT'],kind='right_ratio_lt',threshold='0.9',left_min='240',source_id='moh_cardiac'),
        'rotem_sigma_cardiac_reference': dict(left=['INTEM C','CT'],right=['HEPTEM C','CT'],kind='right_ratio_lt',threshold='0.8',left_min='240',source_id='sigma_cardiac'),
    }
    if id in heparin: obj['heparin_comparison']=heparin[id]
    obj['content_hash']=sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return obj

_PROTOCOLS=[
 _profile('teg6s_trauma_reference','TEG 6s trauma — 2025 consensus reference',['teg6s_gh_lysis'],'trauma',[
 R('plasma',[C('CK','R','gt','10','min')],'plasma',PLASMA,['teg6s_trauma']),
 R('fibrin',[C('CFF','MA','lt','14')],'fibrinogen_replacement',FIB,['teg6s_trauma']),
 R('platelets',[C('CRT','MA','lt','50'),C('CFF','MA','ge','14')],'platelets',PLT,['teg6s_trauma']),
 R('lysis',[C('CK','LY30','gt','2.6','%')],None,'Increased measured clot breakdown. Review trauma antifibrinolytic timing and prior treatment; do not delay independently indicated trauma therapy while awaiting lysis.', ['teg6s_trauma'])],['teg6s_trauma']),
 _profile('teg5000_cardiac_reference','TEG 5000 cardiac — MOH reference',['teg5000_kaolin'],'cardiac',[
 R('plasma',[C('KH','R','gt','12','min')],'plasma',PLASMA,['moh_cardiac']),
 R('fibrin',[C('K','MA','lt','40'),C('FF','MA','lt','8')],'fibrinogen_replacement',FIB,['moh_cardiac']),
 R('platelets',[C('K','MA','lt','40'),C('FF','MA','gt','8')],'platelets',PLT,['moh_cardiac'])],['moh_cardiac'],phases=['post_protamine']),
 _profile('teg5000_trauma_reference','TEG 5000 RapidTEG trauma — Association guideline reference',['teg5000_rapid'],'trauma',[
 R('fibrin',[C('FF','MA','lt','20')],'fibrinogen_replacement',FIB,['aagbi_trauma']),
 R('platelets',[C('RapidTEG','MA','difference_lt','45'),C('FF','MA','ge','20')],'platelets',PLT,['aagbi_trauma'],difference_with=['FF','MA']),
 R('plasma',[C('RapidTEG','MA','gt','65'),C('RapidTEG','ACT','gt','120','s')],'plasma',PLASMA,['aagbi_trauma']),
 R('lysis',[C('RapidTEG','LY30','gt','10','%')],None,'Increased clot breakdown; assess antifibrinolytic treatment within the trauma protocol.', ['aagbi_trauma'])],['aagbi_trauma']),
 _profile('teg6s_cardiac_reference','TEG 6s cardiac — RUH non-obstetric reference',['teg6s_gh'],'cardiac',[
 R('plasma',[C('CK','R','ge','10','min')],'plasma',PLASMA,['ruh']),
 R('fibrin',[C('CFF','MA','le','14')],'fibrinogen_replacement',FIB,['ruh']),
 R('platelets',[C('CRT','MA','le','49'),C('CFF','MA','gt','14')],'platelets',PLT,['ruh'])],['ruh'],phases=['post_protamine'],limitations=['Reference uses the cardiac subset of the RUH non-obstetric algorithm. Unavailable lysis on this GH mask is not evaluated. Institutional approval does not transfer to ClinRx.']),
 _profile('teg6s_hn_cardiac_reference','TEG 6s HN cardiac — concurrent Clauss reference',['teg6s_gh_hn'],'cardiac',[
 R('clauss_fibrin',[C('LAB','fibrinogen_clauss','lt','1.5','g/L')],'fibrinogen_concentrate','Concurrent Clauss fibrinogen below 1.5 g/L with persistent non-surgical post-CPB bleeding supports reviewing fibrinogen concentrate under the source cardiac protocol. This option is laboratory-driven; CFFH is not substituted for Clauss.',['cardiac_clauss'],basis='laboratory',requires_context={'persistent_non_surgical_bleeding':True})],['hn_diagnostic','cardiac_clauss'],phases=['post_protamine'],limitations=['No validated HN-specific numeric product algorithm located; diagnostic CFFH cutoffs are not treatment thresholds.']),
 _profile('rotem_delta_perioperative_reference','ROTEM delta cardiac — MOH reference',['rotem_delta_liquid'],'cardiac',[
 R('fibrin',[C('FIBTEM','A10','lt','10'),C('EXTEM','A10','lt','40')],'fibrinogen_replacement',FIB,['moh_cardiac']),
 R('platelets',[C('FIBTEM','A10','gt','10'),C('EXTEM','A10','lt','40')],'platelets',PLT,['moh_cardiac']),
 R('plasma',[C('EXTEM','CT','gt','100','s'),C('INTEM','CT','gt','240','s')],'plasma',PLASMA,['moh_cardiac'])],['moh_cardiac'],phases=['post_protamine']),
 _profile('rotem_delta_trauma_reference','ROTEM delta S critical bleeding — SCGH reference',['rotem_delta_single_use'],'trauma',[
 R('fibrin',[C('FIBTEM S','A5','le','10')],'fibrinogen_replacement',FIB,['delta_trauma']),
 R('plasma',[C('EXTEM S','CT','gt','80','s'),C('FIBTEM S','A5','gt','10')],'plasma',PLASMA,['delta_trauma'])],['delta_trauma']),
 _profile('rotem_sigma_trauma_reference','ROTEM sigma Complete trauma — FEISTY fibrinogen reference',['rotem_sigma_complete'],'trauma',[
 R('fibrin',[C('FIBTEM C','A5','le','10')],'fibrinogen_replacement',FIB,['sigma_trauma'])],['sigma_trauma'],limitations=['Fibrinogen branch only; no plasma or platelet thresholds borrowed from delta. Verify local cartridge/reagent generation against the study before adoption.']),
 _profile('rotem_sigma_cardiac_reference','ROTEM sigma + HEP cardiac — Fiameni reference',['rotem_sigma_complete_hep'],'cardiac',[
 R('fibrin',[C('FIBTEM C','MCF','lt','9')],'fibrinogen_replacement',FIB,['sigma_cardiac']),
 R('platelets',[C('FIBTEM C','MCF','gt','9'),C('EXTEM C','A10','lt','40')],'platelets',PLT,['sigma_cardiac']),
 R('plasma',[C('FIBTEM C','MCF','gt','9'),C('EXTEM C','CT','gt','90','s')],'plasma',PLASMA,['sigma_cardiac'])],['sigma_cardiac'],phases=['post_protamine']),
 _profile('rotem_delta_obstetric_reference','ROTEM delta postpartum — Tampere trial reference',['rotem_delta_liquid'],'obstetric',[
 R('fibrin',[C('FIBTEM','A5','lt','12')],'fibrinogen_concentrate','The postpartum-haemorrhage trial used fibrinogen concentrate when FIBTEM A5 was below 12 mm during bleeding.',['obstetric'])],['obstetric'],phases=['postpartum']),
 _profile('rotem_delta_liver_reference','ROTEM delta liver transplant — Zamper reference',['rotem_delta_liquid'],'liver_transplant',[
 R('fibrin',[C('EXTEM','A5','lt','25'),C('FIBTEM','A10','lt','10')],'fibrinogen_replacement',FIB,['liver']),
 R('platelets',[C('EXTEM','A5','lt','25'),C('FIBTEM','A10','gt','10')],'platelets',PLT,['liver']),
 R('plasma',[C('INTEM','CT','gt','240','s'),C('HEPTEM','CT','ge_other','0','s')],'plasma',PLASMA,['liver'],compare_with=['INTEM','CT'])],['liver'],phases=['pre_anhepatic','anhepatic','reperfusion','neohepatic'],requires_context={'diffuse_bleeding':True,'physiological_conditions_met':True},context_notes='Source Figure 1 requires temperature >35 C, ionised calcium >1 mmol/L, pH >7.20 and haemoglobin >8 g/dL. Document that these conditions have been checked.',limitations=['Reference study excluded acute liver failure, combined organ transplant and retransplantation within 30 days. PCC and antifibrinolytic branches require additional specific protocols.'],exclusion_keys=['acute_liver_failure','combined_organ_transplant','retransplant_within_30_days']),
]



def device_profiles():
    """Detached JSON-safe device inventory; callers cannot mutate the registry."""
    return deepcopy(_DEVICES)


def protocol_profiles():
    return deepcopy(_PROTOCOLS)
