import {expect,it,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import source from './fixtures/respiratory-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import type {RespiratoryRecord} from '../src/respiratory/respiratoryTypes';
import {respiratoryModel} from '../src/respiratory/respiratoryModel';
import {RespiratoryWorkspace} from '../src/respiratory/RespiratoryWorkspace';

const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
function catalog(){
 const c=structuredClone(fixture.catalog) as unknown as Catalog;
 const f=structuredClone(source) as unknown as RespiratoryRecord;
 f.context.specimen_id='arterial-specimen-1';
 for(const m of f.measurements)if(m.result.kind==='numeric')m.result.unit={namespace:'UCUM',code:m.concept==='ph'?'1':m.concept==='fio2'?'%':'mmHg',version:null,raw_display:m.concept==='ph'?'1':m.concept==='fio2'?'%':'mmHg'};
 const e:Evidence={repository:c.repository,fact:f,canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:f.kind,id:f.id,version:f.revision},superseded:false,metadata:null};
 return {...c,items:[],respiratory_records:[e]};
}
function props(c:Catalog){return {catalog:c,requested,loading:false,current:true,onRefresh:vi.fn().mockResolvedValue(undefined)};}
function openPhysiology(){fireEvent.click(screen.getByRole('tab',{name:'Blood gases & physiology'}));}
function chooseSample(c:Catalog){fireEvent.change(screen.getByLabelText('Sample or measurement set'),{target:{value:respiratoryModel(c,requested).samples[0].id}});}

it('rejects different review instants that share a JavaScript millisecond',()=>{
 const c=catalog();c.combined.context.scope.review_start='2026-10-08T08:00:00.000001Z';
 expect(respiratoryModel(c,{...requested,start:'2026-10-08T08:00:00.000002Z'}).valid).toBe(false);
});
it('accepts equivalent exact offsets and trailing fractional zeroes',()=>{
 const c=catalog();c.combined.context.scope.review_start='2026-10-08T08:00:00.001000Z';
 expect(respiratoryModel(c,{...requested,start:'2026-10-08T13:30:00.001+05:30'}).valid).toBe(true);
});
it('keeps observations a microsecond after review end out of the current period',()=>{
 const c=catalog(),f=c.respiratory_records[0].fact as RespiratoryRecord;f.times.collected.value='2026-10-08T10:00:00.000001Z';
 const model=respiratoryModel(c,requested);expect(model.items).toHaveLength(0);expect(model.contextItems).toHaveLength(1);
});
it('keeps day and approximate collection times as context rather than exact observations',()=>{
 const c=catalog(),f=c.respiratory_records[0].fact as RespiratoryRecord;f.times.collected.precision='approximate';
 const model=respiratoryModel(c,requested);expect(model.items).toHaveLength(0);expect(model.contextItems).toHaveLength(1);
});
it.each(['bounded','not_recorded'] as const)('does not use report time for a gas with %s collection time',state=>{
 const c=catalog(),f=c.respiratory_records[0].fact as RespiratoryRecord;
 f.times.collected={status:state==='bounded'?'known':'not_recorded',precision:state==='bounded'?'bounded':'unknown',value:null,lower:state==='bounded'?'2026-10-08T08:45:00Z':null,upper:state==='bounded'?'2026-10-08T09:15:00Z':null,uncertainty:null};
 const model=respiratoryModel(c,requested);expect(model.samples).toHaveLength(0);expect(model.contextItems).toHaveLength(1);
});
it('requires explicit sample selection before displaying arithmetic',()=>{
 const c=catalog();render(<RespiratoryWorkspace {...props(c)}/>);openPhysiology();
 expect(screen.getByLabelText('Sample or measurement set')).toHaveValue('');
 expect(screen.queryByText('Calculations supported by this evidence')).not.toBeInTheDocument();
 chooseSample(c);expect(screen.getByText('Calculations supported by this evidence')).toBeVisible();expect(screen.getByText('Acidemia')).toBeVisible();
});
it('withholds arithmetic and sample actions when a selected view becomes unconfirmed',()=>{
 const c=catalog(),p=props(c),view=render(<RespiratoryWorkspace {...p}/>);openPhysiology();chooseSample(c);expect(screen.getByText('Acidemia')).toBeVisible();
 view.rerender(<RespiratoryWorkspace {...p} current={false}/>);
 expect(screen.queryByText('Acidemia')).not.toBeInTheDocument();expect(screen.getByLabelText('Sample or measurement set')).toBeDisabled();
 for(const button of screen.getAllByRole('button',{name:'Review this sample'}))expect(button).toBeDisabled();
});
it('treats a retrieval error as unconfirmed even if a caller leaves current true',()=>{
 const c=catalog();render(<RespiratoryWorkspace {...props(c)} error="Refresh failed"/>);openPhysiology();
 expect(screen.getByRole('button',{name:'Add respiratory information'})).toBeDisabled();expect(screen.getByLabelText('Sample or measurement set')).toBeDisabled();
 expect(screen.queryByText('Calculations supported by this evidence')).not.toBeInTheDocument();
});
