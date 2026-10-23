import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,pin,type Chart,type Draft,type Evidence,type Result} from '../src/api/rf2Client';
import {PatientOverview,patientOverviewModel} from '../src/demo/PatientOverview';
import {WeightEntryDialog} from '../src/demo/WeightEntryDialog';
import {decodeWeightRecovery,weightDraft,weightSession,weightStorageKey,type WeightRecovery} from '../src/demo/weightRecovery';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));afterEach(()=>localStorage.clear());
const scope={patient:'synthetic-p1',encounter:'synthetic-e1',repository:fixture.weight.repository};
const requested={patient:scope.patient,encounter:scope.encounter,start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const draftData=()=>{const s=weightSession(scope);s.form={amount:'70.0000',unit:'kg',point:'',acquisition:'measured',method:'Bed scale',context:'New bedside weighing',uncertainty:'Fluid retention recorded',actor:'Synthetic nurse',reason:'New weighing, not a copied record'};return s;};
const response=(status:Result['status'],evidence?:Evidence)=>({status,execution_enabled:false,...(evidence?{evidence}:{})}) as Result;
const action=()=>vi.fn<RF2Client['action']>().mockResolvedValue(response('validated'));
function mount(transport=action(),props:Partial<Parameters<typeof WeightEntryDialog>[0]>={}){const trigger=document.createElement('button');trigger.textContent='Entry trigger';document.body.append(trigger);return {action:transport,...render(<WeightEntryDialog scope={scope} currentScope={scope} current trigger={trigger} transport={{action:transport}} onRefresh={async()=>{}} onClose={()=>{}} {...props}/>)};}
function fill(){for(const [label,value] of [['Weight','70.0000'],['Recorded by','Synthetic nurse'],['Source context','New bedside weighing'],['Uncertainty or limitations','Fluid retention recorded'],['Reason for new entry','New weighing, not a copied record']])fireEvent.change(screen.getByLabelText(label),{target:{value}});fireEvent.change(screen.getByLabelText('How obtained'),{target:{value:'measured'}});}
async function review(){fireEvent.click(screen.getByRole('button',{name:'Review weight'}));await screen.findByRole('button',{name:'Save weight'});}
it('records exact decimal weight and unknown time without assuming a purpose or source key',()=>{
 const s=draftData(),d=weightDraft(s);expect(d.chart).toMatchObject({amount:'70.0000',unit:'kg',point:null,purpose:null,source_record:null,new_collection_reason:s.form.reason,start:null,end:null});expect(d.id).not.toBe(d.revision);
 s.form.amount='0';expect(weightDraft(s).chart?.amount).toBe('0');s.form.amount='7e1';expect(()=>weightDraft(s)).toThrow(/decimal/);s.form.amount='70';s.form.point='2026-10-08T10:00';expect(()=>weightDraft(s)).toThrow(/offset/);
});
it('reviews before saving and saves exactly once when clicked twice',async()=>{
 const a=action().mockResolvedValueOnce(response('validated')).mockResolvedValue(response('saved',fixture.weight as Evidence)),refresh=vi.fn(async()=>{});mount(a,{onRefresh:refresh});fill();await review();expect(a.mock.calls[0][0]).toBe('validate');
 const pending=a.mock.calls[0][1];expect(JSON.parse(localStorage.getItem(weightStorageKey(scope))!).pending).toEqual(pending);const save=screen.getByRole('button',{name:'Save weight'});fireEvent.click(save);fireEvent.click(save);await screen.findByRole('button',{name:'Done'});expect(a.mock.calls.map(c=>c[0])).toEqual(['validate','save']);expect(a.mock.calls[1][1]).toEqual(pending);expect(refresh).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Done'}));expect(localStorage.getItem(weightStorageKey(scope))).toBeNull();
});
it('invalidates review after editing and preserves an unsaved draft over remount',async()=>{
 const a=action(),r=mount(a);fill();await review();const original=a.mock.calls[0][1];fireEvent.click(screen.getByRole('button',{name:'Edit weight'}));fireEvent.change(screen.getByLabelText('Weight'),{target:{value:'71.2500'}});expect(screen.queryByRole('button',{name:'Save weight'})).not.toBeInTheDocument();r.unmount();mount(a);expect(screen.getByLabelText('Weight')).toHaveValue('71.2500');await review();expect(a.mock.calls[1][1].revision).not.toBe(original.revision);expect(a.mock.calls[1][1].chart?.amount).toBe('71.2500');
});
it('recovers a lost save response across reload using lookup before any further save',async()=>{
 const a=action().mockResolvedValueOnce(response('validated')).mockRejectedValueOnce(Error('response lost')).mockResolvedValueOnce(response('saved',fixture.weight as Evidence));const r=mount(a);fill();await review();const original=structuredClone(a.mock.calls[0][1]);fireEvent.click(screen.getByRole('button',{name:'Save weight'}));await screen.findByRole('button',{name:'Check saved result'});r.unmount();mount(a);expect(screen.queryByRole('button',{name:'Save weight'})).not.toBeInTheDocument();expect(a).toHaveBeenCalledTimes(2);fireEvent.click(screen.getByRole('button',{name:'Check saved result'}));await screen.findByRole('button',{name:'Done'});expect(a.mock.calls.map(c=>c[0])).toEqual(['validate','save','lookup']);expect(a.mock.calls[2][1]).toEqual(original);
});
it('requires explicit review and retry of the same request after lookup proves absent',async()=>{
 const s=draftData();s.pending=weightDraft(s);localStorage.setItem(weightStorageKey(scope),JSON.stringify(s));const a=action().mockResolvedValueOnce(response('absent')).mockResolvedValueOnce(response('validated')).mockResolvedValue(response('saved',fixture.weight as Evidence));mount(a);fireEvent.click(screen.getByRole('button',{name:'Check saved result'}));await screen.findByRole('button',{name:'Review same request for retry'});expect(a).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Review same request for retry'}));await screen.findByRole('button',{name:'Save weight'});fireEvent.click(screen.getByRole('button',{name:'Save weight'}));await screen.findByRole('button',{name:'Done'});expect(a.mock.calls.every(c=>JSON.stringify(c[1])===JSON.stringify(s.pending))).toBe(true);
});
it('keeps a confirmed save separate from failed overview refresh',async()=>{
 const a=action().mockResolvedValueOnce(response('validated')).mockResolvedValue(response('saved',fixture.weight as Evidence));mount(a,{onRefresh:async()=>{throw Error('Refresh failed');}});fill();await review();fireEvent.click(screen.getByRole('button',{name:'Save weight'}));await screen.findByText(/Saved confirmation retained/);expect(screen.getByRole('button',{name:'Done'})).toBeEnabled();expect(screen.queryByRole('button',{name:'Check saved result'})).not.toBeInTheDocument();
});
it('preserves correction ownership, source identity and full reason without altering the original',()=>{
 const original=structuredClone(fixture.weight) as Evidence,before=JSON.stringify(original),s=weightSession(scope,original);s.form.actor='Corrector';s.form.reason='Transcription error';s.form.amount='71.000';const d=weightDraft(s);expect(d.predecessor).toEqual(pin(original));expect(d.id).toBe(original.fact.id);expect(d.revision).not.toBe(original.fact.revision);expect(d.chart?.source_record).toEqual(original.metadata?.chart?.source_record);expect(d.reason).toBe('Transcription error');expect(JSON.stringify(original)).toBe(before);const historical={...original,superseded:true};expect(()=>weightSession(scope,historical)).toThrow(/original owner/);
});
it('blocks saving after scope change and does not refresh another patient when an in-flight save completes',async()=>{
 let complete:(value:Result)=>void=()=>{};const a=action().mockResolvedValueOnce(response('validated')).mockImplementationOnce(()=>new Promise(resolve=>{complete=resolve;})),refresh=vi.fn(async()=>{}),r=mount(a,{onRefresh:refresh});fill();await review();fireEvent.click(screen.getByRole('button',{name:'Save weight'}));r.rerender(<WeightEntryDialog scope={scope} currentScope={{...scope,patient:'other'}} current trigger={document.createElement('button')} transport={{action:a}} onRefresh={refresh} onClose={()=>{}}/>);await act(async()=>complete(response('saved',fixture.weight as Evidence)));expect(refresh).not.toHaveBeenCalled();expect(screen.getByText(/no other patient was refreshed/)).toBeInTheDocument();
});
it('retains malformed and concurrent recovery bytes and sends no write',async()=>{
 const key=weightStorageKey(scope);localStorage.setItem(key,'{"version":1,"version":1}');const a=action(),r=mount(a);expect(screen.getByRole('alert')).toHaveTextContent('Existing recovery bytes were preserved');expect(localStorage.getItem(key)).toBe('{"version":1,"version":1}');expect(a).not.toHaveBeenCalled();r.unmount();localStorage.clear();mount(a);fill();const other=JSON.stringify(draftData());localStorage.setItem(key,other);fireEvent.click(screen.getByRole('button',{name:'Review weight'}));await screen.findByText(/another tab changed it/);expect(localStorage.getItem(key)).toBe(other);expect(a).not.toHaveBeenCalled();
});
it('rejects a recovered request with altered owner, amount or duplicate members',()=>{
 const s=draftData();s.pending=weightDraft(s);expect(decodeWeightRecovery(JSON.stringify(s),scope)).toEqual(s);const mutated=structuredClone(s);mutated.pending!.chart!.amount='999';expect(()=>decodeWeightRecovery(JSON.stringify(mutated),scope)).toThrow();expect(()=>decodeWeightRecovery(JSON.stringify(s),{...scope,repository:crypto.randomUUID()})).toThrow();
});
it('retains a reviewed correction with legacy optional fields and restores focus after closing',async()=>{
 const source=structuredClone(fixture.weight) as Evidence;delete (source.metadata!.chart as Partial<Chart>).source_version;
 const s=weightSession(scope,source);s.form.actor='Corrector';s.form.reason='Recorded correction';s.pending=weightDraft(s);expect(decodeWeightRecovery(JSON.stringify(s),scope)).toEqual(s);
 const a=action(),trigger=document.createElement('button');document.body.append(trigger);mount(a,{trigger});fill();await review();expect(screen.getByRole('heading',{name:'Recorded weight',level:2})).toHaveFocus();fireEvent.click(screen.getByRole('button',{name:/^Close$/}));expect(trigger).toHaveFocus();
});
it('groups generic and source-owned weights once while preserving both records',async()=>{
 const catalog=await new RF2Client(async()=>new Response(JSON.stringify(fixture.catalog))).catalog(requested.start,requested.end),source=catalog.items.find(e=>e.metadata?.chart?.category==='weight')!;
 const generic={...structuredClone(source),fact:{...source.fact,kind:'observation',id:'other-weight',concept_id:'body-weight'},metadata:null};catalog.items.push(generic);
 const group=patientOverviewModel(catalog,requested).findings.filter(g=>g.label==='Recorded weight');expect(group).toHaveLength(1);expect(group[0].records).toContain(source);expect(group[0].records).toContain(generic);
});
it('keeps an unresolved lookup recoverable and does not automatically retry',async()=>{
 const s=draftData();s.pending=weightDraft(s);localStorage.setItem(weightStorageKey(scope),JSON.stringify(s));const a=action().mockRejectedValue(Error('Unavailable'));mount(a);fireEvent.click(screen.getByRole('button',{name:'Check saved result'}));await screen.findByText(/no retry was sent/);expect(a.mock.calls.map(c=>c[0])).toEqual(['lookup']);expect(localStorage.getItem(weightStorageKey(scope))).not.toBeNull();
});
it('connects Add information and source-owned correction to the same overview without legacy navigation',async()=>{
 const catalog=await new RF2Client(async()=>new Response(JSON.stringify(fixture.catalog))).catalog(requested.start,requested.end),source=catalog.items.find(e=>e.metadata?.chart?.category==='weight')!,a=action();
 render(<PatientOverview catalog={catalog} requested={requested} status="current" guarded={false} weightEntryEnabled weightTransport={{action:a}} onRefresh={async()=>{}} transport={{history:async()=>[source]}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Add information'}));const choices=screen.getByRole('dialog',{name:'Add information'});fireEvent.click(within(choices).getByRole('button',{name:'Recorded weight'}));expect(screen.getByRole('dialog')).toHaveAccessibleName('Recorded weight');fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Close'}));
 const group=screen.getByRole('heading',{name:'Recorded weight'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));fireEvent.click(within(group).getByRole('button',{name:/Open recorded source/}));await waitFor(()=>expect(screen.getByRole('button',{name:'Correct recorded weight'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Correct recorded weight'}));expect(screen.getByRole('dialog')).toHaveAccessibleName('Correct recorded weight');expect(screen.getByLabelText('Weight')).toHaveValue(source.metadata!.chart!.amount!);
});
