import {useState} from 'react';
import type {CirculatoryItem,ExactRef} from '../api/circulatoryTypes';
export const families:Record<string,string>={
  circulatory_pressure:'Pressure and PAC/RHC',circulatory_cardiac:'Cardiac output and performance',
  circulatory_volume:'Volume and lung water',circulatory_dynamic:'Dynamic measurements',
  circulatory_device_prediction:'Recorded device predictions',circulatory_perfusion:'Tissue perfusion',
  circulatory_oxygen:'Oxygen transport',circulatory_lactate:'Lactate',circulatory_echo:'Echo and POCUS',
  circulatory_ecg:'ECG and rhythm',circulatory_vasoactive:'Vasoactive events',circulatory_monitoring:'Edwards / PiCCO and monitoring context',
  circulatory_assessment:'Dynamic assessment episodes',circulatory_event:'Recorded circulatory events',circulatory_signal:'Signal manifests'};
export function reference(item:CirculatoryItem):ExactRef{return {kind:item.fact.kind,id:item.fact.id,version:item.fact.revision};}
export function refKey(ref:ExactRef):string{return JSON.stringify([ref.kind,ref.id,ref.version]);}
function label(key:string){return key.replaceAll('_',' ');}
/** Render validated source values as text, preserving Decimal strings and offsets. */
export function RecordedDetails({value}:{value:unknown}) {
  if(value===null||value===undefined)return <span className="muted">Not supplied</span>;
  if(typeof value!=='object')return <span className="recorded-value">{String(value)}</span>;
  if(Array.isArray(value))return value.length?<ol>{value.map((child,n)=><li key={n}><RecordedDetails value={child}/></li>)}</ol>:<span className="muted">None declared</span>;
  return <dl>{Object.entries(value).map(([key,child])=><div key={key}><dt>{label(key)}</dt><dd><RecordedDetails value={child}/></dd></div>)}</dl>;
}
export function RecordedDisclosure({label,value}:{label:string;value:unknown}) {
  const [open,setOpen]=useState(false);
  return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>{label}</summary>{open&&<RecordedDetails value={value}/>}</details>;
}
export function CirculatoryEvidence({item,onHistory,disabled}:{item:CirculatoryItem;onHistory:()=>void;disabled:boolean}) {
  return <article className="m7-evidence"><h4>{item.fact.id} · revision {item.fact.revision}</h4>
    <p>Recorded source evidence · {item.inclusion.replaceAll('_',' ')}</p>
    <RecordedDisclosure label="Source, timing, quality and device context" value={item.fact}/>
    <RecordedDisclosure label="Repository metadata and inclusion" value={{expected_digest:item.expected_digest,ingestion:item.ingestion,contextual_for:item.contextual_for,disclosures:item.disclosures}}/>
    <button type="button" disabled={disabled} onClick={onHistory}>Inspect corrections for {item.fact.id}</button>
  </article>;
}
