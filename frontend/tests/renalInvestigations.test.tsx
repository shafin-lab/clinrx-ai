import {expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/renalFluid.json';
import type {RenalFluidState} from '../src/api/renalFluidTypes';
import {renalBedsideModel} from '../src/renal/renalBedsideModel';
import {RenalInvestigations,renalInvestigationPanels,renalInvestigationSources} from '../src/renal/RenalInvestigations';
const scope={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const model=()=>renalBedsideModel(structuredClone(fixture) as unknown as RenalFluidState,scope);
it('makes all five core fields visible without inferring absent test results',()=>{
 render(<RenalInvestigations sources={model().sources} current onOpen={vi.fn()}/>);const core=screen.getByRole('list',{name:'Core kidney investigation fields'});for(const label of ['Urea / BUN','Creatinine','Sodium','Potassium','Urine routine'])expect(within(core).getByText(label)).toBeInTheDocument();expect(within(core).getAllByText('Result feed not connected')).toHaveLength(4);expect(within(core).getByRole('button',{name:'Inspect sources for Creatinine'})).toBeEnabled();
});
it('opens original creatinine evidence without choosing the latest or calculating a trend',()=>{
 const open=vi.fn();render(<RenalInvestigations sources={model().sources} current onOpen={open}/>);fireEvent.click(screen.getByRole('button',{name:'Inspect sources for Creatinine'}));expect(open).toHaveBeenCalledWith('creatinine');expect(screen.queryByText(/improv|normal renal|stage [123]/i)).not.toBeInTheDocument();
});
it('provides urine chemistry and measured osmolality options with distinct sample meanings',()=>{
 render(<RenalInvestigations sources={model().sources} current onOpen={vi.fn()}/>);fireEvent.click(screen.getByText('Urine studies and osmolality'));const list=screen.getByRole('list',{name:'Urine studies and osmolality'});for(const label of ['Urine sodium','Urine osmolality','Measured serum osmolality','Urine creatinine','Urine urea','Urine microscopy','Urine ACR','Urine PCR'])expect(within(list).getByText(label)).toBeInTheDocument();expect(screen.getByText(/Measured osmolality \(mOsm\/kg\)/)).toHaveTextContent('calculated osmolarity (mOsm/L)');expect(within(list).queryByRole('button')).not.toBeInTheDocument();
});
it('does not mistake urine output, narrative mentions or a blood-gas result for a urine assay',()=>{
 const sources=model().sources;for(const test of renalInvestigationPanels.flatMap(p=>p.tests).filter(t=>!t.source))expect(renalInvestigationSources(test,sources)).toEqual([]);const gas=renalInvestigationPanels[1].tests.find(t=>t.id==='bicarbonate')!;expect(renalInvestigationSources(gas,sources).every(s=>s.fluid?.fact.concept==='bicarbonate')).toBe(true);
});
it('blocks source inspection and labels data unconfirmed during retrieval failure',()=>{
 render(<RenalInvestigations sources={model().sources} current={false} onOpen={vi.fn()}/>);expect(screen.getByRole('button',{name:'Inspect sources for Creatinine'})).toBeDisabled();expect(screen.getAllByText('Current results unconfirmed').length).toBeGreaterThan(0);
});
it('does not claim a connected assay has been measured when no source was supplied',()=>{
 render(<RenalInvestigations sources={[]} current onOpen={vi.fn()}/>);expect(screen.getAllByText('No result supplied').length).toBeGreaterThan(0);expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
