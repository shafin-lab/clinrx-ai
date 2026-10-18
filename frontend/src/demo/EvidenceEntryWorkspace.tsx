import type {PatientEvidenceState} from './usePatientEvidenceState';
import {ReassessmentComparison} from './ReassessmentComparison';
import {evidenceKey} from './evidenceIdentity';
import {useCallback,useEffect,useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryItem,CirculatoryState,CirculatoryHistory} from '../api/circulatoryTypes';
import {EvidenceEntryClient,type Draft,type Evidence} from '../api/evidenceEntryClient';
import {families,reference,RecordedDisclosure} from '../patient/CirculatoryEvidence';
import {title,value,sourceTime,record} from './evidencePresentation';
import {EvidenceDraftSummary} from './EvidenceDraftSummary';
import {GuidedEvidenceForm} from './GuidedEvidenceForm';
import {shortcutValue} from './guidedEvidence';
import './demo.css';
import './evidenceEntry.css';
type Phase='editing'|'review'|'saving'|'uncertain'|'absent'|'saved';
export interface SourceHandoff {token:number;item:CirculatoryItem;context:string}
export function EvidenceEntryWorkspace({client,entry,config,shared,handoff,onGuardChange}:{client:CirculatoryClient;entry:EvidenceEntryClient;config:{start:string;end:string};shared?:PatientEvidenceState;handoff?:SourceHandoff;onGuardChange?:(guarded:boolean)=>void}){
  const [localState,setState]=useState<CirculatoryState>(),[selected,setSelected]=useState<CirculatoryItem>();
  const [text,setText]=useState(''),[mode,setMode]=useState<'new'|'correct'|'withdraw'>('new');
  const [actor,setActor]=useState(''),[reason,setReason]=useState('');
  const [editor,setEditor]=useState<'guided'|'source'>('guided');
  const [search,setSearch]=useState(''),[family,setFamily]=useState('all');
  const [phase,setPhase]=useState<Phase>('editing'),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [review,setReview]=useState<Evidence>(),[pending,setPending]=useState<Draft>(),[history,setHistory]=useState<CirculatoryHistory>();
  const generation=useRef(0),historyGeneration=useRef(0),handledHandoff=useRef(0),[localGate,setGateConfirmed]=useState(false);
  const state=shared?(shared.state??shared.retainedState):localState,gateConfirmed=shared?shared.state?.execution_enabled===false:localGate;
  const [dirty,setDirty]=useState(false),[formSession,setFormSession]=useState(0);
  const guarded=busy||phase==='review'||phase==='saving'||phase==='uncertain'||phase==='absent'||(phase==='editing'&&dirty);
  useEffect(()=>{onGuardChange?.(guarded);},[guarded,onGuardChange]);
  useEffect(()=>{if(!pending||phase==='saved')return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[pending,phase]);
  const refresh=useCallback(async()=>{
    historyGeneration.current++;setHistory(undefined);
    if(shared){await shared.refresh();return;}
    const request=++generation.current;setGateConfirmed(false);
    try{const reply=await client.circulatoryState(config.start,config.end);
      if(request!==generation.current)return;
      if(reply.data.execution_enabled!==false)throw Error('gate_open');
      setState(reply.data);setGateConfirmed(true);
    }catch(error){if(request!==generation.current)return;setGateConfirmed(false);setError('Evidence entry blocked: disabled execution could not be confirmed. Refresh to check again.');throw error;}
  },[client,config.start,config.end,shared?.refresh]);
  useEffect(()=>{if(shared)return;void refresh().catch(()=>{});return()=>{generation.current++;historyGeneration.current++;};},[refresh]);
  useEffect(()=>{historyGeneration.current++;setHistory(undefined);},[shared?.state?.state_context]);
  let numeric='';try{numeric=String(record(record(JSON.parse(text).result).quantity).value??'');}catch{/* Invalid JSON must be repaired; never replace it with a shortcut. */}
  function editNumeric(next:string){try{setText(shortcutValue(text,next));}catch{setError('Repair the source JSON before editing its numeric value.');}}
  const proposedQuantity=record(record(review?.fact.result).quantity);
  const proposedFinding=record(record(review?.fact.result).finding);
  const locked=phase==='saving'||phase==='uncertain'||phase==='absent';
  function choose(item?:CirculatoryItem){if(locked||busy||!gateConfirmed)return;historyGeneration.current++;setDirty(false);setFormSession(n=>n+1);setSelected(item);setMode(item?'correct':'new');setEditor(item?'source':'guided');setText(item?JSON.stringify(item.fact,null,2):'');setReason('');setHistory(undefined);setReview(undefined);setPending(undefined);setPhase('editing');setError('');}
  useEffect(()=>{
    if(!handoff||handoff.token===handledHandoff.current||!state||!gateConfirmed)return;
    handledHandoff.current=handoff.token;
    const exact=state.assembly.snapshot.items.find(i=>evidenceKey(i.fact)===evidenceKey(handoff.item.fact)&&i.expected_digest===handoff.item.expected_digest);
    if(guarded||state.state_context!==handoff.context||!exact){setError('Exact source handoff is stale or an entry is pending. No source was substituted. Return to evidence after finishing the existing draft.');return;}
    choose(exact);setDirty(true);
  },[handoff?.token,state,gateConfirmed]);
  async function validate(){
    if(!state||!gateConfirmed||busy||locked)return;setBusy(true);setError('');
    try{
      if(!actor.trim()||(mode!=='new'&&!reason.trim()))throw Error('required');
      const fact=JSON.parse(text) as CirculatoryItem['fact'];
      if(mode!=='new'){
        if(!selected)throw Error('required');
        fact.kind=selected.fact.kind;fact.id=selected.fact.id;fact.revision=crypto.randomUUID();
        fact.supersedes=reference(selected);fact.correction_reason=reason.trim();
        if(mode==='withdraw')fact.record_status='withdrawn';
        if(fact.kind==='circulatory_lactate')fact.change='corrected';
        fact.provenance={source:{namespace:'clinrx-local-synthetic-entry',identifier:fact.revision,channel:'clinician',version:null},actor:actor.trim(),recorded_at:new Date().toISOString(),upstream:record(fact.provenance).upstream??[],lineage:'incomplete',limitations:['Local synthetic correction; copied source context requires explicit review.']};
      }else{
        if(fact.supersedes)throw Error('new_requires_root');
        // Complete source provenance remains user-authored on new imports.
        if(record(fact.provenance).actor!==actor.trim())throw Error('actor_mismatch');
      }
      const body:Draft={repository_id:state.assembly.request.scope.repository_cutoff.repository_id,fact,predecessor_digest:mode==='new'?null:selected!.expected_digest};
      const result=await entry.validate(body);
      setReview(result);setPending({...body,fact:result.fact});setPhase('review');
    }catch{setError('Draft not accepted. Supply your actor name, a correction reason where needed, and a complete valid source record. New-entry provenance.actor must match the actor name. No evidence was saved.');}
    finally{setBusy(false);}
  }
  async function save(){if(!pending||busy||!gateConfirmed)return;setPhase('saving');setBusy(true);setError('');
    try{setReview(await entry.save(pending));setPhase('saved');try{await refresh();}catch{setError('Saved revision confirmed; the evidence list could not be refreshed.');}}
    catch(error){if(error instanceof Error&&['conflict','invalid_draft'].includes(error.message)){setPhase('review');setError('Save rejected. The selection may be stale or the revision conflicts. Reload the evidence and create a reviewed draft; no automatic retry occurred.');}else{setPhase('uncertain');setError('Save completion is unknown. Keep this page open and check the exact revision. No automatic retry or replacement will occur.');}}
    finally{setBusy(false);}
  }
  async function recover(){if(!pending||busy)return;setBusy(true);setError('');try{const reply=await entry.lookup(pending);if(reply.status==='absent'){setPhase('absent');}else{setReview(reply.evidence);setPhase('saved');try{await refresh();}catch{setError('Exact revision recovered; refresh unavailable.');}}}catch{setError('The exact revision could not be confirmed. Keep the original draft; no retry occurred.');}finally{setBusy(false);}}
  async function revisions(){if(!selected||!state)return;const token=++historyGeneration.current;setBusy(true);setError('');try{const reply=await client.circulatoryHistory(state.state_context,reference(selected));if(token===historyGeneration.current)setHistory(reply.data);}catch{if(token===historyGeneration.current)setError('History could not be loaded. Refresh the recorded evidence first.');}finally{setBusy(false);}}
  return <main className={shared?"demo-shell entry-workspace integrated-entry":"demo-shell entry-workspace"}>{!shared&&<header><h1>Synthetic patient evidence entry</h1><p>Separate disposable local workspace · synthetic-p1 / synthetic-e1</p><p><strong>{gateConfirmed?'Clinical execution disabled.':'Execution gate not confirmed — new writes blocked.'}</strong> Source entry does not execute an inference or issue treatment advice. The accepted read-only Docker demo is separate.</p><p>Guided source entry and clinician-authored reassessment are available for common hemodynamic records. Advanced source entry preserves access to all 15 families. This remains a local synthetic prototype.</p></header>}
    {error&&<p role="alert">{error}</p>}{!gateConfirmed&&<><p role="status">Any retained snapshot is for reference only. New writes are blocked until the disabled gate is confirmed.</p><button disabled={busy} onClick={()=>void refresh().catch(()=>{})}>Check service and execution gate</button></>}
    {!state?<p>Loading the isolated evidence snapshot…</p>:<><p>{state.assembly.snapshot.items.length} source records in this snapshot. Originals remain in revision history. HPI is optional. Review window: {config.start} to {config.end}; source times may be contextual or unplaced.</p>{!shared&&<ReassessmentComparison state={state}/>}<div className="entry-columns"><section aria-label="Recorded evidence"><h2>Select evidence to correct</h2><button disabled={busy||locked||!gateConfirmed||(!!shared&&guarded)} onClick={()=>choose()}>New source entry</button><button disabled={busy||locked||(!!shared&&guarded)} onClick={()=>void refresh().catch(()=>setError('Refresh failed.'))}>Refresh evidence</button><label>Evidence family<select value={family} onChange={e=>setFamily(e.target.value)} disabled={busy||locked||!gateConfirmed}><option value="all">All 15 families</option>{Object.entries(families).map(([kind,label])=><option key={kind} value={kind}>{label}</option>)}</select></label><label>Find evidence<input value={search} onChange={e=>setSearch(e.target.value)} disabled={busy||locked||!gateConfirmed}/></label><ul className="entry-list">{state.assembly.snapshot.items.filter(item=>(family==='all'||item.fact.kind===family)&&[title(item),item.fact.id,value(item).text].join(' ').toLowerCase().includes(search.toLowerCase())).map(item=><li key={evidenceKey(item.fact)}><button disabled={busy||locked||!gateConfirmed||(!!shared&&guarded)} onClick={()=>choose(item)} aria-pressed={selected?.fact.id===item.fact.id&&selected?.fact.kind===item.fact.kind&&selected?.fact.revision===item.fact.revision}>{title(item)} · {value(item).text} {value(item).unit}<small>{item.fact.id} / {item.fact.revision} · {sourceTime(item)} · {String(item.fact.record_status)}</small></button></li>)}</ul></section>
    <section aria-label="Evidence draft"><h2>{mode==='new'?'New source entry':mode==='withdraw'?'Withdraw selected evidence':'Correct selected evidence'}</h2>
    {selected&&<><p>Original retained: {selected.fact.kind} / {selected.fact.id} / {selected.fact.revision}</p><p>Original recorded value: {value(selected).text} {value(selected).unit} · {sourceTime(selected)}</p><p>Correction keeps the original observation time and context unless explicitly changed in the source record. It is not a new measurement or evidence of ongoing administration.</p><button disabled={busy||locked||!gateConfirmed} onClick={()=>void revisions()}>Load exact revision history</button><RecordedDisclosure label="Original source record" value={selected.fact}/>{history&&<RecordedDisclosure label={'History: '+history.revisions.length+' retained revisions'} value={history.revisions}/>}</>}
    {phase==='editing'?<fieldset onChangeCapture={()=>setDirty(true)} disabled={busy||!gateConfirmed}><label>Actor name<input value={actor} onChange={e=>setActor(e.target.value)} disabled={busy}/></label>{selected&&<><label>Action<select value={mode} onChange={e=>setMode(e.target.value as 'correct'|'withdraw')} disabled={busy}><option value="correct">Append correction</option><option value="withdraw">Append withdrawal</option></select></label><label>Reason for correction or withdrawal<textarea value={reason} onChange={e=>setReason(e.target.value)} disabled={busy}/></label>{record(record(selected.fact.result).quantity).value!==undefined&&<label>Recorded numeric value (raw unit preserved)<input value={numeric} onChange={e=>editNumeric(e.target.value)} disabled={busy}/></label>}</>}
    {mode==='new'&&editor==='guided'?<><GuidedEvidenceForm key={formSession} actor={actor} items={state.assembly.snapshot.items} onDraft={fact=>{setText(JSON.stringify(fact,null,2));setEditor('source');setError('');}}/><button onClick={()=>{setText('');setEditor('source');}}>Advanced source entry</button></>:<><p>One authoritative source draft. The numeric shortcut and complete record editor update the same value.</p><details><summary>Edit complete source record (advanced)</summary><label>Complete source record (JSON)<textarea className="entry-json" value={text} onChange={e=>setText(e.target.value)} disabled={busy} spellCheck={false}/></label></details><p>Preserve exact Decimal strings, sample type, units, method, quality, timing and support references. Nothing is converted or inferred. For a new entry supply a new ID/revision, full binding and provenance; copied source assertions must be reviewed.</p><button disabled={busy} onClick={()=>void validate()}>Validate and review draft</button>{mode==='new'&&<button onClick={()=>{setText('');setEditor('guided');}}>Start a different guided record</button>}</>}{shared&&<button disabled={busy} onClick={()=>choose()}>Discard unsaved entry</button>}</fieldset>:<>
    <h3>Review before append</h3><p>{families[review?.fact.kind??'']} · {review?.fact.id} / {review?.fact.revision}</p>{proposedQuantity.value!==undefined&&<p>Proposed recorded result: {String(proposedQuantity.value)} {String(record(proposedQuantity.unit).raw??'Unit not recorded')}</p>}{proposedFinding.raw_display!==undefined&&<p>Proposed source finding: {String(proposedFinding.raw_display)}</p>}<p>Proposed status: {String(review?.fact.record_status)}</p><p>Actor: {String(record(review?.fact.provenance).actor??'Not recorded')}</p><p>Reason: {String(review?.fact.correction_reason??'New source entry; no predecessor')}</p>{review&&<EvidenceDraftSummary fact={review.fact}/>}<p>Digest: {review?.expected_digest}</p><RecordedDisclosure label="Complete validated record and source caveats" value={review?.fact}/><p>Saving adds one immutable revision. It does not overwrite the original or alter retained clinical receipts.</p>
    {phase==='review'&&<><button disabled={busy||!gateConfirmed} onClick={()=>void save()}>Confirm append to local database</button><button disabled={busy} onClick={()=>{setPhase('editing');setPending(undefined);setReview(undefined);}}>Edit draft</button><button disabled={busy} onClick={()=>{choose();void refresh().catch(()=>setError('Refresh failed.'));}}>Discard draft and reload</button></>}
    {(phase==='uncertain'||phase==='absent')&&<><p>Original pending revision: {pending?.fact.id} / {pending?.fact.revision}</p><button disabled={busy} onClick={()=>void recover()}>Check exact saved revision</button>{phase==='absent'&&<><p>The exact revision is absent in this lookup. This is not proof that an earlier request rolled back. An explicit retry reuses this same reviewed draft and revision.</p><button disabled={busy||!gateConfirmed} onClick={()=>void save()}>Explicitly retry the same revision</button></>}</>}
    {phase==='saving'&&<p role="status">Appending the exact reviewed revision…</p>}
    {phase==='saved'&&<><p role="status">Exact revision saved and confirmed. Ingestion sequence {review?.ingestion?.ingestion_sequence}.</p><button disabled={busy} onClick={()=>choose()}>Start another entry</button></>}
    </>}
    <p>Pending drafts exist only in this page’s memory. Reloading or closing can lose them. Keep this page open while completion is unknown.</p></section></div></>}
  </main>;
}
