// @vitest-environment-options {"url":"http://127.0.0.1:5238/"}
import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import renalFixture from './fixtures/renalFluid.json';
import rf2Fixture from './fixtures/rf2-api.json';
import type {RenalFluidState} from '../src/api/renalFluidTypes';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {RF2Client,type Catalog} from '../src/api/rf2Client';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {RenalBedsideReview} from '../src/renal/RenalBedsideReview';
import {newRenalDraft,renalBedsideModel,validateRenalReview} from '../src/renal/renalBedsideModel';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Existing evidence viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Existing evidence editor</p>}));
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));
afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();window.history.replaceState(null,'','/');localStorage.clear();});
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b',hosted:true};
const fresh=()=>structuredClone(renalFixture) as unknown as RenalFluidState;
const client=()=>new RenalFluidClient('http://127.0.0.1:5238',config.patient,config.encounter);
function props(state=fresh()){return {state,requested:config,loading:false,onRefresh:vi.fn().mockResolvedValue(undefined),client:client()};}
function fill(){for(const [label,value] of [['Renal next step','collection'],['Renal reviewer','Renal tester'],['Renal rationale','Check the documented collection gap'],['Renal next review plan','After catheter and collection review']])fireEvent.change(screen.getByLabelText(label),{target:{value}});}
function recordReview(){fireEvent.click(screen.getByRole('button',{name:'Record renal session review'}));}
const decodeCatalog=()=>new RF2Client(vi.fn().mockResolvedValue(new Response(JSON.stringify(structuredClone(rf2Fixture.catalog))))).catalog(config.start,config.end);

it('preserves original decimal/time strings and distinguishes context from treatment',()=>{
 const model=renalBedsideModel(fresh(),config);expect(model.valid).toBe(true);expect(model.creatinine.some(s=>s.value==='1.1000 mg/dL')).toBe(true);expect(model.creatinine.some(s=>s.value==='150.0 umol/L')).toBe(true);expect(model.sources.some(s=>s.inclusion==='unplaced')).toBe(true);expect(model.urine.some(s=>s.value.startsWith('0 '))).toBe(true);expect(model.support.every(s=>s.limitations.some(t=>t.includes('does not establish')))).toBe(true);
});
it('keeps the same renal evidence identity across request-token and capture-time changes',()=>{
 const state=fresh(),before=renalBedsideModel(state,config).signature,captured='2026-10-08T10:01:00Z';
 state.state_context='rotated-signed-request-token';state.context.scope.repository_cutoff.captured_at=captured;state.circulatory.assembly.request.scope.repository_cutoff.captured_at=captured;state.laboratory.scope.repository_cutoff.captured_at=captured;
 state.context.circulatory_digest='rotated-circulatory-assembly-digest';state.context.observations_digest='rotated-observations-assembly-digest';state.circulatory.assembly_digest='rotated-circulatory-assembly-digest';
 expect(renalBedsideModel(state,config).signature).toBe(before);
});
it('changes renal evidence identity when the immutable repository watermark changes',()=>{
 const state=fresh(),before=renalBedsideModel(state,config).signature;state.context.scope.repository_cutoff.fact_watermark++;
 state.circulatory.assembly.request.scope.repository_cutoff.fact_watermark++;state.laboratory.scope.repository_cutoff.fact_watermark++;
 expect(renalBedsideModel(state,config).signature).not.toBe(before);
});
it.each(['patient','encounter','window','gate','repository','cutoff','duplicate','lab_scope','context_digest'] as const)('withholds the entire renal projection for %s mismatch',kind=>{
 const s=fresh();if(kind==='patient')s.laboratory.observations[0].fact.binding.target.patient_id='other';
 if(kind==='encounter')s.circulatory.assembly.request.scope.encounter_id='other';
 if(kind==='window')s.context.scope.review_end='2026-10-08T10:00:00.0000001Z';
 if(kind==='gate')Object.assign(s,{execution_enabled:true});
 if(kind==='repository')s.laboratory.observations[0].ingestion.repository_id='other';
 if(kind==='cutoff')s.laboratory.observations[0].ingestion.ingestion_sequence=s.context.scope.repository_cutoff.fact_watermark+1;
 if(kind==='duplicate')s.laboratory.observations.push(s.laboratory.observations[0]);
 if(kind==='lab_scope')s.laboratory.scope.review_start='2026-10-08T07:00:00Z';
 if(kind==='context_digest')s.context.circulatory_digest='wrong';
 expect(renalBedsideModel(s,config).sources).toEqual([]);expect(renalBedsideModel(s,config).valid).toBe(false);
});
it('retains unknown result and unresolved units without arithmetic or a default baseline',()=>{
 const m=renalBedsideModel(fresh(),config);expect(m.sources.some(s=>s.value.startsWith('missing'))).toBe(true);expect(m.creatinine.find(s=>s.value==='150.0 umol/L')?.limitations).toContain('Unit mapping: unresolved');expect(Object.keys(m)).not.toContain('akiStage');expect(Object.keys(m)).not.toContain('urineRate');
});
it('does not promote contextual sources or a missing interval to complete urine coverage',()=>{
 const m=renalBedsideModel(fresh(),config);expect(m.windowSources.every(s=>s.inclusion==='in_window'&&s.status==='recorded')).toBe(true);expect(m.urine.every(s=>s.limitations.some(x=>x.includes('completeness')))).toBe(true);expect(m.weights.every(s=>s.limitations.some(x=>x.includes('Not automatically')))).toBe(true);
});
it('reuses the decoded RF2 catalog without duplicating its original base sources',async()=>{
 const c=await decodeCatalog(),m=renalBedsideModel(c.combined,config,c);expect(m.valid).toBe(true);expect(new Set(m.sources.map(s=>s.key)).size).toBe(m.sources.length);expect(m.sources.every(s=>s.entry)).toBe(true);expect(m.sources.some(s=>s.group==='urine')).toBe(true);
});
it.each(['duplicate','foreign','digest','snapshot','sequence'] as const)('rejects RF2 %s inconsistency before presentation',async kind=>{
 const c=await decodeCatalog();if(kind==='duplicate')c.items.push(c.items[0]);if(kind==='foreign')c.items[0].fact.binding.target.patient_id='other';if(kind==='digest')c.items[0].digest='wrong';if(kind==='snapshot')c.combined.execution_enabled=true as false;if(kind==='sequence')c.items[0].ingestion.ingestion_sequence=0;
 expect(renalBedsideModel(c.combined,config,c).valid).toBe(false);
});
it('shows only four bedside questions and clear inactive clinical capability labels',()=>{
 render(<RenalBedsideReview {...props()}/>);const cards=screen.getByRole('region',{name:'Four renal bedside questions'});expect(within(cards).getAllByRole('button')).toHaveLength(4);expect(cards).toHaveTextContent('Baseline: not selected');expect(cards).toHaveTextContent('AKI stage: not calculated');expect(cards).toHaveTextContent('Prescription / delivered dose unavailable');expect(screen.getByText('Effluent ≠ patient removal')).toBeInTheDocument();
});
it('saves a manual review without invoking a transport write and keeps the note copy immutable',async()=>{
 const p=props(),send=vi.fn();vi.stubGlobal('fetch',send);render(<RenalBedsideReview {...p}/>);fill();recordReview();const notes=await screen.findByRole('region',{name:'Renal session review records'});expect(notes).toHaveTextContent('Check the documented collection gap');expect(notes).toHaveTextContent('original evidence pins');fireEvent.change(screen.getByLabelText('Renal rationale'),{target:{value:'Different draft text'}});expect(notes).not.toHaveTextContent('Different draft text');expect(send).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:/^(start dialysis|titrate|prescribe)$/i})).not.toBeInTheDocument();
});
it('rechecks the latest evidence after a renal review save waits for its Web Lock',async()=>{
 let release!:()=>void;const waiting=new Promise<void>(resolve=>{release=resolve;});
 vi.stubGlobal('navigator',{locks:{request:async(_name:string,callback:()=>unknown)=>{await waiting;return callback();}}});
 const p=props(),r=render(<RenalBedsideReview {...p}/>);fill();recordReview();
 expect(await screen.findByRole('button',{name:'Saving…'})).toBeDisabled();
 const changed=fresh(),watermark=changed.context.scope.repository_cutoff.fact_watermark+1;
 changed.state_context+='changed';changed.context.scope.repository_cutoff.fact_watermark=watermark;
 changed.circulatory.assembly.request.scope.repository_cutoff.fact_watermark=watermark;changed.laboratory.scope.repository_cutoff.fact_watermark=watermark;
 r.rerender(<RenalBedsideReview {...p} state={changed}/>);
 await act(async()=>{release();await Promise.resolve();});
 expect(await screen.findByRole('alert')).toHaveTextContent(/Evidence changed before the review could be saved/i);
 expect(screen.queryByRole('region',{name:'Renal session review records'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('Renal rationale')).toHaveValue('Check the documented collection gap');
});
it('retains draft text after a changed snapshot and blocks recording until explicit discard',()=>{
 const p=props(),r=render(<RenalBedsideReview {...p}/>);fill();const s=fresh(),watermark=s.context.scope.repository_cutoff.fact_watermark+1;s.state_context+='changed';s.context.scope.repository_cutoff.fact_watermark=watermark;s.circulatory.assembly.request.scope.repository_cutoff.fact_watermark=watermark;s.laboratory.scope.repository_cutoff.fact_watermark=watermark;r.rerender(<RenalBedsideReview {...p} state={s}/>);recordReview();expect(screen.getByRole('alert')).toHaveTextContent('Evidence changed');expect(screen.getByLabelText('Renal rationale')).toHaveValue('Check the documented collection gap');expect(screen.queryByRole('region',{name:'Renal session review records'})).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Discard stale renal draft'}));expect(screen.getByLabelText('Renal rationale')).toHaveValue('');
});
it('blocks new reviews and source history after retrieval failure or a pending source write',async()=>{
 const p=props(),r=render(<RenalBedsideReview {...p}/>);fill();recordReview();await screen.findByRole('region',{name:'Renal session review records'});r.rerender(<RenalBedsideReview {...p} error="failed"/>);expect(screen.getByRole('button',{name:'Record renal session review'})).toBeDisabled();expect(screen.getByRole('region',{name:'Renal session review records'})).toHaveTextContent('Historical renal session review');r.rerender(<RenalBedsideReview {...p} guarded/>);expect(screen.getByRole('button',{name:'Refresh renal evidence'})).toBeDisabled();expect(screen.getByRole('button',{name:'Record renal session review'})).toBeDisabled();
});
it('does not leak original values when scope is invalid',()=>{
 const p=props();p.state.laboratory.observations[0].fact.binding.target.patient_id='other';render(<RenalBedsideReview {...p}/>);expect(screen.queryByText(/1.10 mg\/dL/)).not.toBeInTheDocument();expect(screen.getByRole('alert')).toHaveTextContent('could not be confirmed');
});
it('requests RF1 history for the exact selected original lab and context',async()=>{
 const p=props(),lab=p.state.laboratory.observations[0],history=vi.spyOn(p.client,'renalHistory').mockResolvedValue({data:{context:p.state.context,reference:{kind:lab.fact.kind,id:lab.fact.id,version:lab.fact.revision},revisions:[lab]}} as Awaited<ReturnType<RenalFluidClient['renalHistory']>>);render(<RenalBedsideReview {...p}/>);
 const drawer=screen.getByRole('complementary',{name:'Renal evidence drawer'});fireEvent.click(within(drawer).getByRole('button',{name:/1.10 mg\/dL/}));fireEvent.click(screen.getByRole('button',{name:'View renal revision history'}));await screen.findByRole('region',{name:'Exact renal revision history'});expect(history).toHaveBeenCalledWith(p.state,lab);
});
it('discards late history when another exact source is selected',async()=>{
 const p=props();let resolve!:(value:Awaited<ReturnType<RenalFluidClient['renalHistory']>>)=>void;
 vi.spyOn(p.client,'renalHistory').mockImplementation(()=>new Promise(done=>{resolve=done;}));render(<RenalBedsideReview {...p}/>);const drawer=screen.getByRole('complementary',{name:'Renal evidence drawer'});fireEvent.click(within(drawer).getByRole('button',{name:/1.10 mg\/dL/}));fireEvent.click(screen.getByRole('button',{name:'View renal revision history'}));fireEvent.click(screen.getByRole('button',{name:'← Back to renal evidence'}));fireEvent.click(within(drawer).getByRole('button',{name:/2.00 mg\/dL/}));await act(async()=>{resolve({data:{old:'Late original history'}} as unknown as Awaited<ReturnType<RenalFluidClient['renalHistory']>>);});expect(screen.queryByText(/Late original history/)).not.toBeInTheDocument();expect(screen.getByRole('region',{name:'Exact renal source'})).toHaveTextContent('2.00 mg/dL');
});
it('reports history failure without replacing the selected revision',async()=>{
 const p=props();vi.spyOn(p.client,'renalHistory').mockRejectedValue(Error('missing'));render(<RenalBedsideReview {...p}/>);fireEvent.click(within(screen.getByRole('complementary',{name:'Renal evidence drawer'})).getByRole('button',{name:/1.10 mg\/dL/}));fireEvent.click(screen.getByRole('button',{name:'View renal revision history'}));expect(await screen.findByRole('alert')).toHaveTextContent('No different version was substituted');expect(screen.getByRole('region',{name:'Exact renal source'})).toHaveTextContent('1.10 mg/dL');
});
it('uses RF2 source ownership for history when the source came through the shared catalog',async()=>{
 const c=await decodeCatalog(),transport={history:vi.fn().mockResolvedValue([])};render(<RenalBedsideReview {...props(c.combined)} catalog={c} historyTransport={transport}/>);const drawer=screen.getByRole('complementary',{name:'Renal evidence drawer'});fireEvent.click(within(drawer).getByRole('button',{name:/1.20 mg\/dL|2.00 mg\/dL/}));fireEvent.click(screen.getByRole('button',{name:'View renal revision history'}));await screen.findByRole('region',{name:'Exact renal revision history'});expect(transport.history).toHaveBeenCalledTimes(1);expect(c.items).toContain(transport.history.mock.calls[0][0]);
});
it('supports closing/reopening the source drawer and searching by exact source id',()=>{
 render(<RenalBedsideReview {...props()}/>);fireEvent.change(screen.getByLabelText('Find a renal source'),{target:{value:'rf1-creatinine-unlike-unit'}});expect(within(screen.getByRole('complementary',{name:'Renal evidence drawer'})).getAllByRole('button').some(b=>b.textContent?.includes('1.70 mg/dL'))).toBe(true);fireEvent.keyDown(screen.getByRole('complementary',{name:'Renal evidence drawer'}),{key:'Escape'});expect(screen.queryByRole('complementary',{name:'Renal evidence drawer'})).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Open renal evidence ↗'}));expect(screen.getByLabelText('Find a renal source')).toHaveValue('');
});
it('restores the saved review on a fresh page session',async()=>{
 const p=props(),r=render(<RenalBedsideReview {...p}/>);fill();recordReview();await screen.findByRole('region',{name:'Renal session review records'});r.unmount();render(<RenalBedsideReview {...p}/>);expect(await screen.findByRole('region',{name:'Renal session review records'})).toHaveTextContent('Check the documented collection gap');expect(screen.getByText(/Exact snapshot and evidence pins are saved locally/)).toBeInTheDocument();
});
it('rejects invalid review options and field limits',()=>{
 const d={...newRenalDraft(),action:'collection',reviewer:'Reviewer',rationale:'Reason',nextReview:'Plan'};expect(validateRenalReview(d,true,true)).toBe('');expect(validateRenalReview({...d,cause:'auto_diagnosed'},true,true)).not.toBe('');expect(validateRenalReview({...d,rationale:'x'.repeat(2001)},true,true)).not.toBe('');expect(validateRenalReview(d,false,true)).toContain('not confirmed');
});
it('uses one shared catalog across overview, M7 and M8 and retains renal session notes on view changes',async()=>{
 vi.stubEnv('VITE_SYNTHETIC_RF2','true');vi.stubEnv('VITE_SYNTHETIC_AUTHORING','true');const send=vi.fn().mockResolvedValue(new Response(JSON.stringify(structuredClone(rf2Fixture.catalog))));vi.stubGlobal('fetch',send);render(<PatientWorkspace client={client()} entry={new EvidenceEntryClient()} config={config}/>);await screen.findByRole('heading',{name:'Creatinine'});fireEvent.click(screen.getByRole('button',{name:'Renal system'}));await screen.findByRole('heading',{name:'Renal system'});fill();recordReview();await screen.findByRole('region',{name:'Renal session review records'});fireEvent.click(screen.getByRole('button',{name:'Cardiovascular system'}));expect(screen.getByRole('heading',{name:'Cardiovascular system'})).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Renal system'}));expect(screen.getByRole('region',{name:'Renal session review records'})).toHaveTextContent('Check the documented collection gap');expect(send).toHaveBeenCalledTimes(2);expect(String(send.mock.calls[1][0])).toContain('2026-10-09');
});
