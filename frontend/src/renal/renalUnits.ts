import type {RenalObservation} from '../api/renalFluidTypes';
import type {RenalSource} from './renalBedsideModel';
import {record} from '../demo/evidencePresentation';
import {decimal,divide,formatNumber,times} from './chartArithmetic';

export const creatinineDisplayProfile={id:'ClinRxCreatinineDisplay/v1',unit:'mg/dL',digits:2,source:'https://backend.mayocliniclabs.com/order-tests/si-unit-conversion.html'} as const;
const units:Record<string,string>={'mg/dL':'mg/dL','mg/L':'mg/L','umol/L':'umol/L','µmol/L':'umol/L','μmol/L':'umol/L','mmol/L':'mmol/L'};
/** Presentation conversion only; original values/unit mapping/status are never changed. */
export function creatinineDisplay(item:RenalObservation){
 const result=item.fact.value,q=record(result.value),unit=record(q.unit),raw=String(unit.raw??''),canonical=units[raw];
 if(result.status!=='known')return {text:result.status+' · '+(result.reason??'Reason unavailable'),note:'',available:false};
 if(typeof q.value!=='string'||!canonical)return {text:'Standard unit unavailable',note:'Unit review required. The original result is retained in source details.',available:false};
 if(unit.status==='assessed'&&(unit.system!=='UCUM'||units[String(unit.code)]!==canonical))return {text:'Standard unit unavailable',note:'Raw and mapped units do not agree; conversion withheld.',available:false};
 try{
  let v=decimal(q.value);if(v.n<0n)throw Error('Negative creatinine');
  if(canonical==='umol/L')v=divide(v,decimal('88.4'));
  if(canonical==='mmol/L')v=divide(times(v,decimal('1000')),decimal('88.4'));
  if(canonical==='mg/L')v=divide(v,decimal('10'));
  const converted=canonical!=='mg/dL',rounded=formatNumber(v,2,false);
  return {text:(converted?'≈ ':'')+rounded+' mg/dL',available:true,note:[converted?'Converted for display; source values unchanged':'Display rounded to 2 decimal places',unit.status!=='assessed'?'Source unit mapping unresolved; not a validated clinical input':''].filter(Boolean).join(' · ')};
 }catch{return {text:'Value review required',note:'No supported finite nonnegative decimal was supplied. Inspect the original source.',available:false};}
}
export const renalDisplayValue=(source:RenalSource)=>source.lab?creatinineDisplay(source.lab).text:source.value;
export const renalDisplayNote=(source:RenalSource)=>source.lab?creatinineDisplay(source.lab).note:'';
