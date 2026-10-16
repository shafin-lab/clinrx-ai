import type {CirculatoryItem} from '../api/circulatoryTypes';
import {bloodGasSummary,quality,record,words} from './evidencePresentation';

/** Source-display rules only: no thresholds, numeric coercion, time comparison or diagnosis. */
export const explanationStreams=[
  {key:'gases',label:'Blood sample and oxygen context',kinds:['circulatory_oxygen'],
    contribution:'This stream can provide recorded blood pH, gas measurements, saturation and haemoglobin when available. Read the listed sources with their own sample type, collection time and respiratory settings; absent measurements are not filled in.',
    connection:'Place the blood sample beside the flow and echo records for review. The sample alone does not establish the cause of a circulatory finding.'},
  {key:'flow',label:'Recorded flow and pressures',kinds:['circulatory_cardiac','circulatory_pressure'],
    contribution:'Cardiac-output and pressure records add a separate view of recorded flow and pressures, using their documented measurement methods.',
    connection:'Compare these source measurements with the sample context and echo report. A cardiac-output value or pressure alone does not establish oxygen delivery, tissue perfusion or a shock subtype.'},
  {key:'echo',label:'Echo structure, function and estimates',kinds:['circulatory_echo'],
    contribution:'Echo adds source-reported ventricular, valve and pericardial findings, Doppler measurements and pressure estimates. These describe a different evidence stream from the blood sample and monitor measurements.',
    connection:'Read LVOT VTI and ventricular findings beside recorded flow, while keeping RVSP/PASP estimates distinct from invasive pressures. The view does not calculate cardiac output from VTI or confirm PH/PAH.'},
];
export function streamItems(items:CirculatoryItem[],kinds:string[]){return items.filter(item=>kinds.includes(item.fact.kind));}
export type SourceUncertainty={item:CirculatoryItem;reasons:string[];notes:string[]};
export function sourceUncertainties(items:CirculatoryItem[]):SourceUncertainty[]{
  const relevant=items.filter(item=>explanationStreams.some(stream=>stream.kinds.includes(item.fact.kind)));
  return relevant.flatMap(item=>{
    const fact=item.fact,acquisition=record(fact.acquisition),q=record(acquisition.quality),reasons:string[]=[];
    if(quality(item)!=='acceptable')reasons.push('Recorded quality: '+quality(item)+'. This is not upgraded by the explanation.');
    if(item.inclusion!=='in_window')reasons.push('Placement: '+words(item.inclusion)+'. It is not treated as an in-window observation.');
    if(fact.record_status!=='recorded')reasons.push('Record status: '+(words(fact.record_status)||'not recorded')+'.');
    const result=record(fact.result);
    if(result.result_type==='missing')reasons.push('Result unavailable: '+words(result.status)+'. '+String(result.reason??''));
    if(fact.kind==='circulatory_oxygen'){
      const missing=bloodGasSummary(item).filter(([,text])=>text==='Not recorded').map(([label])=>label);
      if(missing.length)reasons.push('Sample context not recorded: '+missing.join(', ')+'. Applicability is not assessed here.');
      if(fact.sample_type==='unknown')reasons.push('Sample type is unknown.');
    }
    if(fact.kind==='circulatory_echo'&&fact.production==='source_calculated')reasons.push('Source-calculated echo estimate; not recalculated or confirmed against invasive pressure here.');
    const notes=[fact.disclosures,acquisition.limitations,q.limitations,q.artifacts]
      .flatMap(value=>Array.isArray(value)?value.filter((note):note is string=>typeof note==='string'):[]);
    return reasons.length||notes.length?[{item,reasons,notes:[...new Set(notes)]}]:[];
  });
}

/** Preserve view disclosures separately from source-specific quality/estimate flags. */
export function recordedViewCaveats(items:CirculatoryItem[]){
  const groups=new Map<string,CirculatoryItem[]>();
  for(const item of items)for(const note of item.disclosures){
    const sources=groups.get(note)??[];
    if(!sources.includes(item))sources.push(item);
    groups.set(note,sources);
  }
  return [...groups].map(([note,sources])=>({note,sources}));
}
