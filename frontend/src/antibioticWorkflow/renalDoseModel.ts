/** Source-transcribed adult candidate profiles. No unreviewed library dependency. */
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
export interface DoseContext {medicine:string;indication:string;route:string;infusion:string;phase:string;bodySize:string;hepatic:string;special:string;safetyReviewed:boolean;cvvhMode:string;flow:string;flowDefinitionReviewed:boolean;residual:string;downtime:string;hdFlux:string;hdStable:string;hdInterval:string;hdTimingReviewed:boolean;cultureReviewed:boolean;cultureBlock:string;cultureSource:string;empiricReviewed:boolean}
export const blankDoseContext:DoseContext={medicine:'',indication:'',route:'',infusion:'',phase:'',bodySize:'',hepatic:'',special:'',safetyReviewed:false,cvvhMode:'',flow:'',flowDefinitionReviewed:false,residual:'',downtime:'',hdFlux:'',hdStable:'',hdInterval:'',hdTimingReviewed:false,cultureReviewed:false,cultureBlock:'',cultureSource:'',empiricReviewed:false};
export interface Regimen {amount:string;unit:'g'|'mg';route:'IV'|'PO';schedule:string;display:string}
export interface DoseResult {status:'suggested'|'review';reason:string;medicine?:ProfileName;maintenance?:Regimen;initial?:string;band?:string;source?:string;notes?:string[];version:string}
export interface PrescriptionSeed {medicine:string;amount:string;unit:'g'|'mg';dose_detail:string;route:string;schedule:string;indication:string}
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
 if(inputs.support==='none'){
  const estimate=clearance(inputs);if(estimate.error||estimate.limited||calculatedCrCl===undefined||!Number.isFinite(calculatedCrCl)||calculatedCrCl!==estimate.value)return hold('Calculate current CrCl with the selected inputs and clinician-assessed stable renal function. Changing/unknown renal function cannot select a steady-state dose.');
  crcl=calculatedCrCl;band=`CrCl ${crcl.toFixed(2)} mL/min (unrounded value used)`;
 }else if(inputs.support==='crrt'){
  if(c.cvvhMode!=='cvvhd')return hold('Loaded CRRT profiles cover CVVHD only. CVVH and CVVHDF require their own validated profiles.');
  if(!/^\d+(?:\.\d+)?$/.test(c.flow)||Number(c.flow)!==2||!c.flowDefinitionReviewed||c.residual!=='lt10'||c.downtime!=='none')return hold('Confirm CVVHD source conditions: treatment flow 2 L/h, residual native GFR <10 mL/min and uninterrupted delivery. Source flow is not patient net fluid removal. Other settings need a dedicated profile.');
  band='CVVHD · source treatment flow 2 L/h · residual native GFR <10 mL/min · no downtime';
  notes.push('Source general table calls the 2 L/h setting ultrafiltration rate; confirm the actual treatment-flow definition with the dialysis prescription. No dose is derived from Cockcroft–Gault or net fluid removal.');
 }else if(inputs.support==='ihd'){
  if(c.hdFlux!=='high'||c.hdStable!=='stable'||!['48','72'].includes(c.hdInterval)||!c.hdTimingReviewed)return hold('Confirm high-flux intermittent HD, a stable schedule, the next 48/72-hour interval and dialysis-day dose timing. Other schedules require a separate review.');
  band=`High-flux intermittent HD · stable schedule · next interval ${c.hdInterval} h`;
  notes.push('Dialysis-specific schedule; Cockcroft–Gault is not used. Review last/next dialysis and previous doses before giving an initial or post-HD dose.');
 }else return hold('Select a supported kidney-support state. SLED/PIRRT, peritoneal dialysis and unknown support do not inherit intermittent-HD or CRRT doses.');
 const hd=inputs.support==='ihd',crrt=inputs.support==='crrt';let maintenance:Regimen|undefined;
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
