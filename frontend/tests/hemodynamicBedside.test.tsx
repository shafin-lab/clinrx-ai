import {act,fireEvent,render,screen,within} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import fixtures from './fixtures/circulatory.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import type {CirculatoryState,CirculatoryItem,CirculatoryHistory} from '../src/api/circulatoryTypes';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {bedsideModel,chronologicalItems,observationSummary,validateReview,emptyReview,sourceLimitations} from '../src/hemodynamics/bedsideModel';
import {M7BedsideReview} from '../src/hemodynamics/M7BedsideReview';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const original=()=>({...decodeCirculatoryState(structuredClone(fixtures.state),{patient_id:requested.patient,encounter_id:requested.encounter}),execution_enabled:false});
const mockClient=()=>({circulatoryHistory:vi.fn().mockResolvedValue({data:fixtures.history}),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn(),circulatoryReconcile:vi.fn()});
function mount(state=original()){
 const client=mockClient(),onRefresh=vi.fn().mockResolvedValue(undefined);
 const props={state,requested,loading:false,retrievalError:'',onRefresh,client:client as unknown as CirculatoryClient};
 return {...render(<M7BedsideReview {...props}/>),props,client,onRefresh};
}
const fill=()=>{
 fireEvent.change(screen.getByLabelText('Next step'),{target:{value:'perfusion'}});
 fireEvent.change(screen.getByLabelText('Reviewer'),{target:{value:'Synthetic reviewer'}});
 fireEvent.change(screen.getByLabelText('Rationale'),{target:{value:'Repeat bedside assessment and confirm source quality.'}});
 fireEvent.change(screen.getByLabelText('Next review plan'),{target:{value:'After repeat pressure and clinical perfusion assessment'}});
};
describe('M7 bedside evidence safety projection',()=>{
 it('preserves all 15 families while excluding contextual/unplaced observations from bedside headline groups',()=>{
  const state=original(),before=JSON.stringify(state),model=bedsideModel(state,requested);
  expect(model.valid).toBe(true);expect(new Set(model.items.map(i=>i.fact.kind)).size).toBe(15);
  expect(model.windowItems.some(i=>i.fact.id==='m7-UNPLACED')).toBe(false);
  expect(model.items.some(i=>i.fact.id==='m7-UNPLACED')).toBe(true);
  expect(model.maps).toHaveLength(1);expect(JSON.stringify(state)).toBe(before);
 });
 it('keeps the same evidence identity when only the signed request token and capture time change',()=>{
  const state=original(),before=bedsideModel(state,requested).signature;
  state.state_context='rotated-signed-request-token';state.assembly.request.scope.repository_cutoff.captured_at='2026-10-08T10:01:00Z';
  state.assembly_digest='rotated-request-assembly-digest';
  expect(bedsideModel(state,requested).signature).toBe(before);
 });
 it('changes evidence identity when a source digest changes',()=>{
  const state=original(),before=bedsideModel(state,requested).signature;
  state.assembly.request.scope.repository_cutoff.fact_watermark++;
  expect(bedsideModel(state,requested).signature).not.toBe(before);
 });
 it.each(['foreign','duplicate','repository','gate','window'])('withholds the patient projection for %s mismatch',part=>{
  const state=original();
  if(part==='foreign')state.assembly.snapshot.items[0].fact.binding.target.patient_id='foreign';
  if(part==='duplicate')state.assembly.snapshot.items.push(state.assembly.snapshot.items[0]);
  if(part==='repository')state.assembly.snapshot.items[0].ingestion.repository_id='foreign';
  if(part==='gate')state.execution_enabled=true;
  if(part==='window')state.assembly.request.scope.review_end='2026-10-08T11:00:00Z';
  const model=bedsideModel(state,requested);expect(model.valid).toBe(false);expect(model.items).toEqual([]);
 });
 it('does not collapse distinct fractional review boundaries',()=>{
  const state=original();state.assembly.request.scope.review_start='2026-10-08T08:00:00.1234561Z';
  expect(bedsideModel(state,{...requested,start:'2026-10-08T08:00:00.1234569Z'}).valid).toBe(false);
  expect(bedsideModel(state,{...requested,start:'2026-10-08T13:30:00.12345610+05:30'}).valid).toBe(true);
 });
 it('does not pick the most favorable or latest reading from multiple sources',()=>{
  const state=original(),item=structuredClone(state.assembly.snapshot.items.find(i=>i.fact.id==='m7-P')!);item.fact.id='another-pressure';state.assembly.snapshot.items.push(item);
  const summary=observationSummary(bedsideModel(state,requested).maps);expect(summary.headline).toBe('2');expect(summary.unit).toBe('observations');expect(summary.item).toBeUndefined();
 });
 it('does not present withdrawn numeric values as usable headline measurements',()=>{
  const item=structuredClone(original().assembly.snapshot.items.find(i=>i.fact.id==='m7-P')!);item.fact.record_status='withdrawn';
  expect(observationSummary([item]).headline).toBe('Source withdrawn');expect(sourceLimitations(item)).toContain('Source status: withdrawn');
 });
 it('retains exact decimals and unknown quality rather than inventing normality',()=>{
  const item=structuredClone(original().assembly.snapshot.items.find(i=>i.fact.id==='m7-L')!);
  expect(observationSummary([item]).headline).toBe('2.000');
  (item.fact.acquisition as {quality:unknown}).quality={status:'unknown'};expect(sourceLimitations(item)).toContain('Source quality: unknown');
  expect(observationSummary([]).headline).toBe('Not recorded');
 });
 it('requires a complete deliberate session review and never supplies a default MAP target',()=>{
  expect(emptyReview().targetLow).toBe('');expect(validateReview(emptyReview(),true,true)).toMatch(/Choose/);
  const draft={...emptyReview(),action:'fluid',reviewer:'Reviewer',rationale:'Review need and tolerance',nextReview:'After assessment'};
  expect(validateReview(draft,true,true)).toBe('');expect(validateReview(draft,false,true)).toMatch(/not confirmed/);expect(validateReview(draft,true,false)).toMatch(/Evidence changed/);
  expect(validateReview({...draft,targetLow:'75',targetHigh:'65'},true,true)).toMatch(/both limits/);
 });
});
describe('M7 bedside clinician workflow',()=>{
 it('renders four questions, original source data and a clinical-advice-disabled boundary',()=>{
  const {client}=mount();
  expect(screen.getByRole('heading',{name:'Patient hemodynamic review'})).toBeInTheDocument();
  expect(within(screen.getByRole('region',{name:'Four bedside questions'})).getAllByRole('button')).toHaveLength(4);
  expect(screen.getByText('Chart target not supplied')).toBeInTheDocument();expect(screen.getByText('Not clinically assessed')).toBeInTheDocument();
  expect(screen.getByText(/Clinical profiles inactive/)).toBeInTheDocument();
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
 });
 it('does not show source or issue counts as confirmed after retrieval fails',()=>{
  const state=original(),client=mockClient();
  render(<M7BedsideReview state={state} requested={requested} loading={false} retrievalError="retrieval_failed" onRefresh={vi.fn()} client={client as unknown as CirculatoryClient}/>);
  const strip=screen.getByRole('group',{name:'Evidence status'});
  expect(within(strip).getAllByText('Not confirmed')).toHaveLength(2);
  expect(within(strip).queryByText('0')).not.toBeInTheDocument();
  expect(within(strip).getAllByRole('button').slice(0,2).every(button=>button.hasAttribute('disabled'))).toBe(true);
  expect(screen.getByText(/Intervention records not confirmed/)).toBeInTheDocument();
  expect(screen.getAllByText(/Refresh evidence to confirm this recorded view/).length).toBeGreaterThan(0);
 });
 it('opens exact source and fetches its bounded history without preparing or executing a review',async()=>{
  const {client}=mount();
  const sources=screen.getByRole('complementary',{name:'Hemodynamic evidence drawer'});
  fireEvent.click(within(sources).getByRole('button',{name:/Mean arterial pressure/}));
  expect(screen.getByRole('region',{name:'Exact source details'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'View revision history'}));
  await screen.findByRole('region',{name:'Exact revision history'});
  expect(client.circulatoryHistory).toHaveBeenCalledWith(expect.any(String),{kind:'circulatory_pressure',id:'m7-P',version:'1'});
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
 });
 it('keeps source orders/preparation and initiation labels distinct from a running infusion',()=>{
  mount();fireEvent.click(screen.getByRole('button',{name:'Infusions'}));
  expect(screen.getByText(/A start event does not establish a currently running infusion/)).toBeInTheDocument();
  const drawer=screen.getByRole('complementary',{name:'Hemodynamic evidence drawer'});
  fireEvent.click(within(drawer).getByRole('button',{name:/Vasoactive event/}));expect(screen.getByRole('heading',{name:'Documented initiation'})).toBeInTheDocument();
  expect(screen.queryByText('Infusion running')).not.toBeInTheDocument();
 });
 it('saves a pinned review without changing source facts or invoking any write API',async()=>{
  const state=original(),before=JSON.stringify(state),{client}=mount(state);fill();fireEvent.click(screen.getByRole('button',{name:'Record session review'}));
  const notes=await screen.findByRole('region',{name:'Session review records'});expect(within(notes).getByText('Reassess perfusion')).toBeInTheDocument();
  expect(within(notes).getByText(/exact evidence pins/)).toBeInTheDocument();expect(JSON.stringify(state)).toBe(before);
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
 });
 it('rechecks the latest evidence after a review save waits for its Web Lock',async()=>{
  let release!:()=>void;const waiting=new Promise<void>(resolve=>{release=resolve;});
  vi.stubGlobal('navigator',{locks:{request:async(_name:string,callback:()=>unknown)=>{await waiting;return callback();}}});
  const x=mount();fill();fireEvent.click(screen.getByRole('button',{name:'Record session review'}));
  expect(await screen.findByRole('button',{name:'Saving…'})).toBeDisabled();
  const changed=original();changed.assembly.request.scope.repository_cutoff.fact_watermark++;
  x.rerender(<M7BedsideReview {...x.props} state={changed}/>);
  await act(async()=>{release();await Promise.resolve();});
  expect(await screen.findByRole('alert')).toHaveTextContent(/Evidence changed before the review could be saved/i);
  expect(screen.queryByRole('region',{name:'Session review records'})).not.toBeInTheDocument();
  expect(screen.getByLabelText('Rationale')).toHaveValue('Repeat bedside assessment and confirm source quality.');
 });
 it('blocks a stale draft after new evidence, without silently rebasing the clinician assessment',()=>{
  const x=mount();fill();const state=original();state.assembly.request.scope.repository_cutoff.fact_watermark++;
  x.rerender(<M7BedsideReview {...x.props} state={state}/>);
  expect(screen.getByText(/Evidence changed while this draft was open/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Record session review'}));expect(screen.queryByRole('region',{name:'Session review records'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Discard stale draft and review refreshed evidence'}));expect(screen.getByLabelText('Rationale')).toHaveValue('');
 });
 it('retains historical saved reviews while blocking a new review when retrieval fails',async()=>{
  const x=mount();fill();fireEvent.click(screen.getByRole('button',{name:'Record session review'}));await screen.findByRole('region',{name:'Session review records'});
  x.rerender(<M7BedsideReview {...x.props} state={undefined} retrievalError="unavailable"/>);
  expect(screen.getByRole('button',{name:'Record session review'})).toBeDisabled();
  expect(screen.getByText(/Historical session review/)).toBeInTheDocument();expect(screen.queryByText('Tied to this evidence snapshot')).not.toBeInTheDocument();
 });
 it('discards late history when a different exact source is selected',async()=>{
  const x=mount();let resolve!:(v:{data:CirculatoryHistory})=>void;
  x.client.circulatoryHistory.mockImplementation(()=>new Promise(done=>{resolve=done;}));
  const drawer=screen.getByRole('complementary',{name:'Hemodynamic evidence drawer'});
  fireEvent.click(within(drawer).getByRole('button',{name:/Mean arterial pressure/}));fireEvent.click(screen.getByRole('button',{name:'View revision history'}));
  fireEvent.click(screen.getByRole('button',{name:'Perfusion'}));
  await act(async()=>{resolve({data:fixtures.history as unknown as CirculatoryHistory});await Promise.resolve();});
  expect(screen.queryByRole('region',{name:'Exact revision history'})).not.toBeInTheDocument();
 });
 it('keeps the full source families searchable and makes the drawer close/reopen operable',()=>{
  mount();fireEvent.click(screen.getByRole('button',{name:'All sources'}));fireEvent.change(screen.getByLabelText('Find a source'),{target:{value:'m7-UNPLACED'}});
  expect(screen.getByText(/1 recorded sources/)).toBeInTheDocument();
  expect(within(screen.getByRole('complementary')).getByText('unplaced')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'× Close'}));expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Open evidence ↗'}));expect(screen.getByRole('complementary')).toBeInTheDocument();
 });
});

function withVitalSigns(){
 const state=original(),items=state.assembly.snapshot.items;
 function add(kind:string,template:string,id:string,concept:string,amount:string,unit:string){
  const item=structuredClone(items.find(i=>i.fact.kind===template)!);item.fact.kind=kind;item.fact.id=id;item.fact.concept=concept;item.fact.result={result_type:'numeric',quantity:{value:amount,unit:{raw:unit}},comparator:'='};item.inclusion='in_window';items.push(item);return item;
 }
 add('circulatory_ecg','circulatory_ecg','vital-HR','heart_rate','88.00','/min');
 add('circulatory_pressure','circulatory_pressure','vital-SBP','systemic_systolic','104.00','mmHg');
 add('circulatory_pressure','circulatory_pressure','vital-DBP','systemic_diastolic','58.0','mmHg');
 add('circulatory_oxygen','circulatory_oxygen','vital-SPO2','spo2','97.0','%');
 add('circulatory_oxygen','circulatory_oxygen','vital-SAO2','sao2','95.00','%');
 add('circulatory_oxygen','circulatory_oxygen','vital-RR','respiratory_rate','22.00','/min');
 return state;
}
describe('M7 recorded vital signs',()=>{
 it('shows compact vitals with only SpO2 in the saturation tile and exact source navigation',()=>{
  const x=mount(withVitalSigns()),vitals=screen.getByRole('region',{name:'Recorded vital signs'});
  for(const amount of ['88','97','22'])expect(within(vitals).getByText(amount,{exact:true})).toBeInTheDocument();
  expect(within(vitals).getByRole('button',{name:/Blood pressure/})).toHaveTextContent('104/58 (65) mmHg');
  expect(within(vitals).queryByRole('article',{name:'Systolic blood pressure'})).not.toBeInTheDocument();
  expect(within(vitals).getByText('SpO₂')).toBeInTheDocument();expect(within(vitals).queryByText('SaO₂')).not.toBeInTheDocument();
  fireEvent.click(within(vitals).getByRole('button',{name:/Respiratory rate/}));expect(screen.getByRole('region',{name:'Exact source details'})).toHaveTextContent('vital-RR / 1');
  expect(x.client.circulatoryExecute).not.toHaveBeenCalled();
 });
 it('keeps missing SpO2 and respiratory rate explicit without substituting other oxygen samples or calculating pressure',()=>{
  mount();const vitals=screen.getByRole('region',{name:'Recorded vital signs'});
  for(const name of [/SpO₂/,/Respiratory rate/])expect(within(vitals).getByRole('button',{name})).toBeDisabled();
  expect(within(vitals).getByRole('button',{name:/SpO₂/})).toHaveTextContent('Not recorded');expect(within(vitals).getByRole('button',{name:/Blood pressure/})).toHaveTextContent('—/— (65) mmHg');
 });
 it('does not combine unmatched readings or select one of multiple heart rates; contextual and unplaced readings stay out',()=>{
  const state=withVitalSigns(),items=state.assembly.snapshot.items,heart=items.find(i=>i.fact.id==='vital-HR')!;
  const another=structuredClone(heart);another.fact.id='vital-HR-2';items.push(another);
  items.find(i=>i.fact.id==='vital-SBP')!.inclusion='contextual';items.find(i=>i.fact.id==='vital-RR')!.inclusion='unplaced';
  const model=bedsideModel(state,requested);expect(observationSummary(model.heartRates).headline).toBe('2');expect(model.systolic).toEqual([]);expect(model.respiratoryRates).toEqual([]);expect(model.diastolic).toHaveLength(1);
  mount(state);const vitals=screen.getByRole('region',{name:'Recorded vital signs'});fireEvent.click(within(vitals).getByRole('button',{name:/Heart rate/}));expect(screen.getByLabelText('Find a source')).toHaveValue('Heart rate');expect(screen.queryByRole('region',{name:'Exact source details'})).not.toBeInTheDocument();
 });
 it('withholds vital headlines when retrieval is unconfirmed or scope is foreign',()=>{
  const x=mount(withVitalSigns());x.rerender(<M7BedsideReview {...x.props} retrievalError="unavailable"/>);const vitals=screen.getByRole('region',{name:'Recorded vital signs'});
  expect(within(vitals).queryByText(/^88.00/)).not.toBeInTheDocument();expect(within(vitals).getAllByText('Not confirmed')).toHaveLength(4);
  const state=withVitalSigns();state.assembly.request.scope.patient_id='foreign';expect(bedsideModel(state,requested).heartRates).toEqual([]);
 });
});
describe('M7 chronological presentation',()=>{
 it('orders dated readings by source timestamp and leaves undated readings last without inventing a time',()=>{
  const state=withVitalSigns(),items=state.assembly.snapshot.items;
  items.find(i=>i.fact.id==='vital-HR')!.fact.occurred={source_timestamp:'2026-10-08T08:20:00Z'};
  items.find(i=>i.fact.id==='vital-SPO2')!.fact.occurred={source_timestamp:'2026-10-08T08:10:00Z'};
  items.find(i=>i.fact.id==='vital-RR')!.fact.occurred={source_timestamp:'2026-10-08T08:30:00Z'};
  const undated=items.find(i=>i.fact.id==='vital-SBP')!;
  expect(chronologicalItems([items.find(i=>i.fact.id==='vital-HR')!,undated,items.find(i=>i.fact.id==='vital-RR')!,items.find(i=>i.fact.id==='vital-SPO2')!]).map(i=>i.fact.id))
   .toEqual(['vital-RR','vital-HR','vital-SPO2','vital-SBP']);
  expect(chronologicalItems([undated])[0]).toBe(undated);
  undated.fact.occurred={source_timestamp:'2026-10-08'};
  expect(chronologicalItems([items.find(i=>i.fact.id==='vital-HR')!,undated]).map(i=>i.fact.id)).toEqual(['vital-HR','vital-SBP']);
 });
 it('presents timestamped vital readings as separate source-linked entries',()=>{
  const state=withVitalSigns(),items=state.assembly.snapshot.items;
  items.find(i=>i.fact.id==='vital-HR')!.fact.occurred={source_timestamp:'2026-10-08T08:20:00Z'};
  items.find(i=>i.fact.id==='vital-RR')!.fact.occurred={source_timestamp:'2026-10-08T08:30:00Z'};
  items.find(i=>i.fact.id==='vital-SBP')!.fact.occurred=undefined;
  mount(state);
  const timeline=screen.getByRole('region',{name:'Recorded readings in time order'});
  const rows=within(timeline).getAllByRole('button');
  expect(rows[0]).toHaveAccessibleName(/2026-10-08T08:30:00Z.*Respiratory rate.*22/);
  expect(rows[1]).toHaveAccessibleName(/2026-10-08T08:20:00Z.*Heart rate.*88/);
  expect(within(timeline).getByRole('button',{name:/Time not established.*Systolic blood pressure.*104 mmHg/})).toBeInTheDocument();
  fireEvent.click(rows[0]);expect(screen.getByRole('region',{name:'Exact source details'})).toHaveTextContent('vital-RR / 1');
 });
 it('shows vasoactive and contextual events in source-time order with documented event labels',()=>{
  const state=original(),items=state.assembly.snapshot.items;
  items.find(i=>i.fact.id==='m7-EVENT')!.fact.occurred={source_timestamp:'2026-10-08T08:20:00Z'};
  items.find(i=>i.fact.id==='m7-V')!.fact.occurred={source_timestamp:'2026-10-08T08:30:00Z'};
  mount(state);
  const heading=screen.getByRole('heading',{name:'Vasoactive and intervention records'}),section=heading.parentElement!.nextElementSibling as HTMLElement;
  const rows=within(section).getAllByRole('button');
  expect(rows[0]).toHaveTextContent('norepinephrine');expect(rows[0]).toHaveTextContent('Documented initiation');expect(rows[0]).toHaveTextContent('2026-10-08T08:30:00Z');
  expect(rows[1]).toHaveTextContent('Position change');expect(rows[1]).toHaveTextContent('2026-10-08T08:20:00Z');
 });
});
