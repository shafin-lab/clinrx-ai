import { useEffect, useRef, useState } from 'react';
import { ApiFailure } from '../api/client';
import type { MicroReviewClient } from '../api/microClient';
import type { Item, MicroState, MicroPrepared, MicroExecution, Role } from '../api/microTypes';
import { MicroEvidence, Notes, factRef, refKey } from './MicroEvidence';
import { MicroResult } from './MicroResult';
import './micro.css';
const roles = [
  ['S','Specimen','microbiology_specimen','specimen_ref'],
  ['I','Isolate identification','microbiology_isolate','isolate_ref'],
  ['U','Susceptibility result','microbiology_susceptibility','susceptibility_ref'],
  ['D','Completed administration','antimicrobial_administration','administration_ref']
] as const;
const empty = ():Record<Role,string>=>({S:'',I:'',U:'',D:''});
type Phase='idle'|'loading_state'|'state_ready'|'selection_incomplete'|'preparing'|'prepared'|'executing'|'released'|'withheld'|'completion_unknown'|'preparation_unknown'|'reconciling'|'reconciled_released'|'reconciled_withheld'|'reconciled_absent'|'error';
const asFailure=(e:unknown)=>e instanceof ApiFailure?e:new ApiFailure('invalid_response');
const uncertain=(e:ApiFailure)=>['completion_unknown','network_error','invalid_response','request_timeout'].includes(e.code);
export interface MicroConfig { patient:string; encounter:string; start:string; end:string }
export function MicroReview({client,config}:{client:MicroReviewClient;config:MicroConfig}) {
  const [start,setStart]=useState(config.start),[end,setEnd]=useState(config.end);
  const [view,setView]=useState<MicroState>(),[selection,setSelection]=useState(empty);
  const [prepared,setPrepared]=useState<MicroPrepared>(),[result,setResult]=useState<MicroExecution>();
  const [phase,setPhase]=useState<Phase>('idle'),[error,setError]=useState<ApiFailure>();
  const [mode,setMode]=useState<string|null>(null),[known,setKnown]=useState<string[]>([]);
  const gate=useRef(false),generation=useRef(0),status=useRef<HTMLParagraphElement>(null);
  const busy=['loading_state','preparing','executing','reconciling'].includes(phase);
  useEffect(()=>{ if(!['idle','state_ready','selection_incomplete'].includes(phase)) status.current?.focus(); },[phase]);
  useEffect(()=>()=>{generation.current++;},[]);
  function invalidate() {generation.current++;setPrepared(undefined);setResult(undefined);setError(undefined);setPhase('idle');}
  function changeWindow(value:string,which:'start'|'end') {invalidate();setView(undefined);setSelection(empty());if(which==='start')setStart(value);else setEnd(value);}
  function select(role:Role,value:string) {invalidate();const next={...selection,[role]:value};setSelection(next);setPhase(roles.every(([r])=>next[r])?'state_ready':'selection_incomplete');}
  function remember(id:string) {setKnown(ids=>ids.includes(id)?ids:[id,...ids]);}
  function accept(value:MicroExecution,reconciled=false) {setResult(value);remember(value.execution_id);setPhase(reconciled?`reconciled_${value.governance.outcome}`:value.governance.outcome);}
  async function load() {
    if(gate.current)return;gate.current=true;invalidate();setSelection(empty());setView(undefined);setPhase('loading_state');const version=generation.current;
    try {const reply=await client.microState(start,end);if(version!==generation.current)return;setView(reply.data);setMode(reply.mode);setPhase('state_ready');}
    catch(e) {if(version===generation.current){setError(asFailure(e));setPhase('error');}}
    finally {gate.current=false;}
  }
  async function prepare() {
    if(gate.current||!view)return;
    const selected=roles.map(([role])=>view.assembly.snapshot.items?.find(i=>refKey(factRef(i.fact))===selection[role]));
    if(selected.some(i=>!i))return;
    const pin=(i:Item)=>({reference:factRef(i.fact),expected_digest:i.expected_digest});
    gate.current=true;setPrepared(undefined);setResult(undefined);setError(undefined);setPhase('preparing');const version=generation.current;
    try {
      const reply=await client.microPrepare({execution_id:crypto.randomUUID(),state_context:view.state_context,
        specimen_ref:pin(selected[0]!),isolate_ref:pin(selected[1]!),susceptibility_ref:pin(selected[2]!),administration_ref:pin(selected[3]!)});
      if(version!==generation.current)return;setPrepared(reply.data);remember(reply.data.execution_id);setPhase('prepared');
    } catch(e) {if(version===generation.current){const failure=asFailure(e);setError(failure);setPhase(uncertain(failure)?'preparation_unknown':'error');}}
    finally {gate.current=false;}
  }
  async function execute() {
    if(gate.current||!prepared||phase==='completion_unknown')return;
    gate.current=true;setError(undefined);setResult(undefined);setPhase('executing');const version=generation.current;
    try {const reply=await client.microExecute(prepared);if(version===generation.current)accept(reply.data);}
    catch(e) {if(version===generation.current){const failure=asFailure(e);setError(failure);setPhase('completion_unknown');}}
    finally {gate.current=false;}
  }
  async function reconcile() {
    if(gate.current||!prepared)return;gate.current=true;setError(undefined);setPhase('reconciling');const version=generation.current;
    try {const reply=await client.microReconcile(prepared);if(version!==generation.current)return;
      if(reply.data.status==='committed_match') {if(!reply.data.execution)throw new ApiFailure('invalid_response');accept(reply.data.execution,true);}
      else {setResult(undefined);setPhase('reconciled_absent');}
    } catch(e) {if(version===generation.current){setError(asFailure(e));setPhase('completion_unknown');}}
    finally {gate.current=false;}
  }
  async function lookup(id:string) {
    if(gate.current)return;gate.current=true;invalidate();setPhase('loading_state');const version=generation.current;
    try {const reply=await client.microLookup(id);if(version===generation.current)accept(reply.data);}
    catch(e) {if(version===generation.current){setError(asFailure(e));setPhase('error');}}
    finally {gate.current=false;}
  }
  const unresolved=phase==='completion_unknown'||phase==='reconciling';
  useEffect(()=>{
    if(!unresolved && phase!=='executing')return;
    const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);
    return ()=>window.removeEventListener('beforeunload',warn);
  },[unresolved,phase]);
  return <section className="panel micro-review" aria-label="Microbiology and antimicrobial review">
    <div className="section-heading"><h2>Microbiology &amp; antimicrobial review</h2><span className="step">S / I / U / D</span></div>
    <p>Four explicitly selected source records. Descriptive timing only; no treatment recommendation or infection diagnosis.</p>
    <p>Patient {config.patient} · Encounter {config.encounter} · {mode??'Load to confirm server mode'}</p>
    <form onSubmit={e=>{e.preventDefault();void load();}}><div className="window-fields">
      <label>Microbiology review start<input value={start} disabled={busy||unresolved} onChange={e=>changeWindow(e.target.value,'start')} spellCheck={false}/></label>
      <label>Microbiology review end<input value={end} disabled={busy||unresolved} onChange={e=>changeWindow(e.target.value,'end')} spellCheck={false}/></label>
      <button disabled={busy||unresolved}>Load microbiology state</button></div></form>
    <p ref={status} tabIndex={-1} role="status">Microbiology review status: {phase.replaceAll('_',' ')}</p>
    {error&&<div role="alert" className="error"><strong>{error.code}</strong><p>{error.message}</p></div>}
    {view&&<><p>Profile: {view.assembly.request.profile_id} / {view.assembly.request.profile_version}</p><p>Repository: {view.assembly.request.scope.repository_cutoff.repository_id} · prefix {view.assembly.request.scope.repository_cutoff.fact_watermark} · captured {view.assembly.request.scope.repository_cutoff.captured_at}</p><MicroEvidence view={view}/>
      <h3>Explicit S/I/U/D selection</h3><p>Role filters show record types only. The backend validates eligibility, exact bindings, timing and canonical identity.</p>
      <div className="micro-selectors">{roles.map(([role,label,kind])=><label key={role}>{role} · {label}<select aria-label={`${role} · ${label}`} value={selection[role]} disabled={busy||unresolved} onChange={e=>select(role,e.target.value)}><option value="">Select an exact record</option>{(view.assembly.snapshot.items??[]).filter(i=>i.fact.kind===kind).map(i=><option key={refKey(factRef(i.fact))} value={refKey(factRef(i.fact))}>{i.fact.id} · revision {i.fact.revision}</option>)}</select></label>)}</div>
      <button disabled={busy||unresolved||phase==='preparation_unknown'||roles.some(([role])=>!selection[role])} onClick={()=>void prepare()}>Prepare S/I/U/D review</button>
    </>}
    {phase==='preparation_unknown'&&<div className="notice"><h3>Preparation completion unknown</h3><p>Protected execution was not invoked. No execution command was confirmed. Explicitly reload the state to abandon this preparation and start again.</p></div>}
    {prepared&&<><p>Prepared execution: {prepared.execution_id}. Command held only in memory.</p>
      {phase==='prepared'&&<section aria-label="Prepared descriptive preview"><h3>Prepared descriptive inference · not executed</h3><p>{prepared.inference.statement}</p><p>{prepared.inference.applicability}</p><p>{prepared.inference.validation_limitations}</p><details><summary>Prepared uncertainty and source limitations</summary><Notes items={[...(prepared.inference.uncertainty??[]),...(prepared.inference.provenance.limitations??[])]}/></details></section>}
      <div className="actions">{!unresolved&&<button disabled={busy} onClick={()=>void execute()}>{phase==='prepared'?'Execute S/I/U/D review':'Explicitly execute same command'}</button>}
      <button className="secondary" disabled={busy} onClick={()=>void reconcile()}>Reconcile S/I/U/D execution</button></div>
    </>}
    {unresolved&&<div className="notice"><h3>Execution completion unknown</h3><p>Do not execute again automatically. Use explicit reconciliation to inspect retained completion. No automatic retry or polling occurs.</p></div>}
    {phase==='reconciled_absent'&&<p className="notice">No retained execution found at reconciliation. Nothing was executed automatically. You may explicitly execute the same prepared command.</p>}
    {result&&<MicroResult result={result}/>}
    <details><summary>S/I/U/D reviews in this session ({known.length})</summary><p>Scoped IDs only. Reload clears commands, selections and this list.</p>{known.map(id=><p key={id}><code>{id}</code> <button className="secondary" disabled={busy||unresolved} onClick={()=>void lookup(id)}>Retrieve S/I/U/D execution {id}</button></p>)}</details>
  </section>;
}
