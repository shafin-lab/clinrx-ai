import type {CirculatoryItem} from '../api/circulatoryTypes';
import {record,words,value,title,sourceTime,method,quality} from './evidencePresentation';
import {chartEntry,intervalText} from './chartEntries';
import {infusionSeries} from './flowsheetPresentation';
export const quantityText=(v:unknown)=>{const q=record(v);return typeof q.value==='string'?q.value+' '+String(record(q.unit).raw??''):'Not recorded';};
const sameScope=(a:CirculatoryItem,b:CirculatoryItem)=>a.fact.binding.target.patient_id===b.fact.binding.target.patient_id&&a.fact.binding.target.encounter_id===b.fact.binding.target.encounter_id;
export function exactLinked(item:CirculatoryItem,items:CirculatoryItem[],ref:unknown){
 const r=record(ref),matches=items.filter(i=>sameScope(item,i)&&i.fact.kind===r.kind&&i.fact.id===r.id&&i.fact.revision===r.version);
 return matches.length===1?matches[0]:null;
}
export function deliverySupport(item:CirculatoryItem,items:CirculatoryItem[]){
 const a=record(item.fact.action),d=record(a.delivery??a.prescribed??a.prepared);
 const weight=exactLinked(item,items,d.dosing_weight);
 const links=Array.isArray(item.fact.associations)?item.fact.associations.map(record).filter(link=>link.role==='delivery'&&link.status==='resolved'&&record(link.scope).patient_id===item.fact.binding.target.patient_id&&record(link.scope).encounter_id===item.fact.binding.target.encounter_id):[];
 const identity=infusionSeries(item),sameSeries=(source:CirculatoryItem)=>{const other=infusionSeries(source);return identity!==null&&other!==null&&identity.namespace===other.namespace&&identity.code===other.code&&identity.version===other.version;};
 const pumps=links.map(link=>exactLinked(item,items,link.exact)).filter((i):i is CirculatoryItem=>i!==null&&chartEntry(i)?.code==='pump_rate'&&sameSeries(i));
 return {weight:weight&&chartEntry(weight)?.code==='dosing_weight'?weight:null,pumps};
}
export function SourceChartDetails({item}:{item:CirculatoryItem}){
 const entry=chartEntry(item),interval=intervalText(item);if(!entry&&!interval)return null;
 return <section aria-label="Source chart context"><h3>Source chart context</h3>{entry&&<p>{entry.sourceType}</p>}{interval&&<p>{interval}</p>}<p>{String(record(item.fact.description).raw_display??'Source description not recorded')}</p><p>Recorded amounts, reported totals and source notes remain separate. No complete fluid reconciliation, rate calculation or clinical target is inferred.</p></section>;
}
export function MeasurementContext({item}:{item:CirculatoryItem}){
 const a=record(item.fact.acquisition);if(!Object.keys(a).length)return null;
 const concept=(v:unknown)=>String(record(v).raw_display??'Not recorded');
 return <section aria-label="Measurement acquisition context"><h3>Measurement context</h3><dl className="demo-source-summary">
 <dt>Method</dt><dd>{method(item)}</dd><dt>Recorded production</dt><dd>{words(item.fact.production)||'Not recorded'}</dd>
 <dt>Respiratory phase</dt><dd>{concept(a.respiratory_phase)}</dd><dt>Position</dt><dd>{concept(a.position)}</dd>
 <dt>Recorded averaging basis</dt><dd>{quantityText(a.averaging)} · no average calculated here</dd>
 <dt>Calibration status</dt><dd>{words(a.calibration)||'Not recorded'}</dd><dt>Zeroing status</dt><dd>{words(a.zeroing)||'Not recorded'}</dd>
 <dt>Indexing denominator</dt><dd>{quantityText(a.indexing_denominator)} · source-recorded, not derived here</dd>
 <dt>Source quality</dt><dd>{quality(item)}</dd></dl><p>Source metadata does not establish measurement validity or dynamic-test applicability.</p></section>;
}
export function AssessmentContext({item,items,onInspect}:{item:CirculatoryItem;items:CirculatoryItem[];onInspect:(item:CirculatoryItem,trigger:HTMLButtonElement)=>void}){
 if(item.fact.kind!=='circulatory_assessment')return null;
 return <section aria-label="Recorded intervention assessment"><h3>Recorded intervention assessment</h3><p>Baseline, intervention and subsequent records are source-linked. No response, change percentage or causal conclusion is calculated.</p>{(['baseline','intervention','subsequent'] as const).map(role=><div key={role}><h4>{words(role)}</h4>{(Array.isArray(item.fact[role])?item.fact[role] as unknown[]:[]).map((ref,n)=>{
 const source=exactLinked(item,items,ref),r=record(ref);return source?<button className="demo-explanation-inspect" key={n} onClick={event=>onInspect(source,event.currentTarget)}>{title(source)} · {value(source).text} {value(source).unit} · {sourceTime(source)} · {source.fact.id} / {source.fact.revision} ↗</button>:<p key={n}>Exact linked revision not available in this view: {String(r.id??'Unknown')} / {String(r.version??'Unknown')}. No successor substituted.</p>;
 })}</div>)}<p>Source-reported interpretation: {String(record(item.fact.reported_interpretation).raw_display??'Not recorded')}</p></section>;
}
