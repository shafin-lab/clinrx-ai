/** M7 structural transport and exact correspondence only; no clinical eligibility. */
import bundle from './circulatorySchemas.json';
import {validateTransportSchema,type Schema,object,array,scopeIdentity,executionIdentity,requireRef,factRef,ref,distinctReferences,reject,sameRef,stableRef,type ExecutionIdentity,type ScopeIdentity} from './decoding';
import type {CirculatoryState,CirculatoryPrepared,CirculatoryExecution,CirculatoryReconciliation,CirculatoryHistory} from './circulatoryTypes';
const schemas=bundle as unknown as {roots:Record<string,Schema>;definitions:Record<string,Schema>};
function validate(name:string,value:unknown) {validateTransportSchema(value,schemas.roots[name],schemas.definitions);return object(value);}
function factScope(value:unknown,expected:ScopeIdentity) {
  const f=object(value);scopeIdentity(object(f.binding).target,expected);
  for(const binding of array(f.associations??[]))scopeIdentity(object(binding).scope,expected);
}
function inference(value:unknown,expected:ScopeIdentity&ExecutionIdentity) {
  const i=object(value);factScope(i,expected);
  if(i.origin!=='inferred' || i.kind!=='inference')reject();
  const inputs=array(i.inputs);if(inputs.length<3 || inputs.length>35)reject();distinctReferences(inputs);
  const edges=array(object(i.provenance).upstream);if(edges.length!==inputs.length)reject();
  for(let n=0;n<inputs.length;n++){const edge=object(edges[n]);if(edge.relationship!=='derived_from')reject();requireRef(inputs[n],edge.target);}
  const kinds=['circulatory_pressure','circulatory_lactate','circulatory_vasoactive'];
  kinds.forEach((kind,n)=>{if(ref(inputs[n]).kind!==kind)reject();});
  if(expected.inference_reference)requireRef(factRef(i),expected.inference_reference);
  return inputs;
}
function same(a:unknown,b:unknown):boolean {
  if(a===b)return true;
  if(Array.isArray(a)&&Array.isArray(b))return a.length===b.length&&a.every((v,n)=>same(v,b[n]));
  if(a&&b&&typeof a==='object'&&typeof b==='object'){
    const x=object(a),y=object(b);return Object.keys(x).length===Object.keys(y).length&&Object.keys(x).every(k=>Object.hasOwn(y,k)&&same(x[k],y[k]));
  }
  return false;
}
function itemScope(value:unknown,scope:Record<string,unknown>) {
  const item=object(value);factScope(item.fact,scope as ScopeIdentity);
  const cutoff=object(scope.repository_cutoff),meta=object(item.ingestion);
  if(meta.repository_id!==cutoff.repository_id || (meta.ingestion_sequence as number)>(cutoff.fact_watermark as number))reject();
}
function ingestionWithin(value:unknown,cutoff:Record<string,unknown>,after=0) {
  const meta=object(value),sequence=meta.ingestion_sequence as number;
  if(meta.repository_id!==cutoff.repository_id || sequence<=after || sequence>(cutoff.fact_watermark as number))reject();
  return meta;
}
export function decodeCirculatoryState(value:unknown,expected:ScopeIdentity={}) {
  const v=validate('CirculatoryStateResponse',value),a=object(v.assembly),request=object(a.request),snapshot=object(a.snapshot),scope=object(request.scope);
  scopeIdentity(scope,expected);if(!same(request,v.assembly_request)||!same(scope,snapshot.scope))reject();
  const items=array(snapshot.items);distinctReferences(items.map(i=>factRef(object(i).fact)));
  const stable=items.map(i=>{const r=factRef(object(i).fact);return JSON.stringify([r.kind,r.id]);});if(new Set(stable).size!==items.length)reject();
  items.forEach(i=>itemScope(i,scope));
  if(object(snapshot.coverage).retained_count!==items.length)reject();
  return value as CirculatoryState;
}
export function decodeCirculatoryPrepared(value:unknown,expected:ScopeIdentity&ExecutionIdentity={}) {
  const v=validate('CirculatoryPreparedResponse',value);executionIdentity(v,expected);inference(v.inference,expected);return value as CirculatoryPrepared;
}
export function decodeCirculatoryExecution(value:unknown,expected:ScopeIdentity&ExecutionIdentity={}) {
  const v=validate('CirculatoryExecutionResponse',value);executionIdentity(v,expected);
  const record=object(v.record),request=object(record.request),ir=object(request.inference_request),scope=object(ir.scope);
  if(request.execution_id!==v.execution_id)reject();scopeIdentity(scope,expected);
  scopeIdentity(object(request.target).context,expected);
  const identity={...expected,patient_id:scope.patient_id as string,encounter_id:scope.encounter_id as string};
  scopeIdentity(object(request.target).context,identity);
  const evidence=object(record.evidence);if(!same(evidence.request,request))reject();
  const inputs=inference(evidence.inference,identity),items=array(evidence.items),facts=array(evidence.facts);
  if(new Set(items.map(item=>object(object(item).ingestion).ingestion_sequence)).size!==items.length)reject();
  const pins=[ir.pressure,ir.lactate,ir.vasopressor,...array(ir.supporting??[])];
  const recheck=object(record.final_recheck),witnesses=array(recheck.evidence),terminals=array(recheck.terminal_facts);
  if(!same(recheck.scope,scope)||items.length!==inputs.length||facts.length!==inputs.length||pins.length!==inputs.length||witnesses.length!==inputs.length||terminals.length!==inputs.length)reject();
  const original=object(scope.repository_cutoff),inferenceCutoff=object(request.inference_cutoff),finalCutoff=object(recheck.final_cutoff);
  if(!same(object(request.assembly_request).scope,scope)||!same(recheck.inference_cutoff,inferenceCutoff)||
    original.repository_id!==inferenceCutoff.repository_id||original.repository_id!==finalCutoff.repository_id||
    (original.fact_watermark as number)>=(inferenceCutoff.fact_watermark as number)||
    (inferenceCutoff.fact_watermark as number)>(finalCutoff.fact_watermark as number))reject();
  const originalInference=object(evidence.inference),iw=object(recheck.inference);
  const inferenceRef={kind:'inference',id:ir.inference_id,version:ir.revision};
  requireRef(factRef(originalInference),inferenceRef);requireRef(iw.reference,inferenceRef);stableRef(iw.reference,iw.terminal);
  if(iw.expected_digest!==request.expected_inference_digest||iw.observed_digest!==request.expected_inference_digest||
    iw.reconstruction_digest!==iw.observed_digest||!same(iw.method,originalInference.method)||
    !same(iw.inputs,inputs)||!same(iw.dependencies,inputs)||!same(iw.declarations,object(originalInference.provenance).upstream)||
    !same(iw.ingestion,evidence.inference_ingestion))reject();
  const inferenceIngestion=ingestionWithin(iw.ingestion,inferenceCutoff,original.fact_watermark as number);
  ingestionWithin(iw.terminal_ingestion,finalCutoff);
  if(sameRef(iw.reference,iw.terminal)) {
    if(iw.observed_digest!==iw.terminal_digest||!same(iw.ingestion,iw.terminal_ingestion))reject();
  } else if((object(iw.terminal_ingestion).ingestion_sequence as number)<=(inferenceIngestion.ingestion_sequence as number))reject();
  for(let n=0;n<inputs.length;n++) {
    const item=object(items[n]),pin=object(pins[n]),w=object(witnesses[n]);
    requireRef(inputs[n],pin.reference);requireRef(inputs[n],factRef(item.fact));requireRef(inputs[n],factRef(facts[n]));requireRef(inputs[n],w.consumed);
    if(w.role!==(n===0?'P':n===1?'L':n===2?'V':'support')||!same(w.original_ingestion,item.ingestion))reject();
    if(!same(item.fact,facts[n]) || item.expected_digest!==pin.expected_digest || w.item_digest!==pin.expected_digest || w.source_digest!==pin.expected_digest)reject();
    itemScope(item,scope);factScope(terminals[n],identity);stableRef(inputs[n],w.terminal);requireRef(w.terminal,factRef(terminals[n]));
    ingestionWithin(w.terminal_ingestion,finalCutoff);
    if(sameRef(w.consumed,w.terminal)&& (w.source_digest!==w.terminal_source_digest||!same(w.original_ingestion,w.terminal_ingestion)))reject();
    if(!sameRef(w.consumed,w.terminal)&& (object(w.terminal_ingestion).ingestion_sequence as number)<=(object(w.original_ingestion).ingestion_sequence as number))reject();
  }
  const decision=object(record.decision),assessment=object(decision.assessment),state=object(assessment.state);
  const review=object(assessment.review),candidate=object(review.candidate),snapshot=object(candidate.snapshot),rendering=object(review.rendering);
  if(decision.actor!==request.actor||!same(assessment.target,request.target)||!same(state.target,request.target)||
    !same(object(state.authorization).target,request.target)||!same(object(assessment.content_validation).target,request.target)||
    !same(snapshot.facts,[originalInference])||!same(snapshot.binding,originalInference.binding)||
    rendering.destination!==object(request.target).destination)reject();
  if(decision.outcome==='released') {if(v.statement!==rendering.content||v.statement!==object(evidence.inference).statement)reject();}
  else if(v.statement!==null)reject();
  return value as CirculatoryExecution;
}
export function decodeCirculatoryReconciliation(value:unknown,expected:ScopeIdentity&ExecutionIdentity={}) {
  const v=validate('CirculatoryReconciliationResponse',value);
  if(v.status==='committed_match')decodeCirculatoryExecution(v.execution,expected);else if(v.execution!==null)reject();
  return value as CirculatoryReconciliation;
}
export function decodeCirculatoryHistory(value:unknown,expected:ScopeIdentity&{reference?:unknown}={}) {
  const v=validate('CirculatoryHistoryResponse',value),scope=object(object(object(v.context).assembly_request).scope);
  scopeIdentity(scope,expected);if(expected.reference)requireRef(v.reference,expected.reference);
  const revisions=array(v.revisions);distinctReferences(revisions.map(i=>factRef(object(i).fact)));
  for(const entry of revisions){itemScope(entry,scope);stableRef(factRef(object(entry).fact),v.reference);}
  if(!revisions.some(i=>sameRef(factRef(object(i).fact),v.reference)))reject();
  return value as CirculatoryHistory;
}
