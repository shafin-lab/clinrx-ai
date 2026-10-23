// @vitest-environment-options {"url":"http://127.0.0.1:5225/"}
import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {weightDraft,weightSession,weightStorageKey} from '../src/demo/weightRecovery';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Mounted evidence viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Mounted legacy editor</p>}));
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));
afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();localStorage.clear();window.history.replaceState(null,'','/');});
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b',hosted:true};
function mount(next=false){
 vi.stubEnv('VITE_SYNTHETIC_RF2','true');vi.stubEnv('VITE_SYNTHETIC_AUTHORING','true');vi.stubEnv('VITE_SYNTHETIC_WEIGHT_ENTRY','true');
 let reads=0;const send=vi.fn<typeof fetch>(async(url)=>{if(String(url).includes('/synthetic-rf2?'))return new Response(JSON.stringify(structuredClone(next&&reads++?fixture.comparison_catalog:fixture.catalog)));throw Error('No additional API operation expected');});vi.stubGlobal('fetch',send);
 return {send,...render(<PatientWorkspace client={new RenalFluidClient('http://127.0.0.1:5225',config.patient,config.encounter)} entry={new EvidenceEntryClient()} config={config}/>)};
}
const hemo=()=>fireEvent.click(screen.getByRole('button',{name:'Cardiovascular system'}));
const overview=()=>fireEvent.click(screen.getByRole('button',{name:'Patient overview'}));
function fill(){for(const [label,value] of [['Next step','perfusion'],['Reviewer','Integration tester'],['Rationale','Shared source review'],['Next review plan','After repeat assessment']])fireEvent.change(screen.getByLabelText(label),{target:{value}});}
it('uses one shared catalog and retains the M7 session review across in-page view changes',async()=>{
 const {send}=mount();await screen.findByRole('heading',{name:'Creatinine'});hemo();await screen.findByRole('heading',{name:'Cardiovascular system'});expect(screen.queryByRole('region',{name:'Connected patient overview'})).not.toBeInTheDocument();
 fill();fireEvent.click(screen.getByRole('button',{name:'Record session review'}));await screen.findByRole('region',{name:'Session review records'});expect(screen.getByRole('region',{name:'Session review records'})).toHaveTextContent('Shared source review');overview();await screen.findByRole('heading',{name:'Creatinine'});hemo();expect(screen.getByRole('region',{name:'Session review records'})).toHaveTextContent('Shared source review');expect(send).toHaveBeenCalledTimes(1);
 expect(screen.queryByRole('link',{name:/protected review tools/i})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Compare notes'})).not.toBeInTheDocument();
});
it('invalidates an M7 draft after the shared weight/catalog snapshot changes without rebasing its text',async()=>{
 const {send}=mount(true);await screen.findByRole('heading',{name:'Creatinine'});hemo();fill();overview();fireEvent.click(screen.getByRole('button',{name:'Refresh records'}));await screen.findByRole('button',{name:'Add information'});await screen.findByText(/recorded assertions or source reports are available together\./);hemo();expect(screen.getByLabelText('Rationale')).toHaveValue('Shared source review');expect(screen.getByRole('alert')).toHaveTextContent('Evidence changed while this draft was open');fireEvent.click(screen.getByRole('button',{name:'Record session review'}));expect(screen.queryByRole('region',{name:'Session review records'})).not.toBeInTheDocument();expect(send).toHaveBeenCalledTimes(2);
});
it('preserves exact pending weight recovery while visiting M7 and returning to the overview',async()=>{
 const scope={patient:config.patient,encounter:config.encounter,repository:fixture.weight.repository},session=weightSession(scope);session.form={amount:'70.0000',unit:'kg',point:'',acquisition:'measured',actor:'Recovery tester',method:'Bed scale',context:'Synthetic bedside weighing',uncertainty:'Not clinically validated',reason:'New weighing episode'};session.pending=weightDraft(session);const raw=JSON.stringify(session);localStorage.setItem(weightStorageKey(scope),raw);
 const {send}=mount();await screen.findByRole('heading',{name:'Creatinine'});hemo();overview();fireEvent.click(screen.getByRole('button',{name:'Add information'}));fireEvent.click(within(screen.getByRole('dialog',{name:'Add information'})).getByRole('button',{name:'Recorded weight'}));expect(screen.getByRole('dialog')).toHaveTextContent('exact pending request');expect(screen.getByRole('button',{name:'Check saved result'})).toBeEnabled();expect(localStorage.getItem(weightStorageKey(scope))).toBe(raw);expect(send).toHaveBeenCalledTimes(1);
});
it('lands an authoring deep link in the shared M7 view and returns to the existing overview without a second load',async()=>{
 window.history.replaceState(null,'','/?workspace=hemodynamics');const {send}=mount();await screen.findByRole('heading',{name:'Cardiovascular system'});await screen.findByRole('button',{name:'Record session review'});overview();await screen.findByRole('heading',{name:'Creatinine'});expect(send).toHaveBeenCalledTimes(1);
});
it('retains the M7 session with one shared assessment catalog and a separate explicit daily chart read',async()=>{
 const {send}=mount();await screen.findByRole('heading',{name:'Creatinine'});hemo();fill();fireEvent.click(screen.getByRole('button',{name:'Record session review'}));await screen.findByRole('region',{name:'Session review records'});
 fireEvent.click(screen.getByRole('button',{name:'Antimicrobials'}));await screen.findByRole('heading',{name:'Antimicrobial reference library'}, {timeout:15000});fireEvent.change(await screen.findByLabelText('Find a medicine'),{target:{value:'teicoplanin'}});
 fireEvent.click(screen.getByRole('button',{name:/^Teicoplanin/}));expect(within(screen.getByRole('complementary',{name:'Antibiotic reference drawer'})).getByRole('heading',{name:'Teicoplanin'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Open kidney evidence ↗'}));await screen.findByRole('heading',{name:'Renal system'});hemo();expect(screen.getByRole('region',{name:'Session review records'})).toHaveTextContent('Shared source review');expect(send).toHaveBeenCalledTimes(2);expect(String(send.mock.calls[1][0])).toContain('2026-10-09');
});
