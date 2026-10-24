import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Evidence viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Source editor</p>}));
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b',hosted:true};
beforeEach(()=>{vi.stubEnv('VITE_SYNTHETIC_RF2','true');vi.stubEnv('VITE_SYNTHETIC_M10','true');vi.stubEnv('VITE_SYNTHETIC_ANTIBIOTICS','false');window.history.replaceState(null,'','/?workspace=overview');});
afterEach(()=>{cleanup();vi.unstubAllEnvs();vi.unstubAllGlobals();localStorage.clear();sessionStorage.clear();window.history.replaceState(null,'','/');});
// Full patient navigation and refresh use the existing 15s integration budget.
it('shares one bounded M10 catalog across overview, detail and back navigation, then refreshes once',async()=>{
 const reads:URL[]=[];let renalReads=0;
 vi.stubGlobal('fetch',vi.fn<typeof fetch>(async input=>{const url=new URL(String(input),'http://localhost');
  if(url.pathname.endsWith('/synthetic-rf2')){renalReads++;return new Response(JSON.stringify(fixture.catalog));}
  if(url.pathname.endsWith('/synthetic-m10/profiles'))return new Response(JSON.stringify({devices:[],protocols:[]}));
  if(url.pathname.endsWith('/synthetic-m10')){reads.push(url);return new Response(JSON.stringify({repository:fixture.catalog.repository,cutoff:fixture.catalog.cutoff,patient_id:config.patient,encounter_id:config.encounter,review_start:config.start,review_end:config.end,items:[],evidence:[],totals:{groups:[],complete:true},execution_enabled:false}));}
  throw Error('Unexpected API request: '+url.pathname);
 }));
 render(<PatientWorkspace client={new RenalFluidClient('http://localhost',config.patient,config.encounter)} entry={new EvidenceEntryClient()} config={config}/>);
 await screen.findByText('0 administration records · 0 TEG / ROTEM reports');expect(reads).toHaveLength(1);
 expect(reads[0].searchParams.get('repository')).toBe(fixture.catalog.repository);expect(reads[0].searchParams.get('cutoff')).toBe(String(fixture.catalog.cutoff.fact_watermark));expect(reads[0].searchParams.get('review_start')).toBe(config.start);expect(reads[0].searchParams.get('review_end')).toBe(config.end);
 fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Record product or event'})).toBeEnabled());expect(reads).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Patient overview'}));await screen.findByText('0 administration records · 0 TEG / ROTEM reports');expect(reads).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));fireEvent.click(screen.getByRole('button',{name:'Refresh evidence'}));await waitFor(()=>expect(reads).toHaveLength(2));await waitFor(()=>expect(screen.getByRole('button',{name:'Record product or event'})).toBeEnabled());expect(renalReads).toBe(2);
},15000);
