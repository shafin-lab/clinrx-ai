import {key,pin,type Catalog,type Evidence} from '../api/rf2Client';
import {compareRespiratoryInstants as compare} from './exactTime';
import {measurementText} from './respiratoryModel';
import type {RecordedTime,RespiratoryRecord,RespiratorySupportType} from './respiratoryTypes';

export const supportLabels:Record<RespiratorySupportType,string>={room_air:'Room air',nasal_cannula:'Nasal prongs / cannula',simple_mask:'Simple face mask',venturi_mask:'Venturi mask',reservoir_mask:'Reservoir / non-rebreather mask',hfnc:'HFNC',niv:'Non-invasive ventilation',invasive:'Invasive ventilation',other:'Other device',unknown:'Support not recorded'};
export const exactTime=(t:RecordedTime)=>t.status==='known'&&t.precision==='instant'&&t.value!==null&&compare(t.value,t.value)===0?t.value:null;
function scopeConfirmed(c:Catalog){const s=c.combined.context.scope;return c.execution_enabled===false&&c.combined.execution_enabled===false&&c.repository===c.cutoff.repository_id&&s.repository_cutoff.repository_id===c.repository&&s.repository_cutoff.fact_watermark===c.cutoff.fact_watermark;}
function inScope(c:Catalog,e:Evidence){const s=c.combined.context.scope;return e.repository===c.repository&&e.ingestion.repository_id===c.repository&&e.ingestion.ingestion_sequence<=e.cutoff&&e.cutoff<=c.cutoff.fact_watermark&&e.fact.binding.target.patient_id===s.patient_id&&e.fact.binding.target.encounter_id===s.encounter_id;}
function availableBy(record:RespiratoryRecord,at:string){return [record.times.available,record.times.reported].every(t=>{const time=t.upper??t.value??t.lower;return time===null||compare(time,at)!==null&&compare(time,at)!<=0;});}
function airwayEvent(f:RespiratoryRecord){return ['procedure','liberation'].includes(f.category)&&/intubat|extubat|tracheostom/i.test([f.title,f.narrative,...f.measurements.filter(m=>['procedure_type','extubation_status','reintubation'].includes(m.concept)).map(measurementText)].join(' '));}
export function supportLabel(record:RespiratoryRecord){return record.context.support_episode?supportLabels[record.context.support_episode.type]:record.context.oxygen_device??record.title;}
export function supportSummary(record:RespiratoryRecord){return [supportLabel(record),record.context.ventilator_mode,...record.measurements.filter(m=>['oxygen_flow','total_gas_flow','fio2','peep','ipap','epap','pressure_support','inspiratory_pressure','set_tidal_volume','set_respiratory_rate'].includes(m.concept)).map(m=>m.label+': '+measurementText(m))].filter(Boolean).join(' · ');}

/** Original records only; date ordering is a view, never an extra stored event. */
export function respiratorySupportTimeline(c:Catalog,requested?:{patient:string;encounter:string;start:string;end:string}):Evidence[]{
 if(!scopeConfirmed(c))return [];
 const s=c.combined.context.scope,end=s.review_end;
 if(requested&&(requested.patient!==s.patient_id||requested.encounter!==s.encounter_id||compare(requested.start,s.review_start)!==0||compare(requested.end,end)!==0))return [];
 const seen=new Set<string>();
 return (c.respiratory_records??[]).filter(e=>{const f=e.fact as RespiratoryRecord,k=key(pin(e));if(!inScope(c,e)||seen.has(k)||!availableBy(f,end)||!(f.category==='support'||airwayEvent(f)))return false;seen.add(k);const at=exactTime(f.times.occurred);return at===null||compare(at,end)!<=0;}).sort((a,b)=>{const x=exactTime((a.fact as RespiratoryRecord).times.occurred),y=exactTime((b.fact as RespiratoryRecord).times.occurred);return x&&y?compare(x,y)??0:x?-1:y?1:key(pin(a)).localeCompare(key(pin(b)));});
}
export interface SupportResolution {status:'matched'|'unconfirmed'|'none';source?:Evidence;reason:string}
const unavailable=(reason:string):SupportResolution=>({status:'unconfirmed',reason});
function usable(e:Evidence){const f=e.fact as RespiratoryRecord;return !e.superseded&&e.terminal_reference.kind===f.kind&&e.terminal_reference.id===f.id&&e.terminal_reference.version===f.revision&&f.record_status==='recorded'&&['final','corrected','preliminary','interim'].includes(f.report_status)&&f.change_state!=='superseded'&&f.conflict!=='unresolved';}
export function supportAtTime(c:Catalog,at:string):SupportResolution{
 if(!scopeConfirmed(c)||compare(at,at)!==0||compare(at,c.combined.context.scope.review_end)!>0)return unavailable('Patient scope or review time is unconfirmed.');
 const timeline=respiratorySupportTimeline(c),points=timeline.filter(e=>(e.fact as RespiratoryRecord).category==='support');
 if(points.some(e=>exactTime((e.fact as RespiratoryRecord).times.occurred)===null))return unavailable('A support source has no exact start time; sequence is uncertain.');
 const preceding=points.filter(e=>compare(exactTime((e.fact as RespiratoryRecord).times.occurred)!,at)!<=0);
 if(!preceding.length)return {status:'none',reason:'No support record establishes support at this time.'};
 const source=preceding.at(-1)!,record=source.fact as RespiratoryRecord,start=exactTime(record.times.occurred)!;
 if(source.cutoff!==c.cutoff.fact_watermark)return unavailable('Latest support is from an older cutoff; current source status is unconfirmed.');
 if(preceding.filter(e=>compare(exactTime((e.fact as RespiratoryRecord).times.occurred)!,start)===0).length!==1)return unavailable('Different support records share this start time.');
 if(!usable(source))return unavailable('Latest support is withdrawn, conflicted, historical or unconfirmed.');
 if(timeline.some(e=>{const f=e.fact as RespiratoryRecord;if(f.category==='support'||!usable(e))return false;const t=exactTime(f.times.occurred),statuses=f.measurements.filter(m=>['procedure_status','extubation_status'].includes(m.concept)).map(m=>m.result.kind==='unavailable'?m.result.reason:m.result.raw_value).join(' ');if(/planned|deferred|cancelled|not performed|not_performed/i.test(statuses||f.title))return false;return t===null||compare(t,start)!>0&&compare(t,at)!<=0;}))return unavailable('An airway event intervenes or has uncertain timing; subsequent support must be established.');
 for(const older of preceding){if(older===source)continue;const f=older.fact as RespiratoryRecord,end=f.context.support_episode?.until;if(end&&exactTime(end)&&compare(exactTime(end)!,at)!>0&&usable(older))return unavailable('Explicit support episodes overlap; no current settings are selected.');}
 const episode=record.context.support_episode;
 if(!episode&&compare(start,at)!==0)return unavailable('A point observation does not establish continuing support.');
 if(episode?.type==='unknown')return unavailable('Support type is explicitly unknown.');
 if(episode?.until){const end=exactTime(episode.until);if(!end||compare(end,at)!<=0)return unavailable('The recorded support episode has ended or its ending is uncertain.');}
 return {status:'matched',source,reason:episode?'Recorded support episode at this time.':'Exact simultaneous support observation.'};
}
