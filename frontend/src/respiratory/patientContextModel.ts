import {type Catalog,type Evidence,key,pin} from '../api/rf2Client';
import {bedsideModel,type BedsideScope} from '../hemodynamics/bedsideModel';
import {asObject,measurementText,respiratoryModel,respiratoryTime} from './respiratoryModel';
import type {RespiratoryRecord} from './respiratoryTypes';
import {compareRespiratoryInstants} from './exactTime';
export interface SharedVital {evidence:Evidence;concept:string;text:string;time:string;quality:string;method:string}
/** Read-only views of original decoded evidence. No converted facts or second store. */
export function sharedPatientContext(catalog:Catalog|undefined,requested:BedsideScope){
 const empty={valid:false,signature:'',evidence:[] as Evidence[],vitals:{spo2:[] as SharedVital[],respiratory_rate:[] as SharedVital[]}};
 const respiratory=respiratoryModel(catalog,requested),circ=bedsideModel(catalog?.combined.circulatory,requested);
 if(!catalog||!respiratory.valid||!circ.valid||respiratory.signature!==circ.signature)return empty;
 const evidence=[...catalog.items,...catalog.laboratory_reports,...(catalog.respiratory_records??[])],vitals={spo2:[] as SharedVital[],respiratory_rate:[] as SharedVital[]};
 for(const e of respiratory.items){
  if(e.fact.kind==='respiratory_record'){
   const f=e.fact as RespiratoryRecord;
   if(f.category!=='bedside')continue;
   for(const concept of ['spo2','respiratory_rate'] as const)for(const m of f.measurements.filter(m=>m.concept===concept&&m.role!=='set')){
    const text=f.record_status!=='recorded'?'Source '+f.record_status:!['final','corrected','preliminary','interim'].includes(f.report_status)?'Report '+f.report_status:m.quality!=='usable'||f.conflict==='unresolved'?'Quality needs review':measurementText(m);
    vitals[concept].push({evidence:e,concept,text,time:f.times.occurred.value!,quality:m.quality,method:m.method??'Method not supplied'});
   }
  }else if(e.fact.kind==='circulatory_oxygen'&&['spo2','respiratory_rate'].includes(String(e.fact.concept))){
   const f=e.fact,q=asObject(asObject(f.acquisition).quality),r=asObject(f.result),amount=asObject(r.quantity),concept=f.concept as keyof typeof vitals;
   const text=f.record_status!=='recorded'?'Source '+String(f.record_status):q.status!=='acceptable'||f.conflict==='unresolved'?'Quality needs review':typeof amount.value==='string'?String(r.comparator??'=') .replace(/^=$/,'')+amount.value+' '+String(asObject(amount.unit).raw??''):'Result unavailable';
   vitals[concept].push({evidence:e,concept,text,time:respiratoryTime(e)!,quality:String(q.status??'unknown'),method:String(asObject(f.acquisition).method??'Method not supplied')});
  }
 }
 for(const rows of Object.values(vitals))rows.sort((a,b)=>compareRespiratoryInstants(b.time,a.time)??0);
 return {valid:true,signature:respiratory.signature,evidence,vitals};
}
export const sharedEvidencePins=(evidence:Evidence[])=>evidence.map(e=>({repository:e.repository,kind:e.fact.kind,id:e.fact.id,version:e.fact.revision,digest:e.digest,ingestion:e.ingestion.ingestion_sequence,cutoff:e.cutoff}));
export function uniqueSharedEvidence(evidence:Evidence[]){return [...new Map(evidence.map(e=>[key(pin(e)),e])).values()];}
/** Typed source context; native records are not members of the legacy M7 snapshot. */
export function nativeSourceContext(e:Evidence):string|null{
 if(e.fact.kind==='respiratory_record'){
  const f=e.fact as RespiratoryRecord,gas=f.category==='blood_gas',point=gas?f.times.collected:f.times.occurred;
  const at=point.value?`${gas?'Collected':'Observed'} ${point.value} · ${point.precision}`:`${gas?'Collection':'Observation'} time ${point.status.replaceAll('_',' ')}`;
  return `${at} · report ${f.report_status} · record ${f.record_status} · measurement quality ${[...new Set(f.measurements.map(m=>m.quality))].join(', ')||'not recorded'}${f.conflict==='unresolved'?' · unresolved source conflict':''} · source cutoff ${e.cutoff}`;
 }
 if(e.fact.kind==='laboratory_report'){
  const times=asObject(e.fact.times),labels={collected:'Collected',reported:'Reported',available:'Available'};
  return Object.entries(labels).map(([key,label])=>{const t=asObject(times[key]);return `${label} ${t.value??String(t.status??'not recorded').replaceAll('_',' ')}${t.precision?' · '+String(t.precision):''}`;}).join(' · ')+` · report ${String(e.fact.report_status??'unknown')} · source cutoff ${e.cutoff}`;
 }
 return null;
}
