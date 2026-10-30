import {useMemo,useState} from 'react';
import {infectionCatalogue} from './catalogue';
import {effectiveCases,filterInfections,formatSourceText,type InfectionCatalogue} from './model';
import './infectionLibrary.css';

export function InfectionLibrary({patient,encounter,unconfirmed=false,catalogue=infectionCatalogue}:{patient:string;encounter:string;unconfirmed?:boolean;catalogue?:InfectionCatalogue|null}){
 const [groupId,setGroupId]=useState(()=>catalogue?.groups.find(g=>/respiratory/i.test(g.name))?.id??catalogue?.groups[0]?.id??'');
 const [query,setQuery]=useState(''),[infectionId,setInfectionId]=useState(''),[caseId,setCaseId]=useState(''),[regimenId,setRegimenId]=useState('');
 const matches=useMemo(()=>catalogue?filterInfections(catalogue.infections,groupId,query):[],[catalogue,groupId,query]);
 const infection=matches.find(i=>i.id===infectionId)??matches[0];
 const cases=infection?effectiveCases(infection.cases):[];
 const clinical=cases.find(c=>c.id===caseId)??cases[0];
 const [referenceCaseId,setReferenceCaseId]=useState('');
 const referenced=clinical?.reference?catalogue?.infections.find(i=>i.id===clinical.reference?.infectionId):undefined;
 const referencedCases=referenced?effectiveCases(referenced.cases):[];
 const treatmentClinical=clinical?.reference?referencedCases.find(c=>c.id===referenceCaseId):clinical;
 const regimen=treatmentClinical?.regimens.find(r=>r.id===regimenId)??treatmentClinical?.regimens[0];
 const source=catalogue?.sources.find(s=>s.id===clinical?.sourceId);
 const snapshot=source?`/assets/infection-sources/ncdc-2025.pdf#page=${clinical?.pdfPages[0]}`:undefined;
 const changeInfection=(id:string)=>{setInfectionId(id);setCaseId('');setRegimenId('');setReferenceCaseId('');};
 if(!catalogue)return <section className="infection-library"><h2>Infection library unavailable</h2><p role="alert">The reference catalogue could not be verified. No guidance is displayed.</p></section>;
 return <section className="infection-library" aria-label="Infection-based antibiotic library">
  <div className="infection-title"><div><p className="infection-eyebrow">Reference library</p><h2>Infections &amp; treatment</h2><p className="infection-subtitle">{patient} · Encounter {encounter}</p></div><span className="infection-badge">Unreviewed · reference only</span></div>
  <p className="infection-rule">NCDC guidance only. Reference only — not a prescription or a patient-specific recommendation.</p>
  {unconfirmed&&<p className="infection-note">Patient evidence is unconfirmed. This general reference library is not matched to this patient.</p>}
  <div className="infection-layout">
   <aside className="infection-browser" aria-label="Browse infections">
    <label>Clinical group<select value={groupId} onChange={e=>{setGroupId(e.target.value);setQuery('');changeInfection('');}}>{catalogue.groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select></label>
    <label>Find an infection<input type="search" placeholder="Infection, syndrome or clinical situation" value={query} onChange={e=>{setQuery(e.target.value);changeInfection('');}}/></label>
    <p className="infection-count" role="status">{matches.length?`${matches.length} infections in this group`:'No matching infections. Try another search or clinical group.'}</p>
    <div className="infection-list">{matches.map(i=><button type="button" key={i.id} aria-pressed={infection?.id===i.id} onClick={()=>changeInfection(i.id)}><span>{i.name}</span>{' '}<small>NCDC</small></button>)}</div>
   </aside>
   <div className="infection-selected" aria-live="polite">
    {!infection?<div className="infection-empty"><h3>No infection selected</h3><p>No previous regimen is retained when the search has no match.</p></div>:<article className="infection-detail" key={infection.id}>
     <header><div className="infection-detail-title"><h3>{infection.name}</h3>{source&&<span className="infection-badge">NCDC guidance</span>}</div><p className="infection-subtitle">{catalogue.groups.find(g=>g.id===infection.groupId)?.name}</p></header>
     <div className="infection-context">
      {cases.length>1?<label>Clinical situation<select value={clinical?.id??''} onChange={e=>{setCaseId(e.target.value);setRegimenId('');setReferenceCaseId('');}}>{cases.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label>:clinical&&<p><strong>Clinical situation:</strong> {clinical.label}</p>}
      {clinical?.reference&&<><p className="infection-note">{clinical.reference.label}</p><label>Acute osteomyelitis context<select value={referenceCaseId} onChange={e=>{setReferenceCaseId(e.target.value);setRegimenId('');}}><option value="">Choose the applicable acute context</option>{referencedCases.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label></>}
      {treatmentClinical&&treatmentClinical.regimens.length>1&&<label>Treatment option<select value={regimen?.id??''} onChange={e=>setRegimenId(e.target.value)}>{treatmentClinical.regimens.map((r,index)=><option key={r.id} value={r.id}>{r.label||`Source option ${index+1}`}</option>)}</select></label>}
     </div>
     <section className="infection-regimen" aria-label="Selected treatment guidance">
      <h4>{regimen?.source_branch?'Source-stated branch — clarification required':regimen?'Selected source guidance':clinical?.reference&&!treatmentClinical?'Select the applicable acute context':'Source review required'}</h4>
      {regimen?<><p className="infection-instructions">{formatSourceText(regimen.instructions)}</p>{regimen.duration&&<p><strong>Duration:</strong> {regimen.duration}</p>}</>:clinical?.reference&&!treatmentClinical?<p>NCDC refers this situation to acute osteomyelitis. Choose its applicable context above to see the referenced treatment without assuming a disease pattern.</p>:<p>No fixed regimen is displayed for this clinical situation. Review the documented source gaps below.</p>}
      {!!(clinical?.gaps.length||treatmentClinical?.gaps.length||regimen?.gaps.length)&&<div className="infection-gaps"><h4>Conditions &amp; clarification</h4><ul>{[...new Set([...(clinical?.gaps??[]),...(treatmentClinical?.gaps??[]),...(regimen?.gaps??[])])].map((gap,index)=><li key={index}>{gap}</li>)}</ul></div>}
      {clinical?.reference&&treatmentClinical&&<p className="infection-source-label">Referenced treatment: {treatmentClinical.locator} · <a href={'/assets/infection-sources/ncdc-2025.pdf#page='+treatmentClinical.pdfPages[0]} target="_blank" rel="noopener noreferrer">Open referenced treatment source ↗</a></p>}
      <p className="infection-caption">No patient dose adjustment is applied. Product, route, allergy, susceptibility and treatment context require clinical review.</p>
     </section>
     {!!(clinical?.management?.length||treatmentClinical?.management?.length)&&<section className="infection-management" aria-label="Management and treatment notes"><h4>Management and treatment notes</h4>{[...new Set([...(clinical?.management??[]),...(clinical?.reference?treatmentClinical?.management??[]:[])])].map((note,index)=><p key={index}>{formatSourceText(note)}</p>)}</section>}
     {clinical&&source&&<div className="infection-evidence">
      <p className="infection-source-label">{source.name} · {source.version} · {clinical.locator}</p>
      <details><summary>Source details &amp; treatment notes</summary>{clinical.notes.map((note,index)=><p className="infection-source-note" key={index}>{formatSourceText(note)}</p>)}<p><a href={snapshot} target="_blank" rel="noopener noreferrer">Open retained source · PDF page {clinical.pdfPages[0]} ↗</a></p><p><a href={source.url+'#page='+clinical.pdfPages[0]} target="_blank" rel="noopener noreferrer">Open publisher’s source ↗</a></p><p className="infection-caption">Unreviewed source transcription; this does not establish local hospital policy. Missing fields are not inferred.</p><details><summary>Source identity</summary><p>{source.name} · {source.version}</p><code>{source.sha256}</code><p className="infection-caption">Catalogue {catalogue.version}</p></details></details>
     </div>}
    </article>}
   </div>
  </div>
 </section>;
}
