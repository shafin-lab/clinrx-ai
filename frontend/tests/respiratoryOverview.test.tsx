import {expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import record from './fixtures/respiratory-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import type {RespiratoryRecord} from '../src/respiratory/respiratoryTypes';
import {respiratoryModel} from '../src/respiratory/respiratoryModel';
import {RespiratoryBedsideOverview} from '../src/respiratory/RespiratoryBedsideOverview';

const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
function model(){
 const catalog=structuredClone(fixture.catalog) as unknown as Catalog,fact=structuredClone(record) as unknown as RespiratoryRecord;
 const evidence:Evidence={repository:catalog.repository,fact,canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:catalog.repository,ingestion_sequence:1},cutoff:catalog.cutoff.fact_watermark,terminal_reference:{kind:fact.kind,id:fact.id,version:fact.revision},superseded:false,metadata:null};
 return respiratoryModel({...catalog,items:[],respiratory_records:[evidence]},requested);
}
it('presents four bedside questions with explicit gaps and no automatic gas selection',()=>{
 render(<RespiratoryBedsideOverview model={model()} current onNavigate={vi.fn()}/>);
 for(const name of ['Breathing support','Blood gas','Lung mechanics','Review plan'])expect(screen.getByRole('heading',{name})).toBeVisible();
 expect(screen.getByText('Choose a sample')).toBeVisible();expect(screen.getByText('Not assessed')).toBeVisible();
 expect(screen.queryByText('7.30')).not.toBeInTheDocument();expect(screen.queryByText(/normal ventilation/i)).not.toBeInTheDocument();
});
it('shows only the explicitly selected gas with specimen, collection time and original settings',()=>{
 const m=model(),selected=m.samples[0];selected.record.context.specimen_id='arterial-1';
 render(<RespiratoryBedsideOverview model={m} selected={selected} current onNavigate={vi.fn()}/>);
 const gas=within(screen.getByRole('region',{name:'Blood gas'}));
 expect(gas.getByText('7.30')).toBeVisible();expect(gas.getByText(/arterial/i)).toBeVisible();expect(gas.getByText(/09:00/)).toBeVisible();expect(gas.getByText('40 %')).toBeVisible();
 expect(screen.queryByText(/ARDS diagnosed/i)).not.toBeInTheDocument();
});
it('suppresses selected values and old review conclusions when current evidence is unconfirmed',()=>{
 const m=model();render(<RespiratoryBedsideOverview model={m} selected={m.samples[0]} current={false} review={{signature:m.signature,reviewer:'Doctor',rationale:'Old conclusion',nextReview:'After gas'}} onNavigate={vi.fn()}/>);
 expect(screen.queryByText('7.30')).not.toBeInTheDocument();expect(screen.queryByText('Old conclusion')).not.toBeInTheDocument();expect(screen.getAllByText('Evidence unconfirmed')).toHaveLength(4);
});
it('does not promote legacy source setting presence to independently confirmed alignment',()=>{
 const m=model(),selected={...m.samples[0],legacy:true};selected.record.context.settings_confirmed_at_sample=null;
 render(<RespiratoryBedsideOverview model={m} selected={selected} current onNavigate={vi.fn()}/>);
 expect(screen.getByText(/Alignment not independently confirmed/)).toBeVisible();expect(screen.getByText('40 %')).toBeVisible();
});
it('uses a matching clinician review and withholds one from a different snapshot',()=>{
 const m=model(),review={signature:m.signature,reviewer:'Dr Rao',rationale:'Review cough and secretion burden',nextReview:'After SBT'};
 const view=render(<RespiratoryBedsideOverview model={m} current review={review} onNavigate={vi.fn()}/>);
 expect(screen.getByText('Review cough and secretion burden')).toBeVisible();expect(screen.getByText(/Dr Rao/)).toBeVisible();expect(screen.getByText(/After SBT/)).toBeVisible();
 view.rerender(<RespiratoryBedsideOverview model={m} current review={{...review,signature:'old'}} onNavigate={vi.fn()}/>);expect(screen.queryByText('Review cough and secretion burden')).not.toBeInTheDocument();expect(screen.getByText('Not assessed')).toBeVisible();
});
it('links each bedside question to its existing detailed area',()=>{
 const onNavigate=vi.fn();render(<RespiratoryBedsideOverview model={model()} current onNavigate={onNavigate}/>);
 for(const label of ['Inspect breathing support','Choose or review blood gas','Inspect lung mechanics','Open respiratory review plan'])fireEvent.click(screen.getByRole('button',{name:label}));
 expect(onNavigate.mock.calls.map(c=>c[0])).toEqual(['course','physiology','physiology','review']);
});
it('keeps multiple support records explicit rather than choosing one as current',()=>{
 const m=model(),base=m.samples[0].evidence[0];
 m.items=[...m.items,...['support-a','support-b'].map(id=>({...base,fact:{...base.fact,id,category:'support',title:id}} as Evidence))];
 render(<RespiratoryBedsideOverview model={m} current onNavigate={vi.fn()}/>);
 expect(screen.getByText('2 support records')).toBeVisible();expect(screen.getByText(/No support record is selected as current/)).toBeVisible();
});
it('keeps postoperative failure, prevention and deterioration as different contexts',()=>{
 render(<RespiratoryBedsideOverview model={model()} current onNavigate={vi.fn()}/>);
 fireEvent.click(screen.getByText('Terms and postoperative context'));
 for(const text of ['Postoperative respiratory failure','Prevention after planned extubation','Deterioration after extubation'])expect(screen.getByText(text,{exact:true})).toBeVisible();
});
it('does not present a venous component as a capillary measurement',()=>{
 const m=model(),selected=m.samples[0];selected.record.context.sample_type='capillary';selected.record.measurements.find(x=>x.concept==='paco2')!.concept='venous_pco2';
 render(<RespiratoryBedsideOverview model={m} selected={selected} current onNavigate={vi.fn()}/>);
 expect(within(screen.getByRole('region',{name:'Blood gas'})).queryByText('50 mmHg')).not.toBeInTheDocument();
});
