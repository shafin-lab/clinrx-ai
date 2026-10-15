import {it,expect,vi} from 'vitest';
import {ReviewClient,ApiFailure} from '../src/api/client';
import fixture from './fixtures.json';
const id=fixture.execution.execution_id, command='OPAQUE.DO.NOT.DECODE';
const prepared={status:'prepared' as const,execution_id:id,inference_reference:fixture.execution.provenance.inference.reference,command};
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status});
it('preserves exact offset/precision in state query and has no caller cutoff',async()=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply({...fixture.state,scope:{...fixture.state.scope,patient_id:'p /',encounter_id:'e?'}}));const client=new ReviewClient('http://localhost:8000','p /','e?',fetcher);await client.state('2026-10-08T08:00:00.123456+05:30','2026-10-08T10:00:00+05:30');const url=new URL(String(fetcher.mock.calls[0][0]));expect(url.searchParams.get('review_start')).toBe('2026-10-08T08:00:00.123456+05:30');expect([...url.searchParams.keys()]).toEqual(['review_start','review_end']);expect(url.pathname).toContain('p%20%2F');});
it.each(['execute','reconcile'] as const)('%s posts opaque command unchanged',async(op)=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply(op==='execute'?fixture.execution:{status:'committed_match',execution:fixture.execution}));await new ReviewClient('http://localhost:8000','p','e',fetcher)[op](prepared);expect(fetcher.mock.calls[0][1]?.body).toBe(JSON.stringify({command}));expect(fetcher).toHaveBeenCalledTimes(1);});
it.each(['not_found','execution_conflict','storage_integrity_failure','completion_unknown','made_up'])('bounds %s error text and fields',async(code)=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply({code,message:'PRIVATE SQL command',fields:[{path:'PRIVATE',code:'invalid_value'},{path:'body.command',code:'invalid_value'}]},503));try{await new ReviewClient('http://localhost:8000','p','e',fetcher).lookup(id);throw Error('missing rejection');}catch(e){expect(e).toBeInstanceOf(ApiFailure);const error=e as ApiFailure;expect(error.message).not.toContain('PRIVATE');expect(error.fields).toEqual([{path:'body.command',code:'invalid_value'}]);}expect(fetcher).toHaveBeenCalledTimes(1);});
it('does not retry dropped execution',async()=>{const fetcher=vi.fn<typeof fetch>().mockRejectedValue(Error('PRIVATE'));await expect(new ReviewClient('http://localhost:8000','p','e',fetcher).execute(prepared)).rejects.toMatchObject({code:'network_error'});expect(fetcher).toHaveBeenCalledTimes(1);});
it('rejects a mismatched execution receipt',async()=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply({...fixture.execution,execution_id:'wrong'}));await expect(new ReviewClient('http://localhost:8000','p','e',fetcher).execute(prepared)).rejects.toMatchObject({code:'invalid_response'});});
it.each(['https://external.example','http://user:secret@localhost:8000','http://localhost:8000/?command=secret'])('rejects non-demo origin %s',base=>{expect(()=>new ReviewClient(base,'p','e')).toThrow();});

it('invokes browser fetch without a client-object receiver',async()=>{
  const fetcher: typeof fetch = async function(this: unknown) {
    if (this !== undefined) throw new TypeError('Illegal invocation');
    return reply(fixture.state);
  };
  await expect(new ReviewClient('http://localhost:8000',fixture.state.scope.patient_id,fixture.state.scope.encounter_id,fetcher).state('start','end')).resolves.toMatchObject({data:fixture.state});
});

import {MicroReviewClient} from '../src/api/microClient';
import {decodeMicroPrepared} from '../src/api/microDecoders';
import type {Reply} from '../src/api/client';
import microFixture from './microFixtures.json';
const scope=fixture.state.scope;
const make=(fetcher:typeof fetch)=>new ReviewClient('http://localhost:8000',scope.patient_id,scope.encounter_id,fetcher);
const micro=(fetcher:typeof fetch)=>new MicroReviewClient('http://localhost:8000',scope.patient_id,scope.encounter_id,fetcher);
const mPrepared=decodeMicroPrepared(microFixture.prepared);
const pin=(n:number)=>({reference:fixture.state.laboratory[n].reference,expected_digest:fixture.state.laboratory[n].selection_digest});
const preparation={execution_id:id,state_context:fixture.state.state_context,earlier_laboratory:pin(0),later_laboratory:pin(1),medication:{reference:fixture.state.medication[0].reference,expected_digest:fixture.state.medication[0].selection_digest}};
const microPin=(kind:string)=>{const item=microFixture.state.assembly.snapshot.items.find(i=>i.fact.kind===kind)!;return {reference:{kind:item.fact.kind,id:item.fact.id,version:item.fact.revision},expected_digest:item.expected_digest};};
const microPreparation={execution_id:mPrepared.execution_id,state_context:microFixture.state.state_context,specimen_ref:microPin('microbiology_specimen'),isolate_ref:microPin('microbiology_isolate'),susceptibility_ref:microPin('microbiology_susceptibility'),administration_ref:microPin('antimicrobial_administration')};
interface PathCase {name:string;valid:unknown;nested:string;identity:string;run:(fetcher:typeof fetch)=>Promise<Reply<unknown>>}
const paths:PathCase[]=[
  {name:'M5 state',valid:fixture.state,nested:'laboratory.0.source',identity:'scope.patient_id',run:f=>make(f).state(scope.review_start,scope.review_end)},
  {name:'M5 prepare',valid:prepared,nested:'inference_reference',identity:'execution_id',run:f=>make(f).prepare(preparation)},
  {name:'M5 execute',valid:fixture.execution,nested:'governance.reasons',identity:'execution_id',run:f=>make(f).execute(prepared)},
  {name:'M5 lookup',valid:fixture.execution,nested:'provenance.terminal_references',identity:'execution_id',run:f=>make(f).lookup(id)},
  {name:'M5 reconcile',valid:{status:'committed_match',execution:fixture.execution},nested:'execution.provenance',identity:'execution.execution_id',run:f=>make(f).reconcile(prepared)},
  {name:'M6 state',valid:microFixture.state,nested:'assembly.snapshot.items.0.fact.provenance',identity:'assembly.request.scope.patient_id',run:f=>micro(f).microState(scope.review_start,scope.review_end)},
  {name:'M6 prepare',valid:microFixture.prepared,nested:'inference.method',identity:'execution_id',run:f=>micro(f).microPrepare(microPreparation)},
  {name:'M6 execute',valid:microFixture.released,nested:'provenance.final_recheck.evidence',identity:'execution_id',run:f=>micro(f).microExecute(mPrepared)},
  {name:'M6 lookup',valid:microFixture.released,nested:'provenance.consumed.0.fact.provenance',identity:'execution_id',run:f=>micro(f).microLookup(mPrepared.execution_id)},
  {name:'M6 reconcile',valid:{status:'committed_match',execution:microFixture.released},nested:'execution.provenance.final_recheck',identity:'execution.execution_id',run:f=>micro(f).microReconcile(mPrepared)}
];
function changed(raw:unknown,path:string,value:unknown) {
  const result=structuredClone(raw),parts=path.split('.');let target=result as Record<string,unknown>;
  for(const key of parts.slice(0,-1))target=target[key] as Record<string,unknown>;
  target[parts.at(-1)!]=value;return result;
}
it.each(paths)('$name validates a complete response before returning it',async({valid,run})=>{
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(valid));expect((await run(f)).data).toEqual(valid);expect(f).toHaveBeenCalledTimes(1);
  expect(f.mock.calls[0][1]).toMatchObject({cache:'no-store',credentials:'omit'});
});
it.each(paths)('$name rejects HTTP 200 empty objects',async({run})=>{
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply({}));await expect(run(f)).rejects.toMatchObject({code:'invalid_response',status:200});expect(f).toHaveBeenCalledTimes(1);
});
it.each(paths)('$name rejects null nested required structure',async({valid,nested,run})=>{
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(changed(valid,nested,null)));await expect(run(f)).rejects.toMatchObject({code:'invalid_response'});expect(f).toHaveBeenCalledTimes(1);
});
it.each(paths)('$name rejects mismatched scope or execution UUID',async({valid,identity,run})=>{
  const value=identity.endsWith('execution_id')?'22222222-2222-4222-8222-222222222222':'foreign';
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(changed(valid,identity,value)));await expect(run(f)).rejects.toMatchObject({code:'invalid_response'});expect(f).toHaveBeenCalledTimes(1);
});
it.each(paths)('$name never logs, stores or exposes malformed successful payloads',async({valid,run})=>{
  const secret='PRIVATE.SIGNED.COMMAND.CLINICAL.DATA';const log=vi.spyOn(console,'log'),warn=vi.spyOn(console,'warn'),error=vi.spyOn(console,'error'),storage=vi.spyOn(Storage.prototype,'setItem');
  const raw={...valid as Record<string,unknown>,private_payload:secret};const f=vi.fn<typeof fetch>().mockResolvedValue(reply(raw));
  try{await run(f);throw Error('expected rejection');}catch(e){expect(e).toBeInstanceOf(ApiFailure);expect(String(e)).not.toContain(secret);expect(JSON.stringify(e)).not.toContain(secret);expect(e).not.toHaveProperty('cause');}
  expect(f).toHaveBeenCalledTimes(1);for(const spy of [log,warn,error,storage])expect(spy).not.toHaveBeenCalled();vi.restoreAllMocks();
});
it.each(['execute','reconcile'] as const)('M5 %s checks the prepared inference identity',async(op)=>{
  const other={...prepared,inference_reference:{...prepared.inference_reference,version:'different'}};
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(op==='execute'?fixture.execution:{status:'committed_match',execution:fixture.execution}));
  await expect(make(f)[op](other)).rejects.toMatchObject({code:'invalid_response'});
});
it.each(['microExecute','microReconcile'] as const)('M6 %s checks the prepared inference identity',async(op)=>{
  const other={...mPrepared,inference:{...mPrepared.inference,revision:'different'}};
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(op==='microExecute'?microFixture.released:{status:'committed_match',execution:microFixture.released}));
  await expect(micro(f)[op](other)).rejects.toMatchObject({code:'invalid_response'});
});
it('M6 retained lookup checks foreign patient scope',async()=>{
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(microFixture.released));
  await expect(new MicroReviewClient('http://localhost:8000','foreign',scope.encounter_id,f).microLookup(mPrepared.execution_id)).rejects.toMatchObject({code:'invalid_response'});
});
it('projects only bounded, strictly typed error fields',async()=>{
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply({code:'invalid_request',message:'PRIVATE',fields:[{path:'body.command',code:['invalid_value']},{path:'body.command',code:'invalid_value',private:'PRIVATE'}]},422));
  try{await make(f).lookup(id);}catch(e){expect(e).toBeInstanceOf(ApiFailure);expect((e as ApiFailure).fields).toEqual([{path:'body.command',code:'invalid_value'}]);expect(JSON.stringify(e)).not.toContain('PRIVATE');}
});
it('preserves valid absence without automatically executing',async()=>{
  for(const run of [(f:typeof fetch)=>make(f).reconcile(prepared),(f:typeof fetch)=>micro(f).microReconcile(mPrepared)]) {
    const f=vi.fn<typeof fetch>().mockResolvedValue(reply({status:'absent',execution:null}));expect((await run(f)).data).toEqual({status:'absent',execution:null});expect(f).toHaveBeenCalledTimes(1);
  }
});
it('preserves exact numeric and timestamp strings through both network paths',async()=>{
  const m5=structuredClone(fixture.state);m5.laboratory[0].quantity.value='1.234567890123456789000';m5.laboratory[0].time.event='2026-11-01T01:30:00.123456-04:00';
  const f=vi.fn<typeof fetch>().mockResolvedValue(reply(m5));const data=(await make(f).state(scope.review_start,scope.review_end)).data;
  expect(data.laboratory[0].quantity.value).toBe('1.234567890123456789000');expect(data.laboratory[0].time.event).toBe('2026-11-01T01:30:00.123456-04:00');
  const g=vi.fn<typeof fetch>().mockResolvedValue(reply(microFixture.state));expect((await micro(g).microState(scope.review_start,scope.review_end)).data).toEqual(microFixture.state);
});
