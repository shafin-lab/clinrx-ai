import type {Item} from '../api/microTypes';
import type {Fact,Ref} from '../api/rf2Client';
import {stable} from '../api/rf2Client';
import {record} from '../demo/evidencePresentation';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {antibioticMetadata} from '../api/antibioticClient';
import {antibioticLabel,microKey} from './patientModel';
export function ownedMetadata(item:Item){try{return antibioticMetadata(item.fact as unknown as Fact);}catch{return;}}
export function orderReference(item:Item):Ref|undefined{const bindings=(item.fact.domain_bindings??[]).filter(b=>b.role==='order');if(bindings.length!==1||bindings[0].status!=='resolved'||bindings[0].exact?.kind!=='antimicrobial_order')return;return bindings[0].exact;}
export function therapyTime(item:Item){const f=record(item.fact),time=record(f.kind==='antimicrobial_order'?f.created:f.kind==='antimicrobial_administration'?f.administered:f.occurred);return time.status==='known'&&time.precision==='instant'&&typeof time.value==='string'&&compare(time.value,time.value)===0?time.value:'';}
export function therapyDose(item:Item){const f=record(item.fact);if(f.kind==='antimicrobial_non_delivery')return '—';const dose=record(f.kind==='antimicrobial_order'?f.prescribed_dose:f.administered_dose),q=record(dose.amount),bases:Record<string,string>={per_day:' per day',per_kg_per_dose:'/kg per dose',per_kg_per_day:'/kg per day',per_m2_per_dose:'/m² per dose',unknown:' · basis unknown: '+String(dose.basis_detail??'not recorded')};return typeof q.value==='string'?q.value+' '+String(record(q.unit).raw??'unit not recorded')+(bases[String(dose.basis)]??''):'Not recorded';}
export function therapyDoseDetails(item:Item){const f=record(item.fact),dose=record(f.kind==='antimicrobial_order'?f.prescribed_dose:f.administered_dose);return ['basis_detail','concentration','volume','rate','duration'].flatMap(k=>{const value=dose[k];if(typeof value==='string')return [k.replaceAll('_',' ')+': '+value];const q=record(value);return typeof q.value==='string'?[k+': '+q.value+' '+String(record(q.unit).raw??'unit not recorded')]:[];});}
function identityKey(item:Item){const f=record(item.fact),a=record(f.antimicrobial);return stable([a.canonical_id,a.ingredient_ids,a.product,a.source_code,a.formulation,a.mapping_status,a.raw_display,record(f.route)]);}
function frequency(item:Item){const f=record(item.fact);if(typeof f.schedule==='string')return f.schedule;const frequency=record(f.frequency),interval=record(frequency.interval);return frequency.occurrences&&interval.value?`${frequency.occurrences} administrations per ${interval.value} ${record(interval.unit).raw??'unit not recorded'}`:'Not recorded';}
export function therapyIdentity(item:Item){const f=record(item.fact),m=ownedMetadata(item);return {medicine:antibioticLabel(item),product:String(record(f.antimicrobial).formulation??m?.product??'Product not recorded'),route:String(record(f.route).raw_display??m?.route??'Not recorded')};}
export interface TherapyHistory {item:Item;time:string;dose:string;status:string;reason:string;route:string;orderReference?:Ref}
export interface TherapyCourse {key:string;medicine:string;product:string;route:string;dose:string;frequency:string;order?:Item;administrations:Item[];history:TherapyHistory[];conflict:boolean}
export function therapyCourses(input:Item[]):TherapyCourse[]{
 const items=new Map<string,Item>(),conflicts=new Set<string>();
 for(const i of input){if(!String(i.fact.kind).startsWith('antimicrobial_'))continue;const id=microKey(i),old=items.get(id);if(old&&old.expected_digest!==i.expected_digest)conflicts.add(id);else if(!old)items.set(id,i);}
 const rows:TherapyCourse[]=[],byOrder=new Map<string,TherapyCourse>(),unlinked=new Map<string,TherapyCourse>();
 for(const i of items.values())if(i.fact.kind==='antimicrobial_order'){
  const id=stable([i.fact.kind,i.fact.id]),identity=therapyIdentity(i),row={key:microKey(i),...identity,dose:therapyDose(i),frequency:frequency(i),order:i,administrations:[],history:[],conflict:conflicts.has(microKey(i))};
  const prior=byOrder.get(id);if(prior){prior.conflict=true;row.conflict=true;}else byOrder.set(id,row);rows.push(row);
 }
 for(const i of items.values())if(i.fact.kind!=='antimicrobial_order'){
  const ref=orderReference(i),identity=therapyIdentity(i);let course=ref?byOrder.get(stable([ref.kind,ref.id])):undefined;
  // Exact order binding owns the relationship. Unbound records are never linked by name.
  if(course&&(course.conflict||course.medicine!==identity.medicine||course.product!==identity.product))course=undefined;
  if(!course){const k=stable(['unlinked',identityKey(i),ref??null]);course=unlinked.get(k);if(!course){course={key:k,...identity,dose:'No linked prescription',frequency:'Not established',administrations:[],history:[],conflict:false};unlinked.set(k,course);rows.push(course);}}
  course.administrations.push(i);if(conflicts.has(microKey(i)))course.conflict=true;
 }
 const statuses:Record<string,string>={held:'Held',missed:'Missed',refused:'Refused',cancelled:'Cancelled',not_given:'Not given'};
 for(const row of rows){row.history=row.administrations.map(item=>{const f=record(item.fact);return {item,time:therapyTime(item),dose:therapyDose(item),status:item.fact.kind==='antimicrobial_administration'?'Given':f.status==='other'?String(f.other_status):statuses[String(f.status)]??'Status not recorded',reason:String(f.recorded_reason??ownedMetadata(item)?.indication??'Not recorded'),route:therapyIdentity(item).route,orderReference:orderReference(item)};}).sort((a,b)=>a.time&&b.time?compare(b.time,a.time)??0:a.time?-1:b.time?1:0);}
 return rows;
}
