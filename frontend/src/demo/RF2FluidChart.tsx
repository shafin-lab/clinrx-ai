import {useMemo,type MouseEvent} from 'react';
import {key,pin,type Catalog,type Evidence} from '../api/rf2Client';

export type CatalogStatus='current'|'loading'|'retained';
type Column='Intake'|'Urine'|'Drain output'|'Other output';
const columns:Column[]=['Intake','Urine','Drain output','Other output'];
const categories:Record<string,{label:string;column?:Column;summary?:boolean}>={
 input_oral:{label:'Oral intake',column:'Intake'},input_enteral:{label:'Enteral intake',column:'Intake'},input_iv:{label:'IV fluid intake',column:'Intake'},input_blood:{label:'Blood-product intake',column:'Intake'},
 output_urine:{label:'Urine output',column:'Urine'},output_drain:{label:'Drain output',column:'Drain output'},output_other:{label:'Other recorded loss',column:'Other output'},
 output_crrt:{label:'Recorded CRRT net removal',column:'Other output'},output_crrt_net:{label:'Recorded CRRT net removal',column:'Other output'},output_crrt_effluent:{label:'Recorded CRRT effluent',column:'Other output'},
 net_balance_reported:{label:'Source-reported interval balance',summary:true},urine_total_reported:{label:'Source-reported urine total',summary:true},balance_total_reported:{label:'Source-reported cumulative balance',summary:true},
};
const object=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:{};
function category(e:Evidence){
 if(e.metadata?.chart)return e.metadata.chart.category;
 const coding=object(object(e.fact.description).coding);
 return coding.namespace==='clinrx.synthetic.hemodynamic-chart/v1'?String(coding.code):undefined;
}
function rawTime(v:unknown){const t=object(v),r=object(t.recorded);return typeof t.source_timestamp==='string'?t.source_timestamp:typeof r.value==='string'?r.value:undefined;}
function timeValue(raw:string|undefined){
 // Grouping is presentation only. Retain finer-than-millisecond assertions unplaced
 // rather than assigning them to a rounded hour or falling back to interval-end time.
 if(!raw||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(raw))return undefined;
 const n=Date.parse(raw);return Number.isFinite(n)?n:undefined;
}
function exactRecordedTime(value:unknown){
 const t=object(value),r=object(t.recorded);
 // A representative source string does not override the typed assertion.
 // Clock verification is deliberately NOT a placement requirement.
 if(r.status!=='known'||r.precision!=='instant'||r.lower!=null||r.upper!=null||r.uncertainty!=null)return undefined;
 const recorded=timeValue(typeof r.value==='string'?r.value:undefined);
 if(recorded===undefined)return undefined;
 if(t.source_timestamp!=null&&(typeof t.source_timestamp!=='string'||timeValue(t.source_timestamp)!==recorded))return undefined;
 return recorded;
}
function placedTime(value:unknown){
 const t=object(value),recorded=exactRecordedTime(value);
 if(recorded===undefined||(Array.isArray(t.conflicting)&&t.conflicting.length)||(Array.isArray(t.conflicting_source_timestamps)&&t.conflicting_source_timestamps.length))return undefined;
 if(t.alternative_sources!=null&&!Array.isArray(t.alternative_sources))return undefined;
 if(Array.isArray(t.alternative_sources)&&t.alternative_sources.some(a=>exactRecordedTime(a)!==recorded))return undefined;
 return recorded;
}
export function chartTiming(e:Evidence){
 const interval=object(e.fact.recorded_interval),chart=e.metadata?.chart;
 const hasInterval=Object.keys(interval).length>0||chart?.start!=null||chart?.end!=null;
 const start=chart?.start??rawTime(interval.start),end=chart?.end??rawTime(interval.end);
 const point=chart?.point??rawTime(e.fact.occurred);
 if(hasInterval)return {kind:'interval' as const,start,end,a:placedTime(interval.start),b:placedTime(interval.end)};
 return {kind:'point' as const,start:point,end:undefined,a:placedTime(e.fact.occurred),b:undefined};
}
function TimingSummary({label,value}:{label:string;value:unknown}){
 const r=object(object(value).recorded);
 return <p>{label}: precision {String(r.precision??'unknown')} · uncertainty: {String(r.uncertainty??'not supplied')}{r.lower!=null&&<> · lower bound: {String(r.lower)}</>}{r.upper!=null&&<> · upper bound: {String(r.upper)}</>}</p>;
}
function TimingDetails({label,value}:{label:string;value:unknown}){
 const t=object(value),r=object(t.recorded);
 const describe=(name:string,v:Record<string,unknown>)=>{const recorded=object(v.recorded),source=object(v.source);return <p>{name}: raw timestamp {String(v.source_timestamp??'not supplied')} · status {String(recorded.status??'unavailable')} · precision {String(recorded.precision??'unknown')} · representative value {String(recorded.value??'not supplied')} · lower bound {String(recorded.lower??'not supplied')} · upper bound {String(recorded.upper??'not supplied')} · uncertainty {String(recorded.uncertainty??'not supplied')} · clock {String(v.clock??'unknown')}{source.namespace!=null&&<> · source {String(source.namespace)} / {String(source.code)}: {String(source.raw_display??'')}</>}</p>;};
 return <>{describe(label,{...t,recorded:r})}{Array.isArray(t.conflicting)&&t.conflicting.length>0&&<p>Conflicting timestamps: {t.conflicting.map(String).join(' · ')}</p>}{Array.isArray(t.conflicting_source_timestamps)&&t.conflicting_source_timestamps.length>0&&<p>Raw conflicting timestamps: {t.conflicting_source_timestamps.map(String).join(' · ')}</p>}{Array.isArray(t.alternative_sources)&&t.alternative_sources.map((v,n)=><div key={n}>{describe('Alternative source assertion '+(n+1),object(v))}</div>)}</>;
}
function correspondence(c:Catalog){
 const scope=c.combined.context.scope,circ=c.combined.circulatory.assembly.request.scope;
 if(c.execution_enabled!==false||c.cutoff.repository_id!==c.repository||scope.patient_id!=='synthetic-p1'||scope.encounter_id!=='synthetic-e1'||scope.repository_cutoff.repository_id!==c.repository||scope.repository_cutoff.fact_watermark!==c.cutoff.fact_watermark||circ.repository_cutoff.repository_id!==c.repository||circ.repository_cutoff.fact_watermark!==c.cutoff.fact_watermark||circ.review_start!==scope.review_start||circ.review_end!==scope.review_end||circ.patient_id!==scope.patient_id||circ.encounter_id!==scope.encounter_id)return false;
 const seen=new Set<string>();
 for(const e of c.items){const k=key(pin(e));if(seen.has(k)||e.repository!==c.repository||e.ingestion.repository_id!==c.repository||e.cutoff!==c.cutoff.fact_watermark||e.ingestion.ingestion_sequence>e.cutoff||e.fact.binding.target.patient_id!==scope.patient_id||e.fact.binding.target.encounter_id!==scope.encounter_id)return false;seen.add(k);}
 return true;
}
export function fluidChartModel(c:Catalog){
 const scope=c.combined.context.scope,start=timeValue(scope.review_start),end=timeValue(scope.review_end);
 const groups=new Map<string,Evidence[]>(),unplaced:Evidence[]=[],separate:Evidence[]=[],summaries:Evidence[]=[],unclassified:Evidence[]=[];
 const valid=correspondence(c)&&start!==undefined&&end!==undefined&&start<end;
 if(!valid)return {valid,groups:[] as [string,Evidence[]][],unplaced,separate,summaries,unclassified};
 for(const e of c.items){
  if(e.fact.kind!=='circulatory_event'||e.metadata?.note)continue;
  const cat=category(e),info=cat?categories[cat]:undefined;
  if(info?.summary){summaries.push(e);continue;}
  if(!info?.column){unclassified.push(e);continue;}
  const t=chartTiming(e),a=t.a,b=t.b;
  if(a===undefined||(t.kind==='interval'&&(b===undefined||b<=a))){unplaced.push(e);continue;}
  const hour=new Date(a).toISOString().slice(0,13)+':00:00Z';
  const boundary=Date.parse(hour)+3600000;
  const contained=t.kind==='interval'?a>=start&&b!<=end:a>=start&&a<end;
  if(!contained||(t.kind==='interval'&&b!>boundary)){separate.push(e);continue;}
  groups.set(hour,[...(groups.get(hour)??[]),e]);
 }
 const order=(a:Evidence,b:Evidence)=>(chartTiming(a).a??Infinity)-(chartTiming(b).a??Infinity)||key(pin(a)).localeCompare(key(pin(b)));
 return {valid,groups:[...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([h,es])=>[h,es.sort(order)] as [string,Evidence[]]),unplaced:unplaced.sort(order),separate:separate.sort(order),summaries:summaries.sort(order),unclassified:unclassified.sort(order)};
}
interface Props {catalog:Catalog;status:CatalogStatus;retrievalMessage?:string;requestedPeriod?:{start:string;end:string};text:(e:Evidence)=>string;context:(e:Evidence)=>string;onInspect:(e:Evidence,button:HTMLButtonElement)=>void}
export function RF2FluidChart({catalog,status,retrievalMessage,requestedPeriod,text,context,onInspect}:Props){
 const model=useMemo(()=>fluidChartModel(catalog),[catalog]);
 const scope=catalog.combined.context.scope;
 const requestedMatches=!requestedPeriod||(timeValue(requestedPeriod.start)===timeValue(scope.review_start)&&timeValue(requestedPeriod.end)===timeValue(scope.review_end));
 const valid=model.valid&&(status!=='current'||requestedMatches);
 const current=status==='current';
 const card=(e:Evidence)=>{
  const cat=category(e),info=cat?categories[cat]:undefined,t=chartTiming(e),interval=object(e.fact.recorded_interval);
  return <article className="rf2-fluid-entry" key={key(pin(e))} aria-label={`${info?.label??'Unclassified recorded assertion'} ${e.fact.id} / ${e.fact.revision}`}>
   <strong>{info?.label??'Unclassified recorded assertion'}{cat&&<small>Source category: {cat}</small>}</strong><p className="rf2-fluid-amount">{text(e)}</p>
   <p>{t.kind==='interval'?<>Recorded interval: {t.start??'start unknown'} → {t.end??'end unknown'}</>:<>Recorded point: {t.start??'unknown'}</>}</p>
   {t.kind==='interval'?<><TimingSummary label="Interval start" value={interval.start}/><TimingSummary label="Interval end" value={interval.end}/></>:<TimingSummary label="Recorded point" value={e.fact.occurred}/>}
   {cat==='output_drain'&&<p>Drain identity unresolved — individual drains are not inferred.</p>}
   <p>Record status: {String(e.fact.record_status??'unavailable')}{e.superseded?' · Superseded historical revision retained':''}</p>
   <p>{e.metadata?.chart?.source_context??String(object(e.fact.description).raw_display??'Source context unavailable')}</p>
   {e.metadata?.chart?.uncertainty&&<p>Uncertainty: {e.metadata.chart.uncertainty}</p>}
   {Array.isArray(e.fact.disclosures)&&e.fact.disclosures.map((x,n)=><p key={n}>{String(x)}</p>)}
   {Array.isArray(e.fact.uncertainty)&&e.fact.uncertainty.map((x,n)=><p key={n}>Source caveat: {String(x)}</p>)}
   <p className="rf2-fluid-reference">Exact source: {e.fact.id} / {e.fact.revision}</p>
   <button type="button" onClick={(event:MouseEvent<HTMLButtonElement>)=>onInspect(e,event.currentTarget)}>Open exact source {e.fact.id} / {e.fact.revision}</button>
   <details><summary>Source timing, verification and exact pin</summary>{t.kind==='interval'?<><TimingDetails label="Interval start" value={interval.start}/><TimingDetails label="Interval end" value={interval.end}/></>:<TimingDetails label="Recorded point" value={e.fact.occurred}/>}<p>{context(e)}</p><p>Repository {e.repository} · cutoff {e.cutoff} · ingestion {e.ingestion.ingestion_sequence} · digest {e.digest}</p></details>
  </article>;
 };
 const extra=(name:string,items:Evidence[],description:string)=>items.length>0?<section aria-label={name}><h4>{name}</h4><p>{description}</p>{items.map(card)}</section>:null;
 return <section className="rf2-fluid-chart" aria-label="Fluid chart">
  <h3>Fluid chart — recorded entries</h3>
  <p><strong>Calculations unavailable — source eligibility not established</strong></p><p><strong>Completeness unresolved</strong></p>
  <p>Selected source period: {scope.review_start} → {scope.review_end}. Hour groups use UTC (+00:00); source timestamps keep their recorded offsets. Groups are navigation only, not measured hourly volumes.</p>
  <p>Repository {catalog.repository} · source cutoff {catalog.cutoff.fact_watermark}. Recorded entries do not establish complete intake/output coverage.</p>
  <p>The existing selected period is retained. No additional 24-hour retrieval is introduced in this view; no period total is calculated.</p>
  {!current&&<p role="alert">{status==='loading'?'Refresh in progress.':'Retrieval is unconfirmed or failed.'} Retained prior catalog — not confirmed current. {retrievalMessage} Empty cells cannot establish that records are absent.{!requestedMatches&&requestedPeriod&&<> Requested period: {requestedPeriod.start} → {requestedPeriod.end}.</>}</p>}
  {!valid?<p role="alert">Chart unavailable — scope, cutoff or selected-period correspondence could not be confirmed. No empty chart is substituted.</p>:<>
   <p id="rf2-fluid-scroll-help">At narrow widths, focus the chart region and use Left/Right arrow keys to scroll. Each source button is keyboard-accessible. Amounts are separate source assertions, with no summing, conversion or allocation.</p>
   <div className="rf2-fluid-scroll" role="region" aria-label="Scrollable recorded fluid chart" aria-describedby="rf2-fluid-scroll-help" tabIndex={0} onKeyDown={e=>{if(e.target!==e.currentTarget)return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();e.currentTarget.scrollLeft+=e.key==='ArrowRight'?80:-80;}}}>
    <table><caption>Recorded entries side by side — no hourly totals</caption><thead><tr><th scope="col">Hour group / actual interval</th>{columns.map(c=><th scope="col" key={c}>{c}</th>)}</tr></thead><tbody>
    {model.groups.map(([hour,es])=><tr key={hour}><th scope="row">{hour} · UTC +00:00</th>{columns.map(col=><td key={col}>{es.filter(e=>categories[category(e)!]?.column===col).length?es.filter(e=>categories[category(e)!]?.column===col).map(card):<p>{current?'No recorded entry shown':'Unavailable while catalog is unconfirmed'}</p>}</td>)}</tr>)}
    </tbody></table>
   </div>
   {!model.groups.length&&<p>{current?'No individually placed source entries shown for this period. Inspect the separate sections below; this is not a zero-volume assertion.':'Prior catalog contains no individually placed entries; current retrieval is unconfirmed.'}</p>}
   {extra('Intervals spanning hour boundaries or outside the selected period',model.separate,'Original intervals remain intact. No hourly allocation or prorating is performed.')}
   {extra('Unplaced entries',model.unplaced,'Timing is missing, ambiguous, invalid or too precise for safe browser grouping. No fallback to a collection completion point is used.')}
   {extra('Source-reported summaries',model.summaries,'Recorded aggregate assertions are displayed separately, never combined with individual entries or treated as calculated totals.')}
   {extra('Other source assertions — category not mapped to the chart',model.unclassified,'Source-category meaning has not been established for these entries. They are not silently placed into a generic output column.')}
  </>}
 </section>;
}
