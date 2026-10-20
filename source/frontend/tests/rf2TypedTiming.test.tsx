import {afterAll,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within} from '@testing-library/react';
import rawCases from './fixtures/rf2-fc1-timing.json';
import apiFixture from './fixtures/rf2-api.json';
import {RF2Client,decodeEvidence,type Catalog,type Evidence} from '../src/api/rf2Client';
import {RF2FluidChart,fluidChartModel} from '../src/demo/RF2FluidChart';
import {evidenceText,sourceContext} from '../src/demo/RenalFluidEntryWorkspace';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const previousCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:previousCrypto,configurable:true}));
const cases=rawCases as unknown as {name:string;expected_placed:boolean;evidence:Evidence}[];
async function catalogFor(evidence:Evidence):Promise<Catalog>{
 const catalog=await new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(apiFixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 const decoded=await decodeEvidence(structuredClone(evidence),catalog.repository);
 return {...catalog,items:[decoded]};
}
it.each(cases)('uses decoded typed precision/alternatives for $name',async c=>{
 const catalog=await catalogFor(c.evidence);const model=fluidChartModel(catalog);
 expect(model.valid).toBe(true);
 expect(model.groups.flatMap(([,entries])=>entries)).toHaveLength(c.expected_placed?1:0);
 expect(model.unplaced).toHaveLength(c.expected_placed?0:1);
 expect(catalog.items[0].digest).toBe(c.evidence.digest);
});
it('shows approximate interval raw timestamp, precision and uncertainty rather than losing the typed assertion',async()=>{
 const c=cases.find(c=>c.name==='interval-approximate-start')!,catalog=await catalogFor(c.evidence);
 render(<RF2FluidChart catalog={catalog} status="current" text={evidenceText} context={e=>sourceContext(e,catalog)} onInspect={()=>{}}/>);
 const region=screen.getByRole('region',{name:'Unplaced entries'});
 expect(region).toHaveTextContent('2026-10-08T08:30:00Z');
 expect(region).toHaveTextContent(/precision approximate/i);
 expect(region).toHaveTextContent('Collection boundary could be anywhere from 08:00 to 09:15');
});
it('keeps point bounds and contradictory alternative source details readable',async()=>{
 const c=cases.find(c=>c.name==='point-bounded')!,catalog=await catalogFor(c.evidence);
 const r=render(<RF2FluidChart catalog={catalog} status="current" text={evidenceText} context={e=>sourceContext(e,catalog)} onInspect={()=>{}}/>);
 expect(screen.getByRole('region',{name:'Unplaced entries'})).toHaveTextContent('2026-10-08T09:15:00Z');
 expect(screen.getByRole('region',{name:'Unplaced entries'})).toHaveTextContent(/precision bounded/i);
 const alt=await catalogFor(cases.find(c=>c.name==='point-alternative-disagrees')!.evidence);
 r.rerender(<RF2FluidChart catalog={alt} status="current" text={evidenceText} context={e=>sourceContext(e,alt)} onInspect={()=>{}}/>);
 const card=screen.getByRole('article');fireEvent.click(within(card).getByText('Source timing, verification and exact pin'));
 expect(card).toHaveTextContent('2026-10-08T09:30:00Z');expect(card).toHaveTextContent('Alternative source assertion');
});
