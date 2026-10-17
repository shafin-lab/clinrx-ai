import {useEffect,useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import {ApiFailure} from '../api/client';
import type {CirculatoryState,CirculatoryPrepared,CirculatoryExecution,CirculatoryHistory,CirculatoryItem} from '../api/circulatoryTypes';
import {CirculatoryEvidence,RecordedDetails,RecordedDisclosure,families,reference,refKey} from './CirculatoryEvidence';
import './circulatory.css';
type Phase='idle'|'loading'|'ready'|'preparing'|'preparation_unknown'|'prepared'|'executing'|'completion_unknown'|'reconciling'|'absent'|'completed'|'error';
const failure=(e:unknown)=>e instanceof ApiFailure?e:new ApiFailure('invalid_response');
const roles=['pressure','lactate','vasopressor'] as const;
const roleKinds={pressure:'circulatory_pressure',lactate:'circulatory_lactate',vasopressor:'circulatory_vasoactive'};
export function CirculatoryReview({client,config}:{client:CirculatoryClient;config:{start:string;end:string}}) {
  const [start,setStart]=useState(config.start),[end,setEnd]=useState(config.end),[view,setView]=useState<CirculatoryState>();
  const [working,setWorking]=useState(false);
  const [phase,setPhase]=useState<Phase>('idle'),[error,setError]=useState<ApiFailure>();
  const [selected,setSelected]=useState({pressure:'',lactate:'',vasopressor:''}),[support,setSupport]=useState<string[]>([]);
  const [prepared,setPrepared]=useState<CirculatoryPrepared>(),[result,setResult]=useState<CirculatoryExecution>();
  const [history,setHistory]=useState<CirculatoryHistory>(),[lookup,setLookup]=useState('');
  const gate=useRef(false),generation=useRef(0);
  useEffect(()=>()=>{generation.current++;},[]);
  const busy=working||['loading','preparing','executing','reconciling'].includes(phase);
  const unresolved=['executing','completion_unknown','reconciling','preparation_unknown','absent'].includes(phase);
  const locked=!!prepared||unresolved;
  useEffect(()=>{
    if(!unresolved)return;
    const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);return ()=>window.removeEventListener('beforeunload',warn);
  },[unresolved]);
  async function work(action:(current:()=>boolean)=>Promise<void>){
    if(gate.current)return;gate.current=true;setWorking(true);const token=generation.current;const current=()=>token===generation.current;
    try{await action(current);}finally{if(current()){gate.current=false;setWorking(false);}}
  }
  async function load(){if(locked)return;await work(async current=>{
    setPhase('loading');setError(undefined);setView(undefined);setResult(undefined);setHistory(undefined);setSelected({pressure:'',lactate:'',vasopressor:''});setSupport([]);
    try{const reply=await client.circulatoryState(start,end);if(current()){setView(reply.data);setPhase('ready');}}
    catch(e){if(current()){setError(failure(e));setPhase('error');}}
  });}
  const items=view?.assembly.snapshot.items??[];
  const find=(key:string)=>items.find(item=>refKey(reference(item))===key);
  const pin=(item:CirculatoryItem)=>({reference:reference(item),expected_digest:item.expected_digest});
  async function prepare(){if(!view||!view.execution_enabled||locked)return;const chosen=roles.map(role=>find(selected[role]));if(chosen.some(item=>!item))return;
    await work(async current=>{
      setPhase('preparing');setError(undefined);setResult(undefined);
      try{const reply=await client.circulatoryPrepare({execution_id:crypto.randomUUID(),state_context:view.state_context,
        pressure:pin(chosen[0]!),lactate:pin(chosen[1]!),vasopressor:pin(chosen[2]!),supporting:support.map(find).filter((i):i is CirculatoryItem=>!!i).map(pin)});
        if(current()){setPrepared(reply.data);setPhase('prepared');}}
      catch(e){if(current()){const err=failure(e);setError(err);setPhase(['network_error','request_timeout','invalid_response','completion_unknown'].includes(err.code)?'preparation_unknown':'error');}}
    });
  }
  async function execute(){if(!prepared||!['prepared','absent'].includes(phase))return;await work(async current=>{
    setPhase('executing');setError(undefined);
    try{const reply=await client.circulatoryExecute(prepared);if(current()){setResult(reply.data);setPhase('completed');}}
    catch(e){if(current()){setError(failure(e));setPhase('completion_unknown');}}
  });}
  async function reconcile(){if(!prepared)return;await work(async current=>{
    setPhase('reconciling');setError(undefined);
    try{const reply=await client.circulatoryReconcile(prepared);if(!current())return;
      if(reply.data.status==='committed_match'){if(!reply.data.execution)throw new ApiFailure('invalid_response');setResult(reply.data.execution);setPhase('completed');}
      else setPhase('absent');
    }catch(e){if(current()){setError(failure(e));setPhase('completion_unknown');}}
  });}
  async function inspect(item:CirculatoryItem){if(!view||busy)return;await work(async current=>{
    setError(undefined);try{const reply=await client.circulatoryHistory(view.state_context,reference(item));if(current())setHistory(reply.data);}
    catch(e){if(current())setError(failure(e));}
  });}
  async function retained(){if(busy||locked)return;await work(async current=>{
    setError(undefined);setResult(undefined);try{const reply=await client.circulatoryLookup(lookup);if(current())setResult(reply.data);}
    catch(e){if(current())setError(failure(e));}
  });}
  function reset(){if(unresolved||busy)return;setPrepared(undefined);setResult(undefined);setPhase(view?'ready':'idle');setError(undefined);}
  return <section className="panel m7-review" aria-label="Comprehensive circulatory evidence" aria-busy={busy}>
    <h2>Hemodynamic and circulatory evidence</h2><p>Synthetic recorded evidence across 15 families. No shock diagnosis, causal interpretation or treatment advice.</p>
    <form onSubmit={e=>{e.preventDefault();void load();}}><div className="window-fields">
      <label>Circulatory review start<input value={start} disabled={busy||locked} onChange={e=>{setStart(e.target.value);setView(undefined);setSelected({pressure:'',lactate:'',vasopressor:''});setSupport([]);}}/></label>
      <label>Circulatory review end<input value={end} disabled={busy||locked} onChange={e=>{setEnd(e.target.value);setView(undefined);setSelected({pressure:'',lactate:'',vasopressor:''});setSupport([]);}}/></label>
      <button disabled={busy||locked}>Load circulatory evidence</button></div></form>
    <p role="status">Circulatory review: {phase.replaceAll('_',' ')}</p>{error&&<p role="alert">{error.message}</p>}
    {view&&<>
      {!view.execution_enabled&&<p role="note">Protected P/L/V execution is gated pending independent policy review and end-to-end acceptance. Recorded evidence remains available.</p>}
      <RecordedDisclosure label="Coverage and recorded-state issues" value={{coverage:view.assembly.snapshot.coverage,issues:view.assembly.snapshot.issues}}/>
      {Object.entries(families).map(([kind,label])=><section key={kind} className="m7-family"><h3>{label}</h3>
        {items.filter(i=>i.fact.kind===kind).map(item=><CirculatoryEvidence key={refKey(reference(item))} item={item} disabled={busy} onHistory={()=>void inspect(item)}/>)}
        {!items.some(i=>i.fact.kind===kind)&&<p>No records retained in this bounded view. Clinical absence is not established.</p>}
      </section>)}
      {history&&<section aria-label="Circulatory correction history"><h3>Exact revision history: {history.reference.id}</h3><RecordedDetails value={history.revisions}/></section>}
      <h3>Explicit P/L/V descriptive review</h3><p>Select exact pressure, lactate and actual vasopressor-initiation evidence. The backend applies SyntheticPLVEligibility/1; appearing here does not imply eligibility.</p>
      <fieldset disabled={busy||locked||!view.execution_enabled}><legend>Exact primary selections</legend>
        {roles.map(role=><label key={role}>{role}<select aria-label={'Select '+role} value={selected[role]} onChange={e=>{const value=e.target.value;setSelected(old=>({...old,[role]:value}));setSupport(old=>old.filter(key=>key!==value));setResult(undefined);}}>
          <option value="">Choose exact revision</option>{items.filter(i=>i.fact.kind===roleKinds[role]).map(item=><option key={refKey(reference(item))} value={refKey(reference(item))}>{item.fact.id} / {item.fact.revision}</option>)}</select></label>)}
      </fieldset>
      <details><summary>Explicit independently revisioned support</summary><p>Select every supporting revision actually consumed. No evidence is added silently.</p>
        {items.filter(i=>!Object.values(selected).includes(refKey(reference(i)))).map(item=><label key={refKey(reference(item))}><input type="checkbox" disabled={busy||locked||!view.execution_enabled} checked={support.includes(refKey(reference(item)))} onChange={e=>{const key=refKey(reference(item));setSupport(old=>e.target.checked?[...old,key]:old.filter(x=>x!==key));}}/>{item.fact.id} / {item.fact.revision}</label>)}
      </details>
      <button disabled={busy||locked||!view.execution_enabled||roles.some(role=>!selected[role])} onClick={()=>void prepare()}>Prepare P/L/V review</button>
    </>}
    {prepared&&<section aria-label="Prepared circulatory review"><h3>Prepared descriptive inference</h3><p>{prepared.inference.statement}</p><p>Execution UUID: <code>{prepared.execution_id}</code></p>
      <button disabled={busy||!['prepared','absent'].includes(phase)} onClick={()=>void execute()}>{phase==='absent'?'Explicitly retry same command':'Execute prepared P/L/V review'}</button>
      <button disabled={busy||phase==='completed'} onClick={()=>void reconcile()}>Reconcile original circulatory command</button></section>}
    {phase==='completion_unknown'&&<p>Completion is uncertain. The original command and execution UUID are retained in this page. Reconcile explicitly; do not create a replacement execution.</p>}
    {phase==='absent'&&<p>No retained match was found. Absence is not proof of rollback. Nothing has been retried. An explicit retry uses the same command and UUID.</p>}
    {phase==='preparation_unknown'&&<p>Preparation completion could not be confirmed. No execution command is available; nothing will be executed or re-prepared automatically. Keep this page open for investigation.</p>}
    {result&&<section aria-label="Retained circulatory result"><h3>Retained decision</h3><p>Retained execution UUID: <code>{result.execution_id}</code></p>{result.statement?<p>{result.statement}</p>:<p>Withheld: no released statement.</p>}
      <RecordedDisclosure label="Complete original evidence, terminal witnesses and governance receipt" value={result.record}/><p>Receipt ingested: {result.ingested_at}</p></section>}
    <button disabled={unresolved||busy} onClick={reset}>Start another circulatory selection</button>
    <form onSubmit={e=>{e.preventDefault();void retained();}}><label>Retained circulatory execution UUID<input value={lookup} disabled={busy||locked} onChange={e=>setLookup(e.target.value)}/></label><button disabled={!lookup||busy||locked}>Look up retained circulatory execution</button></form>
    <p className="muted">Commands remain in page memory only. Keep this page open while completion is unresolved. Source measurements and source interpretations are distinct from the explicitly labelled ClinRx descriptive inference. VA-ECMO, Impella and IABP are deferred.</p>
  </section>;
}
