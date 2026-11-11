import {useEffect,useRef,useState,type FormEvent} from 'react';
import {hash,RF2DefiniteRejection,stable,validateReproductiveImport,type Catalog,type Fact,type RF2Client} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import {eventTimeISO} from '../antibioticWorkflow/recordForm';
import {reservePending,releasePending} from '../gastrointestinal/pendingJournal';
import {blankTime} from '../respiratory/respiratoryModel';
import {compareRespiratoryInstants} from '../respiratory/exactTime';
import {phaseLabels,reproductiveCategories,type Category,type Phase,type ReproductiveScope} from './model';

const pendingKey=(repository:string)=>'clinrx.m12.pending/v1/'+encodeURIComponent(repository);
export function readPendingFinding(repository:string):Fact|false|'unreadable' {
 try{
  const raw=localStorage.getItem(pendingKey(repository));
  if(raw===null)return false;
  if(raw.length>131072)return 'unreadable';
  const record=parseRF2JSON(raw) as Fact;
  validateReproductiveImport(repository,record);
  return record;
 }catch{return 'unreadable';}
}
const namespace='clinrx.synthetic.m12';
const optionalInteger=(input:string)=>input===''?null:Number(input);
export function ReproductiveEntry({catalog,requested,current,transport,onClose,onRefresh,onGuardChange}:{
 catalog:Catalog;requested:ReproductiveScope;current:boolean;
 transport:Pick<RF2Client,'importReproductive'|'lookupReproductive'>;
 onClose:()=>void;onRefresh:()=>Promise<void>;onGuardChange?:(guard:boolean)=>void;
}){
 const dialog=useRef<HTMLDialogElement>(null),running=useRef(false);
 const scope=useRef({repository:catalog.repository,watermark:catalog.cutoff.fact_watermark});
 const latest=useRef({catalog,current});latest.current={catalog,current};
 const [initial]=useState(()=>readPendingFinding(scope.current.repository));
 const [pending,setPending]=useState<Fact|undefined>(typeof initial==='object'?initial:undefined);
 const [category,setCategory]=useState<Category>('maternal_assessment'),[phase,setPhase]=useState<Phase>('unknown');
 const [weeks,setWeeks]=useState(''),[days,setDays]=useState(''),[due,setDue]=useState(''),[count,setCount]=useState(''),[basis,setBasis]=useState('');
 const [title,setTitle]=useState(''),[narrative,setNarrative]=useState(''),[occurred,setOccurred]=useState(''),[actor,setActor]=useState('');
 const [error,setError]=useState(''),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false);
 const [saved,setSaved]=useState(false),[canDiscard,setCanDiscard]=useState(false),[canRetry,setCanRetry]=useState(false);
 const guard=!saved&&(dirty||!!pending||initial==='unreadable');
 const stale=()=>!latest.current.current||latest.current.catalog.repository!==scope.current.repository||
  latest.current.catalog.cutoff.fact_watermark!==scope.current.watermark;
 useEffect(()=>{dialog.current?.showModal();},[]);
 useEffect(()=>{
  onGuardChange?.(guard);
  if(!guard)return;
  const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
  window.addEventListener('beforeunload',warn);
  return ()=>{onGuardChange?.(false);window.removeEventListener('beforeunload',warn);};
 },[guard,onGuardChange]);
 async function execute(action:()=>Promise<void>){
  if(running.current)return;
  running.current=true;setBusy(true);setError('');
  try{await action();}
  catch(e){setError(e instanceof Error?e.message:'Finding save could not be confirmed.');}
  finally{running.current=false;setBusy(false);}
 }
 async function finish(record:Fact){
  await releasePending(pendingKey(scope.current.repository),record);
  setPending(undefined);setSaved(true);setDirty(false);setCanDiscard(false);setCanRetry(false);
  try{await onRefresh();}catch{setError('Finding saved. Refresh evidence to see the updated record.');}
 }
 async function withRequestOwnership(record:Fact,action:()=>Promise<void>){
  if(!navigator.locks)throw Error('Safe pending-request storage is unavailable.');
  return navigator.locks.request('clinrx.m12.submit:'+scope.current.repository,async()=>{
   if(stable(readPendingFinding(scope.current.repository))!==stable(record))throw Error('This pending request changed in another tab.');
   await action();
  });
 }
 async function send(record:Fact,firstAttempt=false){
  setCanDiscard(false);setCanRetry(false);
  await withRequestOwnership(record,async()=>{
   if(!latest.current.current||latest.current.catalog.repository!==scope.current.repository||(firstAttempt&&stale())){
    throw Error('Patient evidence changed. Check the retained request before proceeding.');
   }
   try{await transport.importReproductive(scope.current.repository,record);}
   catch(e){if(firstAttempt&&e instanceof RF2DefiniteRejection)setCanDiscard(true);throw e;}
   await finish(record);
  });
 }
 async function submit(event:FormEvent){
  event.preventDefault();
  await execute(async()=>{
   if(stale())throw Error('Patient evidence changed. Reopen the form after reviewing the current sources.');
   const at=eventTimeISO(occurred),enteredAt=new Date().toISOString();
   if(compareRespiratoryInstants(at,requested.end)===1)throw Error('Use a source observation time within or before this review period.');
   const reportId=crypto.randomUUID(),source={namespace,identifier:reportId,version:'1',channel:'clinician'};
   const binding={target:{patient_id:requested.patient,encounter_id:requested.encounter,longitudinal_context_id:null},
    verification:{status:'unresolved',method:'Synthetic encounter selection',verifier:actor.trim(),assessed_at:enteredAt,source,ambiguity:'Fictional patient only.'}};
   const record:Fact={
    id:'repro-'+(await hash(namespace+'\0'+reportId)).slice(0,32),revision:'1',kind:'reproductive_record',
    binding,
    origin:'observed',provenance:{source,actor:actor.trim(),recorded_at:enteredAt,upstream:[],lineage:'unknown',limitations:['Synthetic local finding.']},
    time:{precision:'unknown',event:null,recorded:null,effective_start:null,effective_end:null,retrieved:null,processed:null,uncertainty:null},
    verification:'unverified',conflict:'unknown',temporal_status:'unknown',uncertainty:[],supersedes:null,correction_reason:null,
    contract_version:'2',source_identifiers:[],domain_bindings:[],disclosures:[],category,
    title:title.trim()||reproductiveCategories[category],narrative:narrative.trim(),
    source_identity:{issuer_namespace:namespace,source_report_id:reportId,source_version:'1',accession_id:null},
    times:{occurred:{...blankTime(),status:'known',precision:'instant',value:at},reported:blankTime(),available:blankTime()},
    report_status:'final',record_status:'recorded',change_state:'original',linked_sources:[],
    pregnancy:category==='pregnancy_status'?{phase,gestational_weeks:optionalInteger(weeks),gestational_days:optionalInteger(days),
     estimated_due_date:due||null,fetus_count:optionalInteger(count),dating_basis:basis.trim()||null}:null,
   };
   validateReproductiveImport(scope.current.repository,record);
   if(stale())throw Error('Patient evidence changed. Review the current records again.');
   await reservePending(pendingKey(scope.current.repository),record);
   setPending(record);
   await send(record,true);
  });
 }
 function check(record:Fact){return execute(async()=>{
  setCanDiscard(false);setCanRetry(false);
  if(await transport.lookupReproductive(scope.current.repository,record)==='committed_match')await finish(record);
  else{setCanRetry(true);setError('The exact request is not visible yet. You can retry the same request.');}
 });}
 function close(){if(!busy)onClose();}
 return <dialog className="gi-dialog" ref={dialog} aria-labelledby="m12-entry-title" onCancel={e=>{e.preventDefault();close();}}>
  <header><h2 id="m12-entry-title">Record finding</h2><button type="button" disabled={busy} onClick={close}>Close</button></header>
  {saved?<p role="status">Finding saved to this fictional encounter.</p>:<form onSubmit={e=>void submit(e)} onChange={()=>setDirty(true)}>
   <fieldset disabled={busy||!!pending||initial==='unreadable'||stale()}>
    <div className="gi-form-grid">
     <label>Finding type<select value={category} onChange={e=>setCategory(e.target.value as Category)}>
      {Object.entries(reproductiveCategories).map(([id,label])=><option key={id} value={id}>{label}</option>)}
     </select></label>
     <label>Observation time (local)<input type="datetime-local" required value={occurred} onChange={e=>setOccurred(e.target.value)}/></label>
     <label>Title<input maxLength={256} value={title} onChange={e=>setTitle(e.target.value)}/></label>
     <label>Recorded by<input required maxLength={120} value={actor} onChange={e=>setActor(e.target.value)}/></label>
     {category==='pregnancy_status'&&<>
      <label>Pregnancy phase<select value={phase} onChange={e=>setPhase(e.target.value as Phase)}>
       {Object.entries(phaseLabels).map(([id,label])=><option key={id} value={id}>{label}</option>)}
      </select></label>
      <label>Dating basis<input maxLength={256} value={basis} onChange={e=>setBasis(e.target.value)}/></label>
      <label>Gestational weeks<input type="number" min={0} max={49} value={weeks} onChange={e=>setWeeks(e.target.value)}/></label>
      <label>Gestational days<input type="number" min={0} max={6} value={days} onChange={e=>setDays(e.target.value)}/></label>
      <label>Estimated due date<input type="date" value={due} onChange={e=>setDue(e.target.value)}/></label>
      <label>Fetus count<input type="number" min={0} value={count} onChange={e=>setCount(e.target.value)}/></label>
     </>}
     <label className="gi-wide">Recorded finding or report<textarea required maxLength={16384} value={narrative} onChange={e=>setNarrative(e.target.value)}/></label>
    </div><button type="submit">Save finding</button>
   </fieldset>
  </form>}
  {(error||initial==='unreadable')&&<p role="alert">{error||'Pending request data is unreadable. It has been preserved.'}</p>}
  {pending&&!saved&&<section aria-label="Pending finding save">
   <button type="button" disabled={busy} onClick={()=>void check(pending)}>Check pending save</button>
   {canRetry&&<button type="button" disabled={busy||!current} onClick={()=>void execute(()=>send(pending))}>Retry exact request</button>}
   {canDiscard&&<button type="button" disabled={busy} onClick={()=>void execute(()=>withRequestOwnership(pending,async()=>{
    await releasePending(pendingKey(scope.current.repository),pending);setPending(undefined);setCanDiscard(false);
   }))}>Discard rejected request</button>}
  </section>}
 </dialog>;
}
