import {afterAll,beforeAll,afterEach,expect,it,vi} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,stable,hash,validateReproductiveImport,type Draft} from '../src/api/rf2Client';
import gastrointestinal from './fixtures/gastrointestinal-record.json';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));
afterEach(()=>vi.unstubAllGlobals());

it('accepts a calendar due date in a reproductive source and rejects impossible dates',()=>{
 const source={...gastrointestinal,kind:'reproductive_record',category:'pregnancy_status',
  pregnancy:{phase:'antepartum',gestational_weeks:32,gestational_days:4,estimated_due_date:'2026-11-29',
   fetus_count:1,dating_basis:'First-trimester ultrasound'}};
 expect(()=>validateReproductiveImport(fixture.catalog.repository,source)).not.toThrow();
 for(const date of ['2026-02-29','2026-11-29T00:00:00Z','2026-11-29\n']){
  expect(()=>validateReproductiveImport(fixture.catalog.repository,{...source,pregnancy:{...source.pregnancy,estimated_due_date:date}})).toThrow();
 }
});
it.each(['default','injected'] as const)('calls %s fetch without rebinding its receiver on catalog and pending lookup',async source=>{
 const calls:{url:string;body:unknown}[]=[];
 const draft=structuredClone(fixture.weight_draft) as Draft;
 const canonical=stable(draft);
 const absent={status:'absent',request_canonical:canonical,request_digest:await hash(canonical),execution_enabled:false};
 const send=async function(this:unknown,input:RequestInfo|URL,init?:RequestInit){
  // Model native fetch rejecting an arbitrary class instance as its receiver.
  if(this!==undefined&&this!==globalThis)throw new TypeError('Illegal invocation');
  calls.push({url:String(input),body:init?.body});
  return new Response(JSON.stringify(calls.length===1?structuredClone(fixture.catalog):absent));
 } satisfies typeof fetch;
 vi.stubGlobal('fetch',send);
 const api=source==='default'?new RF2Client():new RF2Client(send);
 const catalog=await api.catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 expect(catalog.execution_enabled).toBe(false);
 expect((await api.action('lookup',draft)).status).toBe('absent');
 expect(calls).toHaveLength(2);
 expect(calls[0].url).toContain('/synthetic-rf2?');
 expect(calls[1].url).toMatch(/\/synthetic-rf2\/lookup$/);
 expect(calls[1].body).toBe(JSON.stringify(draft));
});

it.each(['complete', 'different cutoff', 'skipped offset', 'premature end', 'duplicate record'] as const)(
 'loads a paginated catalog only when the same snapshot is complete (%s)', async variant => {
  const first = structuredClone(fixture.catalog);
  const evidence = structuredClone(fixture.weight);
  evidence.fact.id = '12345678-1234-4234-8234-123456789abc';
  evidence.terminal_reference.id = evidence.fact.id;
  evidence.cutoff = first.cutoff.fact_watermark;
  evidence.canonical_fact = stable(evidence.fact);
  evidence.digest = await hash(evidence.canonical_fact);
  const total = variant === 'duplicate record' ? 2 : 1;
  const header = {repository:first.repository, cutoff:first.cutoff, execution_enabled:false,
   items:[], laboratory_reports:[], respiratory_records:[], gastrointestinal_records:[]};
  const pages = [
   {...header, combined:first.combined, pagination:{offset:0, total, next_cursor:'second.page'}},
   {...header, cutoff:variant === 'different cutoff' ? {...first.cutoff, fact_watermark:7} : first.cutoff,
    items:variant === 'premature end' ? [] : [evidence],
    pagination:{offset:variant === 'skipped offset' ? 1 : 0, total, next_cursor:variant === 'duplicate record' ? 'third.page' : null}},
   {...header, items:[evidence], pagination:{offset:1, total, next_cursor:null}},
  ];
  const send = vi.fn<typeof fetch>().mockImplementation(async () => new Response(JSON.stringify(pages.shift())));
  const catalog = new RF2Client(send).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
  if (variant === 'complete') {
   expect((await catalog).items.filter(item => item.fact.id === evidence.fact.id)).toEqual([evidence]);
   const queries = send.mock.calls.map(([url]) => new URL(String(url), 'http://localhost').searchParams);
   expect(queries[0].get('paginate')).toBe('true');
   expect(queries[1].get('cursor')).toBe('second.page');
   expect(queries[1].get('review_end')).toBe(queries[0].get('review_end'));
  } else {
   await expect(catalog).rejects.toThrow();
  }
 });
