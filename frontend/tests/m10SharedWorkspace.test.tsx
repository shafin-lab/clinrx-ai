import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {hash,stable} from '../src/api/rf2Client';
import type {M10Command,M10Item} from '../src/transfusion/types';
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

it.each(['success','failure'] as const)('keeps the exact confirmed save dialog and guard through a pending shared refresh and its %s outcome',async outcome=>{
 const saves:M10Command[]=[],validations:M10Command[]=[];let reads=0,renalReads=0,finishRefresh!:(response:Response)=>void,savedItem:M10Item|undefined;
 const snapshot=(updated=false)=>({repository:fixture.catalog.repository,cutoff:(updated?fixture.comparison_catalog:fixture.catalog).cutoff,patient_id:config.patient,encounter_id:config.encounter,review_start:config.start,review_end:config.end,items:updated&&savedItem?[savedItem]:[],evidence:[],totals:{groups:[],complete:true},execution_enabled:false});
 vi.stubGlobal('fetch',vi.fn<typeof fetch>(async(input,init)=>{const url=new URL(String(input),'http://localhost');
  if(url.pathname.endsWith('/synthetic-rf2')){renalReads++;return new Response(JSON.stringify(saves.length?fixture.comparison_catalog:fixture.catalog));}
  if(url.pathname.endsWith('/synthetic-m10/profiles'))return new Response(JSON.stringify({devices:[],protocols:[]}));
  if(url.pathname.endsWith('/synthetic-m10')){reads++;if(reads===1)return new Response(JSON.stringify(snapshot()));return new Promise(resolve=>{finishRefresh=resolve;});}
  if(url.pathname.endsWith('/synthetic-m10/validate')||url.pathname.endsWith('/synthetic-m10/save')){
   const command=JSON.parse(String(init?.body)) as M10Command,request_canonical=stable(command),request_digest=await hash(request_canonical);
   if(url.pathname.endsWith('/validate')){validations.push(command);return new Response(JSON.stringify({status:'validated',request_canonical,request_digest,execution_enabled:false}));}
   saves.push(command);const fact={kind:command.kind,id:command.id,revision:command.revision,binding:{target:{patient_id:command.patient_id,encounter_id:command.encounter_id}},source_record:command.source_record,source_issuer:command.source_issuer,data:command.data},canonical_fact=stable(fact),digest=await hash(canonical_fact);savedItem={fact,canonical_fact,digest,ingestion:8};return new Response(JSON.stringify({status:'saved',request_canonical,request_digest,execution_enabled:false,...savedItem}));
  }
  throw Error('Unexpected API request: '+url.pathname);
 }));
 render(<PatientWorkspace client={new RenalFluidClient('http://localhost',config.patient,config.encounter)} entry={new EvidenceEntryClient()} config={config}/>);
 await screen.findByText('0 administration records · 0 TEG / ROTEM reports');fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Record product or event'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Record product or event'}));const dialog=screen.getByRole('dialog',{name:'Record M10 information'});
 for(const [label,value] of [['Source record ID','one-confirmed-bag'],['Source institution or issuer','Synthetic bank'],['Documented by','Synthetic clinician'],['Indication','Synthetic recorded bleeding'],['Delivered count','2'],['Actual administered volume (mL)','125']])fireEvent.change(within(dialog).getByLabelText(label),{target:{value}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Review record'}));fireEvent.click(await within(dialog).findByRole('button',{name:'Confirm and save record'}));await waitFor(()=>expect(reads).toBe(2));
 expect(screen.getByRole('dialog',{name:'Record M10 information'})).toBe(dialog);expect(within(dialog).getByText('Record saved. Refreshing the shared patient evidence…')).toBeVisible();expect(screen.getByRole('button',{name:'Patient overview'})).toBeDisabled();expect(within(dialog).getByRole('button',{name:'Record another transfusion'})).toBeDisabled();expect(screen.getByRole('button',{name:'Record product or event'})).toBeDisabled();expect(saves).toHaveLength(1);expect(saves[0]).toEqual(validations[0]);
 await act(async()=>{finishRefresh(outcome==='success'?new Response(JSON.stringify(snapshot(true))):new Response('{}',{status:503}));});
 await within(dialog).findByText('Record saved.');expect(screen.getByRole('dialog',{name:'Record M10 information'})).toBe(dialog);expect(within(dialog).queryByText(/evidence refreshed/i)).not.toBeInTheDocument();expect(within(dialog).queryByRole('button',{name:'Review record'})).not.toBeInTheDocument();expect(within(dialog).queryByRole('button',{name:'Confirm and save record'})).not.toBeInTheDocument();expect(within(dialog).queryByLabelText('Source record ID')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Patient overview'})).toBeDisabled();expect(saves).toHaveLength(1);expect(reads).toBe(2);expect(renalReads).toBe(2);
 if(outcome==='success')expect(within(dialog).getByRole('button',{name:'Record another transfusion'})).toBeEnabled();else{expect(await screen.findByText(/hematologic evidence read is unconfirmed or unavailable/)).toBeVisible();expect(within(dialog).getByRole('button',{name:'Record another transfusion'})).toBeDisabled();}
 fireEvent.click(within(dialog).getByRole('button',{name:'Done'}));expect(screen.queryByRole('dialog',{name:'Record M10 information'})).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Patient overview'})).toBeEnabled();if(outcome==='failure')expect(screen.getByRole('button',{name:'Record product or event'})).toBeDisabled();expect(saves).toHaveLength(1);
},15000);
