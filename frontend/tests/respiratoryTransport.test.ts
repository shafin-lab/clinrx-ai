import {afterAll,beforeAll,expect,it,vi} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import respiratory from './fixtures/respiratory-record.json';
import type {RecordedTime,RespiratoryRecord} from '../src/respiratory/respiratoryTypes';
import {decodeRF2Catalog,decodeEvidence,hash,RF2Client,stable,type Evidence} from '../src/api/rf2Client';
const previous=globalThis.crypto;const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:previous,configurable:true}));
async function evidence(){const c=fixture.catalog,fact=structuredClone(respiratory),canonical_fact=stable(fact);return {repository:c.repository,fact,canonical_fact,digest:await hash(canonical_fact),ingestion:{repository_id:c.repository,ingestion_sequence:1,ingested_at:'2026-10-08T09:00:00Z',payload_version:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:fact.kind,id:fact.id,version:fact.revision},superseded:false,metadata:null};}
it('decodes typed respiratory evidence with canonical hash and patient identity checked',async()=>{const e=await evidence();expect((await decodeEvidence(e,e.repository)).fact).toEqual(respiratory);await expect(decodeEvidence({...e,digest:'0'.repeat(64)},e.repository)).rejects.toThrow();});
it('includes respiratory sources in the same catalog without duplicating existing records',async()=>{const c={...structuredClone(fixture.catalog),respiratory_records:[await evidence()]};const decoded=await decodeRF2Catalog(c,'2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');expect(decoded.respiratory_records?.[0].fact.kind).toBe('respiratory_record');expect(decoded.items).toHaveLength(fixture.catalog.items.length+fixture.catalog.combined.circulatory.assembly.snapshot.items.length+fixture.catalog.combined.laboratory.observations.length);});
it('rejects respiratory records from another patient even when their hash is internally consistent',async()=>{const e=await evidence();e.fact.binding.target.patient_id='other';e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);await expect(decodeEvidence(e,e.repository)).rejects.toThrow();});
it('sends exact respiratory import and rejects a different response record',async()=>{const e=await evidence();const send=vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(e)));const client=new RF2Client(send);expect(await client.importRespiratory(e.repository,respiratory as unknown as Evidence['fact'])).toMatchObject({fact:respiratory});expect(JSON.parse(String(send.mock.calls[0][1]?.body))).toEqual({repository:e.repository,record:respiratory});const changed=structuredClone(e);changed.fact.title='Different source';changed.canonical_fact=stable(changed.fact);changed.digest=await hash(changed.canonical_fact);await expect(new RF2Client(async()=>new Response(JSON.stringify(changed))).importRespiratory(e.repository,respiratory as unknown as Evidence['fact'])).rejects.toThrow();});
it('accepts an explicitly narrowed historical respiratory evidence cutoff but rejects future ones',async()=>{const e=await evidence(),c={...structuredClone(fixture.catalog),respiratory_records:[{...e,cutoff:1}]};expect((await decodeRF2Catalog(c,'2026-10-08T08:00:00Z','2026-10-08T10:00:00Z')).respiratory_records).toHaveLength(1);c.respiratory_records[0].cutoff=c.cutoff.fact_watermark+1;await expect(decodeRF2Catalog(c,'2026-10-08T08:00:00Z','2026-10-08T10:00:00Z')).rejects.toThrow();});
it('distinguishes definite no-append rejection from an uncertain respiratory request',async()=>{const c=fixture.catalog;const client=new RF2Client(async()=>new Response('{}',{status:409}));await expect(client.importRespiratory(c.repository,respiratory as unknown as Evidence['fact'])).rejects.toMatchObject({name:'RF2DefiniteRejection'});});
it.each([
 ['2026-10-08T09:00:00.382Z','2026-10-08T09:00:00.382000Z'],
 ['2026-10-08T09:00:00.000Z','2026-10-08T09:00:00Z'],
 ['2026-10-08T14:30:00.382001+05:30','2026-10-08T09:00:00.382001Z'],
])('confirms a saved source when typed timestamps round-trip as the same exact instant (%s)',async(sent,stored)=>{
 const e=await evidence(),request=structuredClone(e.fact);
 request.provenance.recorded_at=sent;e.fact.provenance.recorded_at=stored;
 request.binding.verification.assessed_at=sent;e.fact.binding.verification.assessed_at=stored;
 request.times.collected.value=sent;e.fact.times.collected.value=stored;
 e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);
 const client=new RF2Client(async()=>new Response(JSON.stringify(e)));
 expect((await client.importRespiratory(e.repository,request)).fact).toEqual(e.fact);
 expect(request.provenance.recorded_at).toBe(sent);
});
it('rejects changed microseconds and source content despite valid response hashes',async()=>{
 for(const field of ['timestamp','narrative'] as const){
  const e=await evidence(),request=structuredClone(e.fact);
  request.provenance.recorded_at='2026-10-08T09:00:00.382001Z';e.fact.provenance.recorded_at='2026-10-08T09:00:00.382002Z';
  if(field==='narrative'){e.fact.provenance.recorded_at=request.provenance.recorded_at;request.narrative='2026-10-08T09:00:00.382Z';e.fact.narrative='2026-10-08T09:00:00.382000Z';}
  e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);
  await expect(new RF2Client(async()=>new Response(JSON.stringify(e))).importRespiratory(e.repository,request)).rejects.toThrow();
 }
});

it.each([
 ['instant', '2026-10-08T10:00:00.000Z', '2026-10-08T10:00:00Z'],
 ['instant', '2026-10-08T10:00:00.382Z', '2026-10-08T10:00:00.382000Z'],
 ['bounded', '2026-10-08T10:00:00.382Z', '2026-10-08T10:00:00.382000Z'],
] as const)('confirms a support episode when its %s until timestamps retain their exact instants (%s)',async(precision,sent,stored)=>{
 const e=await evidence(),request=structuredClone(e.fact) as unknown as RespiratoryRecord,response=e.fact as unknown as RespiratoryRecord;
 const until:RecordedTime={status:'known',precision,value:precision==='instant'?sent:null,lower:precision==='bounded'?sent:null,upper:precision==='bounded'?'2026-10-08T11:00:00.000Z':null,uncertainty:null};
 request.context.support_episode={type:'nasal_cannula',until};response.context.support_episode=structuredClone(request.context.support_episode);
 const saved=response.context.support_episode.until!;
 if(precision==='instant')saved.value=stored;else{saved.lower=stored;saved.upper='2026-10-08T11:00:00Z';}
 e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);
 const before=stable(request),result=await new RF2Client(async()=>new Response(JSON.stringify(e))).importRespiratory(e.repository,request);
 expect((result.fact as RespiratoryRecord).context.support_episode?.until).toEqual({...until,...(precision==='instant'?{value:stored}:{lower:stored,upper:'2026-10-08T11:00:00Z'})});
 expect(stable(request)).toBe(before);
});
it.each(['value','lower','upper','uncertainty','narrative'] as const)('rejects changed support-until %s or untyped source text despite a valid response hash',async(field)=>{
 const e=await evidence(),request=structuredClone(e.fact) as unknown as RespiratoryRecord,response=e.fact as unknown as RespiratoryRecord;
 const bounded=field==='lower'||field==='upper';
 request.context.support_episode={type:'nasal_cannula',until:{status:'known',precision:bounded?'bounded':'instant',value:bounded?null:'2026-10-08T10:00:00.382001Z',lower:bounded?'2026-10-08T10:00:00.382001Z':null,upper:bounded?'2026-10-08T11:00:00.382001Z':null,uncertainty:null}};
 if(field==='uncertainty')request.context.support_episode.until!.uncertainty='2026-10-08T10:00:00.382Z';
 if(field==='narrative')request.narrative='2026-10-08T10:00:00.382Z';
 response.context.support_episode=structuredClone(request.context.support_episode);response.narrative=request.narrative;
 if(field==='narrative')response.narrative='2026-10-08T10:00:00.382000Z';
 else response.context.support_episode.until![field]=field==='uncertainty'?'2026-10-08T10:00:00.382000Z':field==='upper'?'2026-10-08T11:00:00.382002Z':'2026-10-08T10:00:00.382002Z';
 e.canonical_fact=stable(e.fact);e.digest=await hash(e.canonical_fact);
 await expect(new RF2Client(async()=>new Response(JSON.stringify(e))).importRespiratory(e.repository,request)).rejects.toThrow();
});
