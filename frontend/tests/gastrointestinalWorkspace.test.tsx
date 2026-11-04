import {expect,it,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import record from './fixtures/gastrointestinal-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import {GastrointestinalWorkspace} from '../src/gastrointestinal/GastrointestinalWorkspace';
import {PatientOverview,patientOverviewModel} from '../src/demo/PatientOverview';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
beforeEach(()=>localStorage.clear());
it('automatically shows the same original finding in GI and patient overview without duplicating the source',()=>{
 const c=structuredClone(fixture.catalog) as unknown as Catalog;c.gastrointestinal_records=[{repository:c.repository,fact:structuredClone(record),canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:record.kind,id:record.id,version:'1'},superseded:false,metadata:null} as Evidence];
 const before=JSON.stringify(c);const view=render(<GastrointestinalWorkspace catalog={c} requested={requested} current loading={false} onRefresh={async()=>{}}/>);
 expect(screen.getByText('Nausea reduced; no vomiting reported.')).toBeVisible();expect(screen.getByRole('button',{name:'Record finding'})).toBeEnabled();fireEvent.click(screen.getByRole('tab',{name:'Results & trends'}));expect(within(screen.getByRole('tabpanel',{name:'Results & trends'})).getByText(/No mapped GI\/liver results/)).toBeVisible();
 const overview=patientOverviewModel(c,requested);expect(overview.valid).toBe(true);expect(overview.courseSections.find(s=>s.label==='Gastrointestinal & liver')?.events[0].evidence.fact.id).toBe(record.id);expect(JSON.stringify(c)).toBe(before);view.unmount();render(<PatientOverview catalog={c} status="current" requested={requested} guarded={false}/>);expect(within(screen.getByRole('region',{name:'Gastrointestinal & liver'})).getAllByText('Nausea reduced; no vomiting reported.',{exact:true})[0]).toBeVisible();
});
