import type {Item} from '../api/microTypes';
import {stable} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import {record} from '../demo/evidencePresentation';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import type {AutomaticRenalModel} from './automaticRenalModel';
import {blankMedicineAssessment,medicineIndications,type MedicineAssessment,ANIDULAFUNGIN_SOURCE} from './medicationDoseModel';
import {DOSE_PROFILE_VERSION,profileName,profileSources,type DoseSource} from './renalDoseModel';
import {orderReference,ownedMetadata,therapyDose,therapyTime,type TherapyCourse} from './therapyModel';

export interface ReviewScope {repository:string;patient:string;encounter:string;orderId:string}
export interface ReviewDependencies {product:string;treatment:string;patient:string;rationale:string;history:string;profile:string}
export interface SavedDoseReview {version:1;id:string;reviewer:string;savedAt:string;cutoff:number;reviewEnd:string;assessment:MedicineAssessment;dependencies:ReviewDependencies;evidence:DoseSource[]}
export interface DoseReviewLog {version:1;scope:ReviewScope;reviews:SavedDoseReview[]}
const groups=['product','treatment','patient','rationale','history','profile'] as const;
const instant=(s:unknown):s is string=>typeof s==='string'&&compare(s,s)===0;
const bounded=(s:unknown,max=256):s is string=>typeof s==='string'&&s.length>0&&s.length<=max;
const exact=(v:unknown,keys:string[])=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join()!==[...keys].sort().join())throw Error('Saved review structure is invalid. Original bytes were preserved.');return v as Record<string,unknown>;};

export function scopeFor(course:TherapyCourse,model:AutomaticRenalModel):ReviewScope|undefined {
 return course.order&&model.scope?{repository:model.scope.repository,patient:model.scope.patient,encounter:model.scope.encounter,orderId:course.order.fact.id}:undefined;
}
export const reviewKey=(scope:ReviewScope)=>'clinrx.dose-reviews.v1.'+encodeURIComponent(stable(scope));
export function initialMedicineAssessment(course:TherapyCourse):MedicineAssessment {
 const review=course.order&&ownedMetadata(course.order)?.dose_review;
 return review?{indication:review.context.indication,phase:review.context.phase,infusion:review.context.infusion,empiricReviewed:review.basis==='empiric',productReviewed:false}:{...blankMedicineAssessment,indication:medicineIndications(course.medicine).find(i=>i.label===record(course.order?.fact).recorded_indication)?.id??''};
}
export function dependenciesFor(course:TherapyCourse,model:AutomaticRenalModel,cultures:Item[],history:Item[],assessment:MedicineAssessment):ReviewDependencies {
 const f=record(course.order?.fact),a=record(f.antimicrobial),dose=record(f.prescribed_dose),name=profileName(course.medicine);
 const exceptional=history.filter(i=>{
  const ref=orderReference(i);if(!ref||ref.id!==course.order?.fact.id)return false;
  const time=therapyTime(i);if(time&&model.scope&&(compare(time,model.scope.end)!>0||Date.parse(time)<Date.parse(model.scope.end)-7*86400000))return false;
  return assessment.phase==='initiation'||i.fact.kind!=='antimicrobial_administration'||!time||record(i.fact).completion!=='completed'||therapyDose(i)!==therapyDose(course.order!)||stable(record(i.fact).route)!==stable(f.route);
 }).map(i=>[i.fact.kind,i.fact.id,i.fact.revision,i.expected_digest]).sort((a,b)=>stable(a).localeCompare(stable(b)));
 return {
  product:stable({medicine:course.medicine,identity:{canonical_id:a.canonical_id,ingredient_ids:a.ingredient_ids,source_code:a.source_code,product:a.product,formulation:a.formulation,raw_display:a.raw_display,mapping_status:a.mapping_status},route:f.route,basis:dose.basis,basis_detail:dose.basis_detail,unit:record(dose.amount).unit}),
  treatment:stable({dose:f.prescribed_dose,schedule:f.schedule,frequency:f.frequency,status:f.order_status,start:f.intended_start,end:f.intended_end,purpose:f.therapy_purpose,priorReview:course.order&&ownedMetadata(course.order)?.dose_review?.context}),
  patient:stable({inputs:model.inputs,context:model.context??null,eligible:model.routineEligible,crcl:model.crcl??null,reasons:[...model.reasons].sort()}),
  rationale:stable({indication:f.recorded_indication??'',cultures:cultures.filter(i=>String(i.fact.kind).startsWith('microbiology_')||String(i.fact.kind).startsWith('blood_culture_')).map(i=>[i.fact.kind,i.fact.id,i.fact.revision,i.expected_digest]).sort((a,b)=>stable(a).localeCompare(stable(b)))}),
  history:stable(exceptional),
  profile:stable(course.medicine.toLowerCase()==='anidulafungin'?['anidulafungin-smPC-2026-10-26/1',ANIDULAFUNGIN_SOURCE]:[DOSE_PROFILE_VERSION,name?profileSources[name]:'unsupported'])
 };
}
export function evaluateReview(saved:SavedDoseReview,dependencies:ReviewDependencies,model:AutomaticRenalModel,course:TherapyCourse){
 const changed=groups.filter(g=>saved.dependencies[g]!==dependencies[g]),assessment={...saved.assessment},reasons:string[]=[];
 const descriptions:Record<typeof groups[number],string>={product:'Product, formulation, route or dose basis changed.',treatment:'Prescription dose, schedule or treatment context changed.',patient:'Patient values or renal, support or safety context changed.',rationale:'Treatment indication or culture evidence changed.',history:'Previous non-delivery or dose history changed.',profile:'The maintained dose reference changed.'};
 for(const g of changed)reasons.push(descriptions[g]);
 if(changed.includes('product')){assessment.productReviewed=false;assessment.infusion='';}
 if(changed.includes('rationale')){assessment.empiricReviewed=false;try{if(record(parseRF2JSON(saved.dependencies.rationale)).indication!==record(parseRF2JSON(dependencies.rationale)).indication)assessment.indication=initialMedicineAssessment(course).indication;}catch{assessment.indication='';}}
 if(changed.includes('treatment')||changed.includes('history'))assessment.phase='';
 if(model.scope&&(model.scope.cutoff<saved.cutoff||compare(model.scope.end,saved.reviewEnd)!<0))reasons.push('An earlier evidence cutoff or historical review period is selected.');
 if(!model.routineEligible)reasons.push(...model.reasons);
 if(course.conflict||record(course.order?.fact).order_status!=='active')reasons.push('The exact active prescription requires source review.');
 return {valid:reasons.length===0,reasons:[...new Set(reasons)],changed,assessment};
}

export function readReviewLog(bytes:string,scope:ReviewScope):DoseReviewLog {
 if(bytes.length>1048576)throw Error('Saved review log exceeds its bound. Original bytes were preserved.');
 const log=exact(parseRF2JSON(bytes),['version','scope','reviews']);
 exact(log.scope,['repository','patient','encounter','orderId']);
 if(log.version!==1||stable(log.scope)!==stable(scope)||!Array.isArray(log.reviews)||!log.reviews.length||log.reviews.length>50)throw Error('Saved review scope or version differs. Original bytes were preserved.');
 const ids=new Set<string>();
 for(const raw of log.reviews){
  const r=exact(raw,['version','id','reviewer','savedAt','cutoff','reviewEnd','assessment','dependencies','evidence']);
  if(r.version!==1||!bounded(r.id,128)||ids.has(r.id)||!bounded(r.reviewer,128)||r.reviewer.trim()!==r.reviewer||!instant(r.savedAt)||Date.parse(r.savedAt)>Date.now()+1000||!instant(r.reviewEnd)||!Number.isSafeInteger(r.cutoff)||Number(r.cutoff)<1)throw Error('Saved review receipt is invalid. Original bytes were preserved.');
  ids.add(r.id);
  const a=exact(r.assessment,['indication','phase','infusion','productReviewed','empiricReviewed']);
  if(!bounded(a.indication,128)||!['maintenance','initiation'].includes(String(a.phase))||!['short','extended'].includes(String(a.infusion))||a.productReviewed!==true||a.empiricReviewed!==true)throw Error('Saved medicine confirmations are invalid. Original bytes were preserved.');
  const d=exact(r.dependencies,[...groups]);for(const g of groups){if(!bounded(d[g],16384)||stable(parseRF2JSON(d[g] as string))!==d[g])throw Error('Saved dependency identity is invalid. Original bytes were preserved.');}
  if(!Array.isArray(r.evidence)||!r.evidence.length||r.evidence.length>6)throw Error('Saved review evidence is invalid.');
  const roles=new Set<string>();
  for(const rawSource of r.evidence){const s=record(rawSource);exact(s,['role','reference','digest','ingestion',...s.component!==undefined?['component']:[]]);const ref=exact(s.reference,['kind','id','version']);if(!['weight','creatinine','patient_context','ast','isolate','specimen'].includes(String(s.role))||roles.has(String(s.role))||!bounded(ref.kind)||!bounded(ref.id)||!bounded(ref.version)||typeof s.digest!=='string'||!/^[a-f0-9]{64}$/.test(s.digest)||!Number.isSafeInteger(s.ingestion)||Number(s.ingestion)<1||Number(s.ingestion)>Number(r.cutoff)||s.component!==undefined&&!bounded(s.component))throw Error('Saved review evidence is invalid.');roles.add(String(s.role));}
 }
 return log as unknown as DoseReviewLog;
}
export async function appendReview(scope:ReviewScope,review:SavedDoseReview,expected:string|null,current:()=>boolean):Promise<string>{
 if(!navigator.locks)throw Error('Web Locks are required to save this browser review.');
 const key=reviewKey(scope);
 return navigator.locks.request(key,()=>{
  if(!current())throw Error('Patient or treatment context changed while the review waited to save.');
  const existing=localStorage.getItem(key);if(existing!==expected)throw Error('Another tab changed this review. Its saved data was preserved.');
  const prior=existing===null?[]:readReviewLog(existing,scope).reviews;
  if(prior.length>=50)throw Error('This browser review log is full. Existing review history was preserved.');
  const bytes=JSON.stringify({version:1,scope,reviews:[...prior,review]});readReviewLog(bytes,scope);
  if(!current())throw Error('Patient or treatment context changed before the review was saved.');
  localStorage.setItem(key,bytes);if(localStorage.getItem(key)!==bytes)throw Error('Saved review completion could not be confirmed. Reload its receipt before retrying.');
  return bytes;
 });
}
