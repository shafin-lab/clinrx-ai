import {useEffect,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryItem,CirculatoryState,CirculatoryHistory} from '../api/circulatoryTypes';
import {EvidenceEntryClient,type Draft,type Evidence} from '../api/evidenceEntryClient';
import {families,reference,RecordedDisclosure} from '../patient/CirculatoryEvidence';
import {title,value,sourceTime,record} from './evidencePresentation';
import './demo.css';
import './evidenceEntry.css';
type Phase='editing'|'review'|'saving'|'uncertain'|'absent'|'saved';
export function EvidenceEntryWorkspace({client,entry,config}:{client:CirculatoryClient;entry:EvidenceEntryClient;config:{start:string;end:string}}){
  const [state,setState]=useState<CirculatoryState>(),[selected,setSelected]=useState<CirculatoryItem>();
  const [text,setText]=useState(''),[mode,setMode]=useState<'new'|'correct'|'withdraw'>('new');
  const [actor,setActor]=useState(''),[reason,setReason]=useState(''),[numeric,setNumeric]=useState('');
  const [search,setSearch]=useState(''),[family,setFamily]=useState('all');
  const [phase,setPhase]=useState<Phase>('editing'),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [review,setReview]=useState<Evidence>(),[pending,setPending]=useState<Draft>(),[history,setHistory]=useState<CirculatoryHistory>();
  async function refresh(){const reply=await client.circulatoryState(config.start,config.end);if(reply.data.execution_enabled!==false)throw Error('gate_open');setState(reply.data);}
  useEffect(()=>{let active=true;void client.circulatoryState(config.start,config.end).then(reply=>{if(active&&reply.data.execution_enabled===false)setState(reply.data);else if(active)setError('Evidence entry blocked: disabled execution was not confirmed.');}).catch(()=>{if(active)setError('The isolated evidence service is unavailable.');});return()=>{active=false;};},[client,config.start,config.end]);
  const proposedQuantity=record(record(review?.fact.result).quantity);
  const proposedFinding=record(record(review?.fact.result).finding);
  const locked=phase==='saving'||phase==='uncertain'||phase==='absent';
  function choose(item?:CirculatoryItem){if(locked)return;setSelected(item);setMode(item?'correct':'new');setText(item?JSON.stringify(item.fact,null,2):'');setNumeric(item?String(record(record(item.fact.result).quantity).value??''):'');setReason('');setHistory(undefined);setReview(undefined);setPending(undefined);setPhase('editing');setError('');}
  async function validate(){
    if(!state||busy||locked)return;setBusy(true);setError('');
    try{
      if(!actor.trim()||(mode!=='new'&&!reason.trim()))throw Error('required');
      const fact=JSON.parse(text) as CirculatoryItem['fact'];
      if(mode!=='new'){
        if(!selected)throw Error('required');
        fact.kind=selected.fact.kind;fact.id=selected.fact.id;fact.revision=crypto.randomUUID();
        fact.supersedes=reference(selected);fact.correction_reason=reason.trim();
        if(mode==='withdraw')fact.record_status='withdrawn';
        if(numeric!==''&&record(record(fact.result).quantity).value!==undefined){const result=record(fact.result);fact.result={...result,quantity:{...record(result.quantity),value:numeric}};}
        if(fact.kind==='circulatory_lactate')fact.change='corrected';
        fact.provenance={source:{namespace:'clinrx-local-synthetic-entry',identifier:fact.revision,channel:'clinician',version:null},actor:actor.trim(),recorded_at:new Date().toISOString(),upstream:[],lineage:'incomplete',limitations:['Local synthetic correction; copied source context requires explicit review.']};
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
  async function save(){if(!pending||busy)return;setPhase('saving');setBusy(true);setError('');
    try{setReview(await entry.save(pending));setPhase('saved');try{await refresh();}catch{setError('Saved revision confirmed; the evidence list could not be refreshed.');}}
    catch(error){if(error instanceof Error&&['conflict','invalid_draft'].includes(error.message)){setPhase('review');setError('Save rejected. The selection may be stale or the revision conflicts. Reload the evidence and create a reviewed draft; no automatic retry occurred.');}else{setPhase('uncertain');setError('Save completion is unknown. Keep this page open and check the exact revision. No automatic retry or replacement will occur.');}}
    finally{setBusy(false);}
  }
  async function recover(){if(!pending||busy)return;setBusy(true);setError('');try{const reply=await entry.lookup(pending);if(reply.status==='absent'){setPhase('absent');}else{setReview(reply.evidence);setPhase('saved');try{await refresh();}catch{setError('Exact revision recovered; refresh unavailable.');}}}catch{setError('The exact revision could not be confirmed. Keep the original draft; no retry occurred.');}finally{setBusy(false);}}
  async function revisions(){if(!selected||!state)return;setBusy(true);setError('');try{setHistory((await client.circulatoryHistory(state.state_context,reference(selected))).data);}catch{setError('History could not be loaded. Refresh the recorded evidence first.');}finally{setBusy(false);}}
  return <main className="demo-shell entry-workspace"><header><h1>Synthetic patient evidence entry</h1><p>Separate disposable local workspace · synthetic-p1 / synthetic-e1</p><p><strong>Clinical execution disabled.</strong> Source entry does not execute an inference or issue treatment advice. The accepted read-only Docker demo is separate.</p><p>This first entry workflow accepts complete structured source records across all 15 evidence families. It is a development tool, not a clinician-ready charting form.</p></header>
    {error&&<p role="alert">{error}</p>}
    {!state?<p>Loading the isolated evidence snapshot…</p>:<><p>{state.assembly.snapshot.items.length} source records in this snapshot. Originals remain in revision history. HPI is optional. Review window: {config.start} to {config.end}; source times may be contextual or unplaced.</p><div className="entry-columns"><section aria-label="Recorded evidence"><h2>Select evidence to correct</h2><button disabled={busy||locked} onClick={()=>choose()}>New source entry</button><button disabled={busy||locked} onClick={()=>void refresh().catch(()=>setError('Refresh failed.'))}>Refresh evidence</button><label>Evidence family<select value={family} onChange={e=>setFamily(e.target.value)} disabled={busy||locked}><option value="all">All 15 families</option>{Object.entries(families).map(([kind,label])=><option key={kind} value={kind}>{label}</option>)}</select></label><label>Find evidence<input value={search} onChange={e=>setSearch(e.target.value)} disabled={busy||locked}/></label><ul className="entry-list">{state.assembly.snapshot.items.filter(item=>(family==='all'||item.fact.kind===family)&&[title(item),item.fact.id,value(item).text].join(' ').toLowerCase().includes(search.toLowerCase())).map(item=><li key={[item.fact.kind,item.fact.id,item.fact.revision].join('/')}><button disabled={busy||locked} onClick={()=>choose(item)} aria-pressed={selected?.fact.id===item.fact.id&&selected?.fact.kind===item.fact.kind}>{title(item)} · {value(item).text} {value(item).unit}<small>{item.fact.id} / {item.fact.revision} · {sourceTime(item)} · {String(item.fact.record_status)}</small></button></li>)}</ul></section>
    <section aria-label="Evidence draft"><h2>{mode==='new'?'New source entry':mode==='withdraw'?'Withdraw selected evidence':'Correct selected evidence'}</h2>
    {selected&&<><p>Original retained: {selected.fact.kind} / {selected.fact.id} / {selected.fact.revision}</p><p>Correction keeps the original observation time and context unless explicitly changed in the source record. It is not a new measurement or evidence of ongoing administration.</p><button disabled={busy||locked} onClick={()=>void revisions()}>Load exact revision history</button><RecordedDisclosure label="Original source record" value={selected.fact}/>{history&&<RecordedDisclosure label={'History: '+history.revisions.length+' retained revisions'} value={history.revisions}/>}</>}
    {phase==='editing'?<><label>Actor name<input value={actor} onChange={e=>setActor(e.target.value)} disabled={busy}/></label>{selected&&<><label>Action<select value={mode} onChange={e=>setMode(e.target.value as 'correct'|'withdraw')} disabled={busy}><option value="correct">Append correction</option><option value="withdraw">Append withdrawal</option></select></label><label>Reason for correction or withdrawal<textarea value={reason} onChange={e=>setReason(e.target.value)} disabled={busy}/></label>{record(record(selected.fact.result).quantity).value!==undefined&&<label>Recorded numeric value (raw unit preserved)<input value={numeric} onChange={e=>setNumeric(e.target.value)} disabled={busy}/></label>}</>}
    <label>Complete source record (JSON)<textarea className="entry-json" value={text} onChange={e=>setText(e.target.value)} disabled={busy} spellCheck={false}/></label><p>Preserve exact Decimal strings, sample type, units, method, quality, timing and support references. Nothing is converted or inferred. For a new entry supply a new ID/revision, full binding and provenance; copied source assertions must be reviewed.</p><button disabled={busy} onClick={()=>void validate()}>Validate and review draft</button></>:<>
    <h3>Review before append</h3><p>{families[review?.fact.kind??'']} · {review?.fact.id} / {review?.fact.revision}</p>{proposedQuantity.value!==undefined&&<p>Proposed recorded result: {String(proposedQuantity.value)} {String(record(proposedQuantity.unit).raw??'Unit not recorded')}</p>}{proposedFinding.raw_display!==undefined&&<p>Proposed source finding: {String(proposedFinding.raw_display)}</p>}<p>Proposed status: {String(review?.fact.record_status)}</p><p>Actor: {String(record(review?.fact.provenance).actor??'Not recorded')}</p><p>Reason: {String(review?.fact.correction_reason??'New source entry; no predecessor')}</p><p>Digest: {review?.expected_digest}</p><RecordedDisclosure label="Complete validated record and source caveats" value={review?.fact}/><p>Saving adds one immutable revision. It does not overwrite the original or alter retained clinical receipts.</p>
    {phase==='review'&&<><button disabled={busy} onClick={()=>void save()}>Confirm append to local database</button><button disabled={busy} onClick={()=>{setPhase('editing');setPending(undefined);setReview(undefined);}}>Edit draft</button><button disabled={busy} onClick={()=>{choose();void refresh().catch(()=>setError('Refresh failed.'));}}>Discard draft and reload</button></>}
    {(phase==='uncertain'||phase==='absent')&&<><p>Original pending revision: {pending?.fact.id} / {pending?.fact.revision}</p><button disabled={busy} onClick={()=>void recover()}>Check exact saved revision</button>{phase==='absent'&&<><p>The exact revision is absent in this lookup. This is not proof that an earlier request rolled back. An explicit retry reuses this same reviewed draft and revision.</p><button disabled={busy} onClick={()=>void save()}>Explicitly retry the same revision</button></>}</>}
    {phase==='saving'&&<p role="status">Appending the exact reviewed revision…</p>}
    {phase==='saved'&&<><p role="status">Exact revision saved and confirmed. Ingestion sequence {review?.ingestion?.ingestion_sequence}.</p><button disabled={busy} onClick={()=>choose()}>Start another entry</button></>}
    </>}
    <p>Pending drafts exist only in this page’s memory. Reloading or closing can lose them. Keep this page open while completion is unknown.</p></section></div></>}
  </main>;
}
