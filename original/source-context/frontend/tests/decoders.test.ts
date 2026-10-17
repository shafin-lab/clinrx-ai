import {describe,it,expect,vi} from 'vitest';
import fixture from './fixtures.json';
import {decodePatientState,decodePrepared,decodeExecution,decodeRetainedExecution,decodeReconciliation} from '../src/api/decoders';
import {DecodeFailure,timestamp,decodeContract} from '../src/api/decoding';
const clone=<T,>(x:T):T=>structuredClone(x);
const execution=fixture.execution;
const prepared={status:'prepared',execution_id:execution.execution_id,inference_reference:execution.provenance.inference.reference,command:'OPAQUE.DO.NOT.DECODE'};
function mutate<T>(value:T,path:string,replacement:unknown,remove=false):T {
  const result=clone(value);const parts=path.split('.');let owner=result as unknown as Record<string,unknown>;
  for(const key of parts.slice(0,-1))owner=owner[key] as Record<string,unknown>;
  const key=parts.at(-1)!;if(remove)delete owner[key];else owner[key]=replacement;return result;
}
describe('M5 pure contracts',()=>{
  it('accepts existing backend state, preserves identity and does not mutate',()=>{
    const before=JSON.stringify(fixture.state);
    expect(decodePatientState(fixture.state,{patient_id:fixture.state.scope.patient_id,encounter_id:fixture.state.scope.encounter_id})).toBe(fixture.state);
    expect(JSON.stringify(fixture.state)).toBe(before);
  });
  it('accepts preparation and both execution read paths',()=>{
    expect(decodePrepared(prepared,{execution_id:execution.execution_id,inference_reference:prepared.inference_reference})).toBe(prepared);
    for(const decode of [decodeExecution,decodeRetainedExecution])expect(decode(execution,{execution_id:execution.execution_id})).toBe(execution);
  });
  it('supports withheld output without reconstructing a statement',()=>{
    const withheld=clone(execution);withheld.governance.outcome='withheld';withheld.provenance.inference.statement=null as unknown as string;
    expect(decodeExecution(withheld).provenance.inference.statement).toBeNull();
    expect(()=>decodeExecution({...withheld,provenance:execution.provenance})).toThrow(DecodeFailure);
  });
  it('requires exact expected identities where response fields exist',()=>{
    for(const expected of [{patient_id:'foreign'},{encounter_id:'foreign'}])expect(()=>decodePatientState(fixture.state,expected)).toThrow(DecodeFailure);
    for(const decode of [decodePrepared,decodeExecution,decodeRetainedExecution])expect(()=>decode(decode===decodePrepared?prepared:execution,{execution_id:'22222222-2222-4222-8222-222222222222'})).toThrow(DecodeFailure);
    expect(()=>decodeExecution(execution,{inference_reference:{...prepared.inference_reference,version:'foreign'}})).toThrow(DecodeFailure);
  });
  it.each([
    ['transport_version','2'],['profile_id','Other'],['profile_version','2'],['laboratory',null],['medication',{}],['coverage',[]],['issues',null],['disclosures',false],
    ['scope.patient_id',22],['scope.repository_cutoff.repository_id','bad'],['scope.repository_cutoff.fact_watermark',Number.MAX_SAFE_INTEGER+1],
    ['laboratory.0.reference',{}],['laboratory.0.selection_digest','A'.repeat(64)],['laboratory.0.quantity.value',1.000],['laboratory.0.quantity.value','NaN'],
    ['laboratory.0.source',null],['laboratory.0.time.event','2025-02-29T08:00:00Z'],['laboratory.0.origin','inferred'],['medication.0.event_type','antimicrobial_order']
  ])('rejects state mutation %s', (path,value)=>expect(()=>decodePatientState(mutate(fixture.state,path,value))).toThrow(DecodeFailure));
  it.each(['scope','state_context','laboratory','medication','coverage','issues','disclosures','laboratory.0.quantity','laboratory.0.reference','laboratory.0.source','laboratory.0.time','medication.0.status'])('rejects missing required %s',path=>expect(()=>decodePatientState(mutate(fixture.state,path,undefined,true))).toThrow(DecodeFailure));
  it.each([
    ['status','pending'],['transport_version','9'],['execution_id','bad'],['context',{}],['governance',{}],['governance.outcome','approved'],['governance.decision_reference',null],
    ['provenance',{}],['provenance.inference.inputs',[]],['provenance.direct_dependencies',[]],['provenance.terminal_references',[]],['context.evidence_references',[]],
    ['provenance.earlier_laboratory.reference.version','wrong'],['provenance.terminal_references.0.id','wrong'],['provenance.direct_dependencies.0.relationship','copied_from'],
    ['provenance.final_cutoff.repository_id','11111111-1111-4111-8111-111111111111'],['provenance.final_recheck','latest'],['provenance.inference.statement',null],['governance.reasons',null]
  ])('rejects execution mutation %s',(path,value)=>expect(()=>decodeExecution(mutate(execution,path,value))).toThrow(DecodeFailure));
  it.each(['governance','governance.decision_reference','governance.reasons','provenance.inference','provenance.medication','finalized_at','ingested_at'])('rejects missing execution %s',path=>expect(()=>decodeExecution(mutate(execution,path,undefined,true))).toThrow(DecodeFailure));
  it('rejects duplicate inputs independently of tuple length',()=>{
    const changed=clone(execution);changed.provenance.inference.inputs[1]=changed.provenance.inference.inputs[0];expect(()=>decodeExecution(changed)).toThrow(DecodeFailure);
  });
  it('validates reconciliation discriminant and nested receipt',()=>{
    expect(decodeReconciliation({status:'absent',execution:null}).execution).toBeNull();
    expect(decodeReconciliation({status:'committed_match',execution}).execution).toBe(execution);
    for(const raw of [{status:'absent',execution},{status:'committed_match',execution:null},{status:'committed_match',execution:{}},{status:'unknown',execution:null}])expect(()=>decodeReconciliation(raw)).toThrow(DecodeFailure);
  });
  it('does not impose closed enums where backend DTO declares text',()=>{
    const changed=mutate(execution,'governance.safety_status','new-backend-text');expect(decodeExecution(changed).governance.safety_status).toBe('new-backend-text');
  });
  it('supports backend defaults as absent, without fabricating them',()=>{
    const changed=mutate(fixture.state,'laboratory.0.provenance_actor',undefined,true);
    expect(decodePatientState(changed).laboratory[0]).not.toHaveProperty('provenance_actor');
    expect(()=>decodePatientState(mutate(fixture.state,'laboratory.0.disclosures',undefined,true))).toThrow(DecodeFailure);
  });
  it('rejects undeclared extra fields rather than dropping evidence',()=>expect(()=>decodeExecution({...execution,extra:'PRIVATE'})).toThrow(DecodeFailure));
  it.each([{},null,[],false,1,'PRIVATE'])('rejects invalid root %#',value=>expect(()=>decodeExecution(value)).toThrow(DecodeFailure));
});
describe('shared fidelity and error boundary',()=>{
  it.each(['1.000','500.00','1.2345678901234567890123456789','-0.000','1e-30'])('preserves exact Decimal %s',value=>{
    const changed=mutate(fixture.state,'laboratory.0.quantity.value',value);expect(decodePatientState(changed).laboratory[0].quantity.value).toBe(value);
  });
  it.each(['2024-02-29T23:59:59.123456+05:30','2026-11-01T01:30:00-04:00','2026-11-01T01:30:00-05:00','0001-01-01T00:00:00Z'])('preserves exact offset timestamp %s',value=>{
    const changed=mutate(fixture.state,'laboratory.0.time.event',value);expect(decodePatientState(changed).laboratory[0].time.event).toBe(value);
  });
  it.each(['2026-02-30T00:00:00Z','1900-02-29T00:00:00Z','2026-01-01T24:00:00Z','2026-01-01T00:00:60Z','2026-01-01T00:00:00+24:00','2026-01-01T00:00:00','2026-01-01T00:00:00.1234567Z','2026-01-01T00:00:00Z\n'])('rejects invalid calendar/syntax %s',value=>expect(()=>timestamp(value)).toThrow(DecodeFailure));
  it('rejects newline digest and wrong nullable types',()=>{
    expect(()=>decodePatientState(mutate(fixture.state,'laboratory.0.selection_digest','a'.repeat(64)+'\n'))).toThrow(DecodeFailure);
    expect(()=>decodePatientState(mutate(fixture.state,'laboratory.0.time.event',false))).toThrow(DecodeFailure);
    expect(decodePatientState(mutate(fixture.state,'laboratory.0.time.event',null)).laboratory[0].time.event).toBeNull();
  });
  it('sanitizes all failure properties and never logs or stores raw values',()=>{
    const logs=[vi.spyOn(console,'log'),vi.spyOn(console,'error'),vi.spyOn(console,'warn')],store=vi.spyOn(Storage.prototype,'setItem');
    const secret='PRIVATE.CLINICAL.SIGNED.COMMAND';
    let error:unknown;try{decodePrepared({...prepared,command:secret,unexpected:secret});}catch(e){error=e;}
    expect(error).toBeInstanceOf(DecodeFailure);expect(String(error)).not.toContain(secret);expect(JSON.stringify(error)).not.toContain(secret);expect(error).not.toHaveProperty('cause');
    for(const log of logs)expect(log).not.toHaveBeenCalled();expect(store).not.toHaveBeenCalled();vi.restoreAllMocks();
  });
  it('rejects accessors without invoking them',()=>{
    const getter=vi.fn(()=>fixture.state.scope);const raw={...fixture.state};Object.defineProperty(raw,'scope',{get:getter,enumerable:true});expect(()=>decodePatientState(raw)).toThrow(DecodeFailure);expect(getter).not.toHaveBeenCalled();
  });
  it('counts Unicode codepoints as backend strings do',()=>{
    const changed=mutate(fixture.state,'laboratory.0.reference.id','😀'.repeat(256));expect(decodePatientState(changed).laboratory[0].reference.id).toBe('😀'.repeat(256));
  });
  it('shared contract primitive rejects unsafe integers and malformed nested objects',()=>{
    expect(()=>decodeContract('CutoffView',{repository_id:'11111111-1111-4111-8111-111111111111',fact_watermark:1.5,captured_at:'2026-01-01T00:00:00Z'})).toThrow(DecodeFailure);
  });
});
