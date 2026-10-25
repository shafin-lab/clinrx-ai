import type {DoseReview} from '../antibioticWorkflow/renalDoseModel';
import generated from './antibioticSchemas.json';
import {readRF2JSON,parseRF2JSON} from './rf2JSON';
import {decodeRF2Catalog,hash,stable,type Catalog,type Ref,type Fact} from './rf2Client';
import {decodeMicroState} from './microDecoders';
import type {MicroState} from './microTypes';
import {decodeContract,object,reject,validateTransportSchema,type Schema} from './decoding';
export interface AntibioticDraft{dose_review?:DoseReview|null;dose_review_amendment?:true|null;repository:string;id:string;revision:string;mode:'prescription'|'given'|'held'|'missed'|'refused'|'not_given';medicine:string;product:string;amount:string|null;unit:'mg'|'g'|'IU'|null;dose_detail:string|null;route:string;schedule:string|null;indication:string;point:string;actor:string;source_record:string;recorded_at:string;order:Ref|null;culture_ref:Ref|null;predecessor:Ref|null;predecessor_digest:string|null;correction_reason:string|null}
export interface AntibioticBundle{version:'SyntheticAntibiotics/v1';renal:Catalog;micro:MicroState;execution_enabled:false}
export interface AntibioticResult{status:'validated'|'saved'|'absent';request_canonical:string;request_digest:string;execution_enabled:false;fact?:Fact;canonical_fact?:string;digest?:string;ingestion?:{repository_id:string;ingestion_sequence:number}|null}
const schema=generated as unknown as {roots:Record<string,Schema>;definitions:Record<string,Schema>};
const prefix='/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-antibiotics';
export function validateAntibioticDraft(value:unknown):asserts value is AntibioticDraft{validateTransportSchema(value,schema.roots.AntibioticDraft,schema.definitions);}
export function antibioticMetadata(fact:Fact):AntibioticDraft|undefined{
 const fields=Array.isArray(fact.source_identifiers)?fact.source_identifiers.map(object).filter(s=>s.namespace==='clinrx.local.antibiotic-chart/v1'):[];
 if(!fields.length)return undefined;if(fields.length!==1||fields[0].version!=='1')reject();
 const body=parseRF2JSON(String(fields[0].code));validateAntibioticDraft(body);if(body.id!==fact.id||body.revision!==fact.revision)reject();return {...body,culture_ref:body.culture_ref??null};
}
export class AntibioticClient{
 constructor(private send:typeof fetch=fetch){}
 private async request(path:string,body?:unknown){const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),15000);try{const send=this.send;const response=await send(prefix+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),credentials:'same-origin',redirect:'error',cache:'no-store',signal:abort.signal});if(!response.ok)throw Error(response.status===409?'Source conflict. Inspect the retained source before retrying.':'Antibiotic source operation could not be confirmed.');return await readRF2JSON(response);}finally{clearTimeout(timer);}}
 async catalog(start:string,end:string):Promise<AntibioticBundle>{
  const raw=object(await this.request('?'+new URLSearchParams({review_start:start,review_end:end})));if(Object.keys(raw).sort().join()!=='execution_enabled,micro,renal,version'||raw.version!=='SyntheticAntibiotics/v1'||raw.execution_enabled!==false)reject();
  const renal=await decodeRF2Catalog(raw.renal,start,end),micro=decodeMicroState(raw.micro,{patient_id:'synthetic-p1',encounter_id:'synthetic-e1'});
  const scope=micro.assembly.request.scope;if(stable(scope.repository_cutoff)!==stable(renal.cutoff)||Date.parse(scope.review_start)!==Date.parse(start)||Date.parse(scope.review_end)!==Date.parse(end))reject();
  return {version:'SyntheticAntibiotics/v1',renal,micro,execution_enabled:false};
 }
 async action(action:'validate'|'save'|'lookup',draft:AntibioticDraft):Promise<AntibioticResult>{
  validateAntibioticDraft(draft);const r=object(await this.request('/'+action,draft)) as unknown as AntibioticResult;
  if((action!=='validate'&&r.status==='validated')||!['validated','saved','absent'].includes(r.status)||r.execution_enabled!==false||typeof r.request_canonical!=='string'||stable(parseRF2JSON(r.request_canonical))!==stable(draft)||await hash(r.request_canonical)!==r.request_digest)reject();
  if(r.status==='absent'){if(action!=='lookup'||r.fact!==undefined)reject();return r;}
  if(!r.fact||typeof r.canonical_fact!=='string'||stable(parseRF2JSON(r.canonical_fact))!==stable(r.fact)||await hash(r.canonical_fact)!==r.digest)reject();
  decodeContract('RetainedStateItemV2',{fact:r.fact,expected_digest:r.digest,inclusion:'unplaced',ingestion:r.ingestion});
  const expectedKind=draft.mode==='prescription'?'antimicrobial_order':draft.mode==='given'?'antimicrobial_administration':'antimicrobial_non_delivery';
  if(r.fact.kind!==expectedKind)reject();
  const event=object(draft.mode==='prescription'?r.fact.created:draft.mode==='given'?r.fact.administered:r.fact.occurred);
  if(Date.parse(String(event.value))!==Date.parse(draft.point)||stable(r.fact.supersedes??null)!==stable(draft.predecessor)||r.fact.correction_reason!==draft.correction_reason||object(r.fact.provenance).actor!==draft.actor||Date.parse(String(object(r.fact.provenance).recorded_at))!==Date.parse(draft.recorded_at))reject();
  if(draft.mode==='prescription'&&(r.fact.schedule!==draft.schedule||r.fact.recorded_indication!==draft.indication))reject();
  if(!['prescription','given'].includes(draft.mode)&&(r.fact.status!==draft.mode||r.fact.recorded_reason!==draft.indication))reject();
  if(r.fact.id!==draft.id||r.fact.revision!==draft.revision||r.fact.binding.target.patient_id!=='synthetic-p1'||r.fact.binding.target.encounter_id!=='synthetic-e1'||stable(antibioticMetadata(r.fact))!==stable(draft))reject();
  const identity=object(r.fact.antimicrobial),dose=object((draft.mode==='prescription'?r.fact.prescribed_dose:r.fact.administered_dose)??{});
  if(identity.raw_display!==draft.medicine||identity.formulation!==draft.product)reject();
  if(draft.mode==='prescription'||draft.mode==='given'){if(object(dose.amount).value!==draft.amount||object(object(dose.amount).unit).raw!==draft.unit||dose.basis!==(draft.mode==='given'?'total_administered':'per_dose')||object(r.fact.route).raw_display!==draft.route)reject();}
  if(r.status==='saved'&&(!r.ingestion||r.ingestion.repository_id!==draft.repository||!Number.isSafeInteger(r.ingestion.ingestion_sequence)))reject();return r;
 }
 async courseHistory(state:MicroState,reference:Ref){
  const selected=(state.assembly.snapshot.items??[]).find(i=>i.fact.kind===reference.kind&&i.fact.id===reference.id&&i.fact.revision===reference.version);if(!selected)reject();
  const result=decodeMicroState(await this.request('/course-history',{state_context:state.state_context,reference}),{patient_id:'synthetic-p1',encounter_id:'synthetic-e1'});
  const before=state.assembly.request.scope,after=result.assembly.request.scope,start=Math.min(Date.parse(before.review_start),Date.parse(before.review_end)-7*86400000);
  if(stable(before.repository_cutoff)!==stable(after.repository_cutoff)||Date.parse(after.review_end)!==Date.parse(before.review_end)||Date.parse(after.review_start)!==start)reject();
  for(const item of result.assembly.snapshot.items??[]){if(await hash(stable(item.fact))!==item.expected_digest)reject();}
  return result;
 }
 async history(state:MicroState,reference:Ref){
  const raw=object(await this.request('/history',{state_context:state.state_context,reference}));if(raw.execution_enabled!==false||stable(raw.reference)!==stable(reference)||!Array.isArray(raw.items)||!raw.items.length||raw.items.length>128)reject();
  const selected=(state.assembly.snapshot.items??[]).find(i=>i.fact.kind===reference.kind&&i.fact.id===reference.id&&i.fact.revision===reference.version);if(!selected)reject();
  const seen=new Set<string>();let sequence=0,found=false;const scope=state.assembly.request.scope;
  for(const value of raw.items){const row=object(value),fact=object(row.fact);decodeContract('RetainedStateItemV2',{fact,expected_digest:row.digest,inclusion:'unplaced',ingestion:row.ingestion});const ingestion=object(row.ingestion),target=object(object(fact.binding).target);
   if(typeof row.canonical_fact!=='string'||stable(parseRF2JSON(row.canonical_fact))!==stable(fact)||await hash(row.canonical_fact)!==row.digest||fact.kind!==reference.kind||fact.id!==reference.id||seen.has(String(fact.revision))||target.patient_id!==scope.patient_id||target.encounter_id!==scope.encounter_id||ingestion.repository_id!==scope.repository_cutoff.repository_id||typeof ingestion.ingestion_sequence!=='number'||ingestion.ingestion_sequence<=sequence||ingestion.ingestion_sequence>scope.repository_cutoff.fact_watermark)reject();
   seen.add(String(fact.revision));sequence=ingestion.ingestion_sequence;if(fact.revision===reference.version){if(row.digest!==selected.expected_digest)reject();found=true;}
  }if(!found)reject();return raw.items;
 }

}
