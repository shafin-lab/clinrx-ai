import {readRF2JSON,parseRF2JSON} from './rf2JSON';
import schemas from './rf2Schemas.json';
import circulatory from './circulatorySchemas.json';
import {validateTransportSchema,type Schema,reject,object} from './decoding';
import {equal,decodeRenalFluid} from './renalFluidDecoders';
import type {RenalFluidState} from './renalFluidTypes';
export interface Ref {kind:string;id:string;version:string}
export interface Pin {repository:string;reference:Ref;digest:string;ingestion:number;cutoff:number}
export interface SourceRecord {issuer_namespace:string;issuer:string;record_namespace:string;record_id:string;component:string}
export interface Chart {category:string;amount:string|null;unit:string|null;missing_reason:string|null;point:string|null;start:string|null;end:string|null;acquisition:'measured'|'reported'|'unknown';method:string|null;purpose:string|null;source_context:string;uncertainty:string;source_record:SourceRecord|null;source_version:string|null;new_collection_reason:string|null}
export interface RenalNote {question:string;findings:string;possibilities:string;gaps:string;plan:string;pins:Pin[]}
export interface SourceReview {selected:Ref;terminal:Ref;terminal_digest:string;terminal_ingestion:number;record_status:string|null;retain_historical:boolean}
export const needsHistoricalReview=(r:SourceReview)=>!equal(r.selected,r.terminal)||(r.record_status!==null&&r.record_status!=='recorded');
export interface Draft {source_review?:SourceReview[];repository:string;id:string;revision:string;actor:string;recorded_at:string;chart:Chart|null;note:RenalNote|null;predecessor:Pin|null;reason:string|null}
export interface Fact {kind:string;id:string;revision:string;binding:{target:{patient_id:string;encounter_id:string}};[key:string]:unknown}
export interface Evidence {repository:string;fact:Fact;canonical_fact:string;digest:string;ingestion:{repository_id:string;ingestion_sequence:number;[key:string]:unknown};cutoff:number;terminal_reference:Ref;superseded:boolean;metadata:{version:1;chart:Chart|null;note:RenalNote|null;source_review?:SourceReview[]}|null}
export interface Catalog {repository:string;cutoff:{repository_id:string;fact_watermark:number;captured_at:string};items:Evidence[];combined:RenalFluidState;execution_enabled:false}
export interface Result {source_review?:SourceReview[];status:'validated'|'saved'|'source_replay'|'absent';request_digest:string;request_canonical:string;evidence?:Evidence;fact?:Fact;replay_reference?:Ref|null;execution_enabled:false}
const bundle=schemas as unknown as {roots:Record<string,Schema>;definitions:Record<string,Schema>};
export const stable=(v:unknown):string=>JSON.stringify(v,(_k,x:unknown)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.entries(x).sort(([a],[b])=>a<b?-1:a>b?1:0)):x);
export const hash=async(s:string)=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
export const pin=(e:Evidence):Pin=>({repository:e.repository,reference:{kind:e.fact.kind,id:e.fact.id,version:e.fact.revision},digest:e.digest,ingestion:e.ingestion.ingestion_sequence,cutoff:e.cutoff});
export const key=(p:Pin)=>JSON.stringify([p.repository,p.reference.kind,p.reference.id,p.reference.version]);
export const chartDefaults:Chart={category:'output_urine',amount:'',unit:'mL',missing_reason:null,point:null,start:null,end:null,acquisition:'unknown',method:null,purpose:null,source_context:'',uncertainty:'',source_record:null,source_version:null,new_collection_reason:null};
function sourceReviews(raw:unknown,pins:Pin[]):SourceReview[]{
 if(!Array.isArray(raw)||raw.length!==pins.length)reject();
 return raw.map((v,n)=>{validateTransportSchema(v,bundle.definitions.SourceReview,bundle.definitions);const r=v as SourceReview;
  if(!equal(r.selected,pins[n].reference)||r.terminal.kind!==r.selected.kind||r.terminal.id!==r.selected.id||r.terminal_ingestion<pins[n].ingestion||equal(r.selected,r.terminal)&&(r.terminal_digest!==pins[n].digest||r.terminal_ingestion!==pins[n].ingestion))reject();return r;});
}
function exactKeys(v:object,names:string[]){if(Object.keys(v).sort().join()!==names.sort().join())reject();}
function canonical(raw:string){const v:unknown=parseRF2JSON(raw);if(stable(v)!==raw)reject();return v;}
export async function decodeEvidence(raw:unknown,repository:string,expected?:Pin):Promise<Evidence>{
 const e=object(raw) as unknown as Evidence;exactKeys(e,['repository','fact','canonical_fact','digest','ingestion','cutoff','terminal_reference','superseded','metadata']);const f=object(e.fact);validateTransportSchema(e.ingestion,bundle.roots.IngestionMetadata,bundle.definitions);
 if(e.repository!==repository||f.binding===undefined||e.fact.binding.target.patient_id!=='synthetic-p1'||e.fact.binding.target.encounter_id!=='synthetic-e1'||typeof e.canonical_fact!=='string'||!equal(canonical(e.canonical_fact),e.fact)||await hash(e.canonical_fact)!==e.digest||e.ingestion.repository_id!==repository||!Number.isSafeInteger(e.ingestion.ingestion_sequence)||e.ingestion.ingestion_sequence<1||!Number.isSafeInteger(e.cutoff)||e.cutoff<e.ingestion.ingestion_sequence)reject();
 if(f.kind==='observation')validateTransportSchema(f,bundle.roots.ClinicalObservation,bundle.definitions);
 else{const c=circulatory as unknown as {definitions:Record<string,Schema>};validateTransportSchema({fact:e.fact,ingestion:e.ingestion},c.definitions.CirculatoryHistoricalFact,c.definitions);}
 if(!['observation','circulatory_event'].includes(e.fact.kind)&&!e.fact.kind.startsWith('circulatory_'))reject();
 if(e.fact.kind==='observation'&&!['body-weight','synthetic-serum-creatinine'].includes(String(f.concept_id)))reject();
 if(e.terminal_reference.kind!==e.fact.kind||e.terminal_reference.id!==e.fact.id||typeof e.terminal_reference.version!=='string'||e.superseded!==(e.terminal_reference.version!==e.fact.revision))reject();
 if(expected&&(expected.repository!==repository||!equal(expected.reference,{kind:e.fact.kind,id:e.fact.id,version:e.fact.revision})||expected.digest!==e.digest||expected.ingestion!==e.ingestion.ingestion_sequence||expected.cutoff>e.cutoff))reject();
 const entries=Array.isArray(f.external_evidence)?f.external_evidence.map(object):[];const meta=entries.filter(x=>x.namespace==='clinrx.local.rf2/v1');
 if(meta.length){if(meta.length!==1)reject();const m=object(canonical(String(meta[0].code)));if(m.version!==1)reject();if(m.note){const n=object(m.note);if(!equal(n.pins,[]))reject();n.pins=entries.filter(x=>x.namespace==='clinrx.local.rf2.pin/v1').map(x=>canonical(String(x.code)));m.note=n;}
  const reviews=entries.filter(x=>x.namespace==='clinrx.local.rf2.review/v1');
  if(reviews.length){if(!m.note||reviews.some(x=>x.version!=='1'))reject();const rs=sourceReviews(reviews.map(x=>canonical(String(x.code))),(m.note as RenalNote).pins);if(rs.some(r=>needsHistoricalReview(r)&&!r.retain_historical))reject();m.source_review=rs;}
  if(!equal(m,e.metadata))reject();
  // Validate the reconstructed metadata with the same strict request schema.
  const d={repository,id:'00000000-0000-4000-8000-000000000001',revision:'00000000-0000-4000-8000-000000000002',actor:'metadata decoder',recorded_at:'2026-10-08T10:00:00Z',chart:m.chart,note:m.note,predecessor:null,reason:null};validateTransportSchema(d,bundle.roots.RF2Draft,bundle.definitions);
  if(e.metadata?.chart){const c=e.metadata.chart;const q=f.recorded_amount===null?null:object(f.recorded_amount);if((c.amount===null)!==(q===null)||q&&(q.value!==c.amount||object(q.unit).raw!==c.unit))reject();if(object(f.occurred).source_timestamp!==c.point)reject();if(c.start!==null||c.end!==null){const interval=object(f.recorded_interval);if(object(interval.start).source_timestamp!==c.start||object(interval.end).source_timestamp!==c.end)reject();}else if(f.recorded_interval!==undefined&&f.recorded_interval!==null)reject();}
  if(e.metadata?.note){const pins=e.metadata.note.pins;const associations=Array.isArray(f.associations)?f.associations.map(object):[];if(pins.length<1||pins.length>12||new Set(pins.map(key)).size!==pins.length||associations.length!==pins.length||pins.some(p=>p.repository!==repository||!associations.some(a=>a.role==='context'&&a.status==='resolved'&&equal(a.exact,p.reference))))reject();}
 }else if(e.metadata!==null)reject();
 return e;
}
export class RF2ReviewChanged extends Error {constructor(){super('Selected-source review changed; this request was rejected before append.');}}
export class RF2Client {
 private reviewed=new Map<string,Fact>();
 constructor(private send:typeof fetch=fetch){}
 private async request(path:string,body?:unknown){
  const send=this.send;
  const abort=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
  const deadline=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{abort.abort();reject(Error('Request timed out; completion is unconfirmed.'));},15000);});
  try{return await Promise.race([(async()=>{const r=await send('/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-rf2'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store',credentials:'same-origin',redirect:'error',signal:abort.signal});if(r.status===409&&body!==undefined&&(path==='/save'||path==='/validate')){const failure=object(await readRF2JSON(r));if(failure.code==='rf2_source_review_changed'){exactKeys(failure,['code','request_digest','execution_enabled']);if(failure.execution_enabled!==false||failure.request_digest!==await hash(stable(body)))reject();throw new RF2ReviewChanged();}throw Error('Source conflict: review the original record; no replacement was inserted.');}if(!r.ok)throw Error(r.status===409?'Source conflict: review the original record; no replacement was inserted.':'The exact result could not be confirmed.');return readRF2JSON(r);})(),deadline]);}finally{clearTimeout(timer);}
 }
 async catalog(start:string,end:string):Promise<Catalog>{const c=object(await this.request('?'+new URLSearchParams({review_start:start,review_end:end}))) as unknown as Catalog;
  exactKeys(c,['repository','cutoff','items','combined','execution_enabled']);validateTransportSchema(c.cutoff,bundle.roots.RepositoryCutoff,bundle.definitions);if(c.execution_enabled!==false||c.repository!==c.cutoff.repository_id||!Array.isArray(c.items)||c.items.length>4096)reject();const combined=await decodeRenalFluid(c.combined,{patient_id:'synthetic-p1',encounter_id:'synthetic-e1',start,end});if(!equal(combined.context.scope.repository_cutoff,c.cutoff))reject();
  // Existing facts travel once in the combined response. Build a typed view, not another stored record.
  const baseFacts=[...combined.circulatory.assembly.snapshot.items,...combined.laboratory.observations];
  const derived:Evidence[]=[];
  for(const item of baseFacts){const f=item.fact as unknown as Fact;const raw=stable(f);const entries=Array.isArray(f.external_evidence)?f.external_evidence.map(object):[];const ms=entries.filter(x=>x.namespace==='clinrx.local.rf2/v1');let metadata:Evidence['metadata']=null;
   if(ms.length){if(ms.length!==1)reject();metadata=canonical(String(ms[0].code)) as Evidence['metadata'];if(metadata?.note){if(!equal(metadata.note.pins,[]))reject();metadata.note.pins=entries.filter(x=>x.namespace==='clinrx.local.rf2.pin/v1').map(x=>canonical(String(x.code)) as Pin);const reviews=entries.filter(x=>x.namespace==='clinrx.local.rf2.review/v1');if(reviews.length)metadata.source_review=sourceReviews(reviews.map(x=>canonical(String(x.code))),metadata.note.pins);}}
   derived.push({repository:c.repository,fact:f,canonical_fact:raw,digest:item.expected_digest,ingestion:item.ingestion,cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:f.kind,id:f.id,version:f.revision},superseded:false,metadata});
  }
  c.items=[...derived,...c.items];
  const keys=new Set<string>();for(const item of c.items){await decodeEvidence(item,c.repository);if(item.cutoff!==c.cutoff.fact_watermark||keys.has(key(pin(item))))reject();keys.add(key(pin(item)));}return c;
 }
 async history(original:Evidence){const selected=pin(original);const r=object(await this.request('/history',{repository:selected.repository,pins:[selected]}));exactKeys(r,['repository','selected','items','execution_enabled']);if(r.execution_enabled!==false||r.repository!==selected.repository||!equal(r.selected,selected)||!Array.isArray(r.items)||r.items.length<1||r.items.length>128)reject();const items=await Promise.all(r.items.map(x=>decodeEvidence(x,selected.repository)));if(items.some(x=>x.fact.kind!==selected.reference.kind||x.fact.id!==selected.reference.id||x.cutoff!==selected.cutoff)||items.filter(x=>equal(pin(x).reference,selected.reference)&&x.digest===selected.digest&&x.ingestion.ingestion_sequence===selected.ingestion).length!==1)reject();const matched=items.find(x=>equal(pin(x).reference,selected.reference))!;if(!equal(matched.fact,original.fact)||!equal(matched.ingestion,original.ingestion))reject();return items;}
 async resolve(repository:string,pins:Pin[]){const r=object(await this.request('/resolve',{repository,pins}));exactKeys(r,['repository','items','execution_enabled']);if(r.repository!==repository||r.execution_enabled!==false||!Array.isArray(r.items)||r.items.length!==pins.length)reject();return Promise.all(r.items.map((x,n)=>decodeEvidence(x,repository,pins[n])));}
 async action(action:'validate'|'save'|'lookup',draft:Draft):Promise<Result>{validateTransportSchema(draft,bundle.roots.RF2Draft,bundle.definitions);const result=object(await this.request('/'+action,draft)) as unknown as Result;
  if(result.execution_enabled!==false||typeof result.request_canonical!=='string'||!equal(canonical(result.request_canonical),draft)||await hash(result.request_canonical)!==result.request_digest)reject();
  if(action==='validate'){exactKeys(result,['status','request_digest','request_canonical','fact','replay_reference','execution_enabled',...(draft.note?['source_review']:[])]);if(draft.note){const rs=sourceReviews(result.source_review,draft.note.pins);if(draft.source_review&&!equal(rs,draft.source_review))reject();}else if(result.source_review!==undefined)reject();if(result.status!=='validated'||!result.fact||result.fact.id!==draft.id||result.fact.revision!==draft.revision)reject();const c=circulatory as unknown as {definitions:Record<string,Schema>};const factSchema=c.definitions.CirculatoryHistoricalFact.properties?.fact;if(!factSchema)reject();validateTransportSchema(result.fact,factSchema,c.definitions);if(result.fact.binding.target.patient_id!=='synthetic-p1'||result.fact.binding.target.encounter_id!=='synthetic-e1')reject();const es=(result.fact.external_evidence as {namespace:string;code:string}[]).filter(e=>e.namespace==='clinrx.local.rf2/v1');if(es.length!==1)reject();const m=object(canonical(es[0].code));if(!equal(m.chart,draft.chart))reject();if(draft.note){const n=object(m.note);if(!equal(n.pins,[]))reject();n.pins=(result.fact.external_evidence as {namespace:string;code:string}[]).filter(e=>e.namespace==='clinrx.local.rf2.pin/v1').map(e=>canonical(e.code));if(!equal(n,draft.note))reject();const rs=(result.fact.external_evidence as {namespace:string;code:string}[]).filter(e=>e.namespace==='clinrx.local.rf2.review/v1').map(e=>canonical(e.code));if(!equal(rs,draft.source_review??[]))reject();}else if(m.note!==null)reject();this.reviewed.clear();this.reviewed.set(stable(draft),result.fact);return result;}
  if(result.status==='absent'){exactKeys(result,['status','request_digest','request_canonical','execution_enabled']);if(action!=='lookup'||result.evidence!==undefined)reject();return result;}
  exactKeys(result,['status','request_digest','request_canonical','evidence','execution_enabled']);if(!['saved','source_replay'].includes(result.status)||!result.evidence)reject();await decodeEvidence(result.evidence,draft.repository);
  if(result.status==='saved'&&(result.evidence.fact.id!==draft.id||result.evidence.fact.revision!==draft.revision||this.reviewed.has(stable(draft))&&!equal(this.reviewed.get(stable(draft)),result.evidence.fact)||!equal(result.evidence.metadata?.chart,draft.chart)||!equal(result.evidence.metadata?.note,draft.note)||!equal(result.evidence.metadata?.source_review??null,draft.source_review??null)))reject();
  if(result.status==='source_replay'){if(!draft.chart?.source_record||!result.evidence.metadata?.chart)reject();const a={...draft.chart},b={...result.evidence.metadata.chart};a.new_collection_reason=null;b.new_collection_reason=null;if(!equal(a,b))reject();}
  return result;
 }
}
