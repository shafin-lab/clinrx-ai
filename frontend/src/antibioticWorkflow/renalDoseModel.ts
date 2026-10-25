/** Source-transcribed adult candidate profiles. No unreviewed library dependency. */
import {pin,stable,type Catalog,type Pin} from '../api/rf2Client';
import {record} from '../demo/evidencePresentation';
import {clearance,type ClearanceInputs} from './patientModel';
export const DOSE_PROFILE_VERSION='ucsf-adult-renal-candidate-2026-10-22.1';
export const DIALYSIS_SOURCE='https://idmp.ucsf.edu/antimicrobial-dosing-intermittent-continuous-hemodialysis';
export const NONDIALYSIS_SOURCE='https://idmp.ucsf.edu/adult-antimicrobial-dosing-non-dialysis';
export const PROFILE_NAMES=['Cefepime','Meropenem','Piperacillin/tazobactam','Ceftriaxone','Cefazolin','Ampicillin/sulbactam','Ciprofloxacin'] as const;
export type ProfileName=typeof PROFILE_NAMES[number];
const aliases:Record<string,ProfileName>={'piperacillin-tazobactam':'Piperacillin/tazobactam','ampicillin-sulbactam':'Ampicillin/sulbactam'};
export function profileName(value:string):ProfileName|undefined{return PROFILE_NAMES.find(n=>n.toLowerCase()===value.trim().toLowerCase())??aliases[value.trim().toLowerCase()];}
export const profileSources:Record<ProfileName,string>={Cefepime:'https://idmp.ucsf.edu/content/cefepime',Meropenem:NONDIALYSIS_SOURCE,'Piperacillin/tazobactam':'https://idmp.ucsf.edu/content/piperacillin-tazobactam-zosyn',Ceftriaxone:'https://idmp.ucsf.edu/content/ceftriaxone',Cefazolin:'https://idmp.ucsf.edu/content/cefazolin','Ampicillin/sulbactam':NONDIALYSIS_SOURCE,Ciprofloxacin:'https://idmp.ucsf.edu/content/ciprofloxacin'};
export const indicationOptions:Record<ProfileName,{id:string;label:string}[]>={
 Cefepime:[{id:'nonsevere',label:'Non-severe infection, including cystitis'},{id:'severe',label:'Severe infection / febrile neutropenia / meningitis / Pseudomonas'}],
 Meropenem:[{id:'standard',label:'Standard dosing'},{id:'meningitis',label:'Meningitis'}],
 'Piperacillin/tazobactam':[{id:'nonpseudomonas',label:'Non-Pseudomonas infection'},{id:'pseudomonas',label:'Documented / suspected Pseudomonas infection'}],
 Ceftriaxone:[{id:'standard',label:'Standard dosing'},{id:'uti',label:'Urinary tract infection'},{id:'meningitis',label:'Meningitis'}],
 Cefazolin:[{id:'uncomplicated',label:'Uncomplicated Gram-positive infection'},{id:'complicated',label:'Gram-negative / complicated Gram-positive infection'}],
 'Ampicillin/sulbactam':[{id:'standard',label:'Standard dosing (excludes CRAB)'}],
 Ciprofloxacin:[{id:'standard',label:'Standard dosing'},{id:'systemic',label:'Pseudomonas / Gram-negative bloodstream / staphylococcal hardware induction'}],
};
export interface DoseContext {medicine:string;indication:string;route:string;infusion:string;phase:string;bodySize:string;hepatic:string;special:string;safetyReviewed:boolean;renalFunction:string;support:string;cvvhMode:string;flow:string;flowDefinitionReviewed:boolean;residual:string;downtime:string;hdFlux:string;hdStable:string;hdInterval:string;hdTimingReviewed:boolean;cultureReviewed:boolean;cultureBlock:string;cultureSource:string;empiricReviewed:boolean}
export const blankDoseContext:DoseContext={medicine:'',indication:'',route:'',infusion:'',phase:'',bodySize:'',hepatic:'',special:'',safetyReviewed:false,renalFunction:'unknown',support:'unknown',cvvhMode:'',flow:'',flowDefinitionReviewed:false,residual:'',downtime:'',hdFlux:'',hdStable:'',hdInterval:'',hdTimingReviewed:false,cultureReviewed:false,cultureBlock:'',cultureSource:'',empiricReviewed:false};
export interface Regimen {amount:string;unit:'g'|'mg';route:'IV'|'PO';schedule:string;display:string}
export interface DoseResult {status:'suggested'|'review';reason:string;medicine?:ProfileName;maintenance?:Regimen;initial?:string;band?:string;source?:string;notes?:string[];version:string}
export interface PrescriptionSeed {doseReview?:DoseReview;medicine:string;amount:string;unit:'g'|'mg';dose_detail:string;route:string;schedule:string;indication:string}
const regimen=(amount:string,unit:'g'|'mg',route:'IV'|'PO',schedule:string):Regimen=>({amount,unit,route,schedule,display:`${amount} ${unit} ${route} · ${schedule}`});
export function renalDose(inputs:ClearanceInputs,c:DoseContext,calculatedCrCl?:number):DoseResult{
 const hold=(reason:string):DoseResult=>({status:'review',reason,version:DOSE_PROFILE_VERSION});
 const medicine=profileName(c.medicine);
 if(!medicine)return hold(/vancomycin|amikacin|gentamicin|tobramycin|teicoplanin/i.test(c.medicine)?'Timed concentrations, dose history and a validated monitoring method are required; a fixed CrCl-only dose is not generated.':'No verified executable candidate profile for this exact antibiotic/product. Open the reference library or seek ID/pharmacy review.');
 const age=Number(inputs.age);if(!/^\d+(?:\.\d+)?$/.test(inputs.age)||!Number.isFinite(age)||age<18||age>=140)return hold('Enter an explicit adult age. Pediatric dosing is outside these profiles.');
 if(!indicationOptions[medicine].some(i=>i.id===c.indication))return hold('Select a supported infection indication; no indication is assumed.');
 if(c.route!=='IV'&&!(medicine==='Ciprofloxacin'&&c.route==='PO'))return hold('Select an explicitly supported route.');
 if(c.route==='IV'&&c.infusion!=='short')return hold('These profiles use short infusion only. Extended/continuous infusion needs its separate loading and maintenance protocol.');
 if(!['initiation','maintenance'].includes(c.phase))return hold('Select initiation or maintenance after reviewing previous doses.');
 if(c.bodySize!=='standard'||c.hepatic!=='reviewed'||c.special!=='none'||!c.safetyReviewed)return hold('Confirm body-size applicability, hepatic status, allergy/interaction review and absence of shock, ECMO, pregnancy or other excluded special circumstances.');
 if(c.cultureBlock)return hold(c.cultureBlock);
 if(!c.cultureReviewed||(!c.cultureSource&&!c.empiricReviewed))return hold('Review the exact relevant susceptibility report, or explicitly document an empiric choice when no matching AST is present.');
 if(c.cultureSource){const [cultureMedicine]=c.cultureSource.split('|');if(profileName(cultureMedicine)!==medicine)return hold('The selected culture susceptibility is for a different antibiotic. Select the exact matching AST row or review an empiric choice.');}
 const notes=['Candidate source match; clinician and local-protocol review required before use. This does not establish antibiotic choice, duration or clinical suitability.'];
 if(c.cultureSource)notes.push(`Culture context reviewed: ${c.cultureSource}. Confirm the result is current and relevant to the infection being treated.`);
 if(c.empiricReviewed)notes.push('No matching final susceptible AST was selected; this suggestion is not culture-directed.');
 let crcl:number|undefined,band='',initial:string|undefined;
 if(c.support==='none'){
  const estimate=clearance(inputs);if(estimate.error||c.renalFunction!=='stable'||calculatedCrCl===undefined||!Number.isFinite(calculatedCrCl)||calculatedCrCl!==estimate.value)return hold('Calculate current CrCl and confirm clinician-assessed stable renal function in the dose-review context. Changing/unknown renal function cannot select a steady-state dose.');
  crcl=calculatedCrCl;band=`CrCl ${crcl.toFixed(2)} mL/min (unrounded value used)`;
 }else if(c.support==='crrt'){
  if(c.cvvhMode!=='cvvhd')return hold('Loaded CRRT profiles cover CVVHD only. CVVH and CVVHDF require their own validated profiles.');
  if(!/^\d+(?:\.\d+)?$/.test(c.flow)||Number(c.flow)!==2||!c.flowDefinitionReviewed||c.residual!=='lt10'||c.downtime!=='none')return hold('Confirm CVVHD source conditions: treatment flow 2 L/h, residual native GFR <10 mL/min and uninterrupted delivery. Source flow is not patient net fluid removal. Other settings need a dedicated profile.');
  band='CVVHD · source treatment flow 2 L/h · residual native GFR <10 mL/min · no downtime';
  notes.push('Source general table calls the 2 L/h setting ultrafiltration rate; confirm the actual treatment-flow definition with the dialysis prescription. No dose is derived from Cockcroft–Gault or net fluid removal.');
 }else if(c.support==='ihd'){
  if(c.hdFlux!=='high'||c.hdStable!=='stable'||!['48','72'].includes(c.hdInterval)||!c.hdTimingReviewed)return hold('Confirm high-flux intermittent HD, a stable schedule, the next 48/72-hour interval and dialysis-day dose timing. Other schedules require a separate review.');
  band=`High-flux intermittent HD · stable schedule · next interval ${c.hdInterval} h`;
  notes.push('Dialysis-specific schedule; Cockcroft–Gault is not used. Review last/next dialysis and previous doses before giving an initial or post-HD dose.');
 }else return hold('Select a supported kidney-support state. SLED/PIRRT, peritoneal dialysis and unknown support do not inherit intermittent-HD or CRRT doses.');
 const hd=c.support==='ihd',crrt=c.support==='crrt';let maintenance:Regimen|undefined;
 if(medicine==='Ceftriaxone'){
  if(crrt)return hold('The loaded UCSF source page has no ceftriaxone CRRT row. A non-dialysis or intermittent-HD row is not substituted.');
  maintenance=regimen(c.indication==='uti'?'1':'2','g','IV',c.indication==='meningitis'?'Every 12 hours':'Every 24 hours');notes.push('No renal adjustment for these source indications. Obesity and enterococcal endocarditis combination therapy require a separate assessment.');
 }else if(medicine==='Cefepime'){
  if(hd){maintenance=regimen('2','g','IV','After each HD session');if(c.phase==='initiation')initial='2 g IV once now (source initial-dose step; check prior doses)';}
  else if(crrt)maintenance=regimen('1','g','IV','Every 8 hours');
  else{const n=crcl!;if(n>29&&n<30)return hold('CrCl is in the source gap between 10–29 and 30–60 mL/min. Do not round into a dose band.');const severe=c.indication==='severe';maintenance=n>60?regimen('2','g','IV',severe?'Every 8 hours':'Every 12 hours'):n>=30?regimen('2','g','IV',severe?'Every 12 hours':'Every 24 hours'):n>=10?regimen(severe?'2':'1','g','IV','Every 24 hours'):regimen(severe?'1':'500',severe?'g':'mg','IV','Every 24 hours');}
  notes.push('Short infusion selected. Monitor for neurotoxicity and reassess renal function; extended-infusion loading/timing is not generated.');
 }else if(medicine==='Meropenem'){
  const cns=c.indication==='meningitis';if(hd){maintenance=regimen(cns?'1000':'500','mg','IV','Every evening; confirm HD-day timing');if(c.phase==='initiation')initial=`${cns?'1000':'500'} mg IV once now (check prior doses)`;}
  else if(crrt)maintenance=regimen(cns?'2':'1','g','IV',cns?'Every 12 hours':'Every 8 hours');
  else{const n=crcl!;if(n>25&&n<26)return hold('CrCl is in the source gap between 10–25 and 26–50 mL/min. Do not round into a dose band.');maintenance=n>50?regimen(cns?'2':'1','g','IV','Every 8 hours'):n>=26?regimen(cns?'2':'1','g','IV','Every 12 hours'):regimen(cns?'1':'500',cns?'g':'mg','IV',n>=10?'Every 12 hours':'Every 24 hours');}
  notes.push('Short-infusion profile only; cystic fibrosis and extended-infusion protocols are not selected. CVVHD flow above 2 L/h requires ID/pharmacy review.');
 }else if(medicine==='Piperacillin/tazobactam'){
  if(hd)maintenance=regimen('2.25','g','IV','Every 8 hours; infuse over 30 minutes');
  else if(crrt)maintenance=regimen('4.5','g','IV','Every 8 hours; infuse over 30 minutes');
  else if(c.indication==='pseudomonas'){if(crcl===20)return hold('The source specifies >20 and <20 mL/min for this profile; exactly 20 needs a reviewed boundary convention.');maintenance=crcl!>20?regimen('4.5','g','IV','Every 6 hours; short infusion'):regimen('3.375','g','IV','Every 8 hours; short infusion');}
  else maintenance=crcl!>50?regimen('3.375','g','IV','Every 6 hours; short infusion'):crcl!>=10?regimen('3.375','g','IV','Every 8 hours; short infusion'):regimen('2.25','g','IV','Every 8 hours; short infusion');
  notes.push('Amounts are total piperacillin/tazobactam product mass. ZSFG short-infusion strategy; UCSF prefers a separate extended-infusion protocol where eligible. Do not combine the two regimens.');
 }else if(medicine==='Ampicillin/sulbactam'){
  maintenance=regimen('3','g','IV',hd?'Every 12 hours':crrt?'Every 6 hours':crcl!>30?'Every 6 hours':crcl!>=15?'Every 12 hours':'Every 24 hours');notes.push('Total combination mass. Carbapenem-resistant Acinetobacter dosing is excluded; consult ID/ASP pharmacy.');
 }else if(medicine==='Cefazolin'){
  if(hd){maintenance=regimen(c.hdInterval==='72'?'3':'2','g','IV',`After HD, before the next ${c.hdInterval}-hour interval`);if(c.phase==='initiation')initial='2 g IV once now (check prior doses)';notes.push('Stable-HD alternative: 2 g / 2 g / 3 g post-HD; 3 g precedes the 72-hour interval.');}
  else if(crrt)maintenance=regimen('2','g','IV','Every 12 hours');
  else{const n=crcl!;if(n>29&&n<=30)return hold('The source leaves CrCl >29 through 30 mL/min outside its >30 and 10–29 bands. Do not silently round.');maintenance=regimen(c.indication==='complicated'&&n>=10?'2':'1','g','IV',n>30?'Every 8 hours':n>=10?'Every 12 hours':'Every 24 hours');}notes.push('Deep-seated MSSA or clinical instability may need a different regimen; review with ID/pharmacy.');
 }else if(medicine==='Ciprofloxacin'){
  const iv=c.route==='IV',n=crcl??0,systemic=c.indication==='systemic';let schedule='Every 12 hours';if(hd)schedule='Every evening; confirm HD-day timing';else if(crrt)schedule=iv?'Every 8 hours':'Every 12 hours';else if(n<30)schedule=systemic&&!iv?'Every 12 hours':'Every 24 hours';else if(systemic&&iv&&n>50)schedule='Every 8 hours';const amount=iv?'400':systemic&&!iv&&!hd&&!crrt&&n>50?'750':'500';maintenance=regimen(amount,'mg',iv?'IV':'PO',schedule);
 }
 return {status:'suggested',reason:'Source-based dose suggestion for clinician review',medicine,maintenance,initial,band,source:hd||crrt?DIALYSIS_SOURCE:profileSources[medicine],notes,version:DOSE_PROFILE_VERSION};
}


/** Bounded candidate context, never a validated regimen. Scope owns repository/cutoff
 * once; pins retain only actually used exact sources (up to weight, Cr and AST chain).
 * An absent dose_review is absent from request/history canonical bytes. */
export interface DoseSource {role:'weight'|'creatinine'|'patient_context'|'ast'|'isolate'|'specimen';reference:Pin['reference'];digest:string;ingestion:number;component?:string}
export interface DoseScope {repository:string;patient:string;encounter:string;cutoff:number;start:string;end:string}
export type ReviewContext=Omit<DoseContext,'medicine'|'route'|'cultureSource'|'cultureBlock'|'cultureReviewed'|'empiricReviewed'>;
export interface DoseReview {version:'CandidateDoseReview/v1';profile_version:string;source:string;suggestion:{medicine:string;amount:string;unit:'g'|'mg';route:'IV'|'PO';schedule:string;initial:string|null;band:string};inputs:ClearanceInputs;crcl:number|null;context:ReviewContext;basis:'empiric'|'ast';scope:DoseScope;sources:DoseSource[]}
export function doseScope(catalog:Catalog):DoseScope {const s=catalog.combined.context.scope;return {repository:catalog.repository,patient:s.patient_id,encounter:s.encounter_id,cutoff:catalog.cutoff.fact_watermark,start:s.review_start,end:s.review_end};}
export interface RecordedClearanceInput {value:string;time:string;raw:string;conversion:string;source:DoseSource}
export function recordedClearanceInputs(catalog?:Catalog):{weight?:RecordedClearanceInput;creatinine?:RecordedClearanceInput;reasons:{weight:string[];creatinine:string[]};context:string[];signature:string}{
 const candidates:{weight:RecordedClearanceInput[];creatinine:RecordedClearanceInput[]}={weight:[],creatinine:[]},reasons:{weight:string[];creatinine:string[]}={weight:[],creatinine:[]},context:string[]=[];
 if(!catalog)return {reasons:{weight:['No confirmed snapshot'],creatinine:['No confirmed snapshot']},context,signature:''};
 const scope=doseScope(catalog),seen=new Map<string,string>();
 for(const e of catalog.items){
  const f=e.fact,c=e.metadata?.chart;
  const role=c?.category==='weight'||c?.category==='dosing_weight'||f.kind==='observation'&&f.concept_id==='body-weight'?'weight':f.kind==='observation'&&f.concept_id==='synthetic-serum-creatinine'?'creatinine':undefined;
  if(!role)continue;
  const identity=stable([e.repository,f.kind,f.id,f.revision]),prior=seen.get(identity);if(prior===e.digest)continue;seen.set(identity,e.digest);
  const why:string[]=[],target=f.binding.target;
  if(prior)why.push('Conflicting source digest');
  if(e.repository!==scope.repository||e.ingestion.repository_id!==scope.repository||target.patient_id!==scope.patient||target.encounter_id!==scope.encounter||e.cutoff!==scope.cutoff||e.ingestion.ingestion_sequence>scope.cutoff)why.push('Source scope is not confirmed');
  if(e.superseded||e.terminal_reference.version!==f.revision)why.push('Superseded source');
  let value='',unit='',time='',conversion='Source unit retained';
  if(role==='weight'){
   if(f.kind!=='circulatory_event'||c?.category!=='weight'||c.acquisition!=='measured'||c.purpose!==null)why.push('True measured body weight is not established; dosing weight is excluded');
   if(f.record_status!=='recorded')why.push('Recorded status is not confirmed');
   value=c?.amount??'';unit=c?.unit??'';time=c?.point??'';
   if(unit==='g'){value=String(Number(value)/1000);conversion='Source g ÷ 1000 → kg';}else if(unit!=='kg')why.push('Supported weight unit (kg or g) required');
  }else{
   const v=record(f.value),q=record(v.value),u=record(q.unit),t=record(f.time);
   value=typeof q.value==='string'?q.value:'';unit=typeof u.raw==='string'?u.raw:'';time=t.precision==='instant'&&typeof t.event==='string'?t.event:'';
   if(v.status!=='known'||f.verification!=='verified'||f.conflict!=='none_known')why.push('Known verified non-conflicting creatinine required');
   if(u.status!=='assessed'||u.system!=='UCUM'||u.code!==unit)why.push('Assessed source unit required');
   if(unit==='umol/L'){value=String(Number(value)/88.4);conversion='Source µmol/L ÷ 88.4 → mg/dL';}else if(unit!=='mg/dL')why.push('Supported creatinine unit (mg/dL or umol/L) required');
  }
  const point=Date.parse(time);if(!time||!Number.isFinite(point)||point<Date.parse(scope.start)||point>Date.parse(scope.end))why.push('Exact in-window source time required');
  if(!/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(value)||!Number.isFinite(Number(value))||Number(value)<=0)why.push('Known positive numeric value required');
  context.push(`${role==='weight'?'Weight':'Creatinine'} · ${c?.amount??record(record(f.value).value).value??'unknown'} ${unit} · ${time||'Time unknown'} · ${f.kind}/${f.id}/${f.revision}${why.length?' · '+why.join('; '):''}`);
  if(why.length)reasons[role].push(...why);else{const p=pin(e);candidates[role].push({value,time,raw:`${c?.amount??record(record(f.value).value).value} ${unit}`,conversion,source:{role,reference:p.reference,digest:p.digest,ingestion:p.ingestion}});}
 }
 for(const role of ['weight','creatinine'] as const){if(candidates[role].length>1)reasons[role].push('Multiple distinct recorded sources; no automatic selection');if(!candidates[role].length&&!reasons[role].length)reasons[role].push('No supported measured source in this snapshot');}
 return {weight:!reasons.weight.length&&candidates.weight.length===1?candidates.weight[0]:undefined,creatinine:!reasons.creatinine.length&&candidates.creatinine.length===1?candidates.creatinine[0]:undefined,reasons,context,signature:stable([scope,catalog.items.filter(e=>e.metadata?.chart?.category==='weight'||e.metadata?.chart?.category==='dosing_weight'||['body-weight','synthetic-serum-creatinine'].includes(String(e.fact.concept_id))).map(e=>[pin(e),e.superseded,e.fact,e.metadata])])};
}
