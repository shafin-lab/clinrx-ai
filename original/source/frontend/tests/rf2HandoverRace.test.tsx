import {afterAll,afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,pin,type Evidence,type Catalog} from '../src/api/rf2Client';
import {RenalFluidEntryWorkspace} from '../src/demo/RenalFluidEntryWorkspace';
import {decodeRF2Saved,storageKey} from '../src/demo/rf2Handover';
import {handoverStorageKey} from '../src/demo/localHandover';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const original=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:original,configurable:true}));beforeEach(()=>localStorage.clear());afterEach(()=>vi.restoreAllMocks());
const deferred=()=>{let resolve!:(value:Evidence[])=>void,reject!:(reason:Error)=>void;const promise=new Promise<Evidence[]>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
async function setup(extraSaved=0){
 const catalog=await new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 const weight=catalog.items.find(e=>e.fact.id===fixture.weight.fact.id)!,urine=catalog.items.find(e=>e.fact.id===fixture.urine.fact.id)!;
 const raw=JSON.stringify({version:2,repository:catalog.repository,patient:'synthetic-p1',encounter:'synthetic-e1',savedAt:'2026-10-20T08:39:58.910Z',pins:[pin(weight),...Array.from({length:extraSaved},()=>({...pin(weight),reference:{...pin(weight).reference,id:crypto.randomUUID()}}))]});
 localStorage.setItem(storageKey(catalog.repository),raw);
 const pending=deferred(),resolve=vi.fn().mockReturnValue(pending.promise),action=vi.fn();const transport={resolve,action,history:vi.fn()} as unknown as RF2Client;
 const props={catalog,gateConfirmed:true,onGuardChange:vi.fn(),onRefresh:async()=>{},onLegacyCorrect:vi.fn(),transport};
 const rendered=render(<RenalFluidEntryWorkspace {...props}/>);
 const handover=()=>screen.getByRole('region',{name:'RF2 saved handover'});
 const add=(e:Evidence)=>fireEvent.click(within(screen.getByRole('row',{name:new RegExp(e.fact.id)})).getByRole('button',{name:'Add exact record to RF2 handover'}));
 return {catalog,weight,urine,raw,pending,resolve,action,props,rendered,handover,add};
}
function confirmed(region:HTMLElement,e:Evidence){const card=within(region).getByRole('heading',{name:`${e.fact.kind} / ${e.fact.id} / ${e.fact.revision}`}).closest('article')!;expect(card).toHaveTextContent(/exact source confirmed|superseded historical revision retained/);return card;}
it('retains a newly added exact record when saved-source hydration completes later',async()=>{
 const s=await setup();s.add(s.urine);confirmed(s.handover(),s.urine);
 await act(async()=>s.pending.resolve([s.weight]));confirmed(s.handover(),s.weight);confirmed(s.handover(),s.urine);
 expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);expect(s.action).not.toHaveBeenCalled();expect(s.resolve).toHaveBeenCalledTimes(1);
 fireEvent.click(within(s.handover()).getByRole('button',{name:'Save RF2 handover locally'}));
 expect(decodeRF2Saved(localStorage.getItem(storageKey(s.catalog.repository))!,s.catalog.repository).pins).toEqual([pin(s.weight),pin(s.urine)]);
});
it('keeps a concurrently added source confirmed when hydration fails',async()=>{
 const s=await setup();s.add(s.urine);await act(async()=>s.pending.reject(Error('Unavailable')));confirmed(s.handover(),s.urine);
 expect(s.handover()).toHaveTextContent('Exact source unavailable/unconfirmed; pin retained without substitution.');
 expect(s.handover()).toHaveTextContent('Unsaved changes — save explicitly before reload.');
 expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);expect(s.resolve).toHaveBeenCalledTimes(1);expect(s.action).not.toHaveBeenCalled();
});
it('does not bring a removed selection back when its delayed hydration returns',async()=>{
 const s=await setup();fireEvent.click(within(s.handover()).getByRole('button',{name:'Remove selection only'}));s.add(s.urine);
 await act(async()=>s.pending.resolve([s.weight]));expect(within(s.handover()).queryByRole('heading',{name:new RegExp(s.weight.fact.id)})).not.toBeInTheDocument();confirmed(s.handover(),s.urine);
 fireEvent.click(within(s.handover()).getByRole('button',{name:'Save RF2 handover locally'}));expect(decodeRF2Saved(localStorage.getItem(storageKey(s.catalog.repository))!,s.catalog.repository).pins).toEqual([pin(s.urine)]);
});
it('does not overwrite a newer exact-source confirmation when an older restore finishes',async()=>{
 const s=await setup();fireEvent.click(within(s.handover()).getByRole('button',{name:'Remove selection only'}));
 const newer=structuredClone(s.weight);newer.cutoff++;newer.superseded=true;newer.terminal_reference={...newer.terminal_reference,version:'later-terminal'};
 const catalog={...s.catalog,cutoff:{...s.catalog.cutoff,fact_watermark:newer.cutoff},items:s.catalog.items.map(e=>e.fact.id===newer.fact.id?newer:e)};
 s.rendered.rerender(<RenalFluidEntryWorkspace {...s.props} catalog={catalog}/>);s.add(newer);
 await act(async()=>s.pending.resolve([s.weight]));const card=confirmed(s.handover(),newer);expect(card).toHaveTextContent('superseded historical revision retained');
 expect(card).toHaveTextContent('Original selected cutoff '+newer.cutoff);expect(localStorage.getItem(storageKey(catalog.repository))).toBe(s.raw);
});
it('keeps restoration alive during same-scope refresh and callback replacement',async()=>{
 const s=await setup();s.rendered.rerender(<RenalFluidEntryWorkspace {...s.props} onGuardChange={vi.fn()} catalog={{...s.catalog,items:[...s.catalog.items].reverse()}}/>);
 await act(async()=>s.pending.resolve([s.weight]));confirmed(s.handover(),s.weight);expect(s.resolve).toHaveBeenCalledTimes(1);expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);
});
it('ignores a late restoration from the previous repository',async()=>{
 const s=await setup();const repository=crypto.randomUUID();const catalog={...s.catalog,repository,items:[]};
 s.rendered.rerender(<RenalFluidEntryWorkspace {...s.props} catalog={catalog}/>);
 await act(async()=>s.pending.resolve([s.weight]));expect(within(s.handover()).queryByRole('article')).not.toBeInTheDocument();expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);expect(localStorage.getItem(storageKey(repository))).toBeNull();
});
it('does not drop either source when two additions occur before React renders',async()=>{
 const s=await setup();fireEvent.click(within(s.handover()).getByRole('button',{name:'Remove selection only'}));
 act(()=>{s.add(s.weight);s.add(s.urine);});await act(async()=>s.pending.resolve([s.weight]));confirmed(s.handover(),s.weight);confirmed(s.handover(),s.urine);
 fireEvent.click(within(s.handover()).getByRole('button',{name:'Save RF2 handover locally'}));expect(decodeRF2Saved(localStorage.getItem(storageKey(s.catalog.repository))!,s.catalog.repository).pins).toEqual([pin(s.weight),pin(s.urine)]);
});
it('merges concurrent additions during explicit v1 copying without modifying saved v1/v2 bytes',async()=>{
 const s=await setup();fireEvent.click(within(s.handover()).getByRole('button',{name:'Remove selection only'}));
 fireEvent.click(within(s.handover()).getByRole('button',{name:'Save RF2 handover locally'}));const empty=localStorage.getItem(storageKey(s.catalog.repository));
 const {repository:_,...v1pin}=pin(s.weight);const v1=JSON.stringify({version:1,repository:s.catalog.repository,patient:'synthetic-p1',encounter:'synthetic-e1',savedAt:'2026-10-20T08:39:58.910Z',pins:[v1pin]});
 const v1key=handoverStorageKey(s.catalog.combined.circulatory);localStorage.setItem(v1key,v1);
 const copy=deferred();s.resolve.mockReturnValueOnce(copy.promise);fireEvent.click(within(s.handover()).getByRole('button',{name:'Explicitly copy version 1 into working version 2'}));s.add(s.urine);
 await act(async()=>s.pending.resolve([s.weight]));confirmed(s.handover(),s.urine); // superseded initial restore cannot apply
 await act(async()=>copy.resolve([s.weight]));confirmed(s.handover(),s.weight);confirmed(s.handover(),s.urine);
 expect(localStorage.getItem(v1key)).toBe(v1);expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(empty);expect(s.action).not.toHaveBeenCalled();expect(s.resolve).toHaveBeenCalledTimes(2);
});
it('preserves the 32-pin limit while restoration is pending',async()=>{
 const s=await setup(31);s.add(s.urine);expect(s.handover()).toHaveTextContent('Handover limit reached; no selection was dropped.');
 expect(within(s.handover()).getAllByRole('article')).toHaveLength(32);expect(within(s.handover()).queryByRole('heading',{name:new RegExp(s.urine.fact.id)})).not.toBeInTheDocument();
 await act(async()=>s.pending.resolve([s.weight]));confirmed(s.handover(),s.weight);expect(within(s.handover()).getAllByRole('article')).toHaveLength(32);expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);
});
it('does not deliver an unmounted instance restoration into a newly mounted workspace',async()=>{
 const s=await setup();s.rendered.unmount();const next=deferred();const resolve=vi.fn().mockReturnValue(next.promise);
 render(<RenalFluidEntryWorkspace {...s.props} transport={{...s.props.transport,resolve} as unknown as RF2Client}/>);
 await act(async()=>s.pending.resolve([s.weight]));expect(s.handover()).toHaveTextContent('Exact source unavailable/unconfirmed; pin retained without substitution.');
 await act(async()=>next.resolve([s.weight]));confirmed(s.handover(),s.weight);expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(s.raw);expect(s.action).not.toHaveBeenCalled();
});
it('preserves an explicit save confirmation and exact saved pins if an earlier lookup later fails',async()=>{
 const s=await setup();s.add(s.urine);fireEvent.click(within(s.handover()).getByRole('button',{name:'Save RF2 handover locally'}));
 const saved=localStorage.getItem(storageKey(s.catalog.repository));expect(decodeRF2Saved(saved!,s.catalog.repository).pins).toEqual([pin(s.weight),pin(s.urine)]);
 await act(async()=>s.pending.reject(Error('Lost response')));confirmed(s.handover(),s.urine);
 expect(s.handover()).toHaveTextContent('Saved RF2 handover locally: 2 selection(s).');expect(s.handover()).toHaveTextContent('Saved-reference lookup failed.');
 expect(s.handover()).not.toHaveTextContent('Unsaved changes — save explicitly before reload.');expect(localStorage.getItem(storageKey(s.catalog.repository))).toBe(saved);expect(s.resolve).toHaveBeenCalledTimes(1);expect(s.action).not.toHaveBeenCalled();
});
