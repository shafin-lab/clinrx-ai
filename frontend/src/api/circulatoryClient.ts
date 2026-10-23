import {ReviewClient} from './client';
import {decodeCirculatoryState,decodeCirculatoryPrepared,decodeCirculatoryExecution,decodeCirculatoryReconciliation,decodeCirculatoryHistory} from './circulatoryDecoders';
import type {CirculatoryPreparation,CirculatoryPrepared,ExactRef} from './circulatoryTypes';
export class CirculatoryClient extends ReviewClient {
  circulatoryState(start:string,end:string){return this.request('/patient-state-v3?'+new URLSearchParams({review_start:start,review_end:end}),raw=>decodeCirculatoryState(raw,this.scope));}
  circulatoryPrepare(body:CirculatoryPreparation){return this.request('/circulatory-review-preparations',raw=>decodeCirculatoryPrepared(raw,{...this.scope,execution_id:body.execution_id}),body);}
  circulatoryExecute(prepared:CirculatoryPrepared){return this.request('/circulatory-reviews',raw=>decodeCirculatoryExecution(raw,this.identity(prepared)),{command:prepared.command});}
  circulatoryLookup(id:string){return this.request('/circulatory-reviews/'+encodeURIComponent(id),raw=>decodeCirculatoryExecution(raw,{...this.scope,execution_id:id}));}
  circulatoryReconcile(prepared:CirculatoryPrepared){return this.request('/circulatory-review-reconciliations',raw=>decodeCirculatoryReconciliation(raw,this.identity(prepared)),{command:prepared.command});}
  circulatoryHistory(context:string,reference:ExactRef){return this.request('/circulatory-evidence-history',raw=>decodeCirculatoryHistory(raw,{...this.scope,reference}),{state_context:context,reference});}
  private identity(p:CirculatoryPrepared){return {...this.scope,execution_id:p.execution_id,inference_reference:{kind:'inference',id:p.inference.id,version:p.inference.revision}};}
}
