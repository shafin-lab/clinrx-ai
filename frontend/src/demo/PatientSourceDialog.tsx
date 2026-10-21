import {useEffect,useRef,useState} from 'react';
import {key,pin,type Catalog,type Evidence,type RF2Client} from '../api/rf2Client';
import {evidenceText,sourceContext} from './RenalFluidEntryWorkspace';
import {record} from './evidencePresentation';
export interface SourceSelection {evidence:Evidence;catalog:Catalog;label:string;trigger:HTMLButtonElement}
export function PatientSourceDialog({selection,transport,current,onClose,onCorrect}:{selection:SourceSelection;transport:Pick<RF2Client,'history'>;current:boolean;onClose:()=>void;onCorrect?:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null),heading=useRef<HTMLHeadingElement>(null),generation=useRef(0);
 const [history,setHistory]=useState<Evidence[]>(),[error,setError]=useState('');
 const e=selection.evidence;
 useEffect(()=>{
  const ticket=++generation.current;setHistory(undefined);setError('');if(!dialog.current?.open)dialog.current?.showModal();heading.current?.focus();
  void transport.history(e).then(values=>{if(ticket===generation.current)setHistory(values);}).catch(()=>{if(ticket===generation.current)setError('Source history could not be confirmed. The selected record remains visible; no different version was substituted.');});
  return()=>{generation.current++;};
 },[selection,transport]);
 function close(){dialog.current?.close();onClose();if(selection.trigger.isConnected)selection.trigger.focus();}
 const note=e.metadata?.note,description=record(e.fact.description).raw_display;
 return <dialog ref={dialog} className="connected-source-dialog" aria-labelledby="patient-source-title" onCancel={event=>{event.preventDefault();close();}}>
  <header><div><p className="connected-eyebrow">Recorded patient information</p><h2 id="patient-source-title" ref={heading} tabIndex={-1}>{selection.label}</h2></div><button type="button" onClick={close} aria-label="Close source details">Close</button></header>
  {!current&&<p role="alert" className="connected-warning">Retained selected record — the current patient retrieval is not confirmed.</p>}
  <p className="connected-source-value">{evidenceText(e)}</p><p>{sourceContext(e,selection.catalog)}</p>
  {e.superseded&&<p>Historical corrected version retained. No newer version was substituted.</p>}
  {onCorrect&&e.fact.kind==='circulatory_event'&&e.metadata?.chart?.category==='weight'&&!e.superseded&&e.fact.record_status==='recorded'&&<button type="button" disabled={!current||!history||!!error} onClick={()=>{dialog.current?.close();onCorrect();}}>Correct recorded weight</button>}
  {note?<section aria-label="Recorded clinician note"><p>Clinician-authored record, not a generated conclusion.</p>{(['question','findings','possibilities','gaps','plan'] as const).map(field=><p key={field}><strong>{field[0].toUpperCase()+field.slice(1)}: </strong>{note[field]}</p>)}</section>:typeof description==='string'&&<p>{description}</p>}
  {!history&&!error&&<p role="status">Loading source history…</p>}{error&&<p role="alert">{error}</p>}
  <details><summary>Source history and recorded versions</summary>{history?.map(item=><article key={key(pin(item))}><p><strong>{evidenceText(item)}</strong></p><p>{item.fact.id} / {item.fact.revision} · {item.superseded?'Historical superseded version':'Recorded terminal version at this cutoff'}</p><details><summary>Complete recorded version</summary><pre tabIndex={0}>{JSON.stringify(item,null,2)}</pre></details></article>)}</details>
  <details><summary>Recorded timing, method and exact source</summary><pre tabIndex={0}>{JSON.stringify({reference:pin(e),patient:e.fact.binding.target,status:e.fact.record_status,time:e.fact.time,occurred:e.fact.occurred,interval:e.fact.recorded_interval,acquisition:e.fact.acquisition,verification:e.fact.verification,conflict:e.fact.conflict,uncertainty:e.fact.uncertainty},null,2)}</pre></details>
 </dialog>;
}
