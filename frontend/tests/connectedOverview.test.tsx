import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within,waitFor} from '@testing-library/react';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
import fixture from './fixtures/rf2-api.json';
import {RF2Client,pin,type Evidence} from '../src/api/rf2Client';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {PatientOverview,patientOverviewModel} from '../src/demo/PatientOverview';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Existing evidence viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Existing editor remains mounted</p>}));
const original=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:original,configurable:true}));
afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();localStorage.clear();});
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b'};
const load=()=>new RF2Client(async()=>new Response(JSON.stringify(structuredClone(fixture.catalog)))).catalog(config.start,config.end);
it('groups readings without losing a source, altering its decimal text or inventing a current measurement',async()=>{
 const catalog=await load(),before=JSON.stringify(catalog);const model=patientOverviewModel(catalog,config);expect(model.valid).toBe(true);expect(model.findings.find(g=>g.label==='Creatinine')?.records).toHaveLength(2);expect(model.findings.flatMap(g=>g.records).map(e=>pin(e))).toEqual(expect.arrayContaining(catalog.items.map(e=>pin(e))));expect(model.findings.flatMap(g=>g.records)).toHaveLength(catalog.items.length);expect(JSON.stringify(catalog)).toBe(before);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);expect(screen.getAllByRole('heading',{name:'Creatinine'})).toHaveLength(1);const group=screen.getByRole('heading',{name:'Creatinine'}).closest('article')!;expect(group).toHaveTextContent('2 recorded sources');fireEvent.click(within(group).getByText('View recorded details'));expect(group).toHaveTextContent('1.00 mg/dL');expect(group).toHaveTextContent('2.000 mg/dL');expect(screen.getByText(/A combined clinical interpretation has not been generated/)).toBeVisible();
});
it.each(['patient','period','cutoff','laboratory-scope'] as const)('withholds mismatched %s context rather than presenting unrelated prior data',async change=>{
 const catalog=await load();const requested={...config};if(change==='patient')requested.patient='other';if(change==='period')requested.start='2026-10-07T08:00:00Z';if(change==='cutoff')catalog.cutoff.fact_watermark++;if(change==='laboratory-scope')catalog.combined.laboratory.scope.patient_id='other';
 render(<PatientOverview catalog={catalog} status="current" requested={requested} guarded={false}/>);expect(screen.getByRole('alert')).toHaveTextContent('Overview withheld');expect(screen.queryByRole('heading',{name:'Creatinine'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:/Open recorded source/})).not.toBeInTheDocument();
});
it('labels retained data and prevents stale source opening while keeping old values inspectable',async()=>{const catalog=await load(),history=vi.fn();render(<PatientOverview catalog={catalog} status="retained" requested={config} guarded={false} retrievalMessage="Request failed" transport={{history}}/>);expect(screen.getByRole('alert')).toHaveTextContent('Retained prior data — not confirmed current');for(const toggle of screen.getAllByText('View recorded details'))fireEvent.click(toggle);for(const button of screen.getAllByRole('button',{name:/Open recorded source/})){expect(button).toBeDisabled();fireEvent.click(button);}expect(history).not.toHaveBeenCalled();expect(screen.getByText('35.0000 mL',{selector:'strong'})).toBeVisible();});
it('uses one catalog load and direct exact-source history without legacy workflow destinations',async()=>{
 const catalog=await load(),source=catalog.items.find(e=>e.fact.concept_id==='synthetic-serum-creatinine')!;
 vi.stubEnv('VITE_SYNTHETIC_RF2','true');const send=vi.fn<typeof fetch>().mockImplementation(async(url,init)=>{
  if(String(url).includes('/synthetic-rf2?'))return new Response(JSON.stringify(structuredClone(fixture.catalog)));
  if(String(url).endsWith('/history')){const body=JSON.parse(String(init?.body));expect(body).toEqual({repository:source.repository,pins:[pin(source)]});return new Response(JSON.stringify({repository:source.repository,selected:pin(source),items:[source],execution_enabled:false}));}
  throw Error('Unexpected request');
 });vi.stubGlobal('fetch',send);
 render(<PatientWorkspace client={new RenalFluidClient('http://127.0.0.1:5201',config.patient,config.encounter)} entry={new EvidenceEntryClient()} config={config}/>);
 const overview=await screen.findByRole('region',{name:'Connected patient overview'});await within(overview).findByRole('heading',{name:'Creatinine'});expect(send).toHaveBeenCalledTimes(1);for(const name of ['Source entry and reassessment','Compare notes','Handover','Renal charting and handover'])expect(screen.queryByRole('button',{name})).not.toBeInTheDocument();const group=within(overview).getByRole('heading',{name:'Creatinine'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));const trigger=within(group).getByRole('button',{name:`Open recorded source ${source.fact.id} / ${source.fact.revision}`});fireEvent.click(trigger);
 const dialog=await screen.findByRole('dialog',{name:'Creatinine'});await waitFor(()=>expect(within(dialog).queryByRole('status')).not.toBeInTheDocument());expect(dialog).toHaveTextContent('1.00 mg/dL');expect(send).toHaveBeenCalledTimes(2);fireEvent.click(within(dialog).getByRole('button',{name:'Close source details'}));expect(group.querySelector('details')).toHaveAttribute('open');expect(trigger).toHaveFocus();fireEvent.click(trigger);await waitFor(()=>expect(screen.getByRole('dialog',{name:'Creatinine'})).toBeVisible());expect(within(screen.getByRole('dialog')).getByRole('heading',{name:'Creatinine'})).toHaveFocus();
});
it('keeps the selected source visible if its history fails without substituting another record',async()=>{
 const catalog=await load(),source=catalog.items.find(e=>e.metadata?.chart?.category==='output_urine')!,history=vi.fn(async()=>{throw Error('Unavailable');});render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} transport={{history}}/>);const group=screen.getByRole('heading',{name:'Urine output'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));fireEvent.click(within(group).getByRole('button',{name:/Open recorded source/}));const dialog=await screen.findByRole('dialog',{name:'Urine output'});expect(await within(dialog).findByRole('alert')).toHaveTextContent('no different version was substituted');expect(dialog).toHaveTextContent('35.0000 mL');expect(history).toHaveBeenCalledExactlyOnceWith(source);
});
it('ignores delayed history after closing a source and opening a different one',async()=>{
 const catalog=await load(),sources=catalog.items.filter(e=>e.fact.concept_id==='synthetic-serum-creatinine');let finish:(v:Evidence[])=>void=()=>{};const history=vi.fn().mockImplementationOnce(()=>new Promise<Evidence[]>(resolve=>{finish=resolve;})).mockResolvedValue([sources[1]]);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} transport={{history}}/>);const group=screen.getByRole('heading',{name:'Creatinine'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));fireEvent.click(within(group).getByRole('button',{name:`Open recorded source ${sources[0].fact.id} / ${sources[0].fact.revision}`}));fireEvent.click(screen.getByRole('button',{name:'Close source details'}));fireEvent.click(within(group).getByRole('button',{name:`Open recorded source ${sources[1].fact.id} / ${sources[1].fact.revision}`}));const dialog=await screen.findByRole('dialog',{name:'Creatinine'});await waitFor(()=>expect(within(dialog).queryByRole('status')).not.toBeInTheDocument());finish([sources[0]]);await waitFor(()=>expect(dialog).toHaveTextContent('2.000 mg/dL'));expect(dialog).not.toHaveTextContent('1.00 mg/dL');
});
