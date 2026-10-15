import type { PreparationRequest, Prepared, FieldError } from './types';
import {decodePatientState,decodePrepared,decodeExecution,decodeRetainedExecution,decodeReconciliation} from './decoders';
const messages: Record<string,string> = {
  invalid_request:'Invalid request. Check the supplied fields.', unsupported_review_input:'The backend could not accept the selected evidence.',
  invalid_command:'Invalid execution command.', invalid_state_context:'Invalid state context. Load state again.',
  not_found:'Execution or context not found / unavailable.', execution_conflict:'Execution conflict: the request differs from retained content.',
  storage_integrity_failure:'Stored content failed integrity validation.', storage_unavailable:'Storage is unavailable.',
  transaction_failed:'The transaction could not be completed.', completion_unknown:'Completion could not be confirmed.',
  request_too_large:'Request size limit exceeded.', bounded_view_limit_exceeded:'The bounded view limit was exceeded.',
  internal_error:'The request could not be completed.', method_not_allowed:'Operation not available.',
  network_error:'The server response could not be confirmed.', invalid_response:'The server response could not be read safely.'
};
export class ApiFailure extends Error {
  constructor(public code: string, public status=0, public stage: string|null=null, public fields: FieldError[] = []) { super(messages[code] ?? messages.internal_error); }
}
function object(value: unknown): value is Record<string,unknown> { return typeof value==='object' && value!==null && !Array.isArray(value); }
function fields(value: unknown): FieldError[] {
  const allowed = /^(body|query|path|execution_id|command|state_context|earlier_laboratory|later_laboratory|medication|reference|expected_digest|kind|id|version|patient_id|encounter_id|review_start|review_end|field)(\.(body|query|path|execution_id|command|state_context|earlier_laboratory|later_laboratory|medication|reference|expected_digest|kind|id|version|patient_id|encounter_id|review_start|review_end|field))*$/;
  if (!Array.isArray(value)) return [];
  return value.slice(0,20).filter((v): v is FieldError => object(v) && typeof v.path==='string' && v.path.length<=256 && allowed.test(v.path) && typeof v.code==='string' && ['missing','extra_forbidden','invalid_type','invalid_value','too_long'].includes(v.code)).map(v=>({path:v.path,code:v.code}));
}
export interface Reply<T> { data: T; mode: string|null }
export class ReviewClient {
  private path: string;
  protected readonly scope: {patient_id:string;encounter_id:string};
  constructor(base: string, patient: string, encounter: string, private fetcher: typeof fetch = fetch) {
    this.scope={patient_id:patient,encounter_id:encounter};
    const url = new URL(base);
    if (!['http:','https:'].includes(url.protocol) || !['127.0.0.1','localhost','[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname!=='/') throw new Error('Configure a loopback API origin.');
    this.path = url.origin+'/api/v1/patients/'+encodeURIComponent(patient)+'/encounters/'+encodeURIComponent(encounter);
  }
  protected async request<T>(suffix: string, decode:(value:unknown)=>T, body?: unknown): Promise<Reply<T>> {
    let response: Response;
    const fetcher = this.fetcher;
    try { response = await fetcher(this.path+suffix, {method:body===undefined?'GET':'POST', cache:'no-store', credentials:'omit', headers:body===undefined?undefined:{'Content-Type':'application/json'}, body:body===undefined?undefined:JSON.stringify(body)}); }
    catch { throw new ApiFailure('network_error'); }
    let raw: unknown;
    try { raw=await response.json(); } catch { throw new ApiFailure('invalid_response',response.status); }
    if (!response.ok) {
      const code=object(raw) ? raw.code ?? raw.status : null;
      throw new ApiFailure(typeof code==='string' && Object.hasOwn(messages,code)?code:'internal_error',response.status,response.headers.get('X-ClinRx-Stage')==='inference_preparation'?'inference_preparation':null,object(raw)?fields(raw.fields):[]);
    }
    let data:T;
    try { data=decode(raw); } catch { throw new ApiFailure('invalid_response',response.status); }
    return {data,mode:response.headers.get('X-ClinRx-Mode')};
  }
  state(start:string,end:string) {
    return this.request('/state?'+new URLSearchParams({review_start:start,review_end:end}),raw=>decodePatientState(raw,this.scope));
  }
  prepare(body:PreparationRequest) {
    return this.request('/temporal-review-preparations',raw=>decodePrepared(raw,{execution_id:body.execution_id}),body);
  }
  execute(prepared:Prepared) {
    return this.request('/temporal-reviews',raw=>decodeExecution(raw,{execution_id:prepared.execution_id,inference_reference:prepared.inference_reference}),{command:prepared.command});
  }
  lookup(id:string) {
    return this.request('/temporal-executions/'+encodeURIComponent(id),raw=>decodeRetainedExecution(raw,{execution_id:id}));
  }
  reconcile(prepared:Prepared) {
    return this.request('/temporal-executions/'+encodeURIComponent(prepared.execution_id)+'/reconcile',raw=>decodeReconciliation(raw,{execution_id:prepared.execution_id,inference_reference:prepared.inference_reference}),{command:prepared.command});
  }
}
