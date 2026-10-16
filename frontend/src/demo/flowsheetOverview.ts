import type {CirculatoryItem} from '../api/circulatoryTypes';
import {chartEntry,intervalText} from './chartEntries';
import {chartTime,type ChartRow} from './flowsheetPresentation';
import {record} from './evidencePresentation';
export const overviewGroups=['BP / MAP','Cardiac output / index','Rhythm / heart rate','Infusion events','Fluid records','Perfusion observations'] as const;
export function overviewGroup(row:ChartRow):typeof overviewGroups[number]|null{
 if(row.drug)return 'Infusion events';
 const items=[...row.cells.values()].flat();
 if(items.some(i=>i.fact.kind==='circulatory_pressure'&&['systemic_systolic','systemic_diastolic','systemic_mean'].includes(String(i.fact.concept))))return 'BP / MAP';
 if(items.some(i=>i.fact.kind==='circulatory_cardiac'&&['co','ci'].includes(String(i.fact.concept))))return 'Cardiac output / index';
 if(items.some(i=>i.fact.kind==='circulatory_ecg'&&['rhythm','heart_rate'].includes(String(i.fact.concept))))return 'Rhythm / heart rate';
 if(items.some(i=>['output_urine','net_balance_reported','balance_total_reported'].includes(chartEntry(i)?.code??'')))return 'Fluid records';
 if(items.some(i=>i.fact.kind==='circulatory_lactate'||(i.fact.kind==='circulatory_perfusion'&&i.fact.concept==='capillary_refill')))return 'Perfusion observations';
 return null;
}
/** Only shortens exact same-day UTC source bounds; never calculates duration. */
export function shortSourceInterval(item:CirculatoryItem){
 const interval=record(item.fact.recorded_interval);if(!Object.keys(interval).length)return null;
 const sourceBound=(bound:unknown)=>chartTime({...item,inclusion:'in_window',fact:{...item.fact,collected:undefined,occurred:bound}});
 const start=sourceBound(interval.start),end=sourceBound(interval.end),at=chartTime(item);
 if(start&&end&&at&&start.slice(0,10)===end.slice(0,10)&&end.slice(0,10)===at.slice(0,10))return 'Interval '+start.slice(11,19)+' → '+end.slice(11,19)+' UTC';
 return 'Interval context: inspect source';
}
export function overviewTimeWindow(times:string[],page:number,showAll:boolean){
 const lastPage=Math.max(0,Math.ceil(times.length/4)-1),safePage=Math.max(0,Math.min(page,lastPage));
 const end=Math.max(0,times.length-safePage*4),start=Math.max(0,end-4);
 return {times:showAll?times:times.slice(start,end),start:showAll?0:start,end:showAll?times.length:end,page:safePage,lastPage};
}
export {intervalText};
