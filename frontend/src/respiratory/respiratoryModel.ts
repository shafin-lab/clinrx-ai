import {key,pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import {metricLabel} from './respiratoryCatalog';
import type {RecordedTime,RespiratoryContext,RespiratoryMeasurement,RespiratoryRecord} from './respiratoryTypes';
import {compareRespiratoryInstants} from './exactTime';
export interface RespiratorySample {id:string;record:RespiratoryRecord;evidence:Evidence[];issues:string[];legacy:boolean}
export const asObject=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
export const blankTime=():RecordedTime=>({status:'not_recorded',precision:'unknown',value:null,lower:null,upper:null,uncertainty:null});
export const blankRespiratoryContext=():RespiratoryContext=>({sample_type:'unknown',specimen_id:null,collection_site:null,oxygen_device:null,ventilator_mode:null,airway_id:null,position:null,population:'unknown',settings_confirmed_at_sample:null,passive:null,occlusion_confirmed:null,reference_equation:null});
export function respiratoryTime(e:Evidence):string|null {
 const f=e.fact;
 if(f.kind==='respiratory_record'){const record=f as RespiratoryRecord;return record.category==='blood_gas'?record.times.collected.value:record.times.occurred.value;}
 if(f.kind==='laboratory_report'){const times=asObject(f.times);for(const k of ['collected','reported','available']){const p=asObject(times[k]);if(typeof p.value==='string')return p.value;}}
 for(const p of [asObject(asObject(f.blood_gas_context).collected),asObject(f.occurred),asObject(f.available)]){const value=asObject(p.recorded).value??p.source_timestamp;if(typeof value==='string')return value;}
 return null;
}
function exactObservationTime(e:Evidence):string|null {
 if(e.fact.kind==='respiratory_record'){
  const times=(e.fact as RespiratoryRecord).times;
  // Report/availability times establish knowledge, not physiological collection.
  const point=(e.fact as RespiratoryRecord).category==='blood_gas'?times.collected:times.occurred;
  return point?.status==='known'&&point.precision==='instant'?point.value:null;
 }
 const gas=asObject(e.fact.acquisition).method==='blood_gas';
 for(const assertion of gas?[asObject(e.fact.blood_gas_context).collected]:[e.fact.occurred]){
  const source=asObject(assertion),point=asObject(source.recorded);
  if(typeof point.value==='string'){
   if(point.status!=='known'||point.precision!=='instant')return null;
   if(typeof source.source_timestamp==='string'&&compareRespiratoryInstants(source.source_timestamp,point.value)!==0)return null;
   return String(source.source_timestamp??point.value);
  }
 }
 return null;
}
export function respiratoryLabel(e:Evidence):string {if(e.fact.kind==='respiratory_record')return String(e.fact.title);if(e.fact.kind==='laboratory_report')return String(asObject(e.fact.source_panel).raw_display??'Laboratory report');return String(e.fact.concept??e.fact.kind).replaceAll('_',' ');}
/** Display-only removal of redundant lactate zeroes; raw source bytes stay intact. */
export function bedsideResultText(concept:string,text:string){return concept==='lactate'&&/^[+-]?\d+\.\d+$/.test(text)?text.replace(/(\.\d*?[1-9])0+$/,'$1').replace(/\.0+$/,'.0'):text;}
export function measurementText(m:RespiratoryMeasurement){const r=m.result;return r.kind==='unavailable'?`${r.status.replaceAll('_',' ')}: ${r.reason}`:`${r.kind==='numeric'&&r.comparator!=='='?r.comparator:''}${r.kind==='numeric'?bedsideResultText(m.concept,r.raw_value):r.raw_value}${r.kind==='numeric'&&r.unit&&r.unit.code!=='1'?' '+r.unit.raw_display:''}`;}
export function sourceSummary(e:Evidence):string {
 if(e.fact.kind==='respiratory_record'){const f=e.fact as RespiratoryRecord;return f.record_status==='withdrawn'?'Withdrawn source record':f.measurements.length?f.measurements.slice(0,4).map(m=>`${m.label}: ${measurementText(m)}`).join(' · '):f.narrative??f.report_status;}
 if(e.fact.kind==='laboratory_report'){return (Array.isArray(e.fact.components)?e.fact.components:[]).map(x=>{const c=asObject(x),r=asObject(c.result);return `${asObject(c.test_code).raw_display??c.mapped_concept??'Result'}: ${r.raw_value??r.status??'Not recorded'} ${asObject(r.unit).raw_display??''}`.trim();}).join(' · ');}
 const r=asObject(e.fact.result),q=asObject(r.quantity);return typeof q.value==='string'?`${bedsideResultText(e.fact.kind==='circulatory_lactate'?'lactate':String(e.fact.concept??''),q.value)} ${asObject(q.unit).raw??''}`:String(r.raw_value??asObject(e.fact.description).raw_display??r.result_type??'Inspect recorded content');
}
function sourceMeasurement(e:Evidence):RespiratoryMeasurement {
 const f=e.fact,r=asObject(f.result),q=asObject(r.quantity),u=asObject(q.unit),status=asObject(asObject(f.acquisition).quality).status;
 const raw=typeof q.value==='string'?q.value:undefined,unit=typeof u.raw==='string'?u.raw:null;
 return {concept:String(f.concept??'unknown'),label:metricLabel(String(f.concept??'unknown')),result:raw?{kind:'numeric',raw_value:raw,comparator:(r.comparator??'=') as '=',unit:unit?{namespace:'source.recorded.unit',code:unit,version:null,raw_display:unit}:null}:{kind:'unavailable',status:'unavailable',reason:String(r.reason??'No numeric source result')},role:f.production==='source_calculated'?'calculated_by_source':'measured',quality:status==='acceptable'&&f.record_status==='recorded'&&f.conflict!=='unresolved'?'usable':status==='suspect'||f.record_status!=='recorded'||f.conflict==='unresolved'?'suspect':'unknown',method:String(asObject(f.acquisition).method??'unknown')};
}
function legacySample(evidence:Evidence[]):RespiratorySample {
 const first=evidence[0],f=first.fact,c=asObject(f.blood_gas_context),collected=asObject(c.collected),point=asObject(collected.recorded),sample=asObject(f.specimen);
 const at=typeof point.value==='string'?point.value:typeof collected.source_timestamp==='string'?collected.source_timestamp:null;
 const context=blankRespiratoryContext();context.sample_type=String(f.sample_type??'unknown') as RespiratoryContext['sample_type'];context.specimen_id=typeof sample.code==='string'?sample.code:null;context.oxygen_device=typeof asObject(c.oxygen_device).raw_display==='string'?String(asObject(c.oxygen_device).raw_display):null;context.ventilator_mode=typeof asObject(c.ventilator_mode).raw_display==='string'?String(asObject(c.ventilator_mode).raw_display):null;
 const settingsKeys=['fio2','peep','oxygen_device','ventilator_mode'];const settings=stable(settingsKeys.map(k=>c[k]??null));const conflict=evidence.some(e=>stable(settingsKeys.map(k=>asObject(e.fact.blood_gas_context)[k]??null))!==settings);
 const measurements=evidence.map(sourceMeasurement),issues:string[]=[];
 if(conflict)issues.push('Conflicting sample-time settings; oxygenation calculations withheld.');
 if(!at||!context.specimen_id)issues.push('Exact specimen identity or collection time is missing; this source was not combined with other records.');
 // Presence of source settings is not independent confirmation of their alignment.
 context.settings_confirmed_at_sample=conflict?false:null;
 for(const concept of ['fio2','peep']){const q=asObject(c[concept]),unit=asObject(q.unit).raw;if(typeof q.value==='string')measurements.push({concept,label:concept==='fio2'?'Sample-time FiO₂':'Sample-time PEEP',result:{kind:'numeric',raw_value:q.value,comparator:'=',unit:typeof unit==='string'?{namespace:'source.recorded.unit',code:unit,version:null,raw_display:unit}:null},role:'reported',quality:conflict?'suspect':'usable',method:'source_sample_context'});}
 const time=at?{...blankTime(),...point,value:at} as RecordedTime:blankTime();
 const record={...f,kind:'respiratory_record',category:'blood_gas',title:`${String(f.sample_type??'Unknown').replaceAll('_',' ')} blood gas · ${context.specimen_id??f.id}`,source_identity:{issuer_namespace:String(sample.namespace??'legacy'),source_report_id:context.specimen_id??f.id,source_version:f.revision,accession_id:null},times:{occurred:time,collected:time,reported:blankTime(),available:blankTime()},context,measurements,narrative:null,report_status:'final',change_state:'original',record_status:evidence.some(e=>e.fact.record_status!=='recorded')?'invalid':'recorded',linked_sources:evidence.map(e=>pin(e).reference),supersedes:null,correction_reason:null} as RespiratoryRecord;
 return {id:evidence.map(e=>key(pin(e))).join('|'),record,evidence,issues,legacy:true};
}
export function respiratoryModel(catalog:Catalog|undefined,requested:{patient:string;encounter:string;start:string;end:string}){
 const empty={valid:false,signature:'',items:[] as Evidence[],contextItems:[] as Evidence[],samples:[] as RespiratorySample[],laboratory:[] as Evidence[]};
 if(!catalog)return empty;
 const c=catalog,scope=c.combined.context.scope,sameTime=(a:string,b:string)=>compareRespiratoryInstants(a,b)===0,records=c.respiratory_records??[];
 const all=[...c.items,...c.laboratory_reports,...records],seen=new Set<string>();
 if(c.execution_enabled!==false||c.combined.execution_enabled!==false||c.repository!==c.cutoff.repository_id||scope.patient_id!==requested.patient||scope.encounter_id!==requested.encounter||!sameTime(scope.review_start,requested.start)||!sameTime(scope.review_end,requested.end)||scope.repository_cutoff.repository_id!==c.repository||scope.repository_cutoff.fact_watermark!==c.cutoff.fact_watermark||!all.every(e=>{const k=key(pin(e));if(seen.has(k))return false;seen.add(k);return e.repository===c.repository&&(e.fact.kind==='respiratory_record'?e.cutoff<=c.cutoff.fact_watermark:e.cutoff===c.cutoff.fact_watermark)&&e.ingestion.ingestion_sequence<=e.cutoff&&e.ingestion.repository_id===c.repository&&e.ingestion.ingestion_sequence<=c.cutoff.fact_watermark&&e.fact.binding.target.patient_id===requested.patient&&e.fact.binding.target.encounter_id===requested.encounter;}))return empty;
 const eligible=[...c.items.filter(e=>e.fact.kind==='circulatory_oxygen'||e.fact.kind==='circulatory_lactate'||e.fact.kind==='circulatory_event'&&/ventilat|respirat|airway|prone|intubat/i.test(stable(e.fact))),...records];
 const inPeriod=(e:Evidence)=>{const at=exactObservationTime(e);if(!at)return false;const afterStart=compareRespiratoryInstants(at,requested.start),beforeEnd=compareRespiratoryInstants(at,requested.end);return afterStart!==null&&beforeEnd!==null&&afterStart>=0&&beforeEnd<=0;};
 const items=eligible.filter(inPeriod),contextItems=eligible.filter(e=>!inPeriod(e));
 const groups=new Map<string,Evidence[]>();
 for(const e of items.filter(e=>e.fact.kind==='circulatory_oxygen'&&asObject(e.fact.acquisition).method==='blood_gas')){
  const context=asObject(e.fact.blood_gas_context),specimen=asObject(e.fact.specimen),collected=asObject(context.collected),point=asObject(collected.recorded),at=point.value??collected.source_timestamp;
  const id=specimen.code&&at?stable([specimen.namespace,specimen.code,specimen.version,e.fact.sample_type,at]):key(pin(e));groups.set(id,[...(groups.get(id)??[]),e]);
 }
 const samples:RespiratorySample[]=[...[...groups.values()].map(legacySample),...items.filter(e=>e.fact.kind==='respiratory_record'&&((e.fact as RespiratoryRecord).category==='blood_gas'||(e.fact as RespiratoryRecord).measurements.some(m=>m.result.kind==='numeric'))).map(e=>({id:key(pin(e)),record:e.fact as RespiratoryRecord,evidence:[e],issues:[] as string[],legacy:false}))];
 return {valid:true,signature:JSON.stringify([scope.patient_id,scope.encounter_id,scope.review_start,scope.review_end,c.repository,c.cutoff.fact_watermark]),items,contextItems,samples,laboratory:c.laboratory_reports};
}

/** Group original observations by concept; never combine specimens or choose a current value. */
export function groupRespiratoryObservations(items:Evidence[]){
 const order=['ph','paco2','pao2','bicarbonate','base_excess','sao2','scvo2','svo2','hemoglobin','lactate','spo2','respiratory_rate'];
 const groups=new Map<string,Evidence[]>();
 for(const e of items){const concept=e.fact.kind==='circulatory_lactate'?'lactate':String(e.fact.concept??e.fact.kind);groups.set(concept,[...(groups.get(concept)??[]),e]);}
 return [...groups].sort(([a],[b])=>{const x=order.indexOf(a),y=order.indexOf(b);return (x<0?order.length:x)-(y<0?order.length:y)||a.localeCompare(b);}).map(([concept,rows])=>({concept,items:[...rows].sort((a,b)=>{const x=respiratoryTime(a),y=respiratoryTime(b);return x&&y?compareRespiratoryInstants(y,x)??0:x?-1:y?1:0;})}));
}
