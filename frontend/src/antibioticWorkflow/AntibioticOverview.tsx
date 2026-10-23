import type {MicroState} from '../api/microTypes';
import {recordSummary,antibioticLabel,microKey,microTime} from './patientModel';
const record=(value:unknown):Record<string,any>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,any>:{};
const refKey=(value:unknown)=>{const r=record(value);return JSON.stringify([r.kind,r.id,r.version]);};
const timeValue=(value:unknown)=>{const t=record(value);return t.status==='known'&&typeof t.value==='string'?t.value:'Time not recorded';};
function cultureLabel(item:ReturnType<typeof stateItems>[number]|undefined,hasIsolate:boolean){
 if(!item)return 'Culture finding unavailable';const fact=record(item.fact),report=record(fact.report),status=String(report.status??'unknown'),change=String(report.change??'original'),growth=String(fact.growth??'').toLowerCase();
 if(change==='corrected'||change==='amended')return `Corrected · ${status}`;
 if(change==='superseded')return 'Superseded · prior report retained';
 if(status==='pending')return 'Pending';if(status==='preliminary'||status==='interim')return 'Preliminary';
 if(status==='final'&&['no_growth','no growth','none'].includes(growth))return 'Final · no growth';
 if(status==='final'&&(hasIsolate||['growth','positive','grew'].includes(growth)))return 'Final · positive';
 return status==='unknown'?'Report status unavailable':status[0].toUpperCase()+status.slice(1);
}
function stateItems(state?:MicroState){return state?.assembly.snapshot.items??[];}
export function AntibioticOverview({state,current,onOpen}:{state?:MicroState;current:boolean;onOpen:()=>void}){
 const items=stateItems(state),meds=items.filter(i=>String(i.fact.kind).startsWith('antimicrobial_')),ast=items.filter(i=>i.fact.kind==='microbiology_susceptibility'),cultureReports=items.filter(i=>i.fact.kind==='microbiology_culture');
 const micro=record(state?.assembly.snapshot.microbiology),specimenGroups=Array.isArray(micro.specimens)?micro.specimens.map(record):[];
 const byRef=new Map(items.map(item=>[refKey({kind:item.fact.kind,id:item.fact.id,version:item.fact.revision}),item]));
 return <section aria-label="Patient antibiotics and cultures" className="connected-antibiotics"><h3>Antibiotics and cultures</h3>
  {!state?<p role="status">Microbiology and antibiotic evidence is unavailable or unconfirmed. This does not establish that no reports exist.</p>:<>
   {!cultureReports.length&&<p>No linked culture report is available in this patient view.</p>}
   {!!cultureReports.length&&!specimenGroups.length&&<p>Culture report evidence is present, but no linked specimen group is available in this patient view.</p>}
   {specimenGroups.map(group=>{const specimen=byRef.get(refKey(group.specimen)),sf=record(specimen?.fact),name=[record(sf.specimen_type).raw_display,record(sf.site).raw_display].filter(v=>typeof v==='string'&&v.trim()).join(' · ')||'Specimen details unavailable',cultures=(Array.isArray(group.cultures)?group.cultures:[]).map((ref:unknown)=>byRef.get(refKey(ref))).filter(Boolean),isolates=(Array.isArray(group.isolates)?group.isolates:[]).map((ref:unknown)=>byRef.get(refKey(ref))).filter(Boolean),collected=timeValue(sf.collected);
    return <article className="connected-culture-summary" key={refKey(group.specimen)}><h4>{name}</h4><p>Collected {collected}</p>{cultures.length?cultures.map(item=>{const fact=record(item!.fact),report=record(fact.report);return <p key={microKey(item!)}><strong>{cultureLabel(item,isolates.length>0)}</strong> · {typeof fact.growth==='string'?`Growth: ${fact.growth.replaceAll('_',' ')}`:'Growth not reported'} · Reported {timeValue(report.reported??report.available)} · source {item!.fact.id} / {item!.fact.revision}</p>;}):<p>No culture finding is linked to this specimen in the current snapshot.</p>}{isolates.length>0&&<p>{isolates.map(item=>String(record(record(item!.fact).organism).raw_display??'Organism not reported')).join(' · ')}</p>}</article>;
   })}
   <h4>Reported susceptibility results</h4>{ast.length?ast.map(item=>{const fact=record(item.fact),interp=record(fact.interpretation);return <p key={microKey(item)}>{antibioticLabel(item)} · {String(interp.raw??'Result not reported')} ({String(interp.category??'category unavailable')}) · {microTime(item)} · source {item.fact.id} / {item.fact.revision}</p>;}):<p>No susceptibility result is linked in this patient view.</p>}
   <h4>Prescriptions, administrations and non-delivery</h4>{meds.length?meds.map(item=><p key={microKey(item)}>{recordSummary(item)}</p>):<p>No prescription, administration or non-delivery record appears in this view. This does not establish that no antibiotic was given.</p>}
   <details><summary>Source coverage</summary><p>{specimenGroups.length} specimen groups · {meds.length} prescription/administration/non-delivery sources · {ast.length} susceptibility reports in this patient view.</p></details>
   <p className="connected-course-note">These are source-reported records. They do not establish infection, treatment need, current therapy or a complete regimen.</p>
  </>}
  <button type="button" disabled={!current} onClick={onOpen}>Open antibiotic review</button>
 </section>;
}
