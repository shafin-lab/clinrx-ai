import {displayLaboratoryUnit} from '../clinicalEvidence/laboratoryDisplay';
import type {Evidence} from '../api/rf2Client';
import {asObject} from '../respiratory/respiratoryModel';
export function laboratoryResultText(component: Record<string, unknown>) {
 const result = asObject(component.result);
 if (result.kind === 'unavailable') {
  return String(result.status ?? 'unavailable') + ': ' + String(result.reason ?? 'Reason not supplied');
 }
 const numeric = result.kind === 'numeric';
 const comparator = numeric && result.comparator && result.comparator !== '=' ? String(result.comparator) : '';
 const value = String(result.raw_value ?? 'Not recorded');
 if (!numeric) return value;
 const unit = String(asObject(result.unit).raw_display ?? 'Unit not recorded');
 const shownUnit = displayLaboratoryUnit(unit);
 return comparator + value + (shownUnit ? ' ' + shownUnit : '');
}
export function laboratoryQualifications(e:Evidence,component:Record<string,unknown>,includeUnknown=true){
 const flags=(name:string)=>Array.isArray(component[name])?(component[name] as unknown[]).map(f=>{const x=asObject(f);return String(x.raw_display??x.code??'Source flag not described');}):[];
 return [...flags('source_flags').map(f=>'Source flag: '+f),...flags('source_interference_flags').map(f=>'Source interference: '+f),...(component.source_critical_flag==='flagged'?['Source flagged critical']:includeUnknown&&(component.source_critical_flag==='unknown'||component.source_critical_flag===undefined)?['Critical-flag status not supplied']:[]),...(e.fact.conflict==='unresolved'?['Unresolved source conflict']:[])];
}
