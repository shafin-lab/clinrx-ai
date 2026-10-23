import {beforeAll,afterAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {hash,RF2Client,stable,type Evidence} from '../src/api/rf2Client';
import {PatientOverview} from '../src/demo/PatientOverview';

const priorCrypto=globalThis.crypto;
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:priorCrypto,configurable:true}));
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
async function catalog(){return new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog(requested.start,requested.end);}
async function enter(){
 fireEvent.click(screen.getByRole('button',{name:'Add information'}));
 fireEvent.click(screen.getByRole('button',{name:'Laboratory result'}));
 const dialog=await screen.findByRole('dialog',{name:'Record a laboratory source result'});
 for(const [label,value] of [['Issuer namespace','lab.test.system'],['Source report ID','report-123'],['Source version','v1'],['Specimen type','Serum'],['Source specimen ID','spec-1'],['Test code','SOD'],['Source test display','Sodium'],['Result exactly as reported','138.00'],['Source unit','mmol/L'],['Collected at · source time with offset','2026-10-08T09:00:00+05:30'],['Reported at · source time with offset','2026-10-08T09:15:00+05:30'],['Available at · source time with offset','2026-10-08T09:16:00+05:30']])fireEvent.change(within(dialog).getByLabelText(label),{target:{value}});
 fireEvent.change(within(dialog).getByLabelText('Shared mapping'),{target:{value:'sodium'}});
 fireEvent.change(within(dialog).getByLabelText('Transcribed by'),{target:{value:'Synthetic reviewer'}});
 return dialog;
}
const result=(fact:Record<string,unknown>):Evidence=>({repository:'synthetic-repository',fact:fact as Evidence['fact'],canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:'synthetic-repository',ingestion_sequence:2} as Evidence['ingestion'],cutoff:2,terminal_reference:{kind:'laboratory_report',id:String(fact.id),version:String(fact.revision)},superseded:false,metadata:null});

it('records exact source value, unit and original timestamp offset through Add information',async()=>{
 const c=await catalog(),onRefresh=vi.fn().mockResolvedValue(undefined),send=vi.fn(async(_url:string,init?:RequestInit)=>{const fact=JSON.parse(String(init?.body)),canonical_fact=stable(fact),digest=await hash(canonical_fact);return new Response(JSON.stringify({repository:c.repository,fact,canonical_fact,digest,ingestion:{repository_id:c.repository,ingestion_sequence:2,ingested_at:'2026-10-08T04:00:00Z',payload_version:1},cutoff:2,terminal_reference:{kind:'laboratory_report',id:fact.id,version:fact.revision},superseded:false,metadata:null}));}),client=new RF2Client(send as typeof fetch);
 render(<PatientOverview catalog={c} status="current" requested={requested} guarded={false} onRefresh={onRefresh} laboratoryTransport={{importLaboratory:(repository,fact)=>client.importLaboratory(repository,fact)}}/>);
 const dialog=await enter();fireEvent.click(within(dialog).getByRole('button',{name:'Save source report'}));
 await waitFor(()=>expect(send).toHaveBeenCalledTimes(1));
 const report=JSON.parse(String(send.mock.calls[0][1]?.body)) as Record<string,any>;
 expect(report.kind).toBe('laboratory_report');expect(report.revision).toBe('v1');expect(report.source_identity.source_report_id).toBe('report-123');
 expect(report.times.collected.value).toBe('2026-10-08T09:00:00+05:30');expect(report.times.available.value).toBe('2026-10-08T09:16:00+05:30');
 expect(report.components[0].result.raw_value).toBe('138.00');expect(report.components[0].result.unit.raw_display).toBe('mmol/L');expect(report.components[0].mapped_concept).toBe('sodium');
 expect(report.binding.target).toMatchObject({patient_id:'synthetic-p1',encounter_id:'synthetic-e1'});expect(report.binding.verification.status).toBe('unresolved');
 await waitFor(()=>expect(onRefresh).toHaveBeenCalledTimes(1));
});

it('retries the same exact request after an uncertain response',async()=>{
 const c=await catalog(),importLaboratory=vi.fn().mockRejectedValueOnce(Error('Request timed out; completion is unconfirmed.')).mockImplementationOnce(async(_repository:string,fact:Record<string,unknown>)=>result(fact));
 render(<PatientOverview catalog={c} status="current" requested={requested} guarded={false} onRefresh={vi.fn().mockResolvedValue(undefined)} laboratoryTransport={{importLaboratory}}/>);
 const dialog=await enter();fireEvent.click(within(dialog).getByRole('button',{name:'Save source report'}));await screen.findByRole('alert');
 fireEvent.click(within(dialog).getByRole('button',{name:'Retry exact saved request'}));await waitFor(()=>expect(importLaboratory).toHaveBeenCalledTimes(2));
 expect(importLaboratory.mock.calls[1][1]).toEqual(importLaboratory.mock.calls[0][1]);
});
