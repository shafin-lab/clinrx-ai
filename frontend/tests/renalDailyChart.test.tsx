// @vitest-environment-options {"url":"http://127.0.0.1:5238/"}
import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import renalFixture from './fixtures/renalFluid.json';
import {RF2Client,type Catalog,type Evidence} from '../src/api/rf2Client';
import type {RenalObservation} from '../src/api/renalFluidTypes';
import {decimal,formatNumber,plus} from '../src/renal/chartArithmetic';
import {creatinineDisplay} from '../src/renal/renalUnits';
import {chartWindow,dailyFluidModel,hourLabel} from '../src/renal/dailyFluidModel';
import {DailyFluidChart} from '../src/renal/DailyFluidChart';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto'),oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));afterEach(()=>{vi.unstubAllGlobals();});
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00+00:00',end:'2026-10-09T08:00:00+00:00'};
function typedTime(text:string){return {source_timestamp:text,recorded:{status:'known',precision:'instant',value:text,lower:null,upper:null,uncertainty:null},clock:'unknown',conflicting:[],alternative_sources:[]};}
async function catalog(){
 const c=await new RF2Client(vi.fn().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 // Model tests receive an already-decoded DTO. Transport canonical/hash validation
 // is separately tested by RF2 and exercised by the real preview API.
 const scopes=[c.combined.context.scope,c.combined.laboratory.scope,c.combined.circulatory.assembly.request.scope];for(const scope of scopes){scope.review_start=requested.start;scope.review_end=requested.end;}
 c.items=[];return c;
}
function entry(c:Catalog,id:string,category:string,amount:string|null,start='2026-10-08T08:00:00Z',end:string|null='2026-10-08T09:00:00Z',unit='mL'){
 const e=structuredClone(fixture.urine) as unknown as Evidence;e.repository=c.repository;e.cutoff=c.cutoff.fact_watermark;e.ingestion.repository_id=c.repository;e.fact.id=id;e.terminal_reference={kind:e.fact.kind,id,version:e.fact.revision};e.superseded=false;e.fact.record_status='recorded';
 e.metadata!.chart={...e.metadata!.chart!,category,amount,unit,point:end??start,start:end?start:null,end};e.fact.occurred=typedTime(end??start);e.fact.recorded_interval=end?{start:typedTime(start),end:typedTime(end)}:null;e.fact.recorded_amount=amount===null?null:{value:amount,unit:{raw:unit,status:'unresolved'}};return e;
}
function model(c:Catalog){return dailyFluidModel(c,requested,c.repository);}
function creatinine(value:string,raw:string,status='unresolved'){const lab=structuredClone(renalFixture.laboratory.observations[0]) as unknown as RenalObservation;lab.fact.value={status:'known',value:{value,unit:{raw,status}},reason:null};return lab;}

it('converts the screenshot values to one bedside unit without changing their sources',()=>{
 for(const [value,unit,text] of [['1.1000','mg/dL','1.10 mg/dL'],['2.000','mg/dL','2.00 mg/dL'],['150.0','umol/L','≈ 1.70 mg/dL']]){const source=creatinine(value,unit),before=JSON.stringify(source);expect(creatinineDisplay(source).text).toBe(text);expect(JSON.stringify(source)).toBe(before);}
});
it.each(['µmol/L','μmol/L','umol/L'])('accepts the explicit creatinine %s spelling',unit=>{expect(creatinineDisplay(creatinine('88.4',unit)).text).toBe('≈ 1.00 mg/dL');});
it('handles mmol/L and mg/L through the same explicit analyte profile',()=>{
 expect(creatinineDisplay(creatinine('0.0884','mmol/L')).text).toBe('≈ 1.00 mg/dL');expect(creatinineDisplay(creatinine('10','mg/L')).text).toBe('≈ 1.00 mg/dL');
});
it('does not guess a microgram unit or conflicting mapped unit',()=>{
 expect(creatinineDisplay(creatinine('150','mcg/dL')).available).toBe(false);const s=creatinine('1','mg/dL','assessed');Object.assign((s.fact.value.value as {unit:object}).unit,{system:'UCUM',code:'umol/L'});expect(creatinineDisplay(s).note).toContain('do not agree');
});
it('keeps source mapping uncertainty visible after a display conversion',()=>{expect(creatinineDisplay(creatinine('150','umol/L')).note).toContain('not a validated clinical input');});
it('does not turn a missing creatinine into a zero result',()=>{
 const s=creatinine('0','mg/dL');s.fact.value={status:'missing',value:null,reason:'No result'};expect(creatinineDisplay(s).text).toBe('missing · No result');expect(creatinineDisplay(creatinine('0','mg/dL')).text).toBe('0.00 mg/dL');
});
it('rounds decimal display exactly without binary-float addition or half rounding errors',()=>{
 expect(formatNumber(plus(decimal('0.1'),decimal('0.2')),2,false)).toBe('0.30');expect(formatNumber(decimal('1.005'),2,false)).toBe('1.01');expect(formatNumber(decimal('-1.005'),2,false)).toBe('-1.01');
});
it('defines the requested day start and explicit fixed-offset clock',()=>{
 const w=chartWindow('2026-10-08','08','+05:30');expect(w.b-w.a).toBe(86400000);expect(w.start).toBe('2026-10-08T08:00:00+05:30');expect(w.end).toBe('2026-10-09T08:00:00+05:30');expect(hourLabel(w.a,0,w.offset)).toBe('08:00–09:00');expect(hourLabel(w.a,23,w.offset)).toBe('07:00–08:00');
});
it('rejects an invalid chart day rather than shifting it to another date',()=>{expect(()=>chartWindow('2026-02-30','08','+00:00')).toThrow();});
it('sums recorded intake/output in mL and labels a positive partial net',async()=>{
 const c=await catalog();c.items=[entry(c,'in','input_iv','1.25',undefined,undefined,'L'),entry(c,'out','output_urine','250')];const m=model(c);expect(m.valid).toBe(true);expect(formatNumber(m.intake)).toBe('1250');expect(formatNumber(m.output)).toBe('250');expect(formatNumber(m.net)).toBe('1000');expect(m.fullDayConfirmed).toBe(false);
});
it('calculates negative and zero recorded difference without claiming fluid status',async()=>{
 const c=await catalog();c.items=[entry(c,'in','input_iv','100'),entry(c,'out','output_urine','300')];expect(formatNumber(model(c).net)).toBe('-200');c.items[0]=entry(c,'in','input_iv','300');expect(formatNumber(model(c).net)).toBe('0');
});
it('places interval volumes under their collection hour, not their end hour',async()=>{
 const c=await catalog();c.items=[entry(c,'first','output_urine','35'),entry(c,'second','output_urine','45','2026-10-08T09:00:00Z','2026-10-08T10:00:00Z')];expect(model(c).entries.map(e=>e.hour)).toEqual([0,1]);
});
it('keeps a recorded zero distinct from missing volume',async()=>{
 const c=await catalog();c.items=[entry(c,'zero','output_urine','0'),entry(c,'missing','output_urine',null,'2026-10-08T09:00:00Z','2026-10-08T10:00:00Z')];const m=model(c);expect(m.entries).toHaveLength(1);expect(formatNumber(m.entries[0].amount)).toBe('0');expect(m.issues[0].reason).toContain('not zero');
});
it('never adds cumulative source summaries to individual urine volumes',async()=>{
 const c=await catalog();c.items=[entry(c,'urine','output_urine','145'),entry(c,'sum','urine_total_reported','145')];expect(formatNumber(model(c).output)).toBe('145');expect(model(c).summaries).toHaveLength(1);
});
it('excludes gross effluent while retaining explicit CRRT net removal',async()=>{
 const c=await catalog();c.items=[entry(c,'net','output_crrt_net','100'),entry(c,'effluent','output_crrt_effluent','2400')];expect(formatNumber(model(c).output)).toBe('100');expect(model(c).effluent).toHaveLength(1);
});
it('does not split a cross-hour collection but counts its full eligible day volume once',async()=>{
 const c=await catalog();c.items=[entry(c,'span','output_urine','300','2026-10-08T08:30:00Z','2026-10-08T10:30:00Z')];const m=model(c);expect(m.entries[0].hour).toBeUndefined();expect(m.unallocated).toHaveLength(1);expect(formatNumber(m.output)).toBe('300');
});
it('withholds collections crossing the selected day boundary rather than prorating',async()=>{
 const c=await catalog();c.items=[entry(c,'cross','output_urine','300','2026-10-08T07:30:00Z','2026-10-08T08:30:00Z')];expect(model(c).entries).toHaveLength(0);expect(model(c).issues[0].reason).toContain('no volume prorating');
});
it('puts a point at exactly the end boundary outside the selected day',async()=>{
 const c=await catalog();c.items=[entry(c,'point','input_iv','100',requested.end,null)];expect(model(c).entries).toHaveLength(0);expect(model(c).outside).toHaveLength(1);
});
it('withholds both overlapping collections rather than selecting the preferred volume',async()=>{
 const c=await catalog();c.items=[entry(c,'a','output_urine','20','2026-10-08T09:30:00Z','2026-10-08T09:45:00Z'),entry(c,'b','output_urine','15','2026-10-08T09:40:00Z','2026-10-08T09:50:00Z')];expect(model(c).entries).toHaveLength(0);expect(model(c).issues).toHaveLength(2);
});
it('does not exclude simultaneous intake and urine in distinct categories',async()=>{
 const c=await catalog();c.items=[entry(c,'in','input_iv','100'),entry(c,'urine','output_urine','20')];expect(model(c).entries).toHaveLength(2);
});
it('withholds a same-category point inside a collection where independence is unknown',async()=>{
 const c=await catalog();c.items=[entry(c,'interval','input_iv','100'),entry(c,'point','input_iv','20','2026-10-08T08:30:00Z',null)];expect(model(c).entries).toHaveLength(0);expect(model(c).issues).toHaveLength(2);
});
it('does not integrate a rate as if it were a recorded volume',async()=>{
 const c=await catalog();c.items=[entry(c,'rate','input_iv','100',undefined,undefined,'mL/h')];expect(model(c).entries).toHaveLength(0);expect(model(c).issues[0].reason).toContain('unsupported volume unit');
});
it('rejects scope, repository, duplicate identity and short-period mismatches',async()=>{
 const c=await catalog();c.items=[entry(c,'a','input_iv','100')];expect(dailyFluidModel(c,requested,'foreign').valid).toBe(false);expect(dailyFluidModel(c,{...requested,patient:'other'},c.repository).valid).toBe(false);expect(dailyFluidModel(c,{...requested,end:'2026-10-08T10:00:00Z'},c.repository).valid).toBe(false);c.items.push(c.items[0]);expect(model(c).valid).toBe(false);
});
it('does not resurrect superseded or withdrawn volume entries',async()=>{
 const c=await catalog(),a=entry(c,'old','output_urine','100'),b=entry(c,'withdrawn','output_urine','200');a.superseded=true;b.fact.record_status='withdrawn';c.items=[a,b];expect(model(c).entries).toHaveLength(0);
});
it('renders 24 adjacent hour columns and partial totals after a separate day read',async()=>{
 const c=await catalog();c.items=[entry(c,'in','input_iv','100'),entry(c,'urine','output_urine','20')];const t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current transport={t}/>);
 await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});expect(t.catalog).toHaveBeenCalledWith(requested.start,requested.end);const chart=screen.getByRole('table');expect(within(chart).getByRole('columnheader',{name:'08:00–09:00'})).toBeInTheDocument();expect(within(chart).getByRole('columnheader',{name:'09:00–10:00'})).toBeInTheDocument();expect(within(chart).getAllByRole('columnheader')).toHaveLength(27);expect(screen.getByRole('region',{name:'Recorded daily totals'})).toHaveTextContent('+80 mL');expect(screen.getByText('Not established')).toBeInTheDocument();expect(screen.queryByText(/diuretic/i)).not.toBeInTheDocument();
});
it('retrieves the full selected day instead of silently treating a two-hour snapshot as a day',async()=>{
 const c=await catalog(),t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart="2026-10-08T08:00:00Z" repository={c.repository} current transport={t}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});expect(t.catalog.mock.calls[0][1]).toBe('2026-10-09T08:00:00+00:00');
});
it('avoids a hidden-view day request and blocks unconfirmed source reads',async()=>{
 const c=await catalog(),t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])};const r=render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current active={false} transport={t}/>);expect(t.catalog).not.toHaveBeenCalled();r.rerender(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current={false} transport={t}/>);expect(t.catalog).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Refresh daily chart'})).toBeDisabled();
});
it('does not substitute old results after the selected day read fails',async()=>{
 const c=await catalog(),t={catalog:vi.fn().mockRejectedValue(Error('offline')),history:vi.fn().mockResolvedValue([])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current transport={t}/>);expect(await screen.findByRole('alert')).toHaveTextContent('No older day or different patient was substituted');expect(screen.queryByRole('region',{name:'Hourly 24-hour input output chart'})).not.toBeInTheDocument();
});
it('discards a late day response after the user changes date',async()=>{
 const c=await catalog();let finish!:(c:Catalog)=>void;const t={catalog:vi.fn().mockImplementationOnce(()=>new Promise<Catalog>(done=>{finish=done;})).mockRejectedValue(Error('Second day missing')),history:vi.fn().mockResolvedValue([])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current transport={t}/>);fireEvent.change(screen.getByLabelText('Chart date'),{target:{value:'2026-10-09'}});await screen.findByRole('alert');await act(async()=>{finish(c);});expect(screen.queryByRole('region',{name:'Hourly 24-hour input output chart'})).not.toBeInTheDocument();
});
it('opens the exact contributing volume through the original history owner',async()=>{
 const c=await catalog(),e=entry(c,'urine-original','output_urine','35');c.items=[e];const t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([e])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current transport={t}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});fireEvent.click(screen.getByText('35 *'));fireEvent.click(screen.getByRole('button',{name:/urine-original/}));await screen.findByRole('dialog');expect(t.history).toHaveBeenCalledWith(e);expect(t.catalog).toHaveBeenCalledTimes(1);
});
it('reuses the confirmed daily snapshot when switching views, with an explicit refresh for a new read',async()=>{
 const c=await catalog(),t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])},p={patient:requested.patient,encounter:requested.encounter,reviewStart:requested.start,repository:c.repository,current:true,transport:t};const r=render(<DailyFluidChart {...p}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});r.rerender(<DailyFluidChart {...p} active={false}/>);r.rerender(<DailyFluidChart {...p} active/>);expect(t.catalog).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Refresh daily chart'}));await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});expect(t.catalog).toHaveBeenCalledTimes(2);
});
it('keeps finer-than-millisecond or uncertain source timing unplaced rather than rounding it into an hour',async()=>{
 const c=await catalog(),e=entry(c,'fine','output_urine','40','2026-10-08T08:59:59.9999999Z','2026-10-08T09:15:00Z');c.items=[e];expect(model(c).entries).toHaveLength(0);expect(model(c).issues[0].reason).toContain('Time or collection interval');
});
it('requires a newly confirmed day after the shared source cutoff changes',async()=>{
 const c=await catalog(),t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])},p={patient:requested.patient,encounter:requested.encounter,reviewStart:requested.start,repository:c.repository,current:true,transport:t};const r=render(<DailyFluidChart {...p} sharedCutoff={10}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});r.rerender(<DailyFluidChart {...p} sharedCutoff={11}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});expect(t.catalog).toHaveBeenCalledTimes(2);
});
it('shows partial urine source minutes and does not carry running net into empty hours',async()=>{
 const c=await catalog();c.items=[entry(c,'in','input_iv','100'),entry(c,'zero','output_urine','0','2026-10-08T09:00:00Z','2026-10-08T09:15:00Z')];const t={catalog:vi.fn().mockResolvedValue(c),history:vi.fn().mockResolvedValue([])};render(<DailyFluidChart patient={requested.patient} encounter={requested.encounter} reviewStart={requested.start} repository={c.repository} current transport={t}/>);await screen.findByRole('region',{name:'Hourly 24-hour input output chart'});expect(screen.getByText('15 / 60 min · partial')).toBeInTheDocument();const running=screen.getByRole('row',{name:/Running recorded net/});expect(within(running).getAllByText('+100')).toHaveLength(3);expect(within(running).getAllByText('—')).toHaveLength(22);
});
