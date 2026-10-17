import type {CirculatoryItem} from '../api/circulatoryTypes';
import pins from './syntheticCasePins.json';

export type CaseScope={patientId:string;encounterId:string;start:string;end:string};
/** Compare retained source content without interpreting values or coercing timestamps. */
function stable(value:unknown):string{
  if(Array.isArray(value))return '['+value.map(stable).join(',')+']';
  if(value!==null&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,v])=>JSON.stringify(k)+':'+stable(v)).join(',')+'}';
  return JSON.stringify(value)??'undefined';
}
function pin(item:CirculatoryItem){return {fact:item.fact,expected_digest:item.expected_digest,inclusion:item.inclusion,contextual_for:item.contextual_for,disclosures:item.disclosures};}
const key=(item:{fact:{kind:string;id:string;revision:string}})=>JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision]);
const expected=new Map(pins.items.map(item=>[key(item),stable(item)]));
export function matchesAuthoredCase(items:CirculatoryItem[],scope:CaseScope){
  if(scope.patientId!==pins.patientId||scope.encounterId!==pins.encounterId)return false;
  if(!['2026-10-08T08:00:00Z','2026-10-08T08:00:00+00:00'].includes(scope.start)||!['2026-10-08T10:00:00Z','2026-10-08T10:00:00+00:00'].includes(scope.end))return false;
  // HPI is optional, unconsumed and not a prerequisite for the authored interpretation.
  if(items.some(i=>i.fact.binding.target.patient_id!==scope.patientId||i.fact.binding.target.encounter_id!==scope.encounterId))return false;
  const relevant=items.filter(i=>i.fact.kind!=='circulatory_device_prediction');
  if(relevant.length!==expected.size||new Set(relevant.map(key)).size!==relevant.length)return false;
  return relevant.every(i=>expected.get(key(i))===stable(pin(i)));
}
// Narrative labels resolve through immutable authoring pins, never a bare-ID input map.
const pinnedKeys=new Map(pins.items.map(item=>[item.fact.id,key(item)]));
export function matchedAuthoredSources(items:CirculatoryItem[],scope:CaseScope){
  if(!matchesAuthoredCase(items,scope))return null;
  const byReference=new Map(items.filter(item=>item.fact.kind!=='circulatory_device_prediction').map(item=>[key(item),item]));
  return (id:string)=>{const reference=pinnedKeys.get(id);return reference?byReference.get(reference):undefined;};
}
export const casePanels=[
  {id:'abg',title:'ABG: possible respiratory contribution',sources:['m7-ABG-PH','m7-ABG-PACO2','m7-ABG-HCO3','m7-ABG-BE','m7-ABG-PAO2','m7-ABG-SAO2','m7-ABG-HB'],
    possibility:'The pH and PaCO₂ pattern could include a respiratory contribution to acidemia. PaO₂ in the recorded supplemental-oxygen context also raises a possible oxygenation concern.',
    limits:'Acute versus chronic disturbance, compensation and a mixed metabolic component are not resolved. Electrolytes, albumin, baseline gases and clinical history are not supplied here. No anion gap, compensation formula, oxygenation ratio or respiratory-failure diagnosis is calculated.'},
  {id:'flow',title:'Flow: measured values, adequacy unresolved',sources:['m7-CO','m7-CI','m7-FLOTRAC','m7-PICCO-CO','m7-VOLUMEVIEW','m7-VTI','m7-EF'],
    possibility:'The CO/CI measurements and reported LV ejection fraction leave open whether forward flow meets this patient’s needs. LVOT VTI adds a separate Doppler observation; it is not a second calculated cardiac output in this view.',
    limits:'Unknown-quality PiCCO is not corroborating proof. No method is preferred or averaged. These snapshots do not establish low output, adequate oxygen delivery or adequate tissue perfusion; oxygen-content, demand, perfusion context and trends are not integrated into a validated assessment.'},
  {id:'echo',title:'Echo: possible RV pressure loading',sources:['m7-RVSP','m7-PASP','m7-TRV','m7-RVD','m7-RVFUNCTION','m7-SEPTUM','m7-VALVE','m7-PH'],
    possibility:'The RV pressure estimates, reported mildly reduced RV function and systolic septal flattening raise a possibility of increased RV pressure loading, consistent with the source report’s concern for pulmonary hypertension.',
    limits:'This does not confirm PH, PAH, an acute RV failure syndrome or its cause. Estimated RAP and TR signal quality affect pressure estimates; RVOT obstruction is not documented. Mean pulmonary artery pressure and pulmonary vascular resistance are not provided. The wedge-pressure record alone cannot classify PH.'},
];
