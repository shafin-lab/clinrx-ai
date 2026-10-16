import type {CirculatoryItem} from '../api/circulatoryTypes';
export const record=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:{};
export const words=(v:unknown)=>typeof v==='string'?v.replaceAll('_',' '):'';
const concepts:Record<string,string>={co:'Cardiac output',ci:'Cardiac index',systemic_mean:'Mean arterial pressure',lv_ef:'LV ejection fraction',lvot_vti:'LVOT VTI',tapse:'TAPSE',cvp:'Central venous pressure',pawp:'Pulmonary artery wedge pressure',gedv:'Global end-diastolic volume',svv:'Stroke volume variation',qtc:'QTc',svo2:'Mixed venous oxygen saturation',capillary_refill:'Capillary refill',ph:'pH',paco2:'PaCO₂',pao2:'PaO₂',bicarbonate:'Bicarbonate',base_excess:'Base excess',sao2:'Arterial oxygen saturation',hemoglobin:'Haemoglobin',estimated_rvsp:'Estimated RVSP',estimated_pasp:'Estimated PASP',tr_measurement:'TR peak velocity',rv_dimension:'RV basal dimension',rv_function:'RV function',septal_configuration:'Septal configuration',valve_finding:'Valve finding',pericardial_effusion:'Pericardial effusion',structural_finding:'Structural finding',hpi:'Source HPI (optional)',rhythm:'Source rhythm',configuration:'Monitor configuration',plr:'Passive leg raise episode',position_change:'Position change',arterial_pressure:'Arterial pressure signal'};
export function title(item:CirculatoryItem){const f=item.fact;if(f.id==='m7-PH')return 'Pulmonary hypertension report finding';return concepts[String(f.concept??f.event_type??f.test??f.signal)]??(f.kind==='circulatory_lactate'?'Lactate':f.kind==='circulatory_vasoactive'?'Vasopressor event':words(f.concept??f.event_type??f.test??f.signal)||'Recorded evidence');}
export function value(item:CirculatoryItem){
  const f=item.fact,result=record(f.result),quantity=record(result.quantity),unit=record(quantity.unit);
  if(typeof quantity.value==='string')return {text:quantity.value,unit:typeof unit.raw==='string'?unit.raw:''};
  const finding=record(result.finding??f.finding??f.description),drug=record(f.drug);
  return {text:typeof finding.raw_display==='string'?finding.raw_display:typeof drug.canonical_id==='string'?drug.canonical_id:words(result.reason??result.status??f.event_type??f.availability)||'Recorded source',unit:words(record(f.action).event_type)};
}
export function quality(item:CirculatoryItem){return words(record(record(item.fact.acquisition).quality).status)||'not recorded';}
export function sourceTime(item:CirculatoryItem){
  const time=record(item.fact.collected??item.fact.occurred);
  return typeof time.source_timestamp==='string'?time.source_timestamp:typeof record(time.recorded).value==='string'?String(record(time.recorded).value):'Time not established';
}
export function method(item:CirculatoryItem){const a=record(item.fact.acquisition),device=record(a.device);return [words(a.method),device.technology,device.platform].filter(v=>typeof v==='string'&&v).join(' · ')||'Method not supplied';}
export const lenses={
  cardiac:{label:'Cardiac output + echo',description:'Compare cardiac output and LVOT VTI alongside RVSP/PASP estimates, TR velocity, RV findings, valves and pericardium. Pulmonary hypertension wording is source-reported, not a ClinRx diagnosis or PAH classification.',kinds:['circulatory_cardiac','circulatory_echo','circulatory_pressure','circulatory_ecg','circulatory_oxygen']},
  abg:{label:'ABG + oxygen transport',description:'Inspect arterial pH, PaCO₂, PaO₂, bicarbonate, base excess, saturation and haemoglobin with sample-time respiratory settings. Lactate remains a separate recorded result; no acid–base interpretation is generated.',kinds:['circulatory_oxygen','circulatory_lactate']},
  correction:{label:'Follow a correction',description:'A provenance-only change to calibration support withheld the second prepared example. The original receipt and selected support revision remain available.',kinds:['circulatory_monitoring','circulatory_pressure','circulatory_lactate','circulatory_vasoactive']},
  gaps:{label:'Find the evidence gaps',description:'Find the PiCCO record with unknown quality, earlier contextual cardiac output, unplaced pressure and unavailable waveform samples. Missing evidence does not establish clinical absence.',kinds:[] as string[]}
};
export type Lens=keyof typeof lenses;
export function hasUncertainQuality(item:CirculatoryItem){return typeof record(record(item.fact.acquisition).quality).status==='string'&&quality(item)!=='acceptable';}
export function inLens(item:CirculatoryItem,lens:Lens){return lens==='gaps'?hasUncertainQuality(item)||item.inclusion!=='in_window'||item.fact.availability==='unavailable':lenses[lens].kinds.includes(item.fact.kind);}

/** Display only the sampled source context; never substitute current settings. */
export function bloodGasSummary(item:CirculatoryItem):[string,string][]{
  const gas=record(item.fact.blood_gas_context),collected=record(gas.collected);
  const quantity=(v:unknown)=>{const q=record(v),u=record(q.unit);return typeof q.value==='string'?[q.value,typeof u.raw==='string'?u.raw:''].filter(Boolean).join(' '):'Not recorded';};
  const finding=(v:unknown)=>typeof record(v).raw_display==='string'?String(record(v).raw_display):'Not recorded';
  return [['Sample type',words(item.fact.sample_type)||'Not recorded'],
    ['Specimen',String(record(item.fact.specimen).raw_display??'Not recorded')],
    ['Collected',typeof collected.source_timestamp==='string'?collected.source_timestamp:typeof record(collected.recorded).value==='string'?String(record(collected.recorded).value):'Not recorded'],
    ['Sample-time FiO₂',quantity(gas.fio2)],['Oxygen device',finding(gas.oxygen_device)],
    ['Ventilator mode',finding(gas.ventilator_mode)],['Sample-time PEEP',quantity(gas.peep)]];
}
