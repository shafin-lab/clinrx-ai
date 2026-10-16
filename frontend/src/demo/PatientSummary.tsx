import type {CirculatoryItem} from '../api/circulatoryTypes';
import {bloodGasSummary,method,quality,record,sourceTime,title,value,words} from './evidencePresentation';

type Props={items:CirculatoryItem[];patientId:string;encounterId:string;start:string;end:string;onInspect:(item:CirculatoryItem,trigger:HTMLButtonElement)=>void};
const sections=[
  {id:'gases',title:'ABG and oxygen transport',description:'Read the gases with each sample’s collection time and respiratory settings.',kinds:['circulatory_oxygen']},
  {id:'flow',title:'Cardiac output and pressures',description:'Compare recorded methods. No preferred value, average or trend is calculated.',kinds:['circulatory_cardiac','circulatory_pressure']},
  {id:'echo',title:'Echo and right-heart findings',description:'Source estimates and report findings remain distinct from invasive measurements.',kinds:['circulatory_echo']},
  {id:'perfusion',title:'Perfusion and circulatory support',description:'Lactate, bedside perfusion and vasoactive events add their own source context.',kinds:['circulatory_lactate','circulatory_perfusion','circulatory_vasoactive','circulatory_device_prediction']},
];
function context(item:CirculatoryItem){
  if(item.fact.kind==='circulatory_oxygen')return bloodGasSummary(item).map(([label,text])=>label+': '+text).join(' · ');
  if(item.fact.kind==='circulatory_echo')return 'Study: '+String(record(item.fact.study).raw_display??'Not recorded')+' · Report: '+String(record(item.fact.report).raw_display??'Not recorded')+' · Report revision: '+String(item.fact.report_revision??'Not recorded');
  return method(item);
}
export function PatientSummary({items,patientId,encounterId,start,end,onInspect}:Props){
  return <section aria-label="Combined patient evidence summary" className="demo-summary">
    <div className="demo-summary-intro"><h2>One patient, evidence together</h2><p>Read blood gases and sample-time settings beside recorded flow, pressures and echo findings. Open any source to inspect its exact revision and correction history.</p><p>Patient: {patientId} · Encounter: {encounterId}</p><p><strong>Recorded review window:</strong> {start} → {end}</p><p>These records are grouped for browsing. A shared time or study label does not establish simultaneity or clinical agreement. No combined diagnosis, score, treatment recommendation or new inference is generated.</p></div>
    <div className="demo-summary-panels">{sections.map(section=>{
      const records=items.filter(item=>section.kinds.includes(item.fact.kind));
      return <section key={section.id} className="demo-summary-panel" aria-label={section.title}><h3>{section.title}</h3><p>{section.description}</p>
        {!records.length?<p className="demo-empty">No records in this bounded view. Clinical absence is not established.</p>:<ul>{records.map(item=>{
          const result=value(item),finding=record(item.fact.result).result_type==='qualitative';
          return <li key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])}>
            <button className="demo-summary-source" aria-label={'Open summary source '+title(item)+' '+item.fact.id} onClick={event=>onInspect(item,event.currentTarget)}><span>{title(item)}</span><strong>{result.text}{' '}<small>{result.unit==='1'?'(unit: 1)':result.unit}</small></strong><span className="demo-summary-link">Inspect source ↗</span></button>
            <p>{finding?'Source report finding':words(item.fact.production)||'Recorded source'} · {method(item)}</p>
            <p><strong>{words(item.inclusion)}</strong> · Source time: {sourceTime(item)} · Quality: {quality(item)} · Record status: {words(item.fact.record_status)||'Not recorded'}</p>
            <p className="demo-summary-context">{context(item)}</p>
            {item.fact.kind==='circulatory_echo'&&item.fact.production==='source_calculated'&&<p className="demo-summary-caution">Source-reported estimate; not recalculated by ClinRx.</p>}
            <small>{item.fact.id} / {item.fact.revision}</small>
          </li>;
        })}</ul>}
      </section>;
    })}</div>
    <aside className="demo-summary-gaps" aria-label="Summary limitations"><h3>Keep the gaps in view</h3><p>HPI is optional: {items.some(item=>item.fact.kind==='circulatory_device_prediction')?'a source record is available.':'not recorded in this case.'} Missing sample settings are not borrowed from another record. Earlier contextual and unplaced records retain their labels; source quality is not upgraded.</p><p>Echo PH wording is a source report impression; no PH diagnosis or PAH subtype is inferred. This summary does not calculate cardiac output from VTI or interpret acid–base status. Explore the Evidence library for the other evidence families.</p></aside>
  </section>;
}
