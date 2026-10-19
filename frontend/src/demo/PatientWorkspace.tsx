import {useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryItem} from '../api/circulatoryTypes';
import type {EvidenceEntryClient} from '../api/evidenceEntryClient';
import {usePatientEvidenceState} from './usePatientEvidenceState';
import {ComprehensiveDemo,type EvidenceSearchRequest} from './ComprehensiveDemo';
import {EvidenceEntryWorkspace,type SourceHandoff} from './EvidenceEntryWorkspace';
import {ReassessmentComparison} from './ReassessmentComparison';
import {HandoverReview,type HandoverSelection} from './HandoverReview';
import {evidenceKey} from './evidenceIdentity';
import './evidenceEntry.css';
const steps={evidence:'Patient and evidence',entry:'Source entry and reassessment',compare:'Compare notes',handover:'Handover'} as const;
export function PatientWorkspace({client,entry,config}:{client:CirculatoryClient;entry:EvidenceEntryClient;config:{patient:string;encounter:string;start:string;end:string;releasedExample:string;withheldExample:string;hosted?:boolean}}){
 const shared=usePatientEvidenceState(client,config),[view,setView]=useState<keyof typeof steps>('evidence');
 const [guarded,setGuarded]=useState(false),[handoff,setHandoff]=useState<SourceHandoff>(),[selections,setSelections]=useState<HandoverSelection[]>([]);
 const [actionError,setActionError]=useState(''),[findQuery,setFindQuery]=useState(''),[searchRequest,setSearchRequest]=useState<EvidenceSearchRequest>();
 const snapshot=shared.state??shared.retainedState;
 const token=useRef(0),heading=useRef<HTMLHeadingElement>(null);
 function navigate(next:keyof typeof steps){if(guarded&&next!==view)return;setView(next);heading.current?.focus();}
 function findEvidence(){if(guarded||!shared.state)return;setSearchRequest({token:++token.current,query:findQuery});navigate('evidence');}
 function correct(item:CirculatoryItem){if(guarded||!shared.state)return;setHandoff({token:++token.current,item,context:shared.state.state_context});navigate('entry');}
 function add(item:CirculatoryItem){if(!shared.state)return;const exact=shared.state.assembly.snapshot.items.find(i=>evidenceKey(i.fact)===evidenceKey(item.fact)&&i.expected_digest===item.expected_digest);if(!exact){setActionError('The source selection is stale. Inspect it again before adding it to handover; no successor was substituted.');return;}setActionError('');const repository=shared.state.assembly.request.scope.repository_cutoff.repository_id;setSelections(old=>old.some(s=>s.repository===repository&&evidenceKey(s.item.fact)===evidenceKey(item.fact))?old:[...old,{item:exact,repository,cutoff:shared.state!.assembly.request.scope.repository_cutoff.fact_watermark}]);}
 return <div className="patient-workspace"><a href="#patient-workflow">Skip to patient workflow</a><header><h1 ref={heading} tabIndex={-1}>Synthetic ICU patient workspace</h1><p>Patient {config.patient} · Encounter {config.encounter}</p><p><strong>{shared.state?'Clinical execution disabled.':'Execution gate not confirmed — new writes blocked.'}</strong> Local synthetic evidence only; no treatment advice.</p><form role="search" aria-label="Find patient evidence" onSubmit={event=>{event.preventDefault();findEvidence();}}><label>Find recorded evidence<input type="search" value={findQuery} onChange={event=>setFindQuery(event.target.value)} placeholder="ABG 09:45, cardiac output, RVSP…" disabled={guarded||!shared.state}/></label><button disabled={guarded||!shared.state} type="submit">Find evidence</button></form><p>Recorded evidence → inspect source/history → append correction → author reassessment → compare notes → review handover.</p><p>Recorded source assertions, clinician-authored notes and retained derived examples are labelled separately. A note is not an automatically validated conclusion.</p><nav aria-label="Patient workflow">{Object.entries(steps).map(([key,label])=><button key={key} aria-current={view===key?'page':undefined} disabled={guarded&&view!==key} onClick={()=>navigate(key as keyof typeof steps)}>{label}</button>)}</nav>{guarded&&<p role="status">Finish, recover or explicitly discard the entry before leaving this step. The editor and exact pending revision remain mounted. Do not reload or close while completion is unknown.</p>}</header>
 {actionError&&<p role="alert">{actionError}</p>}{shared.error&&<p role="alert">{shared.error}</p>}{!shared.state&&<button disabled={shared.loading||guarded} onClick={()=>void shared.refresh().catch(()=>{})}>Refresh patient evidence</button>}
 <div id="patient-workflow" tabIndex={-1}><div hidden={view!=='evidence'}><ComprehensiveDemo client={client} config={config} shared={shared} embedded searchRequest={searchRequest} onCorrect={correct} onHandover={add}/></div>
 <div hidden={view!=='entry'}><EvidenceEntryWorkspace client={client} entry={entry} config={config} shared={shared} handoff={handoff} onGuardChange={setGuarded}/></div>
 {snapshot&&<><div hidden={view!=='compare'||!shared.state}><ReassessmentComparison state={snapshot}/><p>Choose two exact notes. Original references remain unchanged when a measurement is corrected.</p></div><div hidden={view!=='handover'||!shared.state}><HandoverReview state={snapshot} selections={selections} onRemove={key=>setSelections(old=>old.filter(s=>s.repository+evidenceKey(s.item.fact)!==key))}/></div></>}
 </div></div>;
}
