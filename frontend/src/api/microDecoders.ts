/** Pure M6 decoders: source structure and identity correspondence, never clinical eligibility. */
import {decodeContract,object,array,tuple,ref,factRef,requireRef,stableRef,sameRef,
  distinctReferences,reject,scopeIdentity,executionIdentity,
  type ScopeIdentity,type ExecutionIdentity} from './decoding';
const kinds=['microbiology_specimen','microbiology_isolate','microbiology_susceptibility','antimicrobial_administration'];
const roles=['S','I','U','D'];
function sameIngestion(a:unknown,b:unknown) {
  const x=object(a),y=object(b);
  for(const key of ['repository_id','ingestion_sequence','ingested_at'])if(x[key]!==y[key])reject();
}
function witnessIdentity(original:unknown,terminal:unknown,sourceDigest:unknown,terminalDigest:unknown,before:unknown,after:unknown) {
  const x=object(before),y=object(after);
  if(x.repository_id!==y.repository_id)reject();
  if(sameRef(original,terminal)) {if(sourceDigest!==terminalDigest)reject();sameIngestion(x,y);}
  else if((y.ingestion_sequence as number)<=(x.ingestion_sequence as number))reject();
}
export interface MicroIdentity extends ExecutionIdentity,ScopeIdentity {}
function factScope(value:unknown,expected:ScopeIdentity) {
  const fact=object(value),target=object(object(fact.binding).target);
  scopeIdentity(target,expected);
  for(const binding of array(fact.domain_bindings??[]))scopeIdentity(object(binding).scope,{patient_id:target.patient_id as string,encounter_id:target.encounter_id as string});
}
function inference(value:unknown,expected:MicroIdentity) {
  const i=object(value),inputs=tuple(i.inputs,4);
  if(i.kind!==undefined && i.kind!=='inference' || i.origin!==undefined && i.origin!=='inferred')reject();
  inputs.forEach((r,n)=>{if(ref(r).kind!==kinds[n])reject();});
  distinctReferences(inputs);
  const edges=tuple(object(i.provenance).upstream,4);
  inputs.forEach((r,n)=>{const edge=object(edges[n]);if(edge.relationship!=='derived_from')reject();requireRef(r,edge.target);});
  factScope(i,expected);
  if(expected.inference_reference)requireRef(factRef(i,'inference'),expected.inference_reference);
  return inputs;
}
function includedViews(snapshot:Record<string,unknown>) {
  const items=array(snapshot.items??[]).map(object), references=items.map(i=>factRef(i.fact));
  distinctReferences(references);
  const has=(r:unknown,allowed?:string[])=>{
    const reference=ref(r);
    if(!references.some(x=>sameRef(x,reference)) || allowed && !allowed.includes(reference.kind))reject();
  };
  const micro=object(snapshot.microbiology??{}),anti=object(snapshot.antimicrobial??{});
  const microRefs=array(micro.references??[]);
  microRefs.forEach(r=>has(r,kindsForMicro));
  const declared=[...microRefs];
  for(const [key,kind] of [['orders','antimicrobial_order'],['administrations','antimicrobial_administration'],['non_delivery','antimicrobial_non_delivery']]) {
    const refs=array(anti[key]??[]);refs.forEach(r=>has(r,[kind]));declared.push(...refs);
  }
  distinctReferences(declared);
  if(declared.length!==references.length)reject();
  array(snapshot.medication_references??[]).forEach(r=>has(r,['antimicrobial_order','antimicrobial_administration','antimicrobial_non_delivery']));
  for(const group of array(micro.specimens??[]).map(object)) {
    has(group.specimen,['microbiology_specimen']);
    for(const [key,kind] of [['examinations','microbiology_direct_examination'],['cultures','microbiology_culture'],['isolates','microbiology_isolate'],['molecular_results','microbiology_molecular']]) array(group[key]??[]).forEach(r=>has(r,[kind]));
  }
  for(const group of array(micro.isolates??[]).map(object)) {
    has(group.isolate,['microbiology_isolate']);
    array(group.susceptibilities??[]).forEach(r=>has(r,['microbiology_susceptibility']));
    array(group.resistance_findings??[]).forEach(r=>has(r,['microbiology_resistance']));
  }
  for(const group of array(micro.panels??[]).map(object))array(group.targets).forEach(r=>has(r,['microbiology_molecular']));
}
const kindsForMicro=['microbiology_specimen','microbiology_direct_examination','microbiology_culture','microbiology_isolate','microbiology_susceptibility','microbiology_resistance','microbiology_molecular','blood_culture_set','blood_culture_bottle'];
export function decodeMicroState(value:unknown,expected:ScopeIdentity={}) {
  return decodeContract('MicroStateResponse',value,v=>{
    const assembly=object(v.assembly),request=object(assembly.request),snapshot=object(assembly.snapshot);
    const scope=object(request.scope), other=object(snapshot.scope);
    scopeIdentity(scope,expected);scopeIdentity(other,{patient_id:scope.patient_id as string,encounter_id:scope.encounter_id as string});
    for(const key of ['review_start','review_end'])if(scope[key]!==other[key])reject();
    const cutoff=object(scope.repository_cutoff),sc=object(other.repository_cutoff);
    for(const key of ['repository_id','fact_watermark','captured_at'])if(cutoff[key]!==sc[key])reject();
    for(const item of array(snapshot.items??[]).map(object)) {
      factScope(item.fact,{patient_id:scope.patient_id as string,encounter_id:scope.encounter_id as string});
      const meta=item.ingestion;
      if(meta!==null && meta!==undefined && object(meta).repository_id!==cutoff.repository_id)reject();
    }
    includedViews(snapshot);
  });
}
export function decodeMicroPrepared(value:unknown,expected:MicroIdentity={}) {
  return decodeContract('MicroPreparedResponse',value,v=>{executionIdentity(v,expected);inference(v.inference,expected);});
}
export function decodeMicroExecution(value:unknown,expected:MicroIdentity={}) {
  return decodeContract('MicroExecutionResponse',value,v=>{
    executionIdentity(v,expected);
    const p=object(v.provenance),recheck=object(p.final_recheck),scope=object(recheck.scope);
    scopeIdentity(scope,expected);
    const identity={...expected,patient_id:scope.patient_id as string,encounter_id:scope.encounter_id as string};
    const inputs=inference(p.inference,identity),items=tuple(p.consumed,4).map(object);
    const witnesses=tuple(recheck.evidence,4).map(object),terminals=tuple(recheck.terminal_facts,4);
    const statuses=tuple(p.witness_statuses,4);
    for(let n=0;n<4;n++) {
      const item=items[n],w=witnesses[n],fact=item.fact;
      requireRef(inputs[n],factRef(fact));requireRef(w.consumed,inputs[n]);
      if(w.role!==roles[n])reject();
      witnessIdentity(w.consumed,w.terminal,w.source_digest,w.terminal_source_digest,w.original_ingestion,w.terminal_ingestion);
      stableRef(w.consumed,w.terminal);requireRef(w.terminal,factRef(terminals[n],kinds[n]));
      if(w.item_digest!==item.expected_digest)reject();
      if(statuses[n]!== (sameRef(w.consumed,w.terminal)?'current':'superseded'))reject();
      factScope(fact,identity);factScope(terminals[n],identity);
      if(item.ingestion!==null && item.ingestion!==undefined) {
        sameIngestion(w.original_ingestion,item.ingestion);
      }
    }
    const iw=object(recheck.inference),i=object(p.inference);
    witnessIdentity(iw.reference,iw.terminal,iw.observed_digest,iw.terminal_digest,iw.ingestion,iw.terminal_ingestion);
    if(iw.expected_digest!==iw.observed_digest)reject();
    requireRef(iw.reference,factRef(i,'inference'));requireRef(iw.method,i.method);stableRef(iw.reference,iw.terminal);
    const witnessInputs=tuple(iw.inputs,4),dependencies=tuple(iw.dependencies,4),declarations=tuple(iw.declarations,4);
    inputs.forEach((r,n)=>{requireRef(r,witnessInputs[n]);requireRef(r,dependencies[n]);const edge=object(declarations[n]);if(edge.relationship!=='derived_from')reject();requireRef(r,edge.target);});
    const cutoffs=[p.original_cutoff,p.inference_cutoff,recheck.inference_cutoff,recheck.final_cutoff,scope.repository_cutoff].map(object);
    if(cutoffs.some(c=>c.repository_id!==cutoffs[0].repository_id))reject();
    for(const [a,b] of [[cutoffs[0],cutoffs[4]],[cutoffs[1],cutoffs[2]]])for(const key of ['repository_id','fact_watermark','captured_at'])if(a[key]!==b[key])reject();
    const outcome=object(v.governance).outcome;
    if(outcome==='released' && (typeof v.statement!=='string' || v.statement!==i.statement))reject();
    if(outcome==='withheld' && v.statement!==null)reject();
  });
}
export const decodeMicroRetainedExecution=decodeMicroExecution;
export function decodeMicroReconciliation(value:unknown,expected:MicroIdentity={}) {
  return decodeContract('MicroReconciliationResponse',value,v=>{
    if(v.status==='committed_match')decodeMicroExecution(v.execution,expected);
    else if(v.execution!==null)reject();
  });
}
export type MicroStateResponse=ReturnType<typeof decodeMicroState>;
export type MicroPreparedResponse=ReturnType<typeof decodeMicroPrepared>;
export type MicroExecutionResponse=ReturnType<typeof decodeMicroExecution>;
export type MicroReconciliationResponse=ReturnType<typeof decodeMicroReconciliation>;
