import bundle from './circulatorySchemas.json';
import {validateTransportSchema,type Schema} from './decoding';
import type {CirculatoryItem} from './circulatoryTypes';
export type Draft={repository_id:string;fact:CirculatoryItem['fact'];predecessor_digest:string|null};
export type Evidence={repository_id:string;fact:CirculatoryItem['fact'];expected_digest:string;canonical_fact:string;ingestion:CirculatoryItem['ingestion']|null};
export type Recovery={status:'absent'}|{status:'committed_match';evidence:Evidence};
const prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-evidence';
export const stable=(v:unknown):string=>JSON.stringify(v,(_key,value:unknown)=>value&&typeof value==='object'&&!Array.isArray(value)?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b))):value);
async function decode(raw:unknown,body:Draft,saved:boolean):Promise<Evidence>{
  if(!raw||typeof raw!=='object')throw Error('invalid_response');
  const e=raw as Evidence;
  const schemas=bundle as unknown as {definitions:Record<string,Schema>};
  const factSchema=schemas.definitions.CirculatoryHistoricalFact.properties?.fact;
  if(!factSchema)throw Error('invalid_response');
  validateTransportSchema(e.fact,factSchema,schemas.definitions);
  if(saved)validateTransportSchema({fact:e.fact,ingestion:e.ingestion},schemas.definitions.CirculatoryHistoricalFact,schemas.definitions);
  else if(e.ingestion!==null)throw Error('invalid_response');
  if(e.repository_id!==body.repository_id||e.fact.kind!==body.fact.kind||e.fact.id!==body.fact.id||e.fact.revision!==body.fact.revision||e.fact.binding.target.patient_id!=='synthetic-p1'||e.fact.binding.target.encounter_id!=='synthetic-e1')throw Error('invalid_response');
  if(typeof e.canonical_fact!=='string'||stable(JSON.parse(e.canonical_fact))!==stable(e.fact))throw Error('invalid_response');
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(e.canonical_fact))),b=>b.toString(16).padStart(2,'0')).join('');
  if(digest!==e.expected_digest || (saved&&(stable(e.fact)!==stable(body.fact)||!e.ingestion||e.ingestion.repository_id!==body.repository_id)))throw Error('invalid_response');
  return e;
}
export class EvidenceEntryClient{
  constructor(private send:typeof fetch=fetch){}
  private async post(path:string,body:Draft){
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const send=this.send;
      const response=await send(prefix+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal,redirect:'error',credentials:'same-origin'});
      if(!response.ok)throw Error(response.status===409?'conflict':response.status===422?'invalid_draft':'unconfirmed');
      return await response.json() as unknown;
    }finally{clearTimeout(timer);}
  }
  async validate(body:Draft){return decode(await this.post('/validate',body),body,false);}
  async save(body:Draft){return decode(await this.post('',body),body,true);}
  async lookup(body:Draft):Promise<Recovery>{
    const raw=await this.post('/lookup',body) as Record<string,unknown>;
    if(raw?.status==='absent'&&Object.keys(raw).length===1)return {status:'absent'};
    if(raw?.status!=='committed_match')throw Error('invalid_response');
    return {status:'committed_match',evidence:await decode(raw.evidence,body,true)};
  }
}
