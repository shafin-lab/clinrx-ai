import {laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryResultText} from './laboratoryPresentation';
import {type Catalog,type Evidence,key,pin,stable} from '../api/rf2Client';
import {asObject} from '../respiratory/respiratoryModel';
import {compareRespiratoryInstants} from '../respiratory/exactTime';
import type {MicroState} from '../api/microTypes';
import {giLabLabels} from './types';
export interface GIScope {patient:string;encounter:string;start:string;end:string}
export interface GILab {evidence:Evidence;component:Record<string,unknown>;concept:string;label:string;text:string;time:string|null;collectionText:string;}
export function giTime(e:Evidence):string|null{if(e.fact.kind==='laboratory_report')return laboratoryCollection(e.fact).instant;const times=asObject(e.fact.times),t=asObject(times.occurred);return t.status==='known'&&t.precision==='instant'&&typeof t.value==='string'?t.value:null;}
function available(e:Evidence,end:string){const observed=giTime(e);if(observed&&(compareRespiratoryInstants(observed,end)??1)>0)return false;return ['reported','available'].every(name=>{const t=asObject(asObject(e.fact.times)[name]),at=t.upper??t.value;if(typeof at!=='string')return true;const cmp=compareRespiratoryInstants(at,end);return cmp!==null&&cmp<=0;});}
export function gastrointestinalModel(c:Catalog|undefined,requested:GIScope,micro?:MicroState){
 const empty={valid:false,signature:'',labs:[] as GILab[],records:[] as Evidence[],unmapped:[] as Evidence[],evidence:[] as Evidence[],context:[] as Evidence[]};
 if(!c)return empty;
 const scope=c.combined.context.scope,all=[...c.items,...c.laboratory_reports,...(c.respiratory_records??[]),...(c.gastrointestinal_records??[])],seen=new Set<string>();
 if(c.execution_enabled!==false||c.combined.execution_enabled!==false||c.repository!==c.cutoff.repository_id||scope.repository_cutoff.repository_id!==c.repository||scope.repository_cutoff.fact_watermark!==c.cutoff.fact_watermark||scope.patient_id!==requested.patient||scope.encounter_id!==requested.encounter||compareRespiratoryInstants(scope.review_start,requested.start)!==0||compareRespiratoryInstants(scope.review_end,requested.end)!==0||all.some(e=>{const k=key(pin(e));if(seen.has(k))return true;seen.add(k);return e.repository!==c.repository||e.ingestion.repository_id!==c.repository||e.ingestion.ingestion_sequence>e.cutoff||e.cutoff>c.cutoff.fact_watermark||e.fact.binding.target.patient_id!==requested.patient||e.fact.binding.target.encounter_id!==requested.encounter;}))return empty;
 const visible=c.laboratory_reports.filter(e=>available(e,requested.end)),labs:GILab[]=[],unmapped:Evidence[]=[];
 for(const e of visible){let unsupported=false;for(const raw of (Array.isArray(e.fact.components)?e.fact.components:[])){
  const component=asObject(raw),concept=String(component.mapped_concept??'');
  if(component.mapping_status!=='mapped'||!component.mapping_version){unsupported=true;continue;}if(!giLabLabels[concept])continue;
  const result=asObject(component.result),status=String(e.fact.record_status??'unknown'),report=String(e.fact.report_status??'unknown');
  const text=status==='withdrawn'?'Withdrawn source record':status!=='recorded'?'Record '+status:!['final','corrected','preliminary','interim'].includes(report)?'Report '+report:result.kind==='unavailable'?String(result.status)+': '+String(result.reason):laboratoryResultText(component);
  const collection=laboratoryCollection(e.fact);
  labs.push({evidence:e,component,concept,label:giLabLabels[concept],text:text.trim(),time:collection.instant,collectionText:collection.text});
 }if(unsupported)unmapped.push(e);}
 const records=(c.gastrointestinal_records??[]).filter(e=>available(e,requested.end));
 const contributing=[...new Map([...labs.map(x=>x.evidence),...records,...unmapped].map(e=>[key(pin(e)),e])).values()];
 const context=c.items.filter(e=>/medication|antimicrobial/.test(e.fact.kind)||e.metadata?.chart||['circulatory_pressure','circulatory_cardiac','circulatory_lactate','circulatory_vasoactive','observation'].includes(e.fact.kind));
 const ms=micro?.assembly.request.scope,microConfirmed=!!ms&&!!micro&&ms.repository_cutoff.repository_id===c.repository&&ms.repository_cutoff.fact_watermark===c.cutoff.fact_watermark&&ms.patient_id===requested.patient&&ms.encounter_id===requested.encounter&&compareRespiratoryInstants(ms.review_start,requested.start)===0&&compareRespiratoryInstants(ms.review_end,requested.end)===0;
 const microEvidence:Evidence[]=microConfirmed?(micro!.assembly.snapshot.items??[]).map(item=>({repository:c.repository,fact:item.fact as Evidence['fact'],canonical_fact:stable(item.fact),digest:item.expected_digest,ingestion:item.ingestion as Evidence['ingestion'],cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:String(item.fact.kind),id:item.fact.id,version:item.fact.revision},superseded:false,metadata:null})):[];
 const evidence=[...new Map([...contributing,...context,...microEvidence].map(e=>[key(pin(e)),e])).values()];
 return {valid:true,signature:stable([requested.patient,requested.encounter,requested.start,requested.end,c.repository,{microbiology:microConfirmed}]),labs,records,unmapped,evidence,context};
}
/** The saved receipt retains exact cutoff pins; current matching ignores an unrelated newer repository watermark. */
export function giReviewIdentity(model:ReturnType<typeof gastrointestinalModel>){return stable([model.signature,model.evidence.map(e=>[e.repository,e.fact.kind,e.fact.id,e.fact.revision,e.digest,e.ingestion.ingestion_sequence]).sort((a,b)=>stable(a).localeCompare(stable(b)))]);}

/** A signature is a receipt label, never a substitute for validating its actual source support. */
export function giReviewMatches(review:import('../clinical/savedReviewStore').SavedReview<unknown>,model:ReturnType<typeof gastrointestinalModel>){
 if(!model.valid||review.domain!=='M11'||review.snapshot.signature!==giReviewIdentity(model))return false;
 const scope=JSON.parse(model.signature) as string[];
 if(review.patient!==scope[0]||review.encounter!==scope[1]||review.repository!==scope[4]||compareRespiratoryInstants(review.period.start,scope[2])!==0||compareRespiratoryInstants(review.period.end,scope[3])!==0)return false;
 const cutoff=asObject(review.snapshot.cutoff);if(cutoff.repository_id!==review.repository||!Number.isSafeInteger(cutoff.fact_watermark))return false;
 const pins=review.snapshot.pins.map(p=>asObject(p));if(pins.length!==model.evidence.length||pins.some(p=>p.repository!==review.repository||typeof p.kind!=='string'||typeof p.id!=='string'||typeof p.version!=='string'||typeof p.digest!=='string'||!Number.isSafeInteger(p.ingestion)||!Number.isSafeInteger(p.cutoff)||Number(p.cutoff)<Number(p.ingestion)||Number(p.cutoff)>Number(cutoff.fact_watermark)))return false;
 const identity=(p:Record<string,unknown>)=>stable([p.repository,p.kind,p.id,p.version,p.digest,p.ingestion]);
 const actual=pins.map(identity).sort(),expected=model.evidence.map(e=>stable([e.repository,e.fact.kind,e.fact.id,e.fact.revision,e.digest,e.ingestion.ingestion_sequence])).sort();
 return new Set(actual).size===actual.length&&stable(actual)===stable(expected);
}
