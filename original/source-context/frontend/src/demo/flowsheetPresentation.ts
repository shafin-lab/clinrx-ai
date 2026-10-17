import {chartEntry,chartSection,type ChartSection} from './chartEntries';
import type {CirculatoryItem} from '../api/circulatoryTypes';
import {record,method,sourceTime,title,words} from './evidencePresentation';
const kinds=new Set(['circulatory_vasoactive','circulatory_pressure','circulatory_cardiac','circulatory_oxygen','circulatory_lactate','circulatory_echo','circulatory_ecg','circulatory_perfusion','circulatory_event','circulatory_assessment']);
const utc=(v:unknown)=>typeof v==='string'&&/^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:Z|\+00:00)$/.test(v)?v.replace('+00:00','Z'):null;
/** Restrictive display placement only. Never rounds, aligns, or infers clinical order. */
export function chartTime(item:CirculatoryItem):string|null{
  if(item.inclusion!=='in_window')return null;
  const t=record(item.fact.collected??item.fact.occurred),r=record(t.recorded);
  if(t.clock!=='verified'||r.status!=='known'||r.precision!=='instant'||t.timestamp_precision!=='M7ExactTimestampInput/v1')return null;
  if(['conflicting','alternative_sources','conflicting_source_timestamps','alternative_source_timestamps'].some(k=>Array.isArray(t[k])&&(t[k] as unknown[]).length))return null;
  if(r.lower!=null||r.upper!=null||r.uncertainty!=null||t.alignment!=null)return null;
  const key=utc(t.source_timestamp);
  return key&&utc(r.value)===key?key:null;
}
export function drugName(item:CirculatoryItem){
  const d=record(item.fact.drug),id=d.mapping==='mapped'?d.canonical_id:undefined;
  return id==='norepinephrine'?'Noradrenaline (norepinephrine)':id==='vasopressin'?'Vasopressin':id==='dobutamine'?'Dobutamine · inotrope':String(record(d.source).raw_display??'Unresolved vasoactive identity');
}
export function infusionText(item:CirculatoryItem){
  const a=record(item.fact.action),delivery=record(a.delivery??a.prescribed??a.prepared),rate=record(delivery.rate),unit=record(rate.unit);
  const event=words(a.event_type)||'Unknown event';
  return {event,rate:typeof rate.value==='string'?rate.value+' '+String(unit.raw??''):'Rate not recorded',delivery,reason:String(record(a.reason).raw_display??'')};
}
export function infusionSeries(item:CirculatoryItem):Record<string,unknown>|null{
  const a=record(item.fact.action),d=record(a.delivery??a.prescribed??a.prepared),series=record(d.infusion);
  if(typeof series.namespace==='string'&&typeof series.code==='string')return series;
  const ids=Array.isArray(item.fact.source_identifiers)?item.fact.source_identifiers.map(record).filter(s=>s.namespace==='clinrx.synthetic.infusion-series/v1'):[];
  return ids.length===1?ids[0]:null;
}
export type ChartRow={key:string;label:string;context:string;drug:boolean;section:ChartSection;cells:Map<string,CirculatoryItem[]>};
export function buildFlowsheet(items:CirculatoryItem[]){
  const rows=new Map<string,ChartRow>(),unplaced:CirculatoryItem[]=[],times=new Set<string>();let included=0;
  for(const item of items){
    if(!kinds.has(item.fact.kind))continue;included++;
    const at=chartTime(item);if(!at){unplaced.push(item);continue;}times.add(at);
    const f=item.fact,a=record(f.acquisition),d=record(a.device),drug=f.kind==='circulatory_vasoactive';
    const entry=chartEntry(item),section=chartSection(item);
    const series=drug||entry?.code==='pump_rate'?infusionSeries(item):null;
    const identity=drug?[record(f.drug).mapping,record(f.drug).canonical_id,record(f.drug).source,series??['unlinked-event',f.id,f.revision]]:entry?[entry.code,series]:[f.concept??f.event_type??f.test,a.method,d,a.algorithm,a.parameter,a.compartment,a.laterality,record(a.site).raw_display,record(f.regional_site).raw_display,f.sample_type??f.blood_source];
    const key=JSON.stringify([f.kind,identity]);let row=rows.get(key);
    if(!row){row={key,label:drug?drugName(item):title(item),context:drug?(series?'Infusion: '+String(series.code)+' · documented events only':'Infusion identity not recorded · separate event'):(entry?entry.sourceType+(series?' · '+String(series.code):''):(method(item)+' · '+words(f.sample_type??f.blood_source??a.compartment))),drug,section,cells:new Map()};rows.set(key,row);}
    row.cells.set(at,[...(row.cells.get(at)??[]),item]);
  }
  const ordered=[...rows.values()].sort((a,b)=>Number(b.drug)-Number(a.drug)||a.label.localeCompare(b.label)||a.key.localeCompare(b.key));
  return {rows:ordered,times:[...times].sort(),unplaced,included};
}
export {sourceTime};
