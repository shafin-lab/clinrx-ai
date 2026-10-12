import { useReducer, useRef, useState } from 'react';
import { ApiFailure, ReviewClient } from '../api/client';
import type { PatientState, Evidence, Execution } from '../api/types';
import { reviewReducer } from './reviewState';
import { ProvenanceDrawer, refLabel, TextList } from './ProvenanceDrawer';
interface Config { patient:string; encounter:string; start:string; end:string }
const key=(item:Evidence)=>JSON.stringify(item.reference);
const pin=(item:Evidence)=>({reference:item.reference,expected_digest:item.selection_digest});
const failure=(error:unknown)=>error instanceof ApiFailure?error:new ApiFailure('invalid_response');
const uncertain=(error:ApiFailure)=>['completion_unknown','network_error','invalid_response'].includes(error.code);
function ErrorPanel({error}:{error:ApiFailure}) { return <div role="alert" className="error"><strong>{error.code}</strong><p>{error.message}</p>{error.fields.map((f,i)=><p key={i}>{f.path}: {f.code}</p>)}</div>; }
function SourceDetails({item}:{item:Evidence}) { return <details><summary>Source details</summary><p>{item.source.namespace} / {item.source.identifier}</p><p>Provenance: {item.provenance_completeness}; {item.provenance_recorded_at}</p><TextList items={[...item.disclosures,...item.provenance_limitations]}/></details>; }
export function PatientReviewPage({client,config}:{client:ReviewClient;config:Config}) {
  const [start,setStart]=useState(config.start),[end,setEnd]=useState(config.end);
  const [view,setView]=useState<PatientState>(),[mode,setMode]=useState<string|null>(null);
  const [selection,setSelection]=useState({a:'',b:'',m:''});
  const [review,dispatch]=useReducer(reviewReducer,{phase:'viewing'});
  const [busy,setBusy]=useState(false),[viewError,setViewError]=useState<ApiFailure>();
  const [known,setKnown]=useState<string[]>([]),[opened,setOpened]=useState<Execution>(),[drawer,setDrawer]=useState(false);
  const gate=useRef(false);
  const locked=!!review.prepared || ['preparing','preparation_unknown','completion_unknown','reconciling'].includes(review.phase);
  const unresolved=['completion_unknown','reconciling','executing'].includes(review.phase);
  const a=view?.laboratory.find(i=>key(i)===selection.a),b=view?.laboratory.find(i=>key(i)===selection.b),m=view?.medication.find(i=>key(i)===selection.m);
  const remember=(id:string)=>setKnown(ids=>ids.includes(id)?ids:[id,...ids]);
  async function work(action:()=>Promise<void>) { if(gate.current)return;gate.current=true;setBusy(true);try{await action();}finally{gate.current=false;setBusy(false);} }
  async function load() { await work(async()=>{setViewError(undefined);setView(undefined);setSelection({a:'',b:'',m:''});setOpened(undefined);dispatch({type:'reset'});try{const reply=await client.state(start,end);setView(reply.data);setMode(reply.mode);}catch(e){setViewError(failure(e));}}); }
  async function prepare() { if(!view || !a || !b || !m || locked)return;await work(async()=>{dispatch({type:'preparing'});setOpened(undefined);try{const reply=await client.prepare({execution_id:crypto.randomUUID(),state_context:view.state_context,earlier_laboratory:pin(a),later_laboratory:pin(b),medication:pin(m)});dispatch({type:'prepared',value:reply.data});remember(reply.data.execution_id);}catch(e){const error=failure(e);dispatch({type:uncertain(error)?'preparation_unknown':'error',error});}}); }
  async function execute() { const prepared=review.prepared;if(!prepared || unresolved)return;await work(async()=>{dispatch({type:'executing'});setOpened(undefined);try{const reply=await client.execute(prepared);dispatch({type:'completed',value:reply.data});remember(reply.data.execution_id);}catch(e){const error=failure(e);dispatch({type:uncertain(error)?'unknown':'error',error});}}); }
  async function reconcile() {const prepared=review.prepared;if(!prepared)return;await work(async()=>{dispatch({type:'reconciling'});try{const reply=await client.reconcile(prepared);if(reply.data.status==='committed_match')dispatch({type:'matched',value:reply.data.execution});else dispatch({type:'absent'});}catch(e){dispatch({type:'unknown',error:failure(e)});}});}
  async function lookup(id:string) {await work(async()=>{setViewError(undefined);setOpened(undefined);try{setOpened((await client.lookup(id)).data);}catch(e){setViewError(failure(e));}});}
  function reset() {dispatch({type:'reset'});setOpened(undefined);setViewError(undefined);}
  const result=opened??review.result;
  return <>
    <header className="topbar"><a href="#main" className="brand">ClinRx <span>AI</span></a><span className="mode">{mode==='synthetic-only-real-clock'?'Synthetic demo · real clock':mode==='historical-synthetic-simulation'?'Historical synthetic simulation':'Historical synthetic simulation · connection not yet verified'}</span></header>
    <main id="main"><div className="page-title"><div><span className="eyebrow">Evidence review / Synthetic patient</span><h1>Patient review</h1><p>Inspect recorded evidence. Review one explicitly selected temporal relationship.</p></div><span className="badge neutral">Synthetic use only</span></div>
    <section className="patient-header" aria-label="Synthetic patient"><strong>Synthetic patient</strong><span>Patient <code>{config.patient}</code></span><span>Encounter <code>{config.encounter}</code></span><p>No live patient care or clinical validation is implied.</p></section>
    <section className="panel"><div className="section-heading"><h2>Review window</h2><span className="step">01 / Recorded state</span></div><p className="muted">Exact timestamps with timezone. The backend determines the bounded repository view.</p>
      <form onSubmit={e=>{e.preventDefault();void load();}}><div className="window-fields"><label>Review start<input value={start} disabled={busy||locked} onChange={e=>{setStart(e.target.value);setView(undefined);setSelection({a:'',b:'',m:''});}} spellCheck={false}/></label><label>Review end<input value={end} disabled={busy||locked} onChange={e=>{setEnd(e.target.value);setView(undefined);setSelection({a:'',b:'',m:''});}} spellCheck={false}/></label><button disabled={busy||locked}>Load state</button></div></form>
      {viewError&&<ErrorPanel error={viewError}/>}
      {busy&&<p role="status">{review.phase==='preparing'?'Preparing review…':review.phase==='executing'?'Running protected review…':review.phase==='reconciling'?'Reconciling execution…':'Loading…'}</p>}
    </section>
    {view&&<><section className="panel"><div className="section-heading"><h2>Recorded evidence</h2><span className="muted">Repository prefix {view.scope.repository_cutoff.fact_watermark}</span></div>
      <p>Loaded window: <time>{view.scope.review_start}</time> → <time>{view.scope.review_end}</time></p>
      <details className="coverage"><summary>Domain coverage · {view.coverage.length} domains</summary><div className="coverage-grid">{view.coverage.map(c=><div key={c.domain}><strong>{c.domain.replaceAll('_',' ')}</strong><span>{c.mapping_support==='unsupported'?'Not mapped':c.mapping_support==='partial'?'Partially mapped':'Mapped'}</span><small>Source completeness: {c.source_completeness} · {c.retrieval.replaceAll('_',' ')}</small></div>)}</div><TextList items={view.disclosures}/></details>
      {view.issues.length>0&&<details><summary>Mapping issues ({view.issues.length})</summary><ul>{view.issues.map((issue,i)=><li key={i}>{refLabel(issue.reference)}: {issue.reason}</li>)}</ul></details>}
      <h3>Laboratory</h3><div className="table-scroll"><table><thead><tr><th scope="col">Select</th><th scope="col">Recorded value</th><th scope="col">Event time</th><th scope="col">Exact reference</th><th scope="col">Source</th></tr></thead><tbody>{view.laboratory.map(item=><tr key={key(item)}><td className="roles">{(['a','b'] as const).map(role=><label key={role}><input type="radio" name={role} aria-label={`Select ${role.toUpperCase()} ${item.reference.id} revision ${item.reference.version}`} checked={selection[role]===key(item)} disabled={busy||locked||selection[role==='a'?'b':'a']===key(item)} onChange={()=>setSelection(s=>({...s,[role]:key(item)}))}/>{role.toUpperCase()}</label>)}</td><td><strong>{item.quantity.value}</strong> {item.quantity.unit_raw}</td><td><time>{item.time.event??'Not recorded'}</time></td><td>{refLabel(item.reference)}</td><td><SourceDetails item={item}/></td></tr>)}</tbody></table></div>
      {view.laboratory.length===0&&<p>No laboratory records retained in this view. This does not establish clinical absence.</p>}
      <h3>Medication</h3><div className="table-scroll"><table><thead><tr><th scope="col">Select</th><th scope="col">Recorded event</th><th scope="col">Event / effective time</th><th scope="col">Exact reference</th><th scope="col">Source</th></tr></thead><tbody>{view.medication.map(item=><tr key={key(item)}><td><label><input type="radio" name="m" aria-label={`Select M ${item.reference.id} revision ${item.reference.version}`} checked={selection.m===key(item)} disabled={busy||locked} onChange={()=>setSelection(s=>({...s,m:key(item)}))}/>M</label></td><td>{item.event_type==='medication_order'?'Medication order':'Medication administration'}<small>{item.product_id??item.ingredient_ids.join(', ')}</small></td><td><time>{item.time.event??'Event not recorded'}</time><small>Effective: {item.time.effective_start??'Not recorded'} → {item.time.effective_end??'Not recorded'}</small></td><td>{refLabel(item.reference)}</td><td><SourceDetails item={item}/></td></tr>)}</tbody></table></div>
      {view.medication.length===0&&<p>No medication records retained in this view. This does not establish clinical absence.</p>}
    </section><section className="panel"><div className="section-heading"><h2>Explicit evidence selection</h2><span className="step">02 / Prepare, then run</span></div><div className="selection-summary">{([['A · Earlier laboratory',a],['B · Later laboratory',b],['M · Medication',m]] as const).map(([label,item])=><div key={label}><strong>{label}</strong><span>{item?refLabel(item.reference):'Select a record'}</span></div>)}</div>
      <p className="muted">Selection is explicit. The backend validates the relationship; selection alone does not establish clinical eligibility.</p>
      <div className="actions"><button disabled={busy||locked||!a||!b||!m} onClick={()=>void prepare()}>Prepare review</button>
      {review.prepared&&!unresolved&&<button disabled={busy} onClick={()=>void execute()}>{review.phase==='absent'?'Run same prepared review':review.result?'Retry same prepared review':'Run protected review'}</button>}
      {(locked||review.phase==='error')&&!unresolved&&<button className="secondary" disabled={busy} onClick={reset}>{review.phase==='preparation_unknown'?'Abandon preparation and start again':'Start a new review'}</button>}</div>
      <p role="status" className="phase">Review status: {review.phase.replaceAll('_',' ')}</p>
      {review.prepared&&<p className="muted">Prepared execution: {review.prepared.execution_id}</p>}
      {review.phase==='prepared'&&<p>Prepared. The exact server-issued command is retained in memory. Execution has not started.</p>}
      {review.phase==='preparation_unknown'&&<div className="notice"><strong>Preparation completion could not be confirmed.</strong><p>Protected execution was not invoked. Execution reconciliation cannot resolve this preparation. Choose explicitly whether to abandon it and prepare again.</p></div>}
      {['completion_unknown','reconciling'].includes(review.phase)&&<div className="notice"><strong>Completion could not be confirmed.</strong><p>Check the retained execution before taking another action.</p><button disabled={busy} onClick={()=>void reconcile()}>Reconcile execution</button></div>}
      {review.phase==='absent'&&<p className="notice">No matching execution was found during that lookup. Nothing was run automatically. You may explicitly run the same prepared review.</p>}
      {review.error&&<ErrorPanel error={review.error}/>}
    </section></>}
    {result&&<section className="panel result" aria-label="Review result"><div className="section-heading"><h2>Review result</h2><span className={'badge '+result.governance.outcome}>{result.governance.outcome==='released'?'Released':'Withheld'}</span></div>
      <p>{result.governance.outcome==='released'?'Released under synthetic policy at':'Withheld at'} <time>{result.governance.decided_at}</time></p>
      <p className="muted">Retained synthetic execution · {result.execution_id}</p>
      {result.governance.outcome==='released'?<><p className="statement">{result.provenance.inference.statement}</p><p>{result.provenance.inference.applicability}</p></>:<><p>No inference statement is presented as released output.</p><TextList items={result.governance.reasons}/><p>Final recheck: {result.provenance.final_recheck}</p><TextList items={result.provenance.recheck_reasons}/></>}
      <h3>Uncertainty</h3><TextList items={result.provenance.inference.uncertainty}/><h3>Limitations</h3><TextList items={[...result.provenance.inference.limitations,...result.governance.limitations]}/>
      <button className="secondary" onClick={()=>setDrawer(true)}>Why am I seeing this?</button>
    </section>}
    <section className="panel"><h2>Reviews opened in this session</h2><p className="muted">Session-local IDs only; this is not the encounter’s complete execution history. Reloading clears this list, selections, and commands.</p>{known.length===0?<p>No reviews opened in this session.</p>:<ul className="session-list">{known.map(id=><li key={id}><code>{id}</code><button className="secondary" disabled={busy||unresolved} onClick={()=>void lookup(id)}>Retrieve execution {id}</button></li>)}</ul>}</section>
    <footer>Synthetic evidence review · No diagnosis, causal interpretation, or treatment recommendation.</footer>
    </main>{drawer&&result&&<ProvenanceDrawer result={result} onClose={()=>setDrawer(false)}/>}
  </>;
}
