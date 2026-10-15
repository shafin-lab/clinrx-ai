import {ReviewClient} from './client';
import type {MicroPreparation,MicroPrepared} from './microTypes';
import {decodeMicroState,decodeMicroPrepared,decodeMicroExecution,decodeMicroRetainedExecution,decodeMicroReconciliation} from './microDecoders';
export class MicroReviewClient extends ReviewClient {
  microState(start:string,end:string) {
    return this.request('/patient-state-v2?'+new URLSearchParams({review_start:start,review_end:end}),raw=>decodeMicroState(raw,this.scope));
  }
  microPrepare(body:MicroPreparation) {
    return this.request('/micro-antimicrobial-review-preparations',raw=>decodeMicroPrepared(raw,{...this.scope,execution_id:body.execution_id}),body);
  }
  microExecute(prepared:MicroPrepared) {
    return this.request('/micro-antimicrobial-reviews',raw=>decodeMicroExecution(raw,{...this.scope,execution_id:prepared.execution_id,inference_reference:this.inferenceReference(prepared)}),{command:prepared.command});
  }
  microLookup(id:string) {
    return this.request('/micro-antimicrobial-reviews/'+encodeURIComponent(id),raw=>decodeMicroRetainedExecution(raw,{...this.scope,execution_id:id}));
  }
  microReconcile(prepared:MicroPrepared) {
    return this.request('/micro-antimicrobial-review-reconciliations',raw=>decodeMicroReconciliation(raw,{...this.scope,execution_id:prepared.execution_id,inference_reference:this.inferenceReference(prepared)}),{command:prepared.command});
  }
  private inferenceReference(prepared:MicroPrepared) {
    return {kind:prepared.inference.kind??'inference',id:prepared.inference.id,version:prepared.inference.revision};
  }
}
