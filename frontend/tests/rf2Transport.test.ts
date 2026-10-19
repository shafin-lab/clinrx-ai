import {afterAll,beforeAll,afterEach,expect,it,vi} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,stable,hash,type Draft} from '../src/api/rf2Client';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
const oldCrypto=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:oldCrypto,configurable:true}));
afterEach(()=>vi.unstubAllGlobals());
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
