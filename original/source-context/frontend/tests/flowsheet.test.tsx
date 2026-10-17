import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,within} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {buildFlowsheet,chartTime,infusionText} from '../src/demo/flowsheetPresentation';
import {ICUFlowsheet,InfusionDetails} from '../src/demo/ICUFlowsheet';
import {record,quality,hasUncertainQuality} from '../src/demo/evidencePresentation';
import {deliverySupport,exactLinked,AssessmentContext} from '../src/demo/HemodynamicContext';
import {chartEntry,intervalText} from '../src/demo/chartEntries';
import type {CirculatoryItem} from '../src/api/circulatoryTypes';
const items=()=>decodeCirculatoryState(structuredClone(fixture)).assembly.snapshot.items;
afterEach(cleanup);
it('keeps repeated values by method and retains missing or contextual times off axis',()=>{
  const sources=items(),before=JSON.stringify(sources),chart=buildFlowsheet(sources);
  expect(sources).toHaveLength(156);expect(chart.rows.filter(r=>r.label==='Cardiac output')).toHaveLength(4);
  expect(chart.rows.filter(r=>r.drug).map(r=>r.label)).toEqual(expect.arrayContaining(['Noradrenaline (norepinephrine)','Vasopressin','Dobutamine · inotrope']));
  expect(chart.unplaced.map(i=>i.fact.id)).toEqual(expect.arrayContaining(['m7-CONTEXT-CO','m7-UNPLACED']));
  expect(chart.times).toContain('2026-10-08T08:50:00Z');expect(JSON.stringify(sources)).toBe(before);
});
const changes:[string,(i:CirculatoryItem)=>void][]=[
 ['fractional time',i=>{record(i.fact.occurred).source_timestamp='2026-10-08T08:15:00.0000001Z';}],
 ['unverified clock',i=>{record(i.fact.occurred).clock='unknown';}],
 ['missing precision declaration',i=>{delete record(i.fact.occurred).timestamp_precision;}],
 ['different recorded time',i=>{record(record(i.fact.occurred).recorded).value='2026-10-08T08:16:00Z';}],
 ['alternative time',i=>{record(i.fact.occurred).alternative_sources=[{}];}],
 ['conflicting time',i=>{record(i.fact.occurred).conflicting=['2026-10-08T08:16:00Z'];}],
 ['retained conflict lexeme',i=>{record(i.fact.occurred).conflicting_source_timestamps=['2026-10-08T08:16:00Z'];}],
 ['time bound',i=>{record(record(i.fact.occurred).recorded).lower='2026-10-08T08:14:00Z';}],
 ['alignment evidence',i=>{record(i.fact.occurred).alignment={};}],
 ['contextual placement',i=>{i.inclusion='contextual';}],
];
it.each(changes)('does not place %s on the axis',(_label,change)=>{
 const item=items().find(i=>i.fact.id==='fs-CO-15')!;change(item);expect(chartTime(item)).toBeNull();expect(buildFlowsheet([item]).unplaced).toEqual([item]);
});
it('keeps two observations at the same exact timestamp instead of averaging or replacing',()=>{
 const item=items().find(i=>i.fact.id==='fs-CO-15')!,other=structuredClone(item);other.fact.id='second-record';
 const chart=buildFlowsheet([item,other]);expect(chart.rows).toHaveLength(1);expect(chart.rows[0].cells.get('2026-10-08T08:15:00Z')).toEqual([item,other]);
});
it('does not carry forward a dose or replace a pause/stop with zero',()=>{
 const chart=buildFlowsheet(items()),n=chart.rows.find(r=>r.label==='Noradrenaline (norepinephrine)')!;
 expect(n.cells.get('2026-10-08T08:30:00Z')).toBeUndefined();
 for(const id of ['fs-D-PAUSE','fs-V-STOP']){const text=infusionText(items().find(i=>i.fact.id===id)!);expect(text.rate).toBe('Rate not recorded');expect(text.reason).toContain('Fictional');}
});
it('preserves exact drug units, event distinctions and source links',()=>{
 const sources=items(),onInspect=vi.fn();render(<ICUFlowsheet items={sources} onInspect={onInspect}/>);
 fireEvent.change(screen.getByLabelText('Flowsheet section'),{target:{value:'all'}});
 const button=screen.getByRole('button',{name:'Chart source fs-D-CHANGE revision 1'});expect(button).toHaveTextContent('3.0 mcg/kg/min');fireEvent.click(button);
 expect(onInspect).toHaveBeenCalledWith(sources.find(i=>i.fact.id==='fs-D-CHANGE'),button);
 expect(screen.getByRole('button',{name:'Chart source fs-N-ORDER revision 1'})).toHaveTextContent('order');
 expect(screen.getByRole('button',{name:'Chart source fs-V-START revision 1'})).toHaveTextContent('1.8 units/h');
 expect(screen.getByRole('button',{name:'Chart source fs-CO-60 revision 1'})).toHaveTextContent('Quality: suspect');
 expect(screen.getAllByText('No event recorded').length).toBeGreaterThan(0);
 expect(screen.getByText(/Blank cells do not mean zero/)).toBeInTheDocument();
});
it('labels prescribed rate and missing weight/pump-rate without converting them to administration',()=>{
 render(<InfusionDetails item={items().find(i=>i.fact.id==='fs-D-ORDER')!}/>);
 const details=screen.getByRole('region',{name:'Recorded infusion event details'});
 expect(details).toHaveTextContent('Prescribed rate — not delivery');expect(details).toHaveTextContent('2.5 mcg/kg/min');
 expect(details).toHaveTextContent('Exact weight reference unavailable in this view; not replaced');expect(details).toHaveTextContent('No exact linked pump-rate record available; not calculated from dose or concentration');
});
it('retains withdrawn source status and empty states without inventing observations',()=>{
 const source=items().find(i=>i.fact.id==='fs-CO-15')!;source.fact.record_status='withdrawn';
 const view=render(<ICUFlowsheet items={[source]} onInspect={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText('Flowsheet section'),{target:{value:'all'}});
 expect(screen.getByRole('button',{name:'Chart source fs-CO-15 revision 1'})).toHaveTextContent('withdrawn');
 view.rerender(<ICUFlowsheet items={[]} onInspect={vi.fn()}/>);expect(screen.getByText(/No observations can be placed/)).toBeInTheDocument();
 expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

it('separates unlinked events and distinct infusion identities for the same agent',()=>{
 const sources=items(),linked=sources.find(i=>i.fact.id==='fs-N-START')!,unknown=sources.find(i=>i.fact.id==='m7-V')!;
 const other=structuredClone(linked);other.fact.id='separate-line';record(record(record(other.fact.action).delivery).infusion).code='another-infusion';
 const chart=buildFlowsheet([linked,unknown,other]);expect(chart.rows).toHaveLength(3);
 const pause=buildFlowsheet(sources).rows.find(row=>row.context.includes('fs-infusion-dobutamine'))!;
 expect(pause.cells.get('2026-10-08T08:50:00Z')![0].fact.id).toBe('fs-D-PAUSE');
});

it('distinguishes interval volumes, explicit zero and source-reported balances without calculating',()=>{
 const sources=items();render(<ICUFlowsheet items={sources} onInspect={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText('Flowsheet section'),{target:{value:'fluids'}});
 expect(screen.getByRole('button',{name:'Chart source fs-IO-output_urine-15 revision 1'})).toHaveTextContent('35 mL');
 expect(screen.getByRole('button',{name:'Chart source fs-IO-input_blood-15 revision 1'})).toHaveTextContent('0 mL');
 const balance=screen.getByRole('button',{name:'Chart source fs-IO-net_balance_reported-60 revision 1'});
 expect(balance).toHaveTextContent('-50 mL');expect(balance).toHaveTextContent('Source-reported calculation; not calculated by ClinRx');
 expect(screen.getByRole('button',{name:'Chart source fs-BALANCE-TOTAL revision 1'})).toHaveTextContent('285 mL');
 expect(screen.getByText(/Intervention volumes may already be included/)).toBeInTheDocument();
 expect(intervalText(sources.find(i=>i.fact.id==='fs-IO-output_urine-15')!)).toContain('2026-10-08T08:00:00+00:00 → 2026-10-08T08:15:00+00:00');
});
it('keeps exact weight and pump support, never substituting successors, foreign scope or another infusion',()=>{
 const sources=items(),event=sources.find(i=>i.fact.id==='fs-D-CHANGE')!;
 expect(deliverySupport(event,sources).weight!.fact.id).toBe('fs-WEIGHT');
 expect(deliverySupport(event,sources).pumps[0].fact.id).toBe('fs-PUMP-RATE-D-CHANGE');
 const changed=structuredClone(sources);changed.find(i=>i.fact.id==='fs-WEIGHT')!.fact.revision='2';
 expect(deliverySupport(event,changed).weight).toBeNull();
 const pump=changed.find(i=>i.fact.id==='fs-PUMP-RATE-D-CHANGE')!;pump.fact.binding.target.encounter_id='foreign';
 expect(deliverySupport(event,changed).pumps).toHaveLength(0);
 const wrong=structuredClone(sources),other=wrong.find(i=>i.fact.id==='fs-PUMP-RATE-D-CHANGE')!;
 record((other.fact.source_identifiers as unknown[])[0]).code='different-infusion';
 expect(deliverySupport(event,wrong).pumps).toHaveLength(0);
});
it('shows separately recorded pump rate and weight without deriving dose or volumetric rate',()=>{
 const sources=items();render(<InfusionDetails item={sources.find(i=>i.fact.id==='fs-D-CHANGE')!} items={sources}/>);
 const detail=screen.getByRole('region',{name:'Recorded infusion event details'});
 expect(detail).toHaveTextContent('70 kg');expect(detail).toHaveTextContent('2.52 mL/h');expect(detail).toHaveTextContent('3.0 mcg/kg/min');
 expect(detail).toHaveTextContent('No continuous exposure, dose conversion');
});
it('shows clinician targets and handover as source notes, separate from system recommendations',()=>{
 render(<ICUFlowsheet items={items()} onInspect={vi.fn()}/>);fireEvent.change(screen.getByLabelText('Flowsheet section'),{target:{value:'goals'}});
 expect(screen.getByRole('button',{name:'Chart source fs-GOAL revision 1'})).toHaveTextContent('not a ClinRx-recommended target');
 expect(screen.getByRole('button',{name:'Chart source fs-HANDOVER revision 1'})).toHaveTextContent('suspect source quality');
 expect(screen.getByText(/source-recorded clinician notes and targets/)).toBeInTheDocument();
});
it('links baseline and subsequent assessment records without calculating response or replacing missing originals',()=>{
 const sources=items(),item=sources.find(i=>i.fact.id==='fs-FLUID-ASSESSMENT')!,onInspect=vi.fn();
 render(<AssessmentContext item={item} items={sources} onInspect={onInspect}/>);
 const button=screen.getByRole('button',{name:/fs-CO-15 \/ 1/});fireEvent.click(button);
 expect(onInspect).toHaveBeenCalledWith(sources.find(i=>i.fact.id==='fs-CO-15'),button);
 expect(screen.getByRole('region',{name:'Recorded intervention assessment'})).toHaveTextContent('No response, change percentage or causal conclusion is calculated');
 expect(exactLinked(item,sources.filter(i=>i.fact.id!=='m7-CO'),{kind:'circulatory_cardiac',id:'m7-CO',version:'1'})).toBeNull();
});
it('recognizes only the explicit versioned synthetic chart namespace',()=>{
 const source=items().find(i=>i.fact.id==='fs-IO-output_urine-15')!;expect(chartEntry(source)!.section).toBe('fluids');
 record(record(source.fact.description).coding).namespace='foreign-namespace';expect(chartEntry(source)).toBeNull();
});

it('retains top-level assessment and signal quality rather than labeling it missing',()=>{
 const sources=items();
 for(const id of ['fs-FLUID-ASSESSMENT','m7-PLR','m7-SIGNAL']){
  const item=sources.find(i=>i.fact.id===id)!;expect(quality(item)).toBe('unknown');expect(hasUncertainQuality(item)).toBe(true);
 }
 render(<ICUFlowsheet items={sources} onInspect={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText('Flowsheet section'),{target:{value:'all'}});
 expect(screen.getByRole('button',{name:'Chart source fs-FLUID-ASSESSMENT revision 1'})).toHaveTextContent('Quality: unknown');
});
