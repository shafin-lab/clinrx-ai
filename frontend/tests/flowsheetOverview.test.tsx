import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {ICUFlowsheet} from '../src/demo/ICUFlowsheet';
import {buildFlowsheet} from '../src/demo/flowsheetPresentation';
import {overviewGroup,overviewTimeWindow,shortSourceInterval} from '../src/demo/flowsheetOverview';
import {record} from '../src/demo/evidencePresentation';
const items=()=>decodeCirculatoryState(structuredClone(fixture)).assembly.snapshot.items;
const ids=()=>screen.getAllByRole('button',{name:/^Chart source /}).map(b=>b.getAttribute('aria-label'));
afterEach(cleanup);
it('defaults to a compact overview with all six groups and exact source selection',()=>{
 const sources=items(),before=JSON.stringify(sources),inspect=vi.fn();render(<ICUFlowsheet items={sources} onInspect={inspect}/>);
 expect(screen.getByRole('combobox',{name:'Flowsheet section'})).toHaveValue('overview');
 for(const name of ['BP / MAP','Cardiac output / index','Rhythm / heart rate','Infusion events','Fluid records','Perfusion observations'])expect(screen.getByRole('rowgroup',{name})).toBeInTheDocument();
 expect(screen.getByText('Recorded times 9–12 of 12 · UTC')).toBeInTheDocument();
 const button=screen.getByRole('button',{name:'Chart source fs-D-CHANGE revision 1'});expect(button).toHaveTextContent('Changed');expect(button).toHaveTextContent('3.0 mcg/kg/min');fireEvent.click(button);
 expect(inspect).toHaveBeenCalledWith(sources.find(i=>i.fact.id==='fs-D-CHANGE'),button);
 expect(screen.getByRole('button',{name:'Chart source fs-BALANCE-TOTAL revision 1'})).toHaveTextContent('285 mL');
 expect(screen.getByRole('button',{name:'Chart source fs-LACTATE-60 revision 1'})).toHaveTextContent('2.0 mmol/L');expect(JSON.stringify(sources)).toBe(before);
});
it('makes every overview event reachable through time pages and through all-times mode',()=>{
 const sources=items(),chart=buildFlowsheet(sources),expected=chart.rows.filter(r=>overviewGroup(r)!==null).flatMap(r=>[...r.cells.values()].flat().map(i=>'Chart source '+i.fact.id+' revision '+i.fact.revision));
 render(<ICUFlowsheet items={sources} onInspect={vi.fn()}/>);const seen=new Set(ids());
 while(!(screen.getByRole('button',{name:'Earlier times'}) as HTMLButtonElement).disabled){fireEvent.click(screen.getByRole('button',{name:'Earlier times'}));ids().forEach(i=>seen.add(i));}
 expect([...seen].sort()).toEqual(expected.sort());expect(screen.getByRole('button',{name:'Chart source fs-N-ORDER revision 1'})).toHaveTextContent('Order');
 fireEvent.click(screen.getByRole('checkbox',{name:'Show all recorded times'}));expect(ids().sort()).toEqual(expected.sort());
 expect(screen.getByRole('button',{name:'Earlier times'})).toBeDisabled();expect(screen.getByRole('button',{name:'Later times'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Chart source fs-D-PAUSE revision 1'})).toHaveTextContent('Paused');expect(screen.getByRole('button',{name:'Chart source fs-D-PAUSE revision 1'})).not.toHaveTextContent('0 mcg');
});
it('keeps full-detail records and unknown or withdrawn source status available',()=>{
 const sources=items(),lactate=sources.find(i=>i.fact.id==='fs-LACTATE-60')!;record(record(lactate.fact.acquisition).quality).status='unknown';lactate.fact.record_status='withdrawn';
 render(<ICUFlowsheet items={sources} onInspect={vi.fn()}/>);
 expect(screen.getByRole('button',{name:'Chart source fs-LACTATE-60 revision 1'})).toHaveTextContent('Quality: unknown');expect(screen.getByRole('button',{name:'Chart source fs-LACTATE-60 revision 1'})).toHaveTextContent('withdrawn');
 expect(screen.getByRole('button',{name:'Chart source fs-CO-60 revision 1'})).toHaveTextContent('Quality: suspect');
 expect(screen.queryByRole('button',{name:'Chart source fs-CVP-60 revision 1'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByRole('combobox',{name:'Flowsheet section'}),{target:{value:'all'}});
 expect(screen.getByRole('button',{name:'Chart source fs-CO-60 revision 1'})).toHaveTextContent('Quality: suspect');
 expect(screen.getAllByRole('button',{name:/^Chart source /})).toHaveLength(150);
});
it('labels source intervals and reported balances without recalculating or confusing them with points',()=>{
 const sources=items();render(<ICUFlowsheet items={sources} onInspect={vi.fn()}/>);
 const button=screen.getByRole('button',{name:'Chart source fs-IO-net_balance_reported-60 revision 1'});
 expect(button).toHaveTextContent('-50 mL');expect(button).toHaveTextContent('Interval 08:45:00 → 09:00:00 UTC');expect(button).toHaveTextContent('Quality: not recorded');
 expect(screen.getByText(/balances are source-reported, not calculated here/)).toBeInTheDocument();
 expect(screen.getByText('Blank means no record at that time.')).toBeInTheDocument();
});
it('does not shorten ambiguous, fractional, foreign-day or missing interval boundaries',()=>{
 const item=items().find(i=>i.fact.id==='fs-IO-output_urine-15')!;
 expect(shortSourceInterval(item)).toBe('Interval 08:00:00 → 08:15:00 UTC');
 for(const change of [(b:Record<string,unknown>)=>{b.clock='unknown';},(b:Record<string,unknown>)=>{b.source_timestamp='2026-10-08T08:00:00.0000001Z';},(b:Record<string,unknown>)=>{b.alternative_sources=[{}];},(b:Record<string,unknown>)=>{b.source_timestamp='2026-10-07T08:00:00Z';record(b.recorded).value=b.source_timestamp;}]){
  const other=structuredClone(item);change(record(record(other.fact.recorded_interval).start));expect(shortSourceInterval(other)).toBe('Interval context: inspect source');
 }
 expect(shortSourceInterval(items().find(i=>i.fact.id==='fs-LACTATE-60')!)).toBeNull();
});
it('clamps paging safely for shorter or empty datasets without inventing columns',()=>{
 expect(overviewTimeWindow([],9,false).times).toEqual([]);
 expect(overviewTimeWindow(['a','b'],9,false)).toMatchObject({times:['a','b'],page:0,start:0,end:2});
 expect(overviewTimeWindow(['a','b','c','d','e'],1,false).times).toEqual(['a']);
});

it('keeps pressure, method-specific flow and source rhythm on exact times with inspectable uncertainty',()=>{
 const sources=items(),before=JSON.stringify(sources),inspect=vi.fn();render(<ICUFlowsheet items={sources} onInspect={inspect}/>);
 for(const id of ['fs-MAP-60','fs-systemic_systolic-60','fs-systemic_diastolic-60','fs-CO-60','fs-CI-60','fs-HR-60','fs-RHYTHM-60']){
  const source=sources.find(i=>i.fact.id===id)!,button=screen.getByRole('button',{name:'Chart source '+id+' revision 1'});
  fireEvent.click(button);expect(inspect).toHaveBeenLastCalledWith(source,button);
  expect(button.closest('td')?.cellIndex).toBe(4);
 }
 expect(screen.getByRole('button',{name:'Chart source fs-CO-60 revision 1'})).toHaveTextContent('Quality: suspect');
 expect(screen.getByText(/No preferred output or rhythm diagnosis/i)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('checkbox',{name:'Show all recorded times'}));
 const table=screen.getByRole('table');
 for(const id of ['m7-CO','m7-FLOTRAC','m7-PICCO-CO','m7-VOLUMEVIEW']){
  const button=screen.getByRole('button',{name:'Chart source '+id+' revision 1'});
  expect(button.closest('tr')).toHaveTextContent(id==='m7-CO'?'bolus thermodilution':id==='m7-VOLUMEVIEW'?'transpulmonary thermodilution':'pulse contour');
 }
 expect(screen.getByRole('button',{name:'Chart source m7-CO revision 1'}).closest('tr')).not.toBe(screen.getByRole('button',{name:'Chart source m7-FLOTRAC revision 1'}).closest('tr'));
 expect(screen.getByRole('button',{name:'Chart source m7-FLOTRAC revision 1'}).closest('tr')).not.toBe(screen.getByRole('button',{name:'Chart source m7-PICCO-CO revision 1'}).closest('tr'));
 expect(table).not.toHaveTextContent('m7-CONTEXT-CO');
 expect(screen.queryByRole('button',{name:'Chart source m7-ECG revision 1'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Chart source fs-RHYTHM-30 revision 1'})).toHaveTextContent('no arrhythmia classification confirmed');
 expect(JSON.stringify(sources)).toBe(before);
});
