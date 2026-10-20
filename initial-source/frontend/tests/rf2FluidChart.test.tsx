import {afterAll,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,pin,stable,hash,type Catalog,type Evidence} from '../src/api/rf2Client';
import {RenalFluidEntryWorkspace,evidenceText,sourceContext} from '../src/demo/RenalFluidEntryWorkspace';
import {RF2FluidChart,fluidChartModel} from '../src/demo/RF2FluidChart';
import {storageKey} from '../src/demo/rf2Handover';
import styles from '../src/demo/rf2.css?raw';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));beforeEach(()=>localStorage.clear());
const load=()=>new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
function mountChart(c:Catalog,props:Partial<Parameters<typeof RF2FluidChart>[0]>={}){const inspect=vi.fn();return {inspect,...render(<RF2FluidChart catalog={c} status="current" text={evidenceText} context={e=>sourceContext(e,c)} onInspect={inspect} {...props}/>)};}
function original(c:Catalog){return c.items.find(e=>e.fact.id===fixture.urine.fact.id)!;}
async function entry(c:Catalog,id:string,category='output_urine',start:string|null='2026-10-08T08:00:00Z',end:string|null='2026-10-08T08:15:00Z'){
 const e=structuredClone(original(c));e.fact.id=id;e.terminal_reference.id=id;e.fact.record_status='recorded';
 e.metadata!.chart = {...e.metadata!.chart!,category,start,end,point:end};
 e.fact.occurred={...(e.fact.occurred as object),source_timestamp:end};
 e.fact.recorded_interval=start!==null||end!==null?{start:{source_timestamp:start},end:{source_timestamp:end}}:null;
 e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);return e;
}
function withEntries(c:Catalog,items:Evidence[]){return {...c,items};}
function props(c:Catalog,t:RF2Client){return {catalog:c,gateConfirmed:true,onGuardChange:vi.fn(),onRefresh:vi.fn(async()=>{}),onLegacyCorrect:vi.fn(),transport:t};}
function transport(c:Catalog){return {history:vi.fn(async(e:Evidence)=>[e]),resolve:vi.fn(async()=>[]),action:vi.fn()} as unknown as RF2Client;}

it('shows original decimal text/unit/interval/category without any arithmetic or new request',async()=>{
 const c=await load(),e=original(c),before=stable(c);const {inspect}=mountChart(c);
 const card=screen.getByRole('article',{name:`Urine output ${e.fact.id} / ${e.fact.revision}`});
 expect(card).toHaveTextContent('35.0000 mL');expect(card).toHaveTextContent('2026-10-08T09:30:00Z');expect(card).toHaveTextContent('Source category: output_urine');expect(card).toHaveTextContent(e.metadata!.chart!.uncertainty);
 expect(screen.getByText('Completeness unresolved')).toBeVisible();expect(screen.getByText('Calculations unavailable — source eligibility not established')).toBeVisible();expect(screen.queryByText(/included-record subtotal/i)).not.toBeInTheDocument();
 fireEvent.click(within(card).getByRole('button',{name:/Open exact source/}));expect(inspect.mock.calls[0][0]).toBe(e);expect(stable(c)).toBe(before);
});
it('retains multiple entries, explicit zero and L raw units separately with no inferred zeros',async()=>{
 const c=await load(),a=await entry(c,'source-A','input_iv'),b=await entry(c,'source-B','input_iv');a.fact.recorded_amount={value:'0.0000',unit:{raw:'mL'}};b.fact.recorded_amount={value:'1.2500',unit:{raw:'L'}};
 mountChart(withEntries(c,[a,b]));const row=screen.getByRole('row',{name:/2026-10-08T08:00:00Z/});expect(within(row).getAllByRole('article')).toHaveLength(2);expect(row).toHaveTextContent('0.0000 mL');expect(row).toHaveTextContent('1.2500 L');expect(row).not.toHaveTextContent('1250');expect(within(row).getAllByText('No recorded entry shown')).toHaveLength(3);
});
it('does not guess zero when amount is unknown or when the selected period is empty',async()=>{
 const c=await load(),e=await entry(c,'missing');e.fact.recorded_amount=null;e.metadata!.chart!.amount=null;e.metadata!.chart!.unit=null;e.metadata!.chart!.missing_reason='Not measured';
 const r=mountChart(withEntries(c,[e]));expect(screen.getByText('Not measured')).toBeVisible();r.rerender(<RF2FluidChart catalog={withEntries(c,[])} status="current" text={evidenceText} context={()=>''} onInspect={()=>{}}/>);
 expect(screen.getByText(/No individually placed source entries/)).toHaveTextContent('not a zero-volume assertion');
});
it('keeps known source summaries separate from collection hour groups',async()=>{
 const c=await load(),actual=await entry(c,'collection'),summary=await entry(c,'total','urine_total_reported');mountChart(withEntries(c,[actual,summary]));
 expect(within(screen.getByRole('region',{name:'Source-reported summaries'})).getByRole('article')).toHaveTextContent('total');expect(within(screen.getByRole('table')).getAllByRole('article')).toHaveLength(1);
});
it('keeps spanning/crossing/outside intervals separate and never uses interval end to invent a point',async()=>{
 const c=await load(),spanning=await entry(c,'spanning','output_urine','2026-10-08T08:30:00Z','2026-10-08T09:30:00Z'),crossing=await entry(c,'crossing','output_urine','2026-10-08T07:45:00Z','2026-10-08T08:15:00Z'),partial=await entry(c,'partial','output_urine',null,'2026-10-08T08:15:00Z');mountChart(withEntries(c,[spanning,crossing,partial]));
 expect(within(screen.getByRole('region',{name:'Intervals spanning hour boundaries or outside the selected period'})).getAllByRole('article')).toHaveLength(2);expect(within(screen.getByRole('region',{name:'Unplaced entries'})).getByRole('article')).toHaveTextContent('start unknown');expect(within(screen.getByRole('table')).queryByRole('article')).not.toBeInTheDocument();
});
it('distinguishes exact interval end from point end without asserting inclusion in a calculation',async()=>{
 const c=await load(),interval=await entry(c,'interval-end','output_urine','2026-10-08T09:45:00Z','2026-10-08T10:00:00Z'),point=await entry(c,'point-end','output_urine',null,null);point.metadata!.chart!.point='2026-10-08T10:00:00Z';point.fact.occurred={source_timestamp:'2026-10-08T10:00:00Z'};
 const model=fluidChartModel(withEntries(c,[interval,point]));expect(model.groups.flatMap(([,es])=>es).map(e=>e.fact.id)).toEqual(['interval-end']);expect(model.separate.map(e=>e.fact.id)).toEqual(['point-end']);
});
it('keeps CRRT net removal, effluent and unresolved drain identity explicit',async()=>{
 const c=await load(),net=await entry(c,'net','output_crrt'),effluent=await entry(c,'effluent','output_crrt_effluent'),drain=await entry(c,'drain','output_drain');mountChart(withEntries(c,[net,effluent,drain]));
 expect(screen.getByRole('article',{name:'Recorded CRRT net removal net / '+net.fact.revision})).toHaveTextContent('output_crrt');expect(screen.getByRole('article',{name:'Recorded CRRT effluent effluent / '+effluent.fact.revision})).toHaveTextContent('output_crrt_effluent');expect(screen.getByText(/Drain identity unresolved/)).toBeVisible();
});
it('preserves legacy source-category coding and visible source caveats',async()=>{
 const c=await load(),e=await entry(c,'legacy','output_crrt');e.metadata=null;e.fact.description={coding:{namespace:'clinrx.synthetic.hemodynamic-chart/v1',code:'output_crrt'},raw_display:'NET removal only; not effluent'};e.fact.disclosures=['Recorded volume is not reconciled.'];mountChart(withEntries(c,[e]));
 expect(screen.getByRole('article')).toHaveTextContent('Recorded CRRT net removal');expect(screen.getByRole('article')).toHaveTextContent('NET removal only; not effluent');expect(screen.getByText('Recorded volume is not reconciled.')).toBeVisible();
});
it('does not categorize unknown coding from fact IDs or silently move it into output',async()=>{
 const c=await load(),e=await entry(c,'fs-IO-output_urine-looking-name','unknown-code');e.metadata=null;e.fact.description={coding:{namespace:'unmapped',code:'output_urine'},raw_display:'Unmapped source'};mountChart(withEntries(c,[e]));expect(within(screen.getByRole('region',{name:'Other source assertions — category not mapped to the chart'})).getByRole('article')).toHaveTextContent('Unmapped source');expect(within(screen.getByRole('table')).queryByRole('article')).not.toBeInTheDocument();
});
it('shows repeated local times with original offsets in distinct UTC hour groups',async()=>{
 const c=await load();c.combined.context.scope.review_start='2026-11-01T04:00:00Z';c.combined.context.scope.review_end='2026-11-01T08:00:00Z';Object.assign(c.combined.circulatory.assembly.request.scope,{review_start:'2026-11-01T04:00:00Z',review_end:'2026-11-01T08:00:00Z'});
 const a=await entry(c,'first','output_urine',null,null),b=await entry(c,'second','output_urine',null,null);a.metadata!.chart!.point='2026-11-01T01:30:00-04:00';b.metadata!.chart!.point='2026-11-01T01:30:00-05:00';mountChart(withEntries(c,[a,b]));
 expect(screen.getByRole('row',{name:/2026-11-01T05:00:00Z/})).toHaveTextContent('01:30:00-04:00');expect(screen.getByRole('row',{name:/2026-11-01T06:00:00Z/})).toHaveTextContent('01:30:00-05:00');expect(screen.getByText(/Hour groups use UTC/)).toBeVisible();
});
it.each(['repository','cutoff','scope','duplicate'])('does not disguise %s mismatch as empty chart',async fault=>{
 const c=await load();if(fault==='repository')c.repository='foreign';if(fault==='cutoff')c.items[0].cutoff++;if(fault==='scope')c.items[0].fact.binding.target.patient_id='foreign';if(fault==='duplicate')c.items.push(c.items[0]);mountChart(c);expect(screen.getByRole('alert')).toHaveTextContent('Chart unavailable');expect(screen.queryByRole('table')).not.toBeInTheDocument();expect(screen.queryByText('No recorded entry shown')).not.toBeInTheDocument();
});
it.each(['retained','loading'] as const)('labels %s prior data prominently and never presents empty cells as current absence',async status=>{
 const c=await load();mountChart(c,{status,retrievalMessage:'Request failed'});expect(screen.getByRole('alert')).toHaveTextContent('Retained prior catalog — not confirmed current');expect(screen.getByRole('alert')).toHaveTextContent('Request failed');expect(screen.queryByText('No recorded entry shown')).not.toBeInTheDocument();expect(screen.getAllByText('Unavailable while catalog is unconfirmed').length).toBeGreaterThan(0);
});
it('withholds a current mismatched requested period but identifies a retained prior period',async()=>{
 const c=await load(),period={start:'2026-10-09T08:00:00Z',end:'2026-10-09T10:00:00Z'};const r=mountChart(c,{requestedPeriod:period});expect(screen.getByRole('alert')).toHaveTextContent('Chart unavailable');r.rerender(<RF2FluidChart catalog={c} status="retained" requestedPeriod={period} text={evidenceText} context={()=>''} onInspect={()=>{}}/>);expect(screen.getByRole('alert')).toHaveTextContent('Requested period: 2026-10-09');expect(screen.getByRole('table')).toBeVisible();
});
it('supports keyboard scrolling and provides 360px CSS rules without claiming rendered layout',async()=>{
 const c=await load();mountChart(c);const region=screen.getByRole('region',{name:'Scrollable recorded fluid chart'});region.focus();expect(region).toHaveFocus();fireEvent.keyDown(region,{key:'ArrowRight'});expect(region.scrollLeft).toBe(80);fireEvent.keyDown(region,{key:'ArrowLeft'});expect(region.scrollLeft).toBe(0);expect(region).toHaveAttribute('aria-describedby','rf2-fluid-scroll-help');expect(styles).toContain('@media(max-width:360px)');expect(styles).toContain('.rf2-fluid-scroll {overflow:auto;max-width:100%');
});
it('opens exact history by keyboard and returns focus while preserving the mounted draft and evidence selection',async()=>{
 const c=await load(),t=transport(c),p=props(c,t);render(<RenalFluidEntryWorkspace {...p}/>);const user=userEvent.setup();const row=screen.getByRole('row',{name:new RegExp(fixture.urine.fact.id)});await user.click(within(row).getByRole('button',{name:'Reuse for reassessment'}));await user.type(screen.getByLabelText('Actor'),'Recorder');await user.type(screen.getByLabelText('question'),'Keep this authored question');const actor=screen.getByLabelText('Actor');const selected=within(screen.getByRole('region',{name:'RF2 draft'})).getByText(new RegExp(fixture.urine.fact.id)).textContent;
 await user.click(screen.getByRole('button',{name:'Fluid chart'}));const button=within(screen.getByRole('region',{name:'Fluid chart'})).getByRole('button',{name:/Open exact source/});button.focus();await user.keyboard('{Enter}');expect(await screen.findByRole('heading',{name:'Selected '+fixture.urine.fact.id+' / '+fixture.urine.fact.revision})).toHaveFocus();expect(t.history).toHaveBeenCalledWith(original(c));await user.click(screen.getByRole('button',{name:'Close history'}));expect(button).toHaveFocus();await user.click(screen.getByRole('button',{name:'Source list'}));expect(screen.getByLabelText('Actor')).toBe(actor);expect(actor).toHaveValue('Recorder');expect(screen.getByLabelText('question')).toHaveValue('Keep this authored question');expect(within(screen.getByRole('region',{name:'RF2 draft'})).getByText(new RegExp(fixture.urine.fact.id))).toHaveTextContent(selected!);expect(t.action).not.toHaveBeenCalled();expect(p.onRefresh).not.toHaveBeenCalled();
});
it('preserves the exact pending request and recovery controls when chart/list changes after uncertain save',async()=>{
 const c=await load(),t=transport(c);vi.mocked(t.action).mockImplementation(async(action)=>{if(action==='save')throw Error('Uncertain');return {status:action==='lookup'?'absent':'validated',fact:fixture.weight.fact,execution_enabled:false} as never;});render(<RenalFluidEntryWorkspace {...props(c,t)}/>);
 const row=screen.getByRole('row',{name:new RegExp(fixture.weight.fact.id)});fireEvent.click(within(row).getByRole('button',{name:'Correct original record'}));fireEvent.change(screen.getByLabelText('Actor'),{target:{value:'Recorder'}});fireEvent.change(screen.getByLabelText('Reason for correction'),{target:{value:'Correction'}});fireEvent.click(screen.getByRole('button',{name:'Validate RF2 draft'}));fireEvent.click(await screen.findByRole('button',{name:'Confirm RF2 append'}));await screen.findByRole('button',{name:'Check exact RF2 saved result'});const pending=vi.mocked(t.action).mock.calls[1][1];fireEvent.click(screen.getByRole('button',{name:'Fluid chart'}));fireEvent.click(screen.getByRole('button',{name:'Source list'}));fireEvent.click(screen.getByRole('button',{name:'Check exact RF2 saved result'}));await screen.findByRole('button',{name:'Explicitly retry identical RF2 request'});expect(vi.mocked(t.action).mock.calls.at(-1)![1]).toBe(pending);expect(vi.mocked(t.action).mock.calls.filter(([action])=>action==='save')).toHaveLength(1);
});
it('retains exact handover selection and storage bytes through chart navigation',async()=>{
 const c=await load(),t=transport(c);render(<RenalFluidEntryWorkspace {...props(c,t)}/>);const row=screen.getByRole('row',{name:new RegExp(fixture.urine.fact.id)});fireEvent.click(within(row).getByRole('button',{name:'Add exact record to RF2 handover'}));fireEvent.click(screen.getByRole('button',{name:'Save RF2 handover locally'}));const before=localStorage.getItem(storageKey(c.repository));fireEvent.click(screen.getByRole('button',{name:'Fluid chart'}));fireEvent.click(screen.getByRole('button',{name:'Source list'}));expect(localStorage.getItem(storageKey(c.repository))).toBe(before);expect(JSON.parse(before!).pins).toEqual([pin(original(c))]);
});
