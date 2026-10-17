/** Pure M5 response decoders. Deliberately not connected to the HTTP client in H1-C1. */
import {decodeContract,object,array,tuple,ref,requireRef,stableRef,distinctReferences,reject,
  executionIdentity,scopeIdentity,type ExecutionIdentity,type ScopeIdentity} from './decoding';

export function decodePatientState(value:unknown,expected:ScopeIdentity={}) {
  return decodeContract('PatientStateViewResponse',value,v=>scopeIdentity(v.scope,expected));
}
export function decodePrepared(value:unknown,expected:ExecutionIdentity={}) {
  return decodeContract('PreparedTemporalReviewResponse',value,v=>{
    executionIdentity(v,expected);
    if(ref(v.inference_reference).kind!=='inference')reject();
    if(expected.inference_reference)requireRef(v.inference_reference,expected.inference_reference);
  });
}
export function decodeExecution(value:unknown,expected:ExecutionIdentity={}) {
  return decodeContract('TemporalExecutionResponse',value,v=>{
    executionIdentity(v,expected);
    const p=object(v.provenance), inference=object(p.inference), g=object(v.governance);
    const inputs=tuple(inference.inputs,3);
    distinctReferences(inputs);
    if(expected.inference_reference)requireRef(inference.reference,expected.inference_reference);
    if(ref(inference.reference).kind!=='inference')reject();
    const evidence=[p.earlier_laboratory,p.later_laboratory,p.medication];
    const terminals=tuple(p.terminal_references,3), edges=tuple(p.direct_dependencies,3);
    inputs.forEach((input,i)=>{
      requireRef(input,object(evidence[i]).reference);
      requireRef(input,object(edges[i]).target);
      stableRef(input,terminals[i]);
    });
    const context=tuple(object(v.context).evidence_references,4);
    [...inputs,inference.reference].forEach((r,i)=>requireRef(r,context[i]));
    stableRef(inference.reference,p.inference_terminal_reference);
    if(g.outcome==='released' && typeof inference.statement!=='string')reject();
    if(g.outcome==='withheld' && inference.statement!==null && inference.statement!==undefined)reject();
    const cutoffs=[p.input_cutoff,p.inference_cutoff,p.final_cutoff].map(object);
    if(cutoffs.some(c=>c.repository_id!==cutoffs[0].repository_id))reject();
  });
}
export const decodeRetainedExecution=decodeExecution;
export function decodeReconciliation(value:unknown,expected:ExecutionIdentity={}) {
  return decodeContract('ReconciliationResponse',value,v=>{
    if(v.status==='committed_match')decodeExecution(v.execution,expected);
    else if(v.execution!==null)reject();
  });
}
// Export inferred wire types, including backend-declared optional fields. Existing client/UI types
// are not silently tightened or normalized; H1-C2 must explicitly adopt these decoded contracts.
export type PatientStateResponse=ReturnType<typeof decodePatientState>;
export type PreparedResponse=ReturnType<typeof decodePrepared>;
export type ExecutionResponse=ReturnType<typeof decodeExecution>;
export type ReconciliationResponse=ReturnType<typeof decodeReconciliation>;
