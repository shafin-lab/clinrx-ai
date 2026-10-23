import type {Catalog,Evidence} from '../api/rf2Client';
import {record} from '../demo/evidencePresentation';
import {chartTiming} from '../demo/RF2FluidChart';
import {renalBedsideModel} from './renalBedsideModel';
import {decimal,formatNumber,minus,plus,times,zero,type Fraction} from './chartArithmetic';

export const fluidRows=[
 {id:'input_oral',label:'Oral',side:'input'},
 {id:'input_enteral',label:'Enteral / feeding',side:'input'},
 {id:'input_iv',label:'IV fluids',side:'input'},
 {id:'input_blood',label:'Blood products',side:'input'},
 {id:'output_urine',label:'Urine',side:'output'},
 {id:'output_drain',label:'Drains',side:'output'},
 {id:'output_other',label:'Other measured losses',side:'output'},
 {id:'output_crrt',label:'CRRT net removal',side:'output'}
] as const;
export type FluidRow=typeof fluidRows[number]['id'];
export interface FluidEntry {source:Evidence;row:FluidRow;amount:Fraction;start:number;end?:number;hour?:number;mappingWarning:boolean}
export interface FluidIssue {source:Evidence;reason:string}
export const fluidCategory=(e:Evidence)=>{if(e.metadata?.chart)return e.metadata.chart.category;const c=record(record(e.fact.description).coding);return c.namespace==='clinrx.synthetic.hemodynamic-chart/v1'?String(c.code):undefined;};
const sourceKey=(e:Evidence)=>JSON.stringify([e.repository,e.fact.kind,e.fact.id,e.fact.revision]);
const rowFor=(s:string)=>s==='output_crrt_net'?'output_crrt':fluidRows.some(r=>r.id===s)?s as FluidRow:undefined;
const isSummary=(s:string)=>['net_balance_reported','urine_total_reported','balance_total_reported'].includes(s);
export function chartWindow(day:string,hour:string,offset:string){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||!/^\d{2}$/.test(hour)||Number(hour)>23||!/^[-+]\d{2}:\d{2}$/.test(offset))throw Error('Invalid chart period');
 const start=day+'T'+hour+':00:00'+offset,a=Date.parse(start);if(!Number.isFinite(a)||new Date(a+offsetMinutes(offset)*60000).toISOString().slice(0,10)!==day)throw Error('Invalid chart date');
 const b=a+24*3600000,localEnd=new Date(b+offsetMinutes(offset)*60000).toISOString().slice(0,19);
 return {start,end:localEnd+offset,a,b,offset};
}
export function offsetMinutes(offset:string){const sign=offset[0]==='-'?-1:1;return sign*(Number(offset.slice(1,3))*60+Number(offset.slice(4,6)));}
export function hourLabel(start:number,hour:number,offset:string){const stamp=(t:number)=>new Date(t+offsetMinutes(offset)*60000).toISOString().slice(11,16);return stamp(start+hour*3600000)+'–'+stamp(start+(hour+1)*3600000);}
export function sumEntries(entries:readonly FluidEntry[]):Fraction{return entries.reduce((sum,e)=>plus(sum,e.amount),zero());}
export const quantityText=(entries:readonly FluidEntry[])=>entries.length?formatNumber(sumEntries(entries)):'—';
export function dailyFluidModel(catalog:Catalog,requested:{patient:string;encounter:string;start:string;end:string},repository:string){
 const empty={valid:false,entries:[] as FluidEntry[],issues:[] as FluidIssue[],summaries:[] as Evidence[],effluent:[] as Evidence[],outside:[] as Evidence[],unallocated:[] as FluidEntry[],intake:zero(),output:zero(),net:zero(),fullDayConfirmed:false as const};
 const a=Date.parse(requested.start),b=Date.parse(requested.end);
 if(b-a!==86400000||catalog.repository!==repository||!renalBedsideModel(catalog.combined,requested,catalog).valid)return empty;
 const accepted:FluidEntry[]=[],issues:FluidIssue[]=[],summaries:Evidence[]=[],effluent:Evidence[]=[],outside:Evidence[]=[];
 for(const e of catalog.items){
  if(e.fact.kind!=='circulatory_event'||e.metadata?.note||e.superseded)continue;
  const category=fluidCategory(e);if(!category)continue;
  if(isSummary(category)){summaries.push(e);continue;}
  if(category==='output_crrt_effluent'){effluent.push(e);continue;}
  const row=rowFor(category);if(!row)continue;
  if(e.fact.record_status!=='recorded'){issues.push({source:e,reason:'Source not recorded/current; excluded'});continue;}
  const t=chartTiming(e);if(t.a===undefined||(t.kind==='interval'&&(t.b===undefined||t.b<=t.a))){issues.push({source:e,reason:'Time or collection interval is unresolved; no placement or volume inference'});continue;}
  if(t.kind==='point'?t.a<a||t.a>=b:t.b!<=a||t.a>=b){outside.push(e);continue;}
  if(t.a<a||t.kind==='interval'&&t.b!>b){issues.push({source:e,reason:'Collection crosses the selected day boundary; no volume prorating'});continue;}
  const amount=record(e.fact.recorded_amount),unit=record(amount.unit),raw=unit.raw;
  if(typeof amount.value!=='string'||!['mL','L'].includes(String(raw))){issues.push({source:e,reason:'Missing volume or unsupported volume unit; not zero'});continue;}
  if(unit.status==='assessed'&&(unit.system!=='UCUM'||unit.code!==raw)){issues.push({source:e,reason:'Raw/mapped volume units conflict; excluded'});continue;}
  let volume:Fraction;try{volume=decimal(amount.value);if(volume.n<0n)throw Error('negative');if(raw==='L')volume=times(volume,decimal('1000'));}catch{issues.push({source:e,reason:'Invalid nonnegative decimal volume; excluded'});continue;}
  const h=Math.floor((t.a-a)/3600000),hourEnd=a+(h+1)*3600000;
  accepted.push({source:e,row,amount:volume,start:t.a,end:t.kind==='interval'?t.b:undefined,hour:t.kind==='point'||t.b!<=hourEnd?h:undefined,mappingWarning:unit.status!=='assessed'});
 }
 // Without collection/line independence, overlapping intervals in one category
 // cannot be combined. Exclude the whole ambiguous pair rather than picking one.
 const ambiguous=new Set<string>();
 for(let i=0;i<accepted.length;i++)for(let j=i+1;j<accepted.length;j++){
  const x=accepted[i],y=accepted[j];if(x.row!==y.row)continue;
  const overlap=x.end!==undefined&&y.end!==undefined?Math.max(x.start,y.start)<Math.min(x.end,y.end):x.end===undefined&&y.end===undefined?x.start===y.start:x.end!==undefined?y.start>=x.start&&y.start<x.end:x.start>=y.start&&x.start<y.end!;
  if(overlap){ambiguous.add(sourceKey(x.source));ambiguous.add(sourceKey(y.source));}
 }
 const entries=accepted.filter(e=>!ambiguous.has(sourceKey(e.source)));
 for(const e of accepted.filter(e=>ambiguous.has(sourceKey(e.source))))issues.push({source:e.source,reason:'Overlapping collections / possible duplicate volume; independence not established'});
 const intake=sumEntries(entries.filter(e=>e.row.startsWith('input_'))),output=sumEntries(entries.filter(e=>e.row.startsWith('output_')));
 return {valid:true,entries,issues,summaries,effluent,outside,unallocated:entries.filter(e=>e.hour===undefined),intake,output,net:minus(intake,output),fullDayConfirmed:false as const};
}
