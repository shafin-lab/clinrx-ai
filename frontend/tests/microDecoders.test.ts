import {describe,it,expect} from 'vitest';
import fixture from './microFixtures.json';
import {decodeMicroState,decodeMicroPrepared,decodeMicroExecution,decodeMicroRetainedExecution,decodeMicroReconciliation} from '../src/api/microDecoders';
import {DecodeFailure,decodeContract} from '../src/api/decoding';
const clone=<T,>(x:T):T=>structuredClone(x);
const state=fixture.state,execution=fixture.released,prepared=fixture.prepared;
function mutate<T>(value:T,path:string,replacement:unknown,remove=false):T {
  const result=clone(value);const parts=path.split('.');let owner=result as unknown as Record<string,unknown>;
  for(const key of parts.slice(0,-1))owner=owner[key] as Record<string,unknown>;
  const key=parts.at(-1)!;if(remove)delete owner[key];else owner[key]=replacement;return result;
}
describe('M6 complete response contracts',()=>{
  it('accepts independent checked-in state and preparation without mutation',()=>{
    const before=JSON.stringify(fixture);
    expect(decodeMicroState(state,{patient_id:'synthetic-p1',encounter_id:'synthetic-e1'})).toBe(state);
    expect(decodeMicroPrepared(prepared,{execution_id:prepared.execution_id})).toBe(prepared);
    expect(JSON.stringify(fixture)).toBe(before);
  });
  it.each([fixture.released,fixture.withheld])('accepts retained $governance.outcome with original provenance',raw=>{
    expect(decodeMicroExecution(raw,{execution_id:raw.execution_id})).toBe(raw);
    expect(decodeMicroRetainedExecution(raw)).toBe(raw);
    expect(decodeMicroReconciliation({status:'committed_match',execution:raw}).execution).toBe(raw);
  });
  it('preserves all four input revisions, consumed/terminal differences and original provenance',()=>{
    const decoded=decodeMicroExecution(fixture.withheld);
    expect(decoded.provenance.inference.inputs.map(r=>r.id)).toEqual(['demo-S','demo-I','demo-U','demo-D']);
    expect(decoded.provenance.consumed[2].fact.revision).toBe('1');
    expect(decoded.provenance.final_recheck.terminal_facts[2].revision).toBe('2');
    expect(decoded.provenance.inference.statement).toBe(fixture.withheld.provenance.inference.statement);
    expect(decoded.statement).toBeNull();
  });
  it.each([
    ['transport_version','2'],['assembly.request.profile_version','3'],['assembly.request.profile_id','Other'],['assembly.snapshot.contract_version','3'],
    ['assembly.snapshot.items',null],['assembly.snapshot.microbiology.references',null],['assembly.snapshot.microbiology.specimens',{}],['assembly.snapshot.antimicrobial.administrations',null],
    ['assembly.bindings.0.status','invented'],['assembly.snapshot.items.0.expected_digest','abc'],['assembly.snapshot.items.0.fact.kind','new_kind'],['assembly.snapshot.items.0.fact.contract_version','3'],
    ['assembly.snapshot.items.0.fact.antimicrobial.identity_version','2'],['assembly.snapshot.items.0.fact.antimicrobial.ingredient_ids',null],['assembly.snapshot.items.0.fact.antimicrobial.mapping_status','equivalent'],
    ['assembly.snapshot.items.0.fact.binding.target.patient_id','foreign'],['assembly.snapshot.items.0.fact.provenance.source',{}],['assembly.snapshot.items.0.ingestion.payload_version',2],
    ['assembly.snapshot.items.0.ingestion.ingestion_sequence',1.2],['assembly.snapshot.scope.encounter_id','foreign']
  ])('rejects malformed state %s',(path,value)=>expect(()=>decodeMicroState(mutate(state,path,value))).toThrow(DecodeFailure));
  it.each(['assembly','state_context','assembly.request','assembly.snapshot.scope','assembly.snapshot.items.0.fact.binding','assembly.snapshot.items.0.fact.provenance','assembly.snapshot.items.0.fact.antimicrobial.source_code'])('rejects missing nested required %s',path=>expect(()=>decodeMicroState(mutate(state,path,undefined,true))).toThrow(DecodeFailure));
  it.each([
    ['transport_version','9'],['execution_id','bad'],['governance',{}],['governance.outcome','approved'],['governance.reasons',null],['provenance.inference',{}],
    ['provenance.consumed',[]],['provenance.witness_statuses',['current']],['provenance.final_recheck.evidence',[]],['provenance.final_recheck.terminal_facts',[]],
    ['provenance.final_recheck.evidence.0.role','I'],['provenance.final_recheck.evidence.0.consumed.version','wrong'],['provenance.final_recheck.evidence.0.terminal.id','wrong'],
    ['provenance.final_recheck.evidence.0.item_digest','a'.repeat(64)],['provenance.final_recheck.evidence.0.suitability','eligible'],
    ['provenance.final_recheck.terminal_facts.0.id','foreign'],['provenance.final_recheck.inference.inputs',[]],['provenance.final_recheck.inference.declarations',[]],
    ['provenance.final_recheck.inference.method.version','other'],['provenance.witness_statuses.0','superseded'],['provenance.inference.origin','observed'],
    ['provenance.inference.inputs',[]],['provenance.inference.provenance.upstream',[]],['provenance.inference.provenance.upstream.0.relationship','copied_from'],
    ['provenance.specimen_binding_matches','true'],['statement',null],['provenance.final_recheck.scope.patient_id','foreign'],['provenance.inference.binding.target.encounter_id','foreign']
  ])('rejects malformed execution %s',(path,value)=>expect(()=>decodeMicroExecution(mutate(execution,path,value))).toThrow(DecodeFailure));
  it.each(['statement','governance','governance.decision_reference','provenance','provenance.inference.statement','provenance.final_recheck.inference','provenance.consumed','provenance.witness_statuses','finalized_at','ingested_at'])('rejects absent required execution %s',path=>expect(()=>decodeMicroExecution(mutate(execution,path,undefined,true))).toThrow(DecodeFailure));
  it('rejects wrong expected scope, UUID and inference revision',()=>{
    for(const expected of [{patient_id:'other'},{encounter_id:'other'}]) {
      expect(()=>decodeMicroState(state,expected)).toThrow(DecodeFailure);expect(()=>decodeMicroPrepared(prepared,expected)).toThrow(DecodeFailure);expect(()=>decodeMicroExecution(execution,expected)).toThrow(DecodeFailure);
    }
    const expected={execution_id:'11111111-1111-4111-8111-111111111111'};
    expect(()=>decodeMicroPrepared(prepared,expected)).toThrow(DecodeFailure);expect(()=>decodeMicroExecution(execution,expected)).toThrow(DecodeFailure);
    expect(()=>decodeMicroExecution(execution,{inference_reference:{kind:'inference',id:prepared.inference.id,version:'other'}})).toThrow(DecodeFailure);
  });
  it('rejects reordered evidence, consumed items, terminal facts and inference inputs',()=>{
    for(const path of ['provenance.consumed','provenance.final_recheck.evidence','provenance.final_recheck.terminal_facts','provenance.inference.inputs']) {
      const parts=path.split('.');let value:unknown=execution;for(const part of parts)value=(value as Record<string,unknown>)[part];
      const reordered=[...(value as unknown[])];[reordered[0],reordered[1]]=[reordered[1],reordered[0]];
      expect(()=>decodeMicroExecution(mutate(execution,path,reordered))).toThrow(DecodeFailure);
    }
  });
  it('does not equate different revisions or accept duplicate exact items',()=>{
    const item=state.assembly.snapshot.items[0];expect(()=>decodeMicroState(mutate(state,'assembly.snapshot.items',[...state.assembly.snapshot.items,item]))).toThrow(DecodeFailure);
    expect(()=>decodeMicroExecution(mutate(execution,'provenance.inference.inputs.1',execution.provenance.inference.inputs[0]))).toThrow(DecodeFailure);
  });
  it('rejects dangling supplied view references without reconstructing bindings',()=>{
    expect(()=>decodeMicroState(mutate(state,'assembly.snapshot.microbiology.references.0.id','foreign'))).toThrow(DecodeFailure);
  });
  it('does not reinterpret withheld status, nullable statement or original inference',()=>{
    expect(()=>decodeMicroExecution({...fixture.withheld,statement:'PRIVATE RELEASED'})).toThrow(DecodeFailure);
    expect(decodeMicroExecution(fixture.withheld).provenance.inference.statement).toBe(fixture.withheld.provenance.inference.statement);
  });
  it('supports absent and rejects contradictory or malformed reconciliation',()=>{
    expect(decodeMicroReconciliation({status:'absent',execution:null})).toEqual({status:'absent',execution:null});
    for(const raw of [{status:'absent',execution},{status:'committed_match',execution:null},{status:'committed_match',execution:{}},{status:'other',execution:null}])expect(()=>decodeMicroReconciliation(raw)).toThrow(DecodeFailure);
  });
  it('accepts structurally valid preliminary/mismatched recorded identity without eligibility logic',()=>{
    const changed=clone(state);
    const isolate=changed.assembly.snapshot.items.find(i=>i.fact.kind==='microbiology_isolate')!;
    (isolate.fact as unknown as Record<string,unknown>).identification_state='provisional';
    const u=changed.assembly.snapshot.items.find(i=>i.fact.kind==='microbiology_susceptibility')!;
    (u.fact as unknown as {antimicrobial:{canonical_id:string}}).antimicrobial.canonical_id='unrelated-canonical';
    expect(decodeMicroState(changed)).toBe(changed);
  });
  it('preserves MIC 1.000, dose 500.00, offsets and uncertainty without normalization',()=>{
    const changed=clone(state);
    const u=changed.assembly.snapshot.items.find(i=>i.fact.kind==='microbiology_susceptibility')!;
    const d=changed.assembly.snapshot.items.find(i=>i.fact.kind==='antimicrobial_administration')!;
    const uf=u.fact as unknown as {mic:{quantity:{value:string}}};uf.mic.quantity.value='1.000';
    const df=d.fact as unknown as {administered_dose:{amount:{value:string}};administered:{value:string}};
    df.administered_dose.amount.value='500.00';df.administered.value='2026-11-01T01:30:00.123456-04:00';
    const decoded=decodeMicroState(changed);expect(decoded).toBe(changed);expect(uf.mic.quantity.value).toBe('1.000');expect(df.administered_dose.amount.value).toBe('500.00');expect(df.administered.value).toBe('2026-11-01T01:30:00.123456-04:00');
  });
  it('preserves missing, unknown, approximate and bounded time shapes',()=>{
    const representations=[{status:'missing',precision:'unknown',value:null,lower:null,upper:null},{status:'unknown',precision:'unknown'},{status:'known',precision:'approximate',value:'2026-10-08T08:00:00+05:30',uncertainty:'source approximation'},{status:'known',precision:'bounded',lower:'2026-10-08T08:00:00Z',upper:'2026-10-08T09:00:00Z'}];
    for(const time of representations)expect(decodeContract('RecordedTime',time)).toBe(time);
  });
  it('supports omitted optional arrays without adding empty arrays',()=>{
    const minimal={status:'not_recorded'};expect(decodeContract('RecordedTime',minimal)).toBe(minimal);expect(minimal).not.toHaveProperty('value');
    const item={...state.assembly.snapshot.items[0]};delete (item as Partial<typeof item>).disclosures;
    expect(decodeContract('RetainedStateItemV2',item)).not.toHaveProperty('disclosures');
  });
  it.each([{},null,[],1])('rejects malformed root %#',value=>expect(()=>decodeMicroExecution(value)).toThrow(DecodeFailure));
});
// These fixtures were independently validated by BloodCultureSet/BloodCultureBottle backend models.
const bloodVariants = [{"kind": "blood_culture_set", "id": "demo-SET", "revision": "1", "binding": {"target": {"patient_id": "synthetic-p1", "encounter_id": "synthetic-e1", "longitudinal_context_id": null}, "verification": {"status": "verified", "method": "synthetic-demo", "verifier": "synthetic-system", "assessed_at": "2026-10-08T08:00:00Z", "source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "ambiguity": null}}, "origin": "reported", "provenance": {"source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "actor": "synthetic-demo", "recorded_at": "2026-10-08T08:00:00Z", "upstream": [], "lineage": "unknown", "limitations": ["Synthetic source assertion only."]}, "time": {"event": null, "recorded": null, "effective_start": null, "effective_end": null, "retrieved": null, "processed": null, "precision": "unknown", "uncertainty": null}, "verification": "unverified", "conflict": "unknown", "temporal_status": "unknown", "uncertainty": [], "supersedes": null, "correction_reason": null, "contract_version": "2", "source_identifiers": [], "domain_bindings": [], "disclosures": [], "set_identifier": {"namespace": "clinrx.synthetic.micro", "code": "sample-1", "version": "1", "raw_display": "sample-1"}, "collected": {"status": "known", "precision": "instant", "value": "2026-10-08T08:00:00Z", "lower": null, "upper": null, "uncertainty": null}}, {"kind": "blood_culture_bottle", "id": "demo-BOTTLE", "revision": "1", "binding": {"target": {"patient_id": "synthetic-p1", "encounter_id": "synthetic-e1", "longitudinal_context_id": null}, "verification": {"status": "verified", "method": "synthetic-demo", "verifier": "synthetic-system", "assessed_at": "2026-10-08T08:00:00Z", "source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "ambiguity": null}}, "origin": "reported", "provenance": {"source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "actor": "synthetic-demo", "recorded_at": "2026-10-08T08:00:00Z", "upstream": [], "lineage": "unknown", "limitations": ["Synthetic source assertion only."]}, "time": {"event": null, "recorded": null, "effective_start": null, "effective_end": null, "retrieved": null, "processed": null, "precision": "unknown", "uncertainty": null}, "verification": "unverified", "conflict": "unknown", "temporal_status": "unknown", "uncertainty": [], "supersedes": null, "correction_reason": null, "contract_version": "2", "source_identifiers": [], "domain_bindings": [{"role": "specimen", "scope": {"patient_id": "synthetic-p1", "encounter_id": "synthetic-e1", "longitudinal_context_id": null}, "status": "resolved", "stable_target": {"kind": "microbiology_specimen", "id": "demo-S"}, "exact": {"kind": "microbiology_specimen", "id": "demo-S", "version": "1"}, "candidates": [], "provenance": {"source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "actor": "synthetic-demo", "recorded_at": "2026-10-08T08:00:00Z", "upstream": [], "lineage": "unknown", "limitations": ["Synthetic source assertion only."]}, "limitation": null}, {"role": "collection_set", "scope": {"patient_id": "synthetic-p1", "encounter_id": "synthetic-e1", "longitudinal_context_id": null}, "status": "resolved", "stable_target": {"kind": "blood_culture_set", "id": "demo-SET"}, "exact": {"kind": "blood_culture_set", "id": "demo-SET", "version": "1"}, "candidates": [], "provenance": {"source": {"namespace": "clinrx.synthetic.demo", "identifier": "patient-state-v1", "version": "1", "channel": "system"}, "actor": "synthetic-demo", "recorded_at": "2026-10-08T08:00:00Z", "upstream": [], "lineage": "unknown", "limitations": ["Synthetic source assertion only."]}, "limitation": null}], "disclosures": [], "bottle_identifier": {"namespace": "clinrx.synthetic.micro", "code": "sample-1", "version": "1", "raw_display": "sample-1"}, "bottle_type": {"raw_display": "Synthetic blood specimen", "coding": null}, "bottle_role": "aerobic", "positive_at": {"status": "not_recorded", "precision": "unknown", "value": null, "lower": null, "upper": null, "uncertainty": null}, "reported_time_to_positivity": null}];

const kindContracts:Record<string,string>={microbiology_specimen:'Specimen',microbiology_direct_examination:'DirectExamination',microbiology_culture:'CultureFinding',microbiology_isolate:'IsolateIdentification',microbiology_susceptibility:'SusceptibilityResult',microbiology_resistance:'ResistanceFinding',microbiology_molecular:'MolecularResult',blood_culture_set:'BloodCultureSet',blood_culture_bottle:'BloodCultureBottle',antimicrobial_order:'AntimicrobialOrder',antimicrobial_administration:'CompletedAntimicrobialAdministration',antimicrobial_non_delivery:'AntimicrobialNonDelivery'};
const variantFixtures=[...state.assembly.snapshot.items.map(i=>i.fact),...bloodVariants];
it.each(variantFixtures)('validates complete $kind variant and rejects missing required identity',fact=>{
  const contract=kindContracts[fact.kind] as Parameters<typeof decodeContract>[0];
  expect(decodeContract(contract,fact)).toBe(fact);
  const missing={...fact} as Record<string,unknown>;delete missing.binding;
  expect(()=>decodeContract(contract,missing)).toThrow(DecodeFailure);
  expect(()=>decodeContract(contract,{...fact,unknown_field:'private'})).toThrow(DecodeFailure);
});

it('honors optional inference and fixed-subtype discriminator defaults without adding them',()=>{
  const raw=clone(prepared);delete (raw.inference as Partial<typeof raw.inference>).kind;
  expect(decodeMicroPrepared(raw).inference).not.toHaveProperty('kind');
  const receipt=clone(execution);delete (receipt.provenance.final_recheck.terminal_facts[0] as {kind?:string}).kind;
  expect(decodeMicroExecution(receipt).provenance.final_recheck.terminal_facts[0]).not.toHaveProperty('kind');
});
it.each([
  {status:'missing',precision:'instant',value:'2026-01-01T00:00:00Z'},
  {status:'known',precision:'instant'},
  {status:'known',precision:'approximate',value:'2026-01-01T00:00:00Z'},
  {status:'known',precision:'bounded',lower:'2026-01-01T02:00:00+01:00',upper:'2026-01-01T00:30:00Z'},
  {status:'known',precision:'bounded',lower:'2026-01-01T00:00:00Z',upper:'2026-01-01T01:00:00Z',value:'2026-01-01T02:00:00Z'}
])('rejects inconsistent recorded-time representation %#',raw=>expect(()=>decodeContract('RecordedTime',raw)).toThrow(DecodeFailure));
it('compares bounded offsets by actual instant with exact microseconds',()=>{
  const raw={status:'known',precision:'bounded',lower:'2026-11-01T01:30:00.000001-04:00',upper:'2026-11-01T01:15:00.000002-05:00'};
  expect(decodeContract('RecordedTime',raw)).toBe(raw);
  expect(()=>decodeContract('RecordedTime',{...raw,lower:'2026-11-01T01:15:00.000003-05:00'})).toThrow(DecodeFailure);
});
it('rejects foreign declared binding scope and contradictory original ingestion metadata',()=>{
  const index=state.assembly.snapshot.items.findIndex(i=>i.fact.kind==='microbiology_isolate');
  expect(()=>decodeMicroState(mutate(state,`assembly.snapshot.items.${index}.fact.domain_bindings.0.scope.patient_id`,'foreign'))).toThrow(DecodeFailure);
  expect(()=>decodeMicroExecution(mutate(execution,'provenance.final_recheck.evidence.0.original_ingestion.ingestion_sequence',999))).toThrow(DecodeFailure);
});
it.each(variantFixtures)('requires $kind subtype-specific nested public structure',fact=>{
  const fields:Record<string,string>={microbiology_specimen:'accession',microbiology_direct_examination:'findings',microbiology_culture:'growth',microbiology_isolate:'organism',microbiology_susceptibility:'antimicrobial',microbiology_resistance:'target',microbiology_molecular:'test_identifier',blood_culture_set:'set_identifier',blood_culture_bottle:'bottle_type',antimicrobial_order:'antimicrobial',antimicrobial_administration:'administered_dose',antimicrobial_non_delivery:'status'};
  const raw={...fact} as Record<string,unknown>;delete raw[fields[fact.kind]];
  expect(()=>decodeContract(kindContracts[fact.kind] as Parameters<typeof decodeContract>[0],raw)).toThrow(DecodeFailure);
});

it('rejects contradictory content for one exact witness identity without hashing clinical data',()=>{
  expect(()=>decodeMicroExecution(mutate(execution,'provenance.final_recheck.evidence.0.terminal_source_digest','a'.repeat(64)))).toThrow(DecodeFailure);
  expect(()=>decodeMicroExecution(mutate(execution,'provenance.final_recheck.inference.terminal_digest','a'.repeat(64)))).toThrow(DecodeFailure);
  expect(()=>decodeMicroExecution(mutate(execution,'provenance.final_recheck.inference.expected_digest','a'.repeat(64)))).toThrow(DecodeFailure);
});
