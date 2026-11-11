import {useMemo,useRef,useState} from 'react';
import {RF2Client,key,pin,type Catalog,type Evidence} from '../api/rf2Client';
import {GISource} from '../gastrointestinal/GISource';
import {PatientSourceDialog} from '../demo/PatientSourceDialog';
import type {MicroState} from '../api/microTypes';
import {microKey,recordSummary} from '../antibioticWorkflow/patientModel';
import {reproductiveModel,reproductiveCategories,categoryOf,findingTime,findingText,recordedFinding,type ReproductiveScope} from './model';
import {ReproductiveReview,useReproductiveReview} from './ReproductiveReview';
import {ReproductiveEntry,readPendingFinding} from './ReproductiveEntry';
import '../gastrointestinal/gastrointestinal.css';
import './reproductive.css';

const tabs=['Overview','Pregnancy & delivery','Gynecology & reproductive care','Results & imaging','Review & plan'] as const;
type Tab=typeof tabs[number];
type Model=ReturnType<typeof reproductiveModel>;
const shortDate=(at:string)=>at.replace('T',' ').replace(/(?:Z|\+00:00)$/,' UTC');
function statusLine(model:Model) {
 const pregnancy=model.pregnancy;
 const count=pregnancy.fetus_count;
 return [model.phaseLabel,model.gestation,count===1?'Singleton':typeof count==='number'?`${count} fetuses`:''].filter(Boolean).join(' · ');
}

export function ReproductiveSummary({catalog,requested,micro,current,onOpen}:{
 catalog?:Catalog;requested:ReproductiveScope;micro?:MicroState;current:boolean;onOpen:()=>void;
}){
 const model=useMemo(()=>reproductiveModel(catalog,requested,micro),[catalog,requested,micro]);
 const saved=useReproductiveReview(catalog,requested);
 const review=current&&model.valid?saved.reviews.find(model.matches):undefined;
 if(!model.records.length)return null;
 return <section className="m12-summary" aria-label="Obstetrics and gynecology summary">
  <div><h3>Obstetrics &amp; gynecology</h3><p>{current&&model.valid?statusLine(model):'Evidence unconfirmed'}
   {review? ` · Review due ${review.draft.nextReview}`:saved.reviews.length&&current?' · Review needed':''}</p></div>
  <button type="button" onClick={onOpen}>Open obstetrics &amp; gynecology</button>
 </section>;
}

function FindingList({records,onSource}:{records:Evidence[];onSource:(e:Evidence,button:HTMLButtonElement)=>void}){
 return records.length?<div>{records.map(source=><article className="m12-row" key={key(pin(source))}>
  <strong>{String(source.fact.title??reproductiveCategories[categoryOf(source)])}</strong>
  <p>{findingText(source)}</p>
  <small>{findingTime(source)?shortDate(findingTime(source)!):'Exact observation time unavailable'} · {String(source.fact.report_status)}</small>
  <button type="button" className="m12-link" onClick={e=>onSource(source,e.currentTarget)}>Open source</button>
 </article>)}</div>:<p>No linked records for this encounter.</p>;
}

function LabTable({rows,onSource}:{rows:Model['labs'];onSource:(e:Evidence,button:HTMLButtonElement)=>void}){
 if(!rows.length)return <p>No relevant mapped laboratory results supplied.</p>;
 return <table className="m12-results"><caption>Shared laboratory results</caption><thead><tr>
  <th scope="col">Test</th><th scope="col">Recorded result</th><th scope="col">Specimen collected</th><th scope="col">Source</th>
 </tr></thead><tbody>{rows.map(row=><tr key={key(pin(row.source))+row.component}>
  <th scope="row">{row.label}</th><td>{row.result}{row.qualifications.map(q=><small key={q}>{q}</small>)}<small>{String(row.source.fact.report_status)}</small></td>
  <td>{row.collection.instant?shortDate(row.collection.instant):row.collection.text}</td>
  <td><button type="button" className="m12-link" onClick={e=>onSource(row.source,e.currentTarget)}>Open lab report</button></td>
 </tr>)}</tbody></table>;
}

export function ReproductiveWorkspace({catalog,requested,micro,current,loading,error,onRefresh,onGuardChange,onNavigate}:{
 catalog?:Catalog;requested:ReproductiveScope;micro?:MicroState;current:boolean;loading:boolean;error?:string;onRefresh:()=>Promise<void>;
 onGuardChange?:(guard:boolean)=>void;onNavigate?:(view:'overview'|'hemodynamics'|'antibiotics')=>void;
}){
 const model=useMemo(()=>reproductiveModel(catalog,requested,micro),[catalog,requested,micro]);
 const saved=useReproductiveReview(catalog,requested);
 const [client]=useState(()=>new RF2Client());
 const [tab,setTab]=useState<Tab>('Overview'),[entry,setEntry]=useState(false);
 const [source,setSource]=useState<Evidence>();
 const returnFocus=useRef<HTMLButtonElement>(null);
 function inspect(e:Evidence,button:HTMLButtonElement){returnFocus.current=button;setSource(e);}
 function closeSource(){setSource(undefined);returnFocus.current?.focus();}
 const confirmed=current&&model.valid&&!loading;
 const matching=confirmed?saved.reviews.find(model.matches):undefined;
 const phase=model.phase;
 const pregnancyRecords=model.records.filter(e=>['pregnancy_status','maternal_assessment','fetal_assessment','labour_delivery','postpartum'].includes(categoryOf(e)));
 const gynecologyRecords=model.records.filter(e=>['gynecology','reproductive_care'].includes(categoryOf(e)));
 const gynecology=phase==='not_pregnant'||phase==='unknown'&&gynecologyRecords.length>0;
 const reports=model.records.filter(e=>['imaging','procedure'].includes(categoryOf(e)));
 const assessment=gynecology?gynecologyRecords:pregnancyRecords.filter(e=>categoryOf(e)!=='pregnancy_status');
 const smallLabs=model.labs.filter(r=>(gynecology?['hemoglobin','platelets']:['platelets','creatinine','ast','hemoglobin']).includes(r.concept)).slice(0,6);
 const pending=catalog?readPendingFinding(catalog.repository):false;
 return <section className="m12-workspace" aria-label="Obstetrics, gynecology and reproductive care workspace">
  <header className="m12-heading">
   <div><h2>Obstetrics, gynecology &amp; reproductive care</h2><small>{shortDate(requested.start)} → {shortDate(requested.end)}</small></div>
   <div><button type="button" className="m12-primary" disabled={!confirmed&&!pending} onClick={()=>setEntry(true)}>{pending?'Resume finding entry':'Record finding'}</button>
    <button type="button" disabled={loading} onClick={()=>void onRefresh().catch(()=>{})}>Refresh evidence</button></div>
  </header>
  {!confirmed&&<p role="status">{loading?'Loading patient evidence…':'Patient evidence is unconfirmed.'} {error}</p>}
  <div className="m12-state">
   <strong>{statusLine(model)}</strong>
   {model.status&&recordedFinding(model.status)&&model.pregnancy.phase!==undefined&&<p>{findingText(model.status)}</p>}
   {(model.pregnancy.dating_basis||model.pregnancy.estimated_due_date)?<small>
    {[model.pregnancy.dating_basis,model.pregnancy.estimated_due_date?`Estimated due date ${model.pregnancy.estimated_due_date}`:null].filter(Boolean).join(' · ')}
   </small>:null}
   {model.status&&model.pregnancy.phase!==undefined&&findingTime(model.status)&&<small>Status recorded {shortDate(findingTime(model.status)!)}</small>}
   {model.status&&<button type="button" className="m12-link" onClick={e=>inspect(model.status!,e.currentTarget)}>View status and dating source</button>}
  </div>
  <div role="tablist" className="m12-tabs" aria-label="Obstetrics and gynecology review areas">
   {tabs.map((label,index)=><button id={`m12-tab-${index}`} aria-controls="m12-panel" type="button" role="tab"
    aria-selected={tab===label} tabIndex={tab===label?0:-1} key={label} onClick={()=>setTab(label)}
    onKeyDown={e=>{const next=e.key==='ArrowRight'?(index+1)%tabs.length:e.key==='ArrowLeft'?(index+tabs.length-1)%tabs.length:e.key==='Home'?0:e.key==='End'?tabs.length-1:null;
     if(next!==null){e.preventDefault();setTab(tabs[next]);document.getElementById(`m12-tab-${next}`)?.focus();}}}>{label}</button>)}
  </div>
  <div id="m12-panel" role="tabpanel" aria-labelledby={`m12-tab-${tabs.indexOf(tab)}`}>
   {tab==='Overview'&&<>
    <div className="m12-grid">
     <section className="m12-card"><h3>{gynecology?'Gynecology and reproductive findings':phase==='postpartum'?'Postpartum findings':'Maternal and fetal findings'}</h3>
      <FindingList records={assessment.slice(0,3)} onSource={inspect}/>
      {!!reports.length&&<button type="button" onClick={()=>setTab('Results & imaging')}>Results &amp; imaging</button>}
     </section>
     <section className="m12-card"><h3>{gynecology?'Relevant results':'Maternal observations & results'}</h3>
      {!!model.pressures.length&&<ul className="m12-pressures">{model.pressures.slice(0,2).map(row=><li key={key(pin(row.sources[0]))}>
       <strong>{row.text}</strong> <small>{shortDate(row.at)}</small>
       {row.sources.map(e=><button key={key(pin(e))} className="m12-link" type="button" onClick={event=>inspect(e,event.currentTarget)}>
        {e.fact.concept==='systemic_systolic'?'Systolic source':'Diastolic source'}</button>)}
      </li>)}</ul>}
      <LabTable rows={smallLabs} onSource={inspect}/>
      {onNavigate&&!gynecology&&<button type="button" onClick={()=>onNavigate('hemodynamics')}>View BP trend</button>}
     </section>
    </div>
    <section className="m12-summary" aria-label="M12 review status"><div><h3>Review &amp; plan</h3>
     {matching?<><p>{matching.draft.rationale}</p><small>Next review {matching.draft.nextReview} · {matching.draft.reviewer}</small></>:
      <p>{!confirmed?'Evidence unconfirmed':saved.reviews.length?'Evidence changed · Review needed':'Review not recorded'}</p>}</div>
     <button type="button" onClick={()=>setTab('Review & plan')}>Open review</button>
    </section>
   </>}
   {tab==='Pregnancy & delivery'&&<section className="m12-card"><h3>Pregnancy, labour and postpartum timeline</h3><FindingList records={pregnancyRecords} onSource={inspect}/></section>}
   {tab==='Gynecology & reproductive care'&&<section className="m12-card"><h3>Gynecology and reproductive care timeline</h3><FindingList records={gynecologyRecords} onSource={inspect}/></section>}
   {tab==='Results & imaging'&&<>
    <section className="m12-card"><div className="m12-heading"><h3>Laboratory results</h3>
     {onNavigate&&<button type="button" onClick={()=>onNavigate('overview')}>Open Patient overview for lab entry</button>}</div><LabTable rows={model.labs} onSource={inspect}/></section>
    <section className="m12-card"><h3>Imaging &amp; procedures</h3><FindingList records={reports} onSource={inspect}/></section>
   </>}
   <div hidden={tab!=='Review & plan'}><ReproductiveReview catalog={catalog} requested={requested} model={model} current={confirmed} saved={saved}/></div>
  </div>
  {onNavigate&&<details className="m12-context"><summary>Shared antimicrobial records</summary>
   {model.medications.length?<ul>{model.medications.map(item=><li key={microKey(item)}>{recordSummary(item)}</li>)}</ul>:
    <p>{model.medicationConfirmed?'No linked antimicrobial record in this view.':'Antimicrobial records are unconfirmed.'}</p>}
   <button type="button" onClick={()=>onNavigate('antibiotics')}>Open antimicrobial prescriptions &amp; administrations</button></details>}
  {source&&source.fact.kind!=='circulatory_pressure'&&<GISource evidence={source} transport={client} current={confirmed} onClose={closeSource}/>}
  {source&&source.fact.kind==='circulatory_pressure'&&catalog&&returnFocus.current&&
   <PatientSourceDialog selection={{evidence:source,catalog,label:source.fact.concept==='systemic_systolic'?'Systolic blood pressure':'Diastolic blood pressure',trigger:returnFocus.current}}
    transport={client} current={confirmed} onClose={closeSource}/>}
  {entry&&catalog&&<ReproductiveEntry catalog={catalog} requested={requested} current={confirmed} transport={client} onClose={()=>setEntry(false)} onRefresh={onRefresh} onGuardChange={onGuardChange}/>}
 </section>;
}
