import type { PatientState, PreparationRequest, Prepared, Execution, Reconciliation, FieldError } from './types';
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
  return value.slice(0,20).filter((v): v is FieldError => object(v) && typeof v.path==='string' && v.path.length<=256 && allowed.test(v.path) && ['missing','extra_forbidden','invalid_type','invalid_value','too_long'].includes(String(v.code)));
}
export interface Reply<T> { data: T; mode: string|null }
export class ReviewClient {
  private path: string;
  constructor(base: string, patient: string, encounter: string, private fetcher: typeof fetch = fetch) {
    const url = new URL(base);
    if (!['http:','https:'].includes(url.protocol) || !['127.0.0.1','localhost','[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname!=='/') throw new Error('Configure a loopback API origin.');
    this.path = url.origin+'/api/v1/patients/'+encodeURIComponent(patient)+'/encounters/'+encodeURIComponent(encounter);
  }
  protected async request<T>(suffix: string, body?: unknown): Promise<Reply<T>> {
    let response: Response;
    const fetcher = this.fetcher;
    try { response = await fetcher(this.path+suffix, {method:body===undefined?'GET':'POST', cache:'no-store', credentials:'omit', headers:body===undefined?undefined:{'Content-Type':'application/json'}, body:body===undefined?undefined:JSON.stringify(body)}); }
    catch { throw new ApiFailure('network_error'); }
    let raw: unknown;
    try { raw=await response.json(); } catch { throw new ApiFailure('invalid_response',response.status); }
    if (!response.ok) {
      const code=object(raw) ? raw.code ?? raw.status : null;
      throw new ApiFailure(typeof code==='string' && Object.hasOwn(messages,code)?code:'internal_error',response.status,response.headers.get('X-ClinRx-Stage'),object(raw)?fields(raw.fields):[]);
    }
    if (!object(raw)) throw new ApiFailure('invalid_response',response.status);
    return {data:raw as T,mode:response.headers.get('X-ClinRx-Mode')};
  }
  state(start: string,end: string) { return this.request<PatientState>('/state?'+new URLSearchParams({review_start:start,review_end:end})); }
  async prepare(body: PreparationRequest) {
    const reply=await this.request<Prepared>('/temporal-review-preparations',body);
    if (reply.data.status!=='prepared' || reply.data.execution_id!==body.execution_id || typeof reply.data.command!=='string' || !reply.data.command) throw new ApiFailure('invalid_response');
    return reply;
  }
  async execute(prepared: Prepared) {
    const reply=await this.request<Execution>('/temporal-reviews',{command:prepared.command});
    this.match(reply.data,prepared.execution_id); return reply;
  }
  async lookup(id: string) { const reply=await this.request<Execution>('/temporal-executions/'+encodeURIComponent(id)); this.match(reply.data,id); return reply; }
  async reconcile(prepared: Prepared) {
    const reply=await this.request<Reconciliation>('/temporal-executions/'+encodeURIComponent(prepared.execution_id)+'/reconcile',{command:prepared.command});
    if (reply.data.status==='committed_match') this.match(reply.data.execution,prepared.execution_id);
    else if (reply.data.status!=='absent' || reply.data.execution!==null) throw new ApiFailure('invalid_response');
    return reply;
  }
  private match(value: Execution,id: string) { if (!value || value.execution_id!==id || value.status!=='completed' || !['released','withheld'].includes(value.governance?.outcome)) throw new ApiFailure('invalid_response'); }
}
