import {useMemo,useRef,useState} from 'react';
import {RF2Client,type Catalog,type Evidence} from '../api/rf2Client';
import {key,pin} from '../api/rf2Client';
import {title,words} from './evidencePresentation';
import {chartEntry} from './chartEntries';
import {evidenceText,sourceContext} from './RenalFluidEntryWorkspace';
import type {CatalogStatus} from './RF2FluidChart';
import {PatientSourceDialog,type SourceSelection} from './PatientSourceDialog';
import {investigationPresentation} from '../clinical/sharedInvestigations';
import {WeightEntryDialog} from './WeightEntryDialog';
import type {WeightScope} from './weightRecovery';
import './patientOverview.css';

type Requested={patient:string;encounter:string;start:string;end:string};
interface Finding {id:string;label:string;records:Evidence[]}
const categories:Record<string,string>={weight:'Recorded weight',input_oral:'Oral intake',input_enteral:'Enteral intake',input_iv:'IV fluid input',input_blood:'Blood-product input',output_urine:'Urine output',output_drain:'Drain output',output_other:'Other measured loss',output_crrt:'CRRT net fluid removal',output_crrt_net:'Recorded CRRT net removal',output_crrt_effluent:'Recorded CRRT effluent',net_balance_reported:'Reported interval fluid balance',urine_total_reported:'Reported cumulative urine volume',balance_total_reported:'Reported cumulative chart balance'};
const names:Record<string,string>={'body-weight':'Recorded weight'};
const sameInstant=(a:string,b:string)=>Number.isFinite(Date.parse(a))&&Date.parse(a)===Date.parse(b);
/** Presentation of an already-decoded shared catalog. No requests, inference or source mutation. */
export function patientOverviewModel(catalog:Catalog,requested:Requested){
 const scope=catalog.combined.context.scope,circ=catalog.combined.circulatory.assembly.request.scope;
 const sameScope=(s:typeof scope)=>s.patient_id===requested.patient&&s.encounter_id===requested.encounter&&sameInstant(s.review_start,requested.start)&&sameInstant(s.review_end,requested.end)&&s.repository_cutoff.repository_id===catalog.repository&&s.repository_cutoff.fact_watermark===catalog.cutoff.fact_watermark;
 const seen=new Set<string>();
 const valid=catalog.execution_enabled===false&&catalog.combined.execution_enabled===false&&catalog.combined.circulatory.execution_enabled===false&&catalog.cutoff.repository_id===catalog.repository&&sameScope(scope)&&sameScope(circ)&&sameScope(catalog.combined.laboratory.scope)&&catalog.items.every(e=>{
  const k=key(pin(e));if(seen.has(k))return false;seen.add(k);
  return e.repository===catalog.repository&&e.cutoff===catalog.cutoff.fact_watermark&&e.ingestion.repository_id===catalog.repository&&e.ingestion.ingestion_sequence<=e.cutoff&&e.fact.binding.target.patient_id===requested.patient&&e.fact.binding.target.encounter_id===requested.encounter;
 });
 if(!valid)return {valid:false,findings:[] as Finding[]};
 const groups=new Map<string,Finding>();
 const sourceItems=new Map(catalog.combined.circulatory.assembly.snapshot.items.map(i=>[JSON.stringify([i.fact.kind,i.fact.id,i.fact.revision]),i]));
 for(const e of catalog.items){
  const item=sourceItems.get(JSON.stringify([e.fact.kind,e.fact.id,e.fact.revision]));
  const chart=item?chartEntry(item):undefined;
  const category=e.metadata?.chart?.category??chart?.code;
  const label=e.metadata?.note?'Clinician-authored review':category?(categories[category]??chart?.label??words(category)):investigationPresentation(e.fact)?.label??names[String(e.fact.concept_id)]??(item?title(item):chart?.label??words(e.fact.kind));
  const id=category==='weight'||e.fact.kind==='observation'&&e.fact.concept_id==='body-weight'?JSON.stringify(['finding','recorded-weight']):JSON.stringify([e.fact.kind,e.metadata?.note?e.fact.id:category??e.fact.concept_id??e.fact.concept??e.fact.test??e.fact.signal??e.fact.event_type??label]);
  if(!groups.has(id))groups.set(id,{id,label,records:[]});
  groups.get(id)!.records.push(e);
 }
 return {valid:true,findings:[...groups.values()]};
}
interface Props {manualClearanceAvailable?:boolean;catalog?:Catalog;status:CatalogStatus;requested:Requested;retrievalMessage?:string;guarded:boolean;onRefresh?:()=>void|Promise<void>;transport?:Pick<RF2Client,'history'>;weightEntryEnabled?:boolean;weightTransport?:Pick<RF2Client,'action'>}
export function PatientOverview({manualClearanceAvailable=false,catalog,status,requested,retrievalMessage,guarded,onRefresh,transport:providedTransport,weightEntryEnabled=false,weightTransport}:Props){
 const [defaultTransport]=useState(()=>new RF2Client()),[selection,setSelection]=useState<SourceSelection>();
 const [entry,setEntry]=useState<{scope:WeightScope;source?:Evidence;trigger:HTMLButtonElement}>();
 const addInformation=useRef<HTMLButtonElement>(null);
 const transport=providedTransport??defaultTransport;
 const model=useMemo(()=>catalog?patientOverviewModel(catalog,requested):undefined,[catalog,requested.patient,requested.encounter,requested.start,requested.end]);
 const current=status==='current';
 const finding=(g:Finding)=><article className="connected-finding" key={g.id}><h4>{g.label}</h4><p>{g.records.length===1?evidenceText(g.records[0]):`${g.records.length} recorded sources`}</p><details><summary>View recorded details</summary>{g.records.map(e=><div className="connected-source" key={key(pin(e))}><p><strong>{evidenceText(e)}</strong></p><p>{sourceContext(e,catalog!)}</p>{e.superseded&&<p>Superseded historical revision retained</p>}<p>Recorded status: {String(e.fact.record_status??'Not supplied')}</p>{e.metadata?.note&&<p>Authored review — not a generated clinical conclusion.</p>}<button type="button" disabled={!current||guarded} aria-label={`Open recorded source ${e.fact.id} / ${e.fact.revision}`} onClick={event=>setSelection({evidence:e,catalog:catalog!,label:g.label,trigger:event.currentTarget})}>Open source details</button><details><summary>Source method, timing and exact reference</summary>{/* Complete timing assertions stay inspectable; no hourly placement is inferred. */}<pre>{JSON.stringify({reference:pin(e),time:e.fact.time,occurred:e.fact.occurred,interval:e.fact.recorded_interval,acquisition:e.fact.acquisition,uncertainty:e.fact.uncertainty},null,2)}</pre></details></div>)}</details></article>;
 return <section className="connected-overview" aria-label="Connected patient overview">
  <div className="connected-heading"><div><p className="connected-eyebrow">One patient · Shared recorded evidence</p><h2>Patient overview</h2></div>{weightEntryEnabled&&onRefresh?<button ref={addInformation} type="button" disabled={!current||!model?.valid||guarded} onClick={event=>{if(!entry)setEntry({scope:{patient:requested.patient,encounter:requested.encounter,repository:catalog!.repository},trigger:event.currentTarget});}}>Add information</button>:<span className="connected-readonly">Read-only source connection</span>}</div>
  <p className="connected-period">Selected period: {requested.start} → {requested.end}. Source timestamps retain their recorded offsets.</p>
  {!current&&<p role="alert" className="connected-warning">{status==='loading'?'Patient evidence is loading or refreshing.':'Patient evidence retrieval is unconfirmed.'} {catalog?'Retained prior data — not confirmed current.':'No confirmed patient overview is available.'} {retrievalMessage}</p>}
  {catalog&&!model?.valid&&<p role="alert" className="connected-warning">Overview withheld — patient, encounter, period or repository/cutoff correspondence could not be confirmed. No different source was substituted.</p>}
  {catalog&&model?.valid&&<>
   <div className="connected-picture"><div><h3>Current picture</h3><p>{catalog.items.length?`${catalog.items.length} recorded assertions are available together.`:'No recorded assertions are supplied in this bounded catalog. This is not evidence of normal findings.'}</p><p>One item per finding, with individual measurements and their context underneath.</p><p className="connected-caveat">Recorded evidence only. A combined clinical interpretation has not been generated.</p></div><div aria-label="Overview supporting findings">{model.findings.slice(0,5).map(finding)}</div></div>
   {model.findings.length>5&&<details className="connected-all"><summary>All recorded findings ({model.findings.length})</summary><div className="connected-all-grid">{model.findings.slice(5).map(finding)}</div></details>}
   <aside className="connected-warning" aria-label="Overview limitations"><h3>Still unresolved</h3><p>Completeness and clinical interpretation. {manualClearanceAvailable?'Automated calculations remain inactive. A manual-input creatinine clearance calculator is available in Antibiotics.':'Calculations unavailable — source eligibility not established.'} Domains not supplied by this catalog are not treated as normal.</p></aside>

   <details className="connected-boundary"><summary>Review scope and recorded coverage</summary><p>Repository {catalog.repository} · cutoff {catalog.cutoff.fact_watermark}</p><pre>{JSON.stringify({coverage:catalog.combined.circulatory.assembly.snapshot.coverage,issues:catalog.combined.circulatory.assembly.snapshot.issues},null,2)}</pre></details>
  </>}
  {onRefresh&&<button type="button" disabled={status==='loading'||guarded||!!entry} onClick={()=>{void Promise.resolve(onRefresh()).catch(()=>{});}}>Refresh records</button>}
  {selection&&model?.valid&&catalog?.repository===selection.evidence.repository&&<PatientSourceDialog selection={selection} transport={transport} current={current} onClose={()=>setSelection(undefined)} onCorrect={weightEntryEnabled&&current&&!guarded&&onRefresh?()=>{const selected=selection;setSelection(undefined);setEntry({scope:{patient:requested.patient,encounter:requested.encounter,repository:catalog.repository},source:selected.evidence,trigger:selected.trigger});}:undefined}/>}
  {entry&&<WeightEntryDialog {...entry} currentScope={{patient:requested.patient,encounter:requested.encounter,repository:catalog?.repository??''}} current={current&&!!model?.valid&&!guarded} transport={weightTransport??defaultTransport} onRefresh={async()=>{await onRefresh?.();}} onClose={()=>setEntry(undefined)} onReturnFocus={()=>addInformation.current?.focus()}/>}
  {!catalog&&status!=='loading'&&<p>This overview requires the existing RF2 shared catalog. Separate source snapshots are not combined to simulate a connected patient.</p>}
 </section>;
}
