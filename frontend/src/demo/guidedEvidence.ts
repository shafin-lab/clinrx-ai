import type {CirculatoryItem} from '../api/circulatoryTypes';
import {record} from './evidencePresentation';
export const guidedFamilies={pressure:'BP / MAP',gas:'ABG / oxygen transport',cardiac:'Cardiac output / index',echo:'Echo',infusion:'Infusions',perfusion:'Perfusion',reassessment:'Reassessment'};
export type GuidedFamily=keyof typeof guidedFamilies;
export const concepts:Record<GuidedFamily,Record<string,string>>={
 pressure:{systemic_systolic:'Systolic BP',systemic_diastolic:'Diastolic BP',systemic_mean:'MAP',cvp:'CVP',pawp:'PAWP'},
 gas:{ph:'pH',paco2:'PaCO₂',pao2:'PaO₂',bicarbonate:'Bicarbonate',base_excess:'Base excess',sao2:'SaO₂',scvo2:'ScvO₂',svo2:'SvO₂',hemoglobin:'Haemoglobin',lactate:'Lactate'},
 cardiac:{co:'Cardiac output',ci:'Cardiac index',sv:'Stroke volume',svi:'Stroke volume index'},
 echo:{lvot_vti:'LVOT VTI',estimated_rvsp:'Estimated RVSP',estimated_pasp:'Estimated PASP',lv_ef:'LV ejection fraction',rv_function:'RV function',rv_dimension:'RV dimension',tr_measurement:'TR velocity',septal_configuration:'Septal configuration',diastolic_function:'Diastolic function',wall_motion:'Wall motion',valve_finding:'Valve finding',pericardial_effusion:'Pericardial effusion',ivc_dimension:'IVC dimension',ivc_variation:'IVC variation',structural_finding:'Other source-reported finding (including PH)',tapse:'TAPSE (optional)'},
 infusion:{},perfusion:{capillary_refill:'Capillary refill',skin_temperature:'Skin temperature',mottling:'Mottling',perfusion_index:'Perfusion index',regional_perfusion:'Regional perfusion'},reassessment:{}};
export type Fields=Record<string,string>;
export const emptyFields=():Fields=>({concept:'systemic_mean',resultType:'numeric',method:'unknown',quality:'unknown',sample:'unknown',production:'direct_measurement',action:'order',drug:'noradrenaline'});
const target={patient_id:'synthetic-p1',encounter_id:'synthetic-e1'};
const code=(text:string,namespace='clinrx-local-synthetic-entry')=>({namespace,code:text,raw_display:text,version:null});
const concept=(text:string)=>({raw_display:text});
const required=(value:string|undefined)=>{if(!value?.trim())throw Error('Complete the required fields.');return value;};
const quantity=(value:string,unit:string)=>({value:required(value),unit:{raw:required(unit),status:'unresolved',limitation:'Locally recorded raw unit; terminology and conversion not assessed.'}});
const stamp=(text:string|undefined)=>text?{recorded:{status:'known',precision:'instant',value:text},source_timestamp:text,clock:'unknown'}:{recorded:{status:'not_recorded'},clock:'unknown'};
export function localProvenance(actor:string,id:string,at:string){return {source:{namespace:'clinrx-local-synthetic-entry',identifier:id,channel:'clinician',version:null},actor:required(actor).trim(),recorded_at:at,upstream:[],lineage:'incomplete',limitations:['Fictional local entry; actor and source assertions are not independently authenticated.']};}
export function buildGuided(family:GuidedFamily,f:Fields,actor:string,items:CirculatoryItem[],id:string,at:string):CirculatoryItem['fact']{
 const provenance=localProvenance(actor,id,at);
 const fact:Record<string,unknown>={id,revision:'1',contract_version:'3',binding:{target,verification:{status:'unresolved',method:'Local synthetic encounter selection',verifier:actor.trim(),assessed_at:at,source:provenance.source,ambiguity:'Fictional patient identity only; not independently verified.'}},origin:'reported',provenance,time:{precision:'unknown'},temporal_status:'unknown',verification:'unverified',record_status:'recorded',occurred:stamp(f.time),available:stamp(f.available),uncertainty:[required(f.uncertainty)]};
 if(family==='reassessment'){
  const stages=['baseline','intervention','followup'];
  const selected=stages.map(stage=>{const item=items.find(i=>[i.fact.kind,i.fact.id,i.fact.revision].join('/')===f[stage]);if(!item||item.fact.binding.target.patient_id!==target.patient_id||item.fact.binding.target.encounter_id!==target.encounter_id)throw Error('Select an exact record in this encounter for each reassessment stage.');return item;});
  if(!['circulatory_event','circulatory_vasoactive','circulatory_monitoring'].includes(selected[1].fact.kind))throw Error('Choose a documented intervention event, not a measurement.');
  const refs=selected.map(i=>({kind:i.fact.kind,id:i.fact.id,version:i.fact.revision}));
  fact.kind='circulatory_event';fact.event_type='other';
  fact.description=concept(['Clinician-authored synthetic reassessment; not a computed response or causal conclusion.','Question: '+required(f.question),...stages.map((stage,n)=>stage+': '+JSON.stringify(refs[n])),'Recorded findings: '+required(f.findings),'Unconfirmed possibilities: '+required(f.possibilities),'Confirmation gaps: '+f.uncertainty,'Next review (recorded plan, not a scheduled action): '+(f.nextReview||'Not recorded')].join('\n'));
  fact.source_identifiers=[code('reassessment','clinrx.local.chart-entry/v1')];
  fact.external_evidence=stages.map((stage,n)=>code(JSON.stringify(refs[n]),'clinrx.local.reassessment.'+stage+'/v1'));
  fact.associations=[...new Map(refs.map(ref=>[JSON.stringify(ref),{role:'context',scope:target,status:'resolved',exact:ref,provenance}])).values()];
  return fact as CirculatoryItem['fact'];
 }
 if(family==='infusion'){
  fact.kind='circulatory_vasoactive';fact.drug={source:code(required(f.drug)),mapping:'unknown',limitation:'Raw agent identity recorded; no terminology mapping asserted.',mapping_provenance:provenance};
  fact.source_status=concept(required(f.sourceStatus));
  const delivery:Record<string,unknown>={infusion:code(required(f.series),'clinrx.local.infusion-series/v1'),route:f.route?concept(f.route):null};
  if(f.rate||f.rateUnit)delivery.rate=quantity(f.rate,f.rateUnit);
  if(f.concentration||f.concentrationUnit)delivery.concentration=quantity(f.concentration,f.concentrationUnit);
  if(f.pump)delivery.pump=code(f.pump);
  if(f.channel)delivery.channel=code(f.channel);
  fact.source_identifiers=[delivery.infusion];
  if(['pause','permanent_stop','non_delivery'].includes(f.action))fact.action={event_type:f.action,reason:concept(required(f.interruption)),attestation:provenance};
  else if(f.action==='order')fact.action={event_type:'order',prescribed:delivery,status:concept(required(f.sourceStatus))};
  else if(f.action==='preparation')fact.action={event_type:'preparation',prepared:delivery};
  else fact.action={event_type:f.action,delivery:{...delivery,attestation:provenance}};
  fact.disclosures=['Orders and preparations do not establish administration. Documented delivery is a source assertion, not continuous exposure, a conversion, or proof of treatment effect. Weight-dependent doses require separately reviewed weight support; this guided form does not calculate doses or pump rates.'];
  return fact as CirculatoryItem['fact'];
 }
 fact.kind=({pressure:'circulatory_pressure',gas:f.concept==='lactate'?'circulatory_lactate':'circulatory_oxygen',cardiac:'circulatory_cardiac',echo:'circulatory_echo',perfusion:'circulatory_perfusion'} as Record<string,string>)[family];
 if(f.concept!=='lactate')fact.concept=required(f.concept);
 if(family==='echo'&&['estimated_rvsp','estimated_pasp'].includes(f.concept)&&f.production!=='source_calculated')throw Error('Record RVSP/PASP as a source-calculated estimate and supply its reported basis.');
 fact.result=f.resultType==='qualitative'?{result_type:'qualitative',finding:concept(required(f.finding))}:{result_type:'numeric',quantity:quantity(f.value,f.unit)};
 fact.production=f.production;fact.acquisition={method:family==='gas'?'blood_gas':family==='echo'?'echo':f.method,quality:{status:f.quality,provenance:f.quality==='unknown'?null:provenance},calibration:'unknown',zeroing:'unknown',...(f.methodContext?{source_method:code(f.methodContext)}:{})};
 if(f.production!=='direct_measurement')fact.calculation_method=code(required(f.productionBasis));
 if(family==='gas'){
  fact.specimen=f.specimen?code(f.specimen):null;
  if(f.concept==='lactate'){fact.blood_source=f.sample;fact.collected=stamp(f.time);fact.collection_assertion=provenance;fact.report_status=f.reportStatus||'unknown';}
  else{fact.sample_type=f.sample;fact.blood_gas_context={collected:stamp(f.time),provenance,limitations:['Context applies only to this recorded specimen.'],...(f.fio2||f.fio2Unit?{fio2:quantity(f.fio2,f.fio2Unit)}:{}),...(f.peep||f.peepUnit?{peep:quantity(f.peep,f.peepUnit)}:{})};}
 }
 if(family==='echo'){
  fact.study=code(required(f.study));fact.report=code(required(f.report));fact.report_revision=required(f.reportRevision);
  fact.disclosures=['Echo assertions and estimates are source-reported; no PH/PAH diagnosis, invasive confirmation or simultaneous later measurement is inferred.'];
 }
 return fact as CirculatoryItem['fact'];
}
export function shortcutValue(text:string,next:string){const fact=JSON.parse(text),result=record(fact.result);fact.result={...result,quantity:{...record(result.quantity),value:next}};return JSON.stringify(fact,null,2);}
