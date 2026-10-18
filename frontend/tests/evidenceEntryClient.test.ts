import {it,expect,vi,afterEach} from 'vitest';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {EvidenceEntryClient,type Draft} from '../src/api/evidenceEntryClient';
afterEach(()=>vi.unstubAllGlobals());
async function setup(){
 vi.stubGlobal('crypto',webcrypto);
 const state=decodeCirculatoryState(structuredClone(fixture)),item=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;
 const draft:Draft={repository_id:item.ingestion.repository_id,fact:item.fact,predecessor_digest:null};
 const canonical_fact=JSON.stringify(item.fact),expected_digest=Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical_fact))),b=>b.toString(16).padStart(2,'0')).join('');
 const evidence={repository_id:draft.repository_id,fact:structuredClone(item.fact),canonical_fact,expected_digest,ingestion:item.ingestion};
 return {draft,evidence};
}
it('uses native fetch as an unbound function and validates exact canonical content',async()=>{
 const {draft,evidence}=await setup();let calls=0;
 const send=function(this:unknown,url:unknown,init?:RequestInit){expect(this).toBeUndefined();expect(url).toMatch(/synthetic-evidence$/);expect(JSON.parse(String(init?.body))).toEqual(draft);calls++;return Promise.resolve(new Response(JSON.stringify(evidence)));};
 expect(await new EvidenceEntryClient(send as typeof fetch).save(draft)).toEqual(evidence);expect(calls).toBe(1);
});
it.each(['scope','digest','canonical','reference','repository','ingestion','quantity'])('rejects a contradictory %s without retry',async fault=>{
 const {draft,evidence}=await setup();const bad=structuredClone(evidence);
 if(fault==='scope')bad.fact.binding.target.encounter_id='foreign';
 if(fault==='digest')bad.expected_digest='f'.repeat(64);
 if(fault==='canonical')bad.canonical_fact='{}';
 if(fault==='reference')bad.fact.revision='other';
 if(fault==='repository')bad.repository_id='00000000-0000-4000-8000-000000000001';
 if(fault==='ingestion')bad.ingestion.repository_id='00000000-0000-4000-8000-000000000001';
 if(fault==='quantity')(bad.fact.result as {quantity:{value:unknown}}).quantity.value=7.35;
 const send=vi.fn().mockResolvedValue(new Response(JSON.stringify(bad)));
 await expect(new EvidenceEntryClient(send).save(draft)).rejects.toThrow();expect(send).toHaveBeenCalledTimes(1);
});
it('rejects malformed recovery instead of reporting absence or saving a replacement',async()=>{
 const {draft}=await setup(),send=vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'committed_match'})));
 await expect(new EvidenceEntryClient(send).lookup(draft)).rejects.toThrow();expect(send).toHaveBeenCalledTimes(1);
});
