import type {RenalFluidState,RenalObservation} from '../api/renalFluidTypes';
import type {CirculatoryItem} from '../api/circulatoryTypes';
import type {Catalog,Evidence} from '../api/rf2Client';
import {equal} from '../api/renalFluidDecoders';
import {record,value,title,sourceTime} from '../demo/evidencePresentation';
import {chartEntry} from '../demo/chartEntries';
import {bedsideModel,type BedsideScope} from '../hemodynamics/bedsideModel';

export const renalGroups={kidney:'Kidney tests',urine:'Urine',support:'Kidney support',weight:'Weight',reviews:'Reviews',all:'All renal sources'} as const;
export type RenalGroup=keyof typeof renalGroups;
export interface RenalSource {
 key:string;group:Exclude<RenalGroup,'all'>;label:string;value:string;time:string;interval:string;
 inclusion:string;status:string;limitations:string[];pin:{repository:string;kind:string;id:string;version:string;digest:string;ingestion:number;cutoff:number};
 raw:unknown;lab?:RenalObservation;fluid?:CirculatoryItem;entry?:Evidence;
}
const interval=(raw:unknown)=>{const i=record(raw);if(!Object.keys(i).length)return 'No collection interval supplied';
 const stamp=(v:unknown)=>String(record(v).source_timestamp??record(record(v).recorded).value??'Unknown');
 return stamp(i.start)+' → '+stamp(i.end);};
const labText=(i:RenalObservation)=>{const v=i.fact.value;if(v.status!=='known')return v.status+' · '+(v.reason??'Reason unavailable');const q=record(v.value);return typeof q.value==='string'?q.value+' '+String(record(q.unit).raw??'Unit unavailable'):String(v.value);};
const groupFor=(category:string):RenalSource['group']|undefined=>category==='weight'||category==='dosing_weight'?'weight':['output_urine','urine_total_reported'].includes(category)?'urine':['output_crrt','output_crrt_net','output_crrt_effluent','crrt_context'].includes(category)?'support':undefined;
const labelFor=(category:string)=>({weight:'Recorded body weight',dosing_weight:'Source dosing weight',output_urine:'Urine interval volume',urine_total_reported:'Source-reported cumulative urine',output_crrt:'CRRT net fluid removal',output_crrt_net:'Recorded CRRT net removal',output_crrt_effluent:'Source-recorded effluent',crrt_context:'CRRT context record'}[category]??category);

/** A source projection only: no staging, clearance, urine rate or treatment inference. */
export function renalBedsideModel(state:RenalFluidState|undefined,requested:BedsideScope,catalog?:Catalog){
 const empty={valid:false,signature:'',sources:[] as RenalSource[],windowSources:[] as RenalSource[],creatinine:[] as RenalSource[],urine:[] as RenalSource[],support:[] as RenalSource[],weights:[] as RenalSource[]};
 if(!state)return empty;
 const base=bedsideModel(state.circulatory,requested),scope=state.context.scope,cutoff=scope.repository_cutoff;
 if(!base.valid||state.execution_enabled!==false||!equal(scope,state.circulatory.assembly.request.scope)||!equal(scope,state.laboratory.scope)||state.context.circulatory_digest!==state.circulatory.assembly_digest)return empty;
 if(catalog&&(catalog.execution_enabled!==false||catalog.repository!==cutoff.repository_id||!equal(catalog.cutoff,cutoff)||!equal(catalog.combined,state)))return empty;
 const sources:RenalSource[]=[],seen=new Set<string>();
 function sourcePin(kind:string,id:string,version:string,digest:string,ingestion:number){return {repository:cutoff.repository_id,kind,id,version,digest,ingestion,cutoff:cutoff.fact_watermark};}
 function admit(kind:string,id:string,version:string,patient:string,encounter:string,repo:string,sequence:number){
  const key=JSON.stringify([kind,id,version]);if(seen.has(key)||patient!==requested.patient||encounter!==requested.encounter||repo!==cutoff.repository_id||!Number.isSafeInteger(sequence)||sequence<1||sequence>cutoff.fact_watermark)return false;seen.add(key);return true;
 }
 for(const item of state.laboratory.observations){const f=item.fact,t=f.binding.target;
  if(!admit(f.kind,f.id,f.revision,t.patient_id,t.encounter_id,item.ingestion.repository_id,item.ingestion.ingestion_sequence)||f.concept_id!=='synthetic-serum-creatinine')return empty;
  const unit=record(record(f.value.value).unit),status=String(f.record_status??'Typed withdrawal status unavailable');
  sources.push({key:JSON.stringify([f.kind,f.id,f.revision]),group:'kidney',label:'Creatinine',value:labText(item),time:f.time.event??'Event time unavailable',interval:'Specimen collection time not established by this legacy source',inclusion:item.inclusion,status,
   limitations:['Baseline selection and specimen collection metadata not supplied',`Verification: ${f.verification}; conflict: ${f.conflict}`,`Unit mapping: ${String(unit.status??'Unavailable')}`,...f.uncertainty],
   pin:sourcePin(f.kind,f.id,f.revision,item.expected_digest,item.ingestion.ingestion_sequence),raw:item,lab:item});
 }
 for(const item of base.items){const f=item.fact,t=f.binding.target;
  if(!admit(f.kind,f.id,f.revision,t.patient_id,t.encounter_id,item.ingestion.repository_id,item.ingestion.ingestion_sequence))return empty;
  const entry=chartEntry(item),group=entry?groupFor(entry.code):f.kind==='circulatory_oxygen'&&['ph','bicarbonate','base_excess'].includes(String(f.concept))?'kidney':undefined;
  if(!group)continue;const v=value(item);
  sources.push({key:JSON.stringify([f.kind,f.id,f.revision]),group,label:entry?labelFor(entry.code):title(item),value:v.text+' '+v.unit,time:sourceTime(item),interval:interval(f.recorded_interval),inclusion:item.inclusion,status:String(f.record_status??'Unknown'),
   limitations:group==='urine'?['Collection completeness, patency and overlapping coverage not established','Original volume/context only; no hourly or weight-normalized rate']:group==='support'?['Context or recorded volume does not establish current modality, prescription or continuous delivery']:group==='weight'?['Not automatically selected for urine or CRRT dose normalization']:[],
   pin:sourcePin(f.kind,f.id,f.revision,item.expected_digest,item.ingestion.ingestion_sequence),raw:item,fluid:item});
 }
 if(catalog){
  const catalogSeen=new Set<string>();
  for(const e of catalog.items){const f=e.fact,t=f.binding.target,k=JSON.stringify([f.kind,f.id,f.revision]);
   if(catalogSeen.has(k)||e.repository!==cutoff.repository_id||e.cutoff!==cutoff.fact_watermark||e.ingestion.repository_id!==cutoff.repository_id||!Number.isSafeInteger(e.ingestion.ingestion_sequence)||e.ingestion.ingestion_sequence<1||e.ingestion.ingestion_sequence>cutoff.fact_watermark||t.patient_id!==requested.patient||t.encounter_id!==requested.encounter)return empty;
   catalogSeen.add(k);
   const original=[...state.laboratory.observations,...base.items].find(i=>JSON.stringify([i.fact.kind,i.fact.id,i.fact.revision])===k);if(seen.has(k)){if(!original||original.expected_digest!==e.digest||!equal(original.fact,e.fact)||!equal(original.ingestion,e.ingestion))return empty;const s=sources.find(s=>s.key===k);if(s){s.entry=e;continue;}}
   seen.add(k);const c=e.metadata?.chart,group=e.metadata?.note?'reviews':c?groupFor(c.category):undefined;if(!group)continue;
   sources.push({key:k,group,label:e.metadata?.note?'Authored renal review':labelFor(c!.category),value:e.metadata?.note?.question??(c?.amount!==null&&c?.amount!==undefined?c.amount+' '+(c.unit??'Unit unavailable'):'Amount unavailable'),time:c?.point??String(record(f.occurred).source_timestamp??'Event time unavailable'),interval:c?.start&&c.end?c.start+' → '+c.end:'No collection interval supplied',inclusion:e.superseded?'historical':original?.inclusion??'source timing not placed',status:e.superseded?'Superseded historical revision':String(f.record_status??'Unknown'),limitations:['Source-authored context; no calculated rate, stage or dose',...(c?[c.uncertainty]:[])],pin:sourcePin(f.kind,f.id,f.revision,e.digest,e.ingestion.ingestion_sequence),raw:e,entry:e});
  }
 }
 const windowSources=sources.filter(s=>s.inclusion==='in_window'&&s.status==='recorded');
 return {valid:true,signature:JSON.stringify([state.context,state.state_context,catalog?.cutoff,catalog?.items.map(e=>[e.fact.kind,e.fact.id,e.fact.revision,e.digest])]),sources,windowSources,
  creatinine:sources.filter(s=>s.lab&&s.inclusion==='in_window'),urine:windowSources.filter(s=>s.group==='urine'),support:windowSources.filter(s=>s.group==='support'),weights:sources.filter(s=>s.group==='weight')};
}
export const renalActions={collection:'Check collection and catheter patency',baseline:'Review baseline and kidney trajectory',urgent:'Seek urgent renal / ICU review',delivery:'Review KRT delivery and interruptions',citrate:'Review citrate, calcium and metabolic context',medications:'Review renal medication dosing and levels',recovery:'Review recovery and continuing KRT need',followup:'Plan renal follow-up'} as const;
export interface RenalDraft {action:string;reviewer:string;rationale:string;nextReview:string;cause:string}
export const newRenalDraft=():RenalDraft=>({action:'',reviewer:'',rationale:'',nextReview:'',cause:''});
export const renalCauses={uncertain:'Uncertain / undifferentiated',hemodynamic:'Hemodynamic component',sepsis:'Sepsis-associated concern',drug:'Drug / toxic exposure concern',obstruction:'Obstruction / collection concern',intrinsic:'Intrinsic renal disease concern',graft:'Kidney graft concern',mixed:'Mixed possibilities'} as const;
export function validateRenalReview(d:RenalDraft,current:boolean,sameSnapshot:boolean){
 if(!current)return 'Current renal evidence is not confirmed. Refresh before recording.';
 if(!sameSnapshot)return 'Evidence changed while this renal draft was open. Start a new review after inspecting the refreshed sources.';
 if(!Object.hasOwn(renalActions,d.action))return 'Choose a renal review step.';
 if(!d.reviewer.trim()||!d.rationale.trim()||!d.nextReview.trim())return 'Add reviewer, rationale and next review plan.';
 if(d.cause&&!Object.hasOwn(renalCauses,d.cause))return 'Choose a listed working possibility or leave it unassessed.';
 if(d.reviewer.length>120||d.rationale.length>2000||d.nextReview.length>250)return 'Keep the review within the displayed field limits.';
 return '';
}
