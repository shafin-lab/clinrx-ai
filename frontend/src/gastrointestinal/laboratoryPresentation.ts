import type {Evidence} from '../api/rf2Client';
import {asObject} from '../respiratory/respiratoryModel';
export function laboratoryResultText(component:Record<string,unknown>){const r=asObject(component.result),unit=asObject(r.unit);if(r.kind==='unavailable')return String(r.status??'unavailable')+': '+String(r.reason??'Reason not supplied');return String(r.kind==='numeric'&&r.comparator&&r.comparator!=='='?r.comparator:'')+String(r.raw_value??'Not recorded')+(r.kind==='numeric'?' '+String(unit.raw_display??'Unit not recorded'):'');}
export function laboratoryQualifications(e:Evidence,component:Record<string,unknown>,includeUnknown=true){
 const flags=(name:string)=>Array.isArray(component[name])?(component[name] as unknown[]).map(f=>{const x=asObject(f);return String(x.raw_display??x.code??'Source flag not described');}):[];
 return [...flags('source_flags').map(f=>'Source flag: '+f),...flags('source_interference_flags').map(f=>'Source interference: '+f),...(component.source_critical_flag==='flagged'?['Source flagged critical']:includeUnknown&&(component.source_critical_flag==='unknown'||component.source_critical_flag===undefined)?['Critical-flag status not supplied']:[]),...(e.fact.conflict==='unresolved'?['Unresolved source conflict']:[])];
}
