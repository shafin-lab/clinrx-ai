import {retainedReassessmentReference} from './retainedReassessmentReference';
import {useState} from 'react';
import type {CirculatoryItem,CirculatoryState,ExactRef} from '../api/circulatoryTypes';
import {evidenceKey,resolveEvidenceKey} from './evidenceIdentity';
import {record,sourceTime} from './evidencePresentation';
import {RecordedDisclosure} from '../patient/CirculatoryEvidence';

const stages=['baseline','intervention','followup'] as const;
const labels={baseline:'Baseline reference',intervention:'Intervention reference',followup:'Follow-up ABG / evidence reference'};
export function isReassessment(item:CirculatoryItem){
 return item.fact.kind==='circulatory_event'&&Array.isArray(item.fact.source_identifiers)&&item.fact.source_identifiers.some(v=>record(v).namespace==='clinrx.local.chart-entry/v1'&&record(v).code==='reassessment');
}
/** Resolve only explicitly stage-labelled references with matching exact context associations. */
export function reassessmentReference(item:CirculatoryItem,stage:typeof stages[number]):ExactRef|undefined{
 const entries=Array.isArray(item.fact.external_evidence)?item.fact.external_evidence.filter(v=>record(v).namespace==='clinrx.local.reassessment.'+stage+'/v1'):[];
 if(entries.length!==1)return undefined;
 const ref=retainedReassessmentReference(record(entries[0]).code);if(!ref)return undefined;
 const associations=Array.isArray(item.fact.associations)?item.fact.associations:[];
 const matched=associations.filter(v=>{const a=record(v),exact=record(a.exact),scope=record(a.scope);return a.role==='context'&&a.status==='resolved'&&exact.kind===ref.kind&&exact.id===ref.id&&exact.version===ref.version&&scope.patient_id===item.fact.binding.target.patient_id&&scope.encounter_id===item.fact.binding.target.encounter_id;});
 return matched.length===1?ref:undefined;
}
export function ReassessmentComparison({state}:{state:CirculatoryState}){
 const [left,setLeft]=useState(''),[right,setRight]=useState('');
 const scope=state.assembly.request.scope;
 const notes=state.assembly.snapshot.items.filter(i=>isReassessment(i)&&i.fact.binding.target.patient_id===scope.patient_id&&i.fact.binding.target.encounter_id===scope.encounter_id);
 const selected=[resolveEvidenceKey(notes,left),resolveEvidenceKey(notes,right)];
 return <section className="note-comparison" aria-label="Read-only reassessment comparison"><h2>Compare reassessment notes</h2>
 <p>Read-only comparison of two explicitly selected notes. A new note does not replace an earlier note or its exact references. A/B selection does not establish chronology, clinical improvement or treatment effect.</p>
 <div className="note-comparison-selectors">{(['A','B'] as const).map((label,n)=><label key={label}>Note {label}<select value={n===0?left:right} onChange={e=>(n===0?setLeft:setRight)(e.target.value)}><option value="">Select an exact reassessment note</option>{(n===0?left:right)&&!selected[n]&&<option value={n===0?left:right}>Selected note unavailable in this snapshot</option>}{notes.map(note=><option key={evidenceKey(note.fact)} value={evidenceKey(note.fact)}>{sourceTime(note)} · {note.fact.id} / {note.fact.revision} · {String(note.fact.record_status)}</option>)}</select></label>)}</div>
 {left&&left===right&&<p role="status">Both columns select the same exact note; this is not a comparison of two different notes.</p>}
 <div className="note-comparison-scroll" tabIndex={0} role="region" aria-label="Note reference comparison table"><table><caption>Exact note identities and retained evidence references</caption><thead><tr><th scope="col">Recorded field</th><th scope="col">Note A</th><th scope="col">Note B</th></tr></thead><tbody>
 <tr><th scope="row">Note identity / revision</th>{selected.map((note,n)=><td key={n}>{note?<>{note.fact.kind}<br/>{note.fact.id}<br/><strong>Revision: {note.fact.revision}</strong></>:((n===0?left:right)?'Selected note unavailable in this snapshot':'No note selected')}</td>)}</tr>
 <tr><th scope="row">Note source time</th>{selected.map((note,n)=><td key={n}>{note?sourceTime(note):'Not available'}</td>)}</tr>
 <tr><th scope="row">Actor / recorded status</th>{selected.map((note,n)=><td key={n}>{note?<>{String(record(note.fact.provenance).actor??'Actor not recorded')}<br/>{String(note.fact.record_status)}</>:'Not available'}</td>)}</tr>
 {stages.map(stage=><tr key={stage}><th scope="row">{labels[stage]}</th>{selected.map((note,n)=>{const ref=note&&reassessmentReference(note,stage);return <td key={n}>{!note?'Not available':ref?<>{ref.kind}<br/>{ref.id}<br/><strong>Revision: {ref.version}</strong></>:<strong>Reference missing, ambiguous or inconsistent — inspect the complete note</strong>}</td>;})}</tr>)}
 </tbody></table></div><p>References are shown exactly as retained by each note, even if a successor exists. Referenced measurement values are not reloaded or substituted here. Use source history to inspect measurements and their uncertainty.</p>
 <div className="note-comparison-details">{selected.map((note,n)=>note&&<div key={n}><h3>Note {n===0?'A':'B'} — authored text and caveats</h3><RecordedDisclosure label={'Note '+(n===0?'A':'B')+' full authored narrative'} value={note.fact.description}/><RecordedDisclosure label={'Note '+(n===0?'A':'B')+' uncertainty and provenance'} value={{uncertainty:note.fact.uncertainty,provenance:note.fact.provenance}}/><RecordedDisclosure label={'Note '+(n===0?'A':'B')+' complete retained record'} value={note.fact}/></div>)}</div>
 </section>;
}
