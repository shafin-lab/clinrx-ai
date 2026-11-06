import {afterAll,beforeAll,expect,it,vi} from 'vitest';
import fixture from './fixtures/antibiotic-workflow.json';
import {AntibioticClient} from '../src/api/antibioticClient';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto'),old=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:old,configurable:true}));
const start='2026-10-08T08:00:00Z',end='2026-10-08T10:00:00Z';
it('loads shared evidence once then antimicrobial evidence at its exact repository cutoff',async()=>{
 const calls:string[]=[];const send=vi.fn(async(input:RequestInfo|URL)=>{const u=String(input);calls.push(u);return new Response(JSON.stringify(u.includes('/synthetic-rf2')?fixture.bundle.renal:fixture.bundle.micro));});
 const bundle=await new AntibioticClient(send as typeof fetch).sharedCatalog(start,end);expect(calls).toHaveLength(2);expect(calls[0]).toContain('/synthetic-rf2?');const next=new URL(calls[1],'http://local');expect(next.pathname).toMatch(/synthetic-antibiotics\/micro$/);expect(next.searchParams.get('repository')).toBe(bundle.renal.repository);expect(next.searchParams.get('cutoff')).toBe(String(bundle.renal.cutoff.fact_watermark));expect(next.searchParams.get('captured_at')).toBe(bundle.renal.cutoff.captured_at);expect(next.searchParams.get('review_start')).toBe(start);expect(bundle.micro.assembly.request.scope.repository_cutoff).toEqual(bundle.renal.cutoff);
});
it.each(['repository','cutoff','capture','window','failure'])('withholds the whole antibiotic bundle after a %s mismatch or failure',async mode=>{
 const micro=structuredClone(fixture.bundle.micro);if(mode==='repository')micro.assembly.request.scope.repository_cutoff.repository_id='11111111-1111-4111-8111-111111111111';if(mode==='cutoff')micro.assembly.request.scope.repository_cutoff.fact_watermark++;if(mode==='capture')micro.assembly.request.scope.repository_cutoff.captured_at='2026-10-09T11:00:00Z';if(mode==='window')micro.assembly.request.scope.review_end='2026-10-08T11:00:00Z';
 const send=vi.fn(async(input:RequestInfo|URL)=>String(input).includes('/synthetic-rf2')?new Response(JSON.stringify(fixture.bundle.renal)):new Response(JSON.stringify(micro),{status:mode==='failure'?503:200}));await expect(new AntibioticClient(send as typeof fetch).sharedCatalog(start,end)).rejects.toThrow();
});
it('reuses a previously decoded RF2 view once without mutating or duplicating its derived sources',async()=>{
 const prior=await new AntibioticClient(async()=>new Response(JSON.stringify(fixture.bundle))).catalog(start,end),before=JSON.stringify(prior.renal);const send=vi.fn(async()=>new Response(JSON.stringify(fixture.bundle.micro)));const result=await new AntibioticClient(send as typeof fetch).sharedCatalog(start,end,prior.renal);expect(send).toHaveBeenCalledOnce();expect(result.renal).toBe(prior.renal);expect(JSON.stringify(prior.renal)).toBe(before);
});

it.each(['patient','repository','window','execution'])('rejects a reused catalog with a %s scope mismatch before reading micro',async mode=>{
 const prior=await new AntibioticClient(async()=>new Response(JSON.stringify(fixture.bundle))).catalog(start,end),shared=structuredClone(prior.renal);if(mode==='patient')shared.combined.context.scope.patient_id='another-patient';if(mode==='repository')shared.repository='11111111-1111-4111-8111-111111111111';if(mode==='window')shared.combined.context.scope.review_end='2026-10-08T11:00:00Z';if(mode==='execution')Object.assign(shared,{execution_enabled:true});const send=vi.fn();await expect(new AntibioticClient(send as typeof fetch).sharedCatalog(start,end,shared)).rejects.toThrow();expect(send).not.toHaveBeenCalled();
});
it.each(['digest','fact','future-ingestion','missing-ingestion','unsafe-ingestion'])('rejects substituted or unpinned micro evidence: %s',async mode=>{
 const micro=structuredClone(fixture.bundle.micro),item=micro.assembly.snapshot.items[0];if(mode==='digest')item.expected_digest='0'.repeat(64);if(mode==='fact')item.fact.provenance.actor='substituted actor';if(mode==='future-ingestion')item.ingestion.ingestion_sequence=micro.assembly.request.scope.repository_cutoff.fact_watermark+1;if(mode==='missing-ingestion')Object.assign(item,{ingestion:null});if(mode==='unsafe-ingestion')item.ingestion.ingestion_sequence=Number.MAX_SAFE_INTEGER+1;
 const send=vi.fn(async(input:RequestInfo|URL)=>new Response(JSON.stringify(String(input).includes('/synthetic-rf2')?fixture.bundle.renal:micro)));await expect(new AntibioticClient(send as typeof fetch).sharedCatalog(start,end)).rejects.toThrow();
});
