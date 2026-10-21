import type {CirculatoryItem, CirculatoryState} from '../api/circulatoryTypes';
import {record, sourceTime, value} from '../demo/evidencePresentation';
import {reference, refKey} from '../patient/CirculatoryEvidence';

export type BedsideScope = {patient:string; encounter:string; start:string; end:string};
export const evidenceGroups = {
  pressure:{label:'Pressure',kinds:['circulatory_pressure','circulatory_monitoring','circulatory_signal']},
  perfusion:{label:'Perfusion',kinds:['circulatory_perfusion','circulatory_lactate','circulatory_oxygen']},
  flow:{label:'Flow & echo',kinds:['circulatory_cardiac','circulatory_echo','circulatory_volume','circulatory_ecg']},
  infusions:{label:'Infusions',kinds:['circulatory_vasoactive','circulatory_event']},
  tests:{label:'Fluid tests',kinds:['circulatory_assessment','circulatory_dynamic']},
  all:{label:'All sources',kinds:[] as string[]}
} as const;
export type EvidenceGroup = keyof typeof evidenceGroups;
export const itemKey = (item:CirculatoryItem) => refKey(reference(item));
export const exactPin = (item:CirculatoryItem) => ({reference:reference(item),expected_digest:item.expected_digest});
export function sourceQuality(item:CirculatoryItem) {
  const assessment=record(record(item.fact.acquisition).quality??item.fact.quality);
  const status=assessment.status;
  return status==='acceptable'?'Source quality: acceptable':status==='suspect'?'Source quality: suspect':status==='invalid'?'Source quality: invalid':'Source quality: unknown';
}
export function sourceLimitations(item:CirculatoryItem):string[] {
  const acquisition=record(item.fact.acquisition),q=record(acquisition.quality??item.fact.quality);
  const result:string[]=[];
  if(item.inclusion!=='in_window') result.push(item.inclusion==='contextual'?'Outside the review window':'Observation time not placed in the review window');
  if(item.fact.record_status!=='recorded') result.push('Source status: '+String(item.fact.record_status??'unknown'));
  if(q.status!=='acceptable') result.push(sourceQuality(item));
  if(Array.isArray(q.artifacts)&&q.artifacts.length) result.push('Source artifacts recorded');
  if(Array.isArray(item.fact.uncertainty)&&item.fact.uncertainty.length) result.push('Source uncertainty recorded');
  return result;
}
/** Display original strings. Never select a "latest" reading, classify shock or calculate treatment. */
export function observationSummary(items:CirculatoryItem[]) {
  if(!items.length) return {headline:'Not recorded',unit:'',detail:'No matching observation in this review window.',item:undefined};
  if(items.length!==1) return {headline:String(items.length),unit:'observations',detail:'Choose an exact source; no reading is selected as current automatically.',item:undefined};
  const item=items[0],v=value(item);
  if(item.fact.record_status!=='recorded')return {headline:'Source '+String(item.fact.record_status??'status unknown'),unit:'',detail:'Original value is retained in evidence; not presented as a usable measurement.',item};
  return {headline:v.text,unit:v.unit,detail:sourceTime(item),item};
}
export function bedsideModel(state:CirculatoryState|undefined, requested:BedsideScope) {
  const empty={valid:false,signature:'',items:[] as CirculatoryItem[],windowItems:[] as CirculatoryItem[],heartRates:[] as CirculatoryItem[],spo2:[] as CirculatoryItem[],sao2:[] as CirculatoryItem[],systolic:[] as CirculatoryItem[],diastolic:[] as CirculatoryItem[],respiratoryRates:[] as CirculatoryItem[],maps:[] as CirculatoryItem[],lactates:[] as CirculatoryItem[],crt:[] as CirculatoryItem[],infusions:[] as CirculatoryItem[],echo:[] as CirculatoryItem[],tests:[] as CirculatoryItem[],qualityConcerns:[] as CirculatoryItem[],issueCount:0};
  if(!state) return empty;
  const scope=state.assembly.request.scope,items=state.assembly.snapshot.items;
  // Compare whole-second offsets separately from the untouched fractional lexeme;
  // Date.parse alone would collapse materially different submicrosecond boundaries.
  const boundaryKey=(text:string)=>{
    const m=/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$/.exec(text);
    if(!m)return null;
    const seconds=Date.parse(m[1]+m[3]);
    return Number.isFinite(seconds)?String(seconds)+':'+(m[2]??'').replace(/0+$/,''):null;
  };
  const sameBoundary=(a:string,b:string)=>{const x=boundaryKey(a),y=boundaryKey(b);return x!==null&&x===y;};
  const seen=new Set<string>();
  if(state.execution_enabled!==false||scope.patient_id!==requested.patient||scope.encounter_id!==requested.encounter||!sameBoundary(scope.review_start,requested.start)||!sameBoundary(scope.review_end,requested.end))return empty;
  for(const item of items){
    const target=item.fact.binding.target,key=itemKey(item);
    if(target.patient_id!==requested.patient||target.encounter_id!==requested.encounter||seen.has(key)||item.ingestion.repository_id!==scope.repository_cutoff.repository_id||item.ingestion.ingestion_sequence>scope.repository_cutoff.fact_watermark)return empty;
    seen.add(key);
  }
  const windowItems=items.filter(item=>item.inclusion==='in_window');
  const signature=JSON.stringify([scope.patient_id,scope.encounter_id,scope.review_start,scope.review_end,scope.repository_cutoff,state.assembly_digest,state.state_context]);
  return {valid:true,signature,items,windowItems,
    heartRates:windowItems.filter(i=>['circulatory_cardiac','circulatory_ecg'].includes(i.fact.kind)&&i.fact.concept==='heart_rate'),
    spo2:windowItems.filter(i=>i.fact.kind==='circulatory_oxygen'&&i.fact.concept==='spo2'),
    sao2:windowItems.filter(i=>i.fact.kind==='circulatory_oxygen'&&i.fact.concept==='sao2'),
    systolic:windowItems.filter(i=>i.fact.kind==='circulatory_pressure'&&i.fact.concept==='systemic_systolic'),
    diastolic:windowItems.filter(i=>i.fact.kind==='circulatory_pressure'&&i.fact.concept==='systemic_diastolic'),
    respiratoryRates:windowItems.filter(i=>i.fact.kind==='circulatory_oxygen'&&i.fact.concept==='respiratory_rate'),
    maps:windowItems.filter(i=>i.fact.kind==='circulatory_pressure'&&i.fact.concept==='systemic_mean'),
    lactates:windowItems.filter(i=>i.fact.kind==='circulatory_lactate'),
    crt:windowItems.filter(i=>i.fact.kind==='circulatory_perfusion'&&i.fact.concept==='capillary_refill'),
    infusions:windowItems.filter(i=>i.fact.kind==='circulatory_vasoactive'),
    echo:windowItems.filter(i=>i.fact.kind==='circulatory_echo'||i.fact.kind==='circulatory_cardiac'),
    tests:windowItems.filter(i=>i.fact.kind==='circulatory_assessment'||i.fact.kind==='circulatory_dynamic'),
    qualityConcerns:windowItems.filter(i=>sourceLimitations(i).length>0),issueCount:state.assembly.snapshot.issues.length};
}
export const reviewActions={confirm:'Confirm measurement',perfusion:'Reassess perfusion',fluid:'Review fluid benefit and harm',vasoactive:'Review vasoactive delivery',specialist:'Seek senior / specialist review',continue:'Continue observation and reassess'} as const;
export const phenotypeOptions={undifferentiated:'Undifferentiated',distributive:'Distributive component',hypovolemic:'Hypovolemic / hemorrhagic component',cardiac:'Cardiac component',right:'RV / pulmonary vascular concern',obstructive:'Obstructive concern',mixed:'Mixed mechanism'} as const;
export type ReviewDraft={action:string;reviewer:string;rationale:string;nextReview:string;phenotype:string;perfusion:string;targetLow:string;targetHigh:string};
export const emptyReview = ():ReviewDraft => ({action:'',reviewer:'',rationale:'',nextReview:'',phenotype:'',perfusion:'',targetLow:'',targetHigh:''});
export function validateReview(draft:ReviewDraft, current:boolean, snapshotMatches:boolean):string {
  if(!current) return 'Current evidence is not confirmed. Refresh before recording a review.';
  if(!snapshotMatches) return 'Evidence changed while this draft was open. Review the refreshed sources and start a new draft.';
  if(!Object.hasOwn(reviewActions,draft.action)) return 'Choose a next review step.';
  if(!draft.reviewer.trim()||!draft.rationale.trim()||!draft.nextReview.trim()) return 'Add your name, a rationale and a next review plan.';
  if(draft.phenotype&&!Object.hasOwn(phenotypeOptions,draft.phenotype))return 'Choose a listed assessment or leave it unassessed.';
  if(draft.perfusion&&!['concern','uncertain','no_concern_on_assessed_scope'].includes(draft.perfusion))return 'Choose a listed perfusion assessment.';
  if(draft.targetLow||draft.targetHigh){
    const decimal=/^(?:0|[1-9]\d*)(?:\.\d+)?$/;
    if(!decimal.test(draft.targetLow)||!decimal.test(draft.targetHigh)||Number(draft.targetLow)<=0||!Number.isFinite(Number(draft.targetHigh))||Number(draft.targetHigh)<Number(draft.targetLow)) return 'For a session MAP goal, enter both limits in mmHg, greater than zero and in order. This is not a chart target.';
  }
  return '';
}
export function deliveryLabel(item:CirculatoryItem) {
  const action=record(item.fact.action),type=String(action.event_type??'unknown');
  if(type==='order')return 'Order only';
  if(type==='preparation')return 'Preparation only';
  if(type==='initiation')return 'Documented initiation';
  if(type==='rate_change')return 'Documented rate change';
  if(type==='restart')return 'Documented restart';
  if(type==='bolus')return 'Documented bolus';
  if(type==='pause')return 'Documented pause';
  if(type==='permanent_stop')return 'Documented stop';
  if(type==='non_delivery')return 'Documented non-delivery';
  return 'Recorded event';
}
