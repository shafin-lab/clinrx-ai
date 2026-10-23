import {afterAll,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import record from './fixtures/respiratory-record.json';
import {RF2Client,type Catalog} from '../src/api/rf2Client';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {PatientOverview,patientOverviewModel} from '../src/demo/PatientOverview';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Existing source viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Existing source editor</p>}));
const previous=globalThis.crypto;const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:previous,configurable:true}));
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b'};
async function catalog(){const c=await new RF2Client(async()=>new Response(JSON.stringify(fixture.catalog))).catalog(requested.start,requested.end);return {...c,respiratory_records:[{repository:c.repository,fact:structuredClone(record),canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:record.kind,id:record.id,version:record.revision},superseded:false,metadata:null}]} as Catalog;}
it('includes original respiratory records in overview without losing existing source entries',async()=>{const c=await catalog(),m=patientOverviewModel(c,requested);expect(m.valid).toBe(true);expect(m.findings.flatMap(f=>f.records).some(e=>e.fact.kind==='respiratory_record')).toBe(true);render(<PatientOverview catalog={c} requested={requested} status="current" guarded={false}/>);expect(screen.getByRole('region',{name:'Respiratory and gas exchange'})).toBeVisible();expect(screen.getByRole('heading',{name:'M9 review'})).toBeVisible();});
it('opens M9 from the same patient navigation and preserves the kidney and antibiotic views',async()=>{vi.stubEnv('VITE_SYNTHETIC_RF2','true');const send=vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)));vi.stubGlobal('fetch',send);render(<PatientWorkspace config={requested} client={new RenalFluidClient('http://127.0.0.1:5201',requested.patient,requested.encounter)} entry={new EvidenceEntryClient()}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Respiratory & ABG'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Respiratory & ABG'}));expect(await screen.findByRole('heading',{name:'Respiratory & ABG'})).toBeVisible();expect(screen.getByRole('button',{name:'Kidney review'})).toBeVisible();expect(screen.getByRole('button',{name:'Antibiotic references'})).toBeVisible();vi.unstubAllGlobals();vi.unstubAllEnvs();});
