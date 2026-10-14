import { ApiFailure, ReviewClient } from './client';
import type { MicroState, MicroPreparation, MicroPrepared, MicroExecution, MicroReconciliation } from './microTypes';
export class MicroReviewClient extends ReviewClient {
  async microState(start:string,end:string) {
    const reply=await this.request<MicroState>('/patient-state-v2?'+new URLSearchParams({review_start:start,review_end:end}));
    if (!reply.data.assembly?.snapshot || !Array.isArray(reply.data.assembly.snapshot.items) || typeof reply.data.state_context!=='string') throw new ApiFailure('invalid_response');
    return reply;
  }
  async microPrepare(body:MicroPreparation) {
    const reply=await this.request<MicroPrepared>('/micro-antimicrobial-review-preparations',body);
    if (reply.data.status!=='prepared' || reply.data.execution_id!==body.execution_id || !reply.data.inference || typeof reply.data.command!=='string' || !reply.data.command) throw new ApiFailure('invalid_response');
    return reply;
  }
  async microExecute(prepared:MicroPrepared) {
    const reply=await this.request<MicroExecution>('/micro-antimicrobial-reviews',{command:prepared.command});
    this.microMatch(reply.data,prepared.execution_id);return reply;
  }
  async microLookup(id:string) {
    const reply=await this.request<MicroExecution>('/micro-antimicrobial-reviews/'+encodeURIComponent(id));
    this.microMatch(reply.data,id);return reply;
  }
  async microReconcile(prepared:MicroPrepared) {
    const reply=await this.request<MicroReconciliation>('/micro-antimicrobial-review-reconciliations',{command:prepared.command});
    if (reply.data.status==='committed_match') this.microMatch(reply.data.execution,prepared.execution_id);
    else if (reply.data.status!=='absent' || reply.data.execution!==null) throw new ApiFailure('invalid_response');
    return reply;
  }
  private microMatch(value:MicroExecution,id:string) {
    if (!value || value.status!=='completed' || value.execution_id!==id || !['released','withheld'].includes(value.governance?.outcome) || !value.provenance?.inference || !Array.isArray(value.provenance.consumed) || (value.governance.outcome==='withheld' && value.statement!==null)) throw new ApiFailure('invalid_response');
  }
}
