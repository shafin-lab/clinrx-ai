import {useEffect,useRef,useState} from 'react';
import type {Evidence,RF2Client} from '../api/rf2Client';
import {decodeWeightRecovery,sameWeightScope,weightDraft,weightSession,weightStorageKey,type WeightForm,type WeightRecovery,type WeightScope} from './weightRecovery';

interface Props {scope:WeightScope;currentScope:WeightScope;source?:Evidence;current:boolean;trigger:HTMLButtonElement;transport:Pick<RF2Client,'action'>;onRefresh:()=>Promise<void>;onClose:()=>void;onReturnFocus?:()=>void}
type Phase='editing'|'review'|'saving'|'uncertain'|'absent'|'saved';
export function WeightEntryDialog({scope,currentScope,source,current,trigger,transport,onRefresh,onClose,onReturnFocus}:Props){
 const key=weightStorageKey(scope);
 const [initial]=useState(()=>{
  let raw:string|null=null;
  try{raw=localStorage.getItem(key);return {raw,session:raw?decodeWeightRecovery(raw,scope):weightSession(scope,source),recovered:raw!==null,error:''};}
  catch{return {raw,session:undefined,recovered:false,error:'Local weight recovery could not be read. Existing recovery bytes were preserved. Close this dialog and resolve that record before making another entry.'};}
 });
 const [session,setSession]=useState<WeightRecovery|undefined>(initial.session),[phase,setPhase]=useState<Phase>(initial.session?.pending?'uncertain':'editing');
 const [message,setMessage]=useState(initial.error),[storageError,setStorageError]=useState(!!initial.error),[busy,setBusy]=useState(false),[saved,setSaved]=useState<Evidence>();
 const dialog=useRef<HTMLDialogElement>(null),heading=useRef<HTMLHeadingElement>(null),lastRaw=useRef(initial.raw),locked=useRef(false),mounted=useRef(true);
 const validScope=sameWeightScope(scope,currentScope),mayWrite=current&&validScope&&!storageError;
 const latest=useRef({current,validScope,onRefresh});latest.current={current,validScope,onRefresh};
 useEffect(()=>{mounted.current=true;dialog.current?.showModal();heading.current?.focus();return()=>{mounted.current=false;};},[]);
 useEffect(()=>{if(['review','uncertain','absent','saved'].includes(phase))heading.current?.focus();},[phase]);
 function persist(next:WeightRecovery|null){
  try{
   if(localStorage.getItem(key)!==lastRaw.current)throw Error('Another tab changed the local recovery record.');
   const raw=next?JSON.stringify(next):null;if(raw) {decodeWeightRecovery(raw,scope);localStorage.setItem(key,raw);}else localStorage.removeItem(key);
   lastRaw.current=raw;return true;
  }catch{setStorageError(true);setMessage('Local recovery could not be updated, or another tab changed it. Nothing else will be saved. Changes in this dialog remain in memory; the existing recovery record was preserved.');return false;}
 }
 function close(){if(locked.current)return;dialog.current?.close();onClose();if(trigger.isConnected&&!trigger.disabled)trigger.focus();else onReturnFocus?.();}
 function change(field:keyof WeightForm,value:string){
  if(!session||locked.current||phase!=='editing')return;
  const next={...session,form:{...session.form,[field]:value},pending:null};setSession(next);if(!storageError){setMessage('');persist(next);}
 }
 async function review(retainRequest=false){
  if(!session||!mayWrite||locked.current)return;
  locked.current=true;setBusy(true);setMessage('');
  try{
   const next=retainRequest?session:{...session,pending:weightDraft(session)};
   if(!next.pending||!persist(next))return;
   setSession(next);
   await transport.action('validate',next.pending);
   if(mounted.current){if(!latest.current.current||!latest.current.validScope){setPhase('uncertain');setMessage('Patient evidence changed during review. The exact request is retained; check it before continuing.');}else setPhase('review');}
  }catch(error){if(mounted.current)setMessage(error instanceof Error?error.message:'Weight review could not be confirmed.');}
  finally{locked.current=false;if(mounted.current)setBusy(false);}
 }
 async function confirm(evidence:Evidence){
  if(!mounted.current)return;
  setSaved(evidence);setPhase('saved');
  // Retain the command until the user explicitly finishes; a crash can still recover it.
  if(!latest.current.validScope){setMessage('Saved to the original synthetic encounter. The displayed patient changed; no other patient was refreshed.');return;}
  try{await latest.current.onRefresh();if(mounted.current)setMessage('Saved. The patient overview was refreshed.');}
  catch{if(mounted.current)setMessage('Saved confirmation retained. The overview could not be refreshed; use Refresh records to confirm the patient picture.');}
 }
 async function save(){
  if(!session?.pending||phase!=='review'||!mayWrite||locked.current)return;
  // Persist before the first byte of a write request can leave this dialog.
  if(!persist(session))return;
  locked.current=true;setBusy(true);setPhase('saving');setMessage('');
  try{const r=await transport.action('save',session.pending);if(!r.evidence)throw Error('Missing confirmation');await confirm(r.evidence);}
  catch{if(mounted.current){setPhase('uncertain');setMessage('Save completion is unconfirmed. Check the original request before retrying or creating another weight.');}}
  finally{locked.current=false;if(mounted.current)setBusy(false);}
 }
 async function lookup(){
  if(!session?.pending||!validScope||locked.current||storageError)return;
  locked.current=true;setBusy(true);setMessage('');
  try{const r=await transport.action('lookup',session.pending);if(!mounted.current)return;if(r.status==='absent'){setPhase('absent');setMessage('The exact request was not found. Review the retained request before an explicit retry, or discard it.');}else if(r.evidence)await confirm(r.evidence);else throw Error();}
  catch{if(mounted.current)setMessage('The original request is still unconfirmed. Recovery data is retained; no retry was sent.');}
  finally{locked.current=false;if(mounted.current)setBusy(false);}
 }
 function edit(){if(!session||locked.current||!mayWrite||!['review','absent'].includes(phase))return;const next={...session,pending:null};if(persist(next)){setSession(next);setPhase('editing');setMessage('');}}
 function finish(){if(locked.current||!persist(null))return;close();}
 const field=(label:string,name:keyof WeightForm,maxLength=512)=><label>{label}<input value={session?.form[name]??''} maxLength={maxLength} onChange={e=>change(name,e.target.value)}/></label>;
 return <dialog ref={dialog} className="connected-source-dialog weight-entry-dialog" aria-labelledby="weight-entry-title" onCancel={event=>{event.preventDefault();close();}}>
  <header><div><p className="connected-eyebrow">Add information · Measurement</p><h2 id="weight-entry-title" ref={heading} tabIndex={-1}>{session?.predecessor?'Correct recorded weight':'Recorded weight'}</h2></div><button type="button" disabled={busy} onClick={close}>Close</button></header>
  <p>Candidate synthetic patient only. Original records are preserved.</p>
  {!validScope&&<p role="alert">Patient or repository changed. This entry belongs to the original encounter; saving and recovery checks are blocked here.</p>}
  {!current&&<p role="status">Patient evidence is unconfirmed. Review and new saves are blocked until refreshed.</p>}
  {initial.recovered&&<p role="status">Recovered the local weight draft{initial.session?.pending?' and its exact pending request. Check whether it was saved before continuing.':'.'}</p>}
  {message&&<p role={phase==='saved'?'status':'alert'} className="connected-warning">{message}</p>}
  {session&&phase==='editing'&&<form onSubmit={event=>{event.preventDefault();void review();}}><fieldset disabled={busy||!mayWrite} className="weight-entry-fields">
   {field('Weight','amount',128)}<label>Unit<select value={session.form.unit} onChange={e=>change('unit',e.target.value)}><option>kg</option><option>g</option></select></label>
   {field('Measurement time (blank if unknown)','point',128)}<p className="weight-entry-hint">Use the recorded date and time with its offset, for example 2026-10-08T09:45:00+05:30. No time is guessed.</p>
   <label>How obtained<select value={session.form.acquisition} onChange={e=>change('acquisition',e.target.value)}><option value="unknown">Unknown</option><option value="measured">Measured</option><option value="reported">Reported</option></select></label>
   {field('Recorded by','actor',128)}{field('Method (optional)','method',128)}{field('Source context','context')}{field('Uncertainty or limitations','uncertainty')}{field(session.predecessor?'Reason for correction':'Reason for new entry','reason')}
   <button type="submit">Review weight</button>
  </fieldset></form>}
  {session&&phase!=='editing'&&<section aria-label="Weight request review"><h3>{session.predecessor?'Correction':'Recorded weight'}</h3><dl><dt>Weight</dt><dd>{session.form.amount} {session.form.unit}</dd><dt>Measurement time</dt><dd>{session.form.point||'Unknown — no time supplied'}</dd><dt>How obtained</dt><dd>{session.form.acquisition}</dd><dt>Recorded by</dt><dd>{session.form.actor}</dd><dt>Method</dt><dd>{session.form.method||'Not supplied'}</dd><dt>Source context</dt><dd>{session.form.context}</dd><dt>Uncertainty or limitations</dt><dd>{session.form.uncertainty}</dd><dt>{session.predecessor?'Reason for correction':'Reason for new entry'}</dt><dd>{session.form.reason}</dd></dl>
   {phase==='review'&&<><button disabled={busy||!mayWrite} onClick={()=>void save()}>Save weight</button><button disabled={busy||!mayWrite} onClick={edit}>Edit weight</button></>}
   {phase==='saving'&&<p role="status">Saving the exact reviewed weight…</p>}
   {phase==='uncertain'&&<button disabled={busy||!validScope||storageError} onClick={()=>void lookup()}>Check saved result</button>}
   {phase==='absent'&&<><button disabled={busy||!mayWrite} onClick={()=>void review(true)}>Review same request for retry</button><button disabled={busy||!mayWrite} onClick={edit}>Edit weight</button></>}
   {phase==='saved'&&<><p>Confirmed saved{saved?.superseded?' — a historical revision; a correction also exists':''}. Its source and revision history remain available in the overview.</p><button disabled={busy||storageError} onClick={finish}>Done</button></>}
  </section>}
  {session&&['editing','review','absent'].includes(phase)&&<button disabled={busy||storageError} onClick={finish}>Discard local draft</button>}
  {phase==='uncertain'&&<p>Close and return through Add information to recover this same request. No automatic retry is performed.</p>}
 </dialog>;
}
