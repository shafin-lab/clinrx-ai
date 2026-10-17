import type {CirculatoryItem} from '../api/circulatoryTypes';
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:{};
export type ChartSection='infusions'|'measurements'|'fluids'|'perfusion'|'interventions'|'goals';
export const chartSections:Record<ChartSection,string>={infusions:'Infusions and delivery context',measurements:'Pressures, flow and rhythm',fluids:'Fluid input / output context',perfusion:'Gases and tissue perfusion',interventions:'Interventions and assessments',goals:'Recorded goals and handover'};
const definitions:Record<string,{label:string;section:ChartSection;sourceType:string}>={
 input_iv:{label:'IV fluid input',section:'fluids',sourceType:'Source-recorded interval volume'},
 input_blood:{label:'Blood-product input',section:'fluids',sourceType:'Source-recorded interval volume'},
 output_urine:{label:'Urine output',section:'fluids',sourceType:'Measured interval volume'},
 output_drain:{label:'Drain output',section:'fluids',sourceType:'Measured interval volume'},
 output_crrt:{label:'CRRT net fluid removal',section:'fluids',sourceType:'Source-recorded net removal, not total effluent'},
 net_balance_reported:{label:'Reported interval fluid balance',section:'fluids',sourceType:'Source-reported calculation; not calculated by ClinRx'},
 urine_total_reported:{label:'Reported cumulative urine volume',section:'fluids',sourceType:'Source-reported total; not calculated by ClinRx'},
 balance_total_reported:{label:'Reported cumulative chart balance',section:'fluids',sourceType:'Source-reported total of charted categories; completeness unknown'},
 dosing_weight:{label:'Source dosing weight',section:'infusions',sourceType:'Source-recorded actual weight'},
 body_surface_area:{label:'Source BSA for indexing',section:'measurements',sourceType:'Source-reported BSA; not calculated by ClinRx'},
 pump_rate:{label:'Pump volumetric rate',section:'infusions',sourceType:'Separately recorded pump rate; no dose conversion'},
 map_goal:{label:'Clinician-recorded MAP goal',section:'goals',sourceType:'Source plan, not a system target'},
 review_note:{label:'Hemodynamic review note',section:'goals',sourceType:'Source clinician note'},
 handover_note:{label:'Hemodynamic handover',section:'goals',sourceType:'Source handover note'},
 fluid_challenge:{label:'Fluid challenge event',section:'interventions',sourceType:'Source event; may already be included in input totals'},
 ventilation_change:{label:'Ventilation context event',section:'interventions',sourceType:'Source event; settings are not carried forward'},
 crrt_context:{label:'CRRT fluid-removal context',section:'interventions',sourceType:'Source chart context; not a renal-management recommendation'},
};
export function chartEntry(item:CirculatoryItem){
 const coding=object(object(item.fact.description).coding);
 if(item.fact.kind!=='circulatory_event'||coding.namespace!=='clinrx.synthetic.hemodynamic-chart/v1'||coding.version!=='1'||typeof coding.code!=='string')return null;
 const definition=definitions[coding.code];return definition?{...definition,code:coding.code}:null;
}
export function chartSection(item:CirculatoryItem):ChartSection{
 const entry=chartEntry(item);if(entry)return entry.section;
 if(item.fact.kind==='circulatory_vasoactive')return 'infusions';
 if(['circulatory_event','circulatory_assessment'].includes(item.fact.kind))return 'interventions';
 if(['circulatory_oxygen','circulatory_lactate','circulatory_perfusion'].includes(item.fact.kind))return 'perfusion';
 return 'measurements';
}
export function intervalText(item:CirculatoryItem){
 const interval=object(item.fact.recorded_interval);if(!Object.keys(interval).length)return null;
 const text=(v:unknown)=>{const t=object(v);return typeof t.source_timestamp==='string'?t.source_timestamp:typeof object(t.recorded).value==='string'?String(object(t.recorded).value):'Not established';};
 return 'Source interval: '+text(interval.start)+' → '+text(interval.end)+'. Duration and interval ordering are not assessed here.';
}
