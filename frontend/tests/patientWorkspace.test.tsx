import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within,waitFor,act} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import type {CirculatoryItem,CirculatoryState,CirculatoryHistory} from '../src/api/circulatoryTypes';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {EvidenceEntryClient,type Draft,type Evidence} from '../src/api/evidenceEntryClient';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {EvidenceEntryWorkspace} from '../src/demo/EvidenceEntryWorkspace';
import {buildGuided} from '../src/demo/guidedEvidence';
import {evidenceKey} from '../src/demo/evidenceIdentity';
// These are full workspace integration journeys with commit, recovery and
// remount steps. Use the existing 15s integration budget, retaining all assertions.
afterEach(()=>{cleanup();window.localStorage.clear();});
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00',releasedExample:'00000000-0000-4000-8000-00000000c901',withheldExample:'00000000-0000-4000-8000-00000000c902',hosted:true};
function setup(change?:(s:CirculatoryState)=>void){
 let state=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false});state.assembly.snapshot.items=state.assembly.snapshot.items.filter(i=>['m7-CO','fs-PH-30','fs-PH-60','fs-D-CHANGE'].includes(i.fact.id));change?.(state);
 const client={circulatoryState:vi.fn(async()=>({data:state})),circulatoryHistory:vi.fn(async()=>({data:{revisions:[] as CirculatoryHistory['revisions']}})),circulatoryLookup:vi.fn(),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn(),circulatoryReconcile:vi.fn()};
 const entry={validate:vi.fn(async(body:Draft)=>({repository_id:body.repository_id,fact:body.fact,expected_digest:'a'.repeat(64),canonical_fact:JSON.stringify(body.fact),ingestion:null} as Evidence)),save:vi.fn(async(body:Draft)=>{const base=state.assembly.snapshot.items[0];const item={...base,fact:body.fact,expected_digest:'a'.repeat(64),ingestion:{...base.ingestion,ingestion_sequence:state.assembly.request.scope.repository_cutoff.fact_watermark+1}};state={...state,state_context:state.state_context+'-refreshed',assembly:{...state.assembly,request:{...state.assembly.request,scope:{...state.assembly.request.scope,repository_cutoff:{...state.assembly.request.scope.repository_cutoff,fact_watermark:item.ingestion.ingestion_sequence}}},snapshot:{...state.assembly.snapshot,items:[...state.assembly.snapshot.items.filter(i=>i.fact.kind!==item.fact.kind||i.fact.id!==item.fact.id),item]}}};return {repository_id:body.repository_id,fact:body.fact,expected_digest:item.expected_digest,canonical_fact:JSON.stringify(body.fact),ingestion:item.ingestion} as Evidence;}),lookup:vi.fn()};
 const view=render(<PatientWorkspace client={client as unknown as CirculatoryClient} entry={entry as unknown as EvidenceEntryClient} config={config}/>);
 return {client,entry,view,getState:()=>state,setState:(s:CirculatoryState)=>{state=s;}};
}
const step=(name:string)=>fireEvent.click(screen.getByRole('button',{name}));
async function ready(){await screen.findByRole('button',{name:'Inspect Cardiac output m7-CO'});}
async function source(){step('Evidence library');fireEvent.change(screen.getByRole('searchbox',{name:'Search recorded evidence'}),{target:{value:'fs-PH-60'}});fireEvent.click(await screen.findByRole('button',{name:'Inspect pH fs-PH-60'}));}
async function correction(){await ready();await source();step('Correct this exact source');await screen.findByRole('heading',{name:'Correct selected evidence'});fireEvent.change(screen.getByRole('textbox',{name:'Actor name'}),{target:{value:'Synthetic integration reviewer'}});fireEvent.change(screen.getByRole('textbox',{name:'Reason for correction or withdrawal'}),{target:{value:'Synthetic transcription correction'}});fireEvent.change(screen.getByRole('textbox',{name:'Recorded numeric value (raw unit preserved)'}),{target:{value:'7.3600'}});step('Validate and review draft');await screen.findByRole('button',{name:'Confirm append to local database'});}
it('uses one shared snapshot and hands off the exact selected revision and digest without enabling execution',async()=>{
 const {client,entry,getState}=setup();await correction();expect(client.circulatoryState).toHaveBeenCalledTimes(1);
 const original=getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;const body=entry.validate.mock.calls[0][0];expect(body.predecessor_digest).toBe(original.expected_digest);expect(body.fact.supersedes).toEqual({kind:original.fact.kind,id:original.fact.id,version:original.fact.revision});expect(body.fact.occurred).toEqual(original.fact.occurred);expect(body.fact.blood_gas_context).toEqual(original.fact.blood_gas_context);
 expect(screen.getByRole('button',{name:'Handover'})).toBeDisabled();expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();expect(entry.save).not.toHaveBeenCalled();
},15000);
it('preserves a guided unsaved draft by blocking navigation and refresh until explicit discard',async()=>{
 const {client}=setup();await ready();step('Source entry and reassessment');fireEvent.change(screen.getByRole('textbox',{name:'Actor name'}),{target:{value:'Draft actor'}});
 expect(screen.getByRole('button',{name:'Patient and evidence'})).toBeDisabled();expect(screen.getByRole('button',{name:'New source entry'})).toBeDisabled();for(const button of screen.getByRole('region',{name:'Recorded evidence'}).querySelectorAll('.entry-list button'))expect(button).toBeDisabled();expect(screen.getByRole('button',{name:'Refresh evidence'})).toBeDisabled();expect(screen.getByRole('textbox',{name:'Actor name'})).toHaveValue('Draft actor');expect(client.circulatoryState).toHaveBeenCalledTimes(1);
 step('Discard unsaved entry');expect(screen.getByRole('button',{name:'Patient and evidence'})).toBeEnabled();step('Patient and evidence');expect(screen.getByRole('navigation',{name:'Evidence views'})).toBeInTheDocument();
},15000);
it.each(['committed','absent'] as const)('retains original pending draft through %s recovery, without navigation or automatic retry',async mode=>{
 const {entry,client}=setup();await correction();entry.save.mockRejectedValueOnce(Error('lost_delivery'));step('Confirm append to local database');await screen.findByRole('button',{name:'Check exact saved revision'});const pending=entry.save.mock.calls[0][0];
 expect(screen.getByRole('button',{name:'Compare notes'})).toBeDisabled();expect(screen.queryByRole('button',{name:'Discard unsaved entry'})).not.toBeInTheDocument();
 if(mode==='committed')entry.lookup.mockResolvedValue({status:'committed_match',evidence:{fact:pending.fact,ingestion:{ingestion_sequence:900}}});else entry.lookup.mockResolvedValue({status:'absent'});
 step('Check exact saved revision');
 if(mode==='absent'){await screen.findByRole('button',{name:'Explicitly retry the same revision'});expect(entry.save).toHaveBeenCalledTimes(1);step('Explicitly retry the same revision');}
 await screen.findByText(/Exact revision saved and confirmed/);expect(entry.lookup).toHaveBeenCalledWith(pending);expect(entry.save).toHaveBeenCalledTimes(mode==='absent'?2:1);if(mode==='absent')expect(entry.save.mock.calls[1][0]).toBe(pending);expect(client.circulatoryExecute).not.toHaveBeenCalled();
},15000);
it('keeps exact pending identity and blocks navigation when lookup fails',async()=>{
 const {entry}=setup();await correction();entry.save.mockRejectedValueOnce(Error('malformed'));step('Confirm append to local database');await screen.findByRole('button',{name:'Check exact saved revision'});entry.lookup.mockRejectedValueOnce(Error('network'));step('Check exact saved revision');await screen.findByText(/exact revision could not be confirmed/);expect(entry.save).toHaveBeenCalledTimes(1);expect(screen.getByRole('button',{name:'Handover'})).toBeDisabled();
},15000);
it.each(['gate','patient','encounter'] as const)('fails closed on unconfirmed %s and recovers only after an explicit refresh',async mode=>{
 const {client,getState,setState}=setup(s=>{if(mode==='gate')s.execution_enabled=true;else if(mode==='patient')s.assembly.request.scope.patient_id='foreign';else s.assembly.request.scope.encounter_id='foreign';});
 await screen.findByRole('alert');expect(screen.queryByRole('button',{name:'Inspect Cardiac output m7-CO'})).not.toBeInTheDocument();const valid=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false});valid.assembly.snapshot.items=valid.assembly.snapshot.items.filter(i=>['m7-CO','fs-PH-30','fs-PH-60','fs-D-CHANGE'].includes(i.fact.id));setState(valid);step('Refresh patient evidence');await ready();expect(client.circulatoryState).toHaveBeenCalledTimes(2);expect(getState().execution_enabled).toBe(false);
},15000);
it('reviews handover from exact selections, retaining historical identity when the latest snapshot changes',async()=>{
 const {client,getState,setState}=setup();await ready();await source();step('Add exact source to handover');step('Handover');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');expect(screen.getByText(/Exact selected revision is also present/)).toBeInTheDocument();
 step('Patient and evidence');const next=structuredClone(getState());next.state_context+='-new';next.assembly.snapshot.items=next.assembly.snapshot.items.filter(i=>i.fact.id!=='fs-PH-60');setState(next);step('Refresh recorded state');await waitFor(()=>expect(client.circulatoryState).toHaveBeenCalledTimes(2));await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh recorded state'})).toBeEnabled());step('Handover');expect(screen.getByText(/Historical selection only/)).toBeInTheDocument();expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');
},15000);
it('invalidates an in-flight inspector history on shared refresh and does not show stale data',async()=>{
 const {client}=setup();await ready();await source();let resolve!:(v:unknown)=>void;client.circulatoryHistory.mockImplementationOnce(()=>new Promise(r=>{resolve=r;}) as never);step('Inspect revision history');step('Refresh recorded state');await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh recorded state'})).toBeEnabled());await act(async()=>{resolve({data:{revisions:[{fact:{id:'STALE',revision:'old'},ingestion:{}}]}});});expect(screen.queryByText('STALE / old')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Correct this exact source'})).not.toBeInTheDocument();
},15000);
it('rejects a stale source handoff rather than replacing the entry selection',async()=>{
 const state=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false});const item=state.assembly.snapshot.items[0],entry={validate:vi.fn(),save:vi.fn(),lookup:vi.fn()};
 render(<EvidenceEntryWorkspace client={{} as CirculatoryClient} entry={entry as unknown as EvidenceEntryClient} config={config} shared={{state,loading:false,error:'',refresh:vi.fn()}} handoff={{token:1,item,context:'stale-context'}}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Exact source handoff is stale');expect(screen.queryByText('Original retained:')).not.toBeInTheDocument();expect(entry.validate).not.toHaveBeenCalled();
},15000);

it('completes correction, separate authored reassessment, comparison and handover without rewriting the original note',async()=>{
 let originalNote!:CirculatoryItem;
 const {entry,client,getState}=setup(s=>{
  const find=(id:string)=>s.assembly.snapshot.items.find(i=>i.fact.id===id)!;
  const baseline=find('fs-PH-30'),intervention=find('fs-D-CHANGE'),followup=find('fs-PH-60');
  const fact=structuredClone(buildGuided('reassessment',{baseline:evidenceKey(baseline.fact),intervention:evidenceKey(intervention.fact),followup:evidenceKey(followup.fact),question:'Original source review',findings:'Original recorded ABG.',possibilities:'Unconfirmed; no response established.',uncertainty:'Unknown clock; synthetic.',nextReview:'Review source.'},'Original synthetic reviewer',s.assembly.snapshot.items,'original-assessment','2026-10-18T12:00:00Z'));
  originalNote={...followup,fact};s.assembly.snapshot.items.push(originalNote);
 });
 const originalBytes=JSON.stringify(originalNote);await correction();step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Compare notes'})).toBeEnabled());
 const corrected=entry.save.mock.calls[0][0].fact;
 step('Start another entry');fireEvent.change(screen.getByRole('combobox',{name:'Entry family'}),{target:{value:'reassessment'}});
 for(const [name,value] of [['Reassessment question','Review exact corrected ABG'],['Recorded findings (your assessment)','Transcription correction, same specimen and time; not a new measurement.'],['Unconfirmed possibilities (your assessment)','No physiological improvement or treatment effect established.'],['Source limitations / uncertainty (required)','Unknown source quality and clock verification.']])fireEvent.change(screen.getByRole('textbox',{name}),{target:{value}});
 const baseline=getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!,intervention=getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
 for(const [name,value] of [['Baseline evidence',evidenceKey(baseline.fact)],['Documented intervention',evidenceKey(intervention.fact)],['Follow-up evidence',evidenceKey(corrected)]])fireEvent.change(screen.getByRole('combobox',{name}),{target:{value}});
 step('Use guided record for validation');step('Validate and review draft');await screen.findByRole('button',{name:'Confirm append to local database'});step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Compare notes'})).toBeEnabled());
 const reassessment=entry.save.mock.calls[1][0].fact;expect(reassessment.supersedes).toBeUndefined();expect(reassessment.associations).toEqual(expect.arrayContaining([expect.objectContaining({exact:{kind:corrected.kind,id:corrected.id,version:corrected.revision}})]));expect(JSON.stringify(originalNote)).toBe(originalBytes);
 step('Compare notes');fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(originalNote.fact)}});fireEvent.change(screen.getByRole('combobox',{name:'Note B'}),{target:{value:evidenceKey(reassessment)}});
 const row=screen.getAllByRole('row').find(r=>r.textContent?.includes('Follow-up ABG / evidence reference'))!;const cells=within(row).getAllByRole('cell');expect(cells[0]).toHaveTextContent('Revision: 1');expect(cells[1]).toHaveTextContent('Revision: '+corrected.revision);
 step('Patient and evidence');fireEvent.change(screen.getByRole('searchbox',{name:'Search recorded evidence'}),{target:{value:reassessment.id}});step('Inspect other '+reassessment.id);step('Add exact source to handover');step('Handover');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('Clinician-authored reassessment (synthetic assertion)');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent(corrected.revision);
 expect(entry.save).toHaveBeenCalledTimes(2);expect(client.circulatoryExecute).not.toHaveBeenCalled();expect(client.circulatoryPrepare).not.toHaveBeenCalled();
},15000);
it('preserves exact comparison selection across refresh and discloses a disappeared note',async()=>{
 const {getState,setState,client}=setup(s=>{
  const baseline=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!,followup=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!,intervention=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
  const fact=structuredClone(buildGuided('reassessment',{baseline:evidenceKey(baseline.fact),intervention:evidenceKey(intervention.fact),followup:evidenceKey(followup.fact),question:'Review',findings:'Recorded',possibilities:'Unconfirmed',uncertainty:'Unknown'},'Synthetic',s.assembly.snapshot.items,'retained-note','2026-10-18T12:00:00Z'));s.assembly.snapshot.items.push({...followup,fact});
 });
 await ready();const note=getState().assembly.snapshot.items.find(i=>i.fact.id==='retained-note')!;step('Compare notes');fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(note.fact)}});
 step('Patient and evidence');const next=structuredClone(getState());next.state_context+='-later';next.assembly.snapshot.items=next.assembly.snapshot.items.filter(i=>i.fact.id!=='retained-note');setState(next);step('Refresh recorded state');await waitFor(()=>expect(client.circulatoryState).toHaveBeenCalledTimes(2));await screen.findByRole('button',{name:'Inspect Cardiac output m7-CO'});step('Compare notes');expect(screen.getByRole('combobox',{name:'Note A'})).toHaveValue(evidenceKey(note.fact));expect(screen.getByRole('cell',{name:'Selected note unavailable in this snapshot'})).toBeInTheDocument();
},15000);

it('retains confirmed save identity when the subsequent shared refresh fails, while blocking new writes',async()=>{
 const {entry,client}=setup();await correction();client.circulatoryState.mockRejectedValueOnce(Error('refresh_failed'));step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await screen.findByText('Saved revision confirmed; the evidence list could not be refreshed.');
 expect(screen.getByText(/Execution gate not confirmed — new writes blocked/, {selector:'header strong'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'New source entry'})).toBeDisabled();expect(entry.save).toHaveBeenCalledTimes(1);expect(screen.getByText(/Retained snapshot is for reference only/i)).toBeInTheDocument();
},15000);

it('finds an ABG by plain name and source time from comparison, resets stale filters and opens the exact source',async()=>{
 const {client,entry,getState}=setup();await ready();step('Evidence library');fireEvent.change(screen.getByRole('combobox',{name:'Evidence family'}),{target:{value:'circulatory_echo'}});fireEvent.change(screen.getByRole('searchbox',{name:'Search recorded evidence'}),{target:{value:'stale-filter'}});step('Compare notes');
 const finder=screen.getByRole('search',{name:'Find patient evidence'});fireEvent.change(within(finder).getByRole('searchbox',{name:'Find recorded evidence'}),{target:{value:'ABG 09:00'}});fireEvent.submit(finder);
 await screen.findByRole('button',{name:'Inspect pH fs-PH-60'});expect(screen.getByRole('heading',{name:'Recorded evidence results'})).toHaveFocus();expect(screen.getByRole('combobox',{name:'Evidence family'})).toHaveValue('all');expect(screen.getByRole('status')).toHaveTextContent('1 recorded item');expect(screen.queryByRole('heading',{name:'Pressure and PAC/RHC'})).not.toBeInTheDocument();
 step('Inspect pH fs-PH-60');const item=getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent(item.fact.revision);step('Inspect revision history');await waitFor(()=>expect(client.circulatoryHistory).toHaveBeenCalledWith(getState().state_context,{kind:item.fact.kind,id:item.fact.id,version:item.fact.revision}));
 expect(client.circulatoryState).toHaveBeenCalledTimes(1);expect(entry.save).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
},15000);
it('blocks the workspace finder while an entry is unresolved or unsaved',async()=>{
 setup();await ready();step('Source entry and reassessment');fireEvent.change(screen.getByRole('textbox',{name:'Actor name'}),{target:{value:'Unsaved'}});expect(screen.getByRole('button',{name:'Find evidence'})).toBeDisabled();expect(screen.getByRole('searchbox',{name:'Find recorded evidence'})).toBeDisabled();
},15000);

it('saves exact handover pins and restores their verified API records after remount',async()=>{
 window.localStorage.clear();const first=setup();await ready();await source();step('Add exact source to handover');step('Handover');step('Save handover locally');await screen.findByText(/Saved locally in this browser: 1 selection/);const stored=window.localStorage.getItem(window.localStorage.key(0)!)!;expect(stored).not.toContain('blood_gas_context');first.view.unmount();
 const second=setup();await ready();fireEvent.click(await screen.findByRole('button',{name:'Open saved handover'}));await screen.findByText(/Restored saved handover: 1 selection/);expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');expect(second.entry.save).not.toHaveBeenCalled();expect(second.client.circulatoryExecute).not.toHaveBeenCalled();second.view.unmount();window.localStorage.clear();
},15000);
it('restores a historical pin as unavailable when a successor exists, preserving the original storage',async()=>{
 window.localStorage.clear();const first=setup();await ready();await source();step('Add exact source to handover');step('Handover');step('Save handover locally');await screen.findByText(/Saved locally/);const raw=window.localStorage.getItem(window.localStorage.key(0)!)!;first.view.unmount();
 const second=setup(s=>{s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!.fact.revision='successor';});await ready();step('Handover');await screen.findByText('Saved reference unavailable in the current snapshot');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');expect(screen.getByRole('region',{name:'Read-only handover'})).not.toHaveTextContent('successor');expect(window.localStorage.getItem(window.localStorage.key(0)!)).toBe(raw);second.view.unmount();window.localStorage.clear();
},15000);
it('reports storage failure without claiming a saved handover or discarding selections',async()=>{
 window.localStorage.clear();const {view}=setup();await ready();await source();step('Add exact source to handover');step('Handover');const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});step('Save handover locally');expect(await screen.findByRole('alert')).toHaveTextContent('not confirmed saved');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');expect(screen.queryByText(/Saved locally in this browser/)).not.toBeInTheDocument();write.mockRestore();view.unmount();window.localStorage.clear();
},15000);
it('blocks overwriting a handover changed in another tab and retains current selections',async()=>{
 window.localStorage.clear();const {view}=setup();await ready();await source();step('Add exact source to handover');step('Handover');const repoKey='clinrx.synthetic.handover.v1:'+JSON.stringify([decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false}).assembly.request.scope.repository_cutoff.repository_id,config.patient,config.encounter]);window.localStorage.setItem(repoKey,'changed');step('Save handover locally');expect(await screen.findByRole('alert')).toHaveTextContent('changed in another tab');expect(window.localStorage.getItem(repoKey)).toBe('changed');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('fs-PH-60 / 1');view.unmount();window.localStorage.clear();
},15000);

it('gives an explicit next step for each part of the patient workflow without claiming clinical completion',async()=>{
 setup();await ready();
 const guide=()=>screen.getByRole('region',{name:'Current workflow step'});
 expect(guide()).toHaveTextContent('source time or source ID');
 for(const [name,text] of [['Source entry and reassessment','exact lookup comes before'],['Compare notes','Select Note A and Note B explicitly'],['Handover','Save handover locally']]){step(name);expect(guide()).toHaveTextContent(text);expect(screen.getByRole('button',{name})).toHaveAttribute('aria-current','page');}
 fireEvent.click(within(guide()).getByText('How to complete this synthetic patient workflow'));
 expect(guide()).toHaveTextContent('not a clinical handover sign-off');expect(guide()).toHaveTextContent('not durably recovered after reload');
},15000);
it('starts a separate reassessment after confirmation with no copied evidence selections or automatic finding',async()=>{
 const {entry}=setup();await correction();step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Start a clinician-authored reassessment'})).toBeEnabled());step('Start a clinician-authored reassessment');
 const form=within(screen.getByRole('region',{name:'Evidence draft'}));
 expect(form.getByRole('combobox',{name:'Entry family'})).toHaveValue('reassessment');
 for(const name of ['Baseline evidence','Documented intervention','Follow-up evidence'])expect(form.getByRole('combobox',{name})).toHaveValue('');
 for(const name of ['Recorded findings (your assessment)','Unconfirmed possibilities (your assessment)'])expect(form.getByRole('textbox',{name})).toHaveValue('');
 expect(entry.save).toHaveBeenCalledTimes(1);
},15000);
it('withholds post-save handover navigation if the refreshed snapshot does not confirm the exact saved digest',async()=>{
 window.localStorage.clear();const {entry,client,getState,view}=setup();await correction();
 client.circulatoryState.mockImplementationOnce(async()=>{const next=structuredClone(getState());const item=next.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;item.expected_digest='b'.repeat(64);return {data:next};});
 step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Add saved record to handover'})).toBeEnabled());step('Add saved record to handover');
 expect(await screen.findByRole('alert')).toHaveTextContent('exact saved revision is not confirmed');expect(screen.getByRole('heading',{name:'Review before append'})).toBeInTheDocument();expect(entry.save).toHaveBeenCalledTimes(1);expect(client.circulatoryExecute).not.toHaveBeenCalled();view.unmount();window.localStorage.clear();
},15000);
it('keeps post-save actions blocked after an unconfirmed refresh',async()=>{
 const {entry,client}=setup();await correction();client.circulatoryState.mockRejectedValueOnce(Error('offline'));step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);
 for(const name of ['Find saved record','Add saved record to handover','Start a clinician-authored reassessment'])expect(screen.getByRole('button',{name})).toBeDisabled();
 expect(entry.save).toHaveBeenCalledTimes(1);expect(client.circulatoryExecute).not.toHaveBeenCalled();
},15000);
it('completes a cardiac-output correction through readable history, separate note, exact comparison and saved handover recovery',async()=>{
 window.localStorage.clear();let originalNote!:CirculatoryItem;
 const first=setup(s=>{
  const baseline=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!,intervention=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!,followup=s.assembly.snapshot.items.find(i=>i.fact.id==='m7-CO')!;
  originalNote={...followup,fact:structuredClone(buildGuided('reassessment',{baseline:evidenceKey(baseline.fact),intervention:evidenceKey(intervention.fact),followup:evidenceKey(followup.fact),question:'Earlier flow review',findings:'Recorded source assertions.',possibilities:'No relationship confirmed.',uncertainty:'Synthetic context and source limitations.'},'Earlier reviewer',s.assembly.snapshot.items,'flow-original-note','2026-10-08T08:10:00Z'))};s.assembly.snapshot.items.push(originalNote);
 });
 const beforeNote=JSON.stringify(originalNote);await ready();step('Inspect Cardiac output m7-CO');step('Correct this exact source');
 const draftForm=()=>within(screen.getByRole('region',{name:'Evidence draft'}));
 fireEvent.change(draftForm().getByRole('textbox',{name:'Actor name'}),{target:{value:'Milestone reviewer'}});fireEvent.change(draftForm().getByRole('textbox',{name:'Reason for correction or withdrawal'}),{target:{value:'Source transcription correction; not a new measurement'}});fireEvent.change(draftForm().getByRole('textbox',{name:'Recorded numeric value (raw unit preserved)'}),{target:{value:'4.5500'}});
 const original=first.getState().assembly.snapshot.items.find(i=>i.fact.id==='m7-CO')!;
 step('Validate and review draft');await screen.findByRole('button',{name:'Confirm append to local database'});step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Find saved record'})).toBeEnabled());
 const corrected=first.getState().assembly.snapshot.items.find(i=>i.fact.id==='m7-CO')!;
 step('Find saved record');await screen.findByRole('button',{name:'Inspect Cardiac output m7-CO'});step('Inspect Cardiac output m7-CO');
 first.client.circulatoryHistory.mockResolvedValueOnce({data:{revisions:[{fact:original.fact,ingestion:original.ingestion},{fact:corrected.fact,ingestion:corrected.ingestion}]}});step('Inspect revision history');
 const history=await screen.findByRole('region',{name:'Bounded source revision history'});expect(history).toHaveTextContent('Recorded result: 4.50 L/min');expect(history).toHaveTextContent('Recorded result: 4.5500 L/min');expect(history).toHaveTextContent('Source time:');
 step('Source entry and reassessment');step('Add saved record to handover');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent(corrected.fact.revision);
 step('Source entry and reassessment');step('Start a clinician-authored reassessment');
 for(const [name,value] of [['Reassessment question','Review recorded flow alongside intervention context'],['Recorded findings (your assessment)','The corrected source retains its original method and time.'],['Unconfirmed possibilities (your assessment)','No treatment response or physiological improvement established.'],['Source limitations / uncertainty (required)','Synthetic source; quality and timing context require review.']])fireEvent.change(draftForm().getByRole('textbox',{name}),{target:{value}});
 const baseline=first.getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!,intervention=first.getState().assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
 for(const [name,item] of [['Baseline evidence',baseline],['Documented intervention',intervention],['Follow-up evidence',corrected]] as const)fireEvent.change(draftForm().getByRole('combobox',{name}),{target:{value:evidenceKey(item.fact)}});
 step('Use guided record for validation');step('Validate and review draft');await screen.findByRole('button',{name:'Confirm append to local database'});step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Compare notes'})).toBeEnabled());
 const note=first.entry.save.mock.calls[1][0].fact;expect(note.supersedes).toBeUndefined();expect(JSON.stringify(originalNote)).toBe(beforeNote);step('Compare notes');fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(originalNote.fact)}});fireEvent.change(screen.getByRole('combobox',{name:'Note B'}),{target:{value:evidenceKey(note)}});
 const row=screen.getAllByRole('row').find(r=>r.textContent?.includes('Follow-up ABG / evidence reference'))!;const cells=within(row).getAllByRole('cell');expect(cells[0]).toHaveTextContent('Revision: 1');expect(cells[1]).toHaveTextContent('Revision: '+corrected.fact.revision);
 step('Add Note B to handover');step('Save handover locally');await screen.findByText(/Saved locally in this browser: 2 selection/);
 const state=structuredClone(first.getState());expect(first.entry.save).toHaveBeenCalledTimes(2);expect(first.client.circulatoryPrepare).not.toHaveBeenCalled();expect(first.client.circulatoryExecute).not.toHaveBeenCalled();first.view.unmount();
 const restored=setup(s=>Object.assign(s,state));await ready();fireEvent.click(await screen.findByRole('button',{name:'Open saved handover'}));const handover=screen.getByRole('region',{name:'Read-only handover'});expect(handover).toHaveTextContent('Restored saved handover: 2 selection');expect(handover).toHaveTextContent('4.5500');expect(handover).toHaveTextContent(note.id);expect(handover).toHaveTextContent(corrected.fact.revision);expect(restored.entry.save).not.toHaveBeenCalled();expect(restored.client.circulatoryExecute).not.toHaveBeenCalled();restored.view.unmount();window.localStorage.clear();
},15000);

it('M1: repository replacement cannot rebind a selected comparison note into the new handover',async()=>{
 const {getState,setState,client,entry}=setup(s=>{
  const baseline=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!,followup=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!,intervention=s.assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
  const fact=structuredClone(buildGuided('reassessment',{baseline:evidenceKey(baseline.fact),intervention:evidenceKey(intervention.fact),followup:evidenceKey(followup.fact),question:'Review',findings:'Original repository note',possibilities:'Unconfirmed',uncertainty:'Unknown'},'Synthetic',s.assembly.snapshot.items,'same-note','2026-10-18T12:00:00Z'));s.assembly.snapshot.items.push({...followup,fact});
 });
 await ready();const original=getState().assembly.snapshot.items.find(i=>i.fact.id==='same-note')!;step('Compare notes');fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(original.fact)}});step('Patient and evidence');
 const next=structuredClone(getState());next.state_context+='-new-repository';next.assembly.request.scope.repository_cutoff.repository_id='replacement-repository';const replacement=next.assembly.snapshot.items.find(i=>i.fact.id==='same-note')!;replacement.fact.description={raw_display:'Different note, same tuple'};replacement.expected_digest='b'.repeat(64);setState(next);
 step('Refresh recorded state');await waitFor(()=>expect(client.circulatoryState).toHaveBeenCalledTimes(2));await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh recorded state'})).toBeEnabled());step('Compare notes');
 expect(screen.getByRole('combobox',{name:'Note A'})).toHaveValue('');expect(screen.queryByRole('button',{name:'Add Note A to handover'})).not.toBeInTheDocument();step('Handover');expect(screen.getByRole('region',{name:'Read-only handover'})).not.toHaveTextContent('Different note, same tuple');
 step('Compare notes');fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(replacement.fact)}});step('Add Note A to handover');expect(screen.getByRole('region',{name:'Read-only handover'})).toHaveTextContent('Different note, same tuple');expect(entry.save).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
},15000);
it('M1: retains repository A saved confirmation but withholds continuation against B with identical reference and digest',async()=>{
 const {entry,client,getState}=setup();await correction();
 client.circulatoryState.mockImplementationOnce(async()=>{const next=structuredClone(getState());next.state_context+='-replacement';next.assembly.request.scope.repository_cutoff.repository_id='replacement-repository';return {data:next};});
 step('Confirm append to local database');await screen.findByText(/Exact revision saved and confirmed/);await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh evidence'})).toBeEnabled());
 expect(screen.getByText(/saved revision belongs to a different repository/i)).toBeInTheDocument();
 for(const name of ['Find saved record','Add saved record to handover'])expect(screen.getByRole('button',{name})).toBeDisabled();
 const saved=entry.save.mock.results[0];const confirmation=await saved.value;expect(screen.getByRole('region',{name:'Evidence draft'})).toHaveTextContent(confirmation.fact.revision);expect(screen.getByRole('region',{name:'Evidence draft'})).toHaveTextContent(confirmation.expected_digest);
 expect(entry.save).toHaveBeenCalledTimes(1);expect(client.circulatoryExecute).not.toHaveBeenCalled();expect(window.localStorage.length).toBe(0);
},15000);

it('M1: repository refresh does not remount the editor or replace an uncertain pending revision',async()=>{
 const state=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false});state.assembly.snapshot.items=state.assembly.snapshot.items.filter(i=>i.fact.id==='fs-PH-60');
 const repository=state.assembly.request.scope.repository_cutoff.repository_id;
 const entry={validate:vi.fn(async(body:Draft)=>({repository_id:body.repository_id,fact:body.fact,expected_digest:'a'.repeat(64),canonical_fact:JSON.stringify(body.fact),ingestion:null} as Evidence)),save:vi.fn(async(_body:Draft)=>{throw Error('lost_delivery');}),lookup:vi.fn(async(_body:Draft)=>({status:'absent'}))};
 const client={} as CirculatoryClient,refresh=vi.fn(async()=>{}),shared={state,loading:false,error:'',refresh};
 const view=render(<EvidenceEntryWorkspace client={client} entry={entry as unknown as EvidenceEntryClient} config={config} shared={shared}/>);
 fireEvent.click(screen.getByRole('region',{name:'Recorded evidence'}).querySelector('.entry-list button')!);
 fireEvent.change(screen.getByRole('textbox',{name:'Actor name'}),{target:{value:'Synthetic reviewer'}});fireEvent.change(screen.getByRole('textbox',{name:'Reason for correction or withdrawal'}),{target:{value:'Transcription correction'}});fireEvent.change(screen.getByRole('textbox',{name:'Recorded numeric value (raw unit preserved)'}),{target:{value:'7.3600'}});
 step('Validate and review draft');await screen.findByRole('button',{name:'Confirm append to local database'});step('Confirm append to local database');await screen.findByRole('button',{name:'Check exact saved revision'});
 const pending=entry.save.mock.calls[0][0],editor=screen.getByRole('region',{name:'Evidence draft'});const next=structuredClone(state);next.assembly.request.scope.repository_cutoff.repository_id='replacement-repository';next.state_context+='-replacement';
 view.rerender(<EvidenceEntryWorkspace client={client} entry={entry as unknown as EvidenceEntryClient} config={config} shared={{...shared,state:next}}/>);
 expect(screen.getByRole('region',{name:'Evidence draft'})).toBe(editor);expect(editor).toHaveTextContent(pending.fact.revision);expect(screen.queryByRole('button',{name:'Discard unsaved entry'})).not.toBeInTheDocument();
 step('Check exact saved revision');await screen.findByRole('button',{name:'Explicitly retry the same revision'});expect(entry.lookup).toHaveBeenCalledExactlyOnceWith(pending);expect(pending.repository_id).toBe(repository);expect(entry.save).toHaveBeenCalledTimes(1);
},15000);
