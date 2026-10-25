import {useMemo,useState} from 'react';
import {infectionCatalogue} from './catalogue';
import {formatSourceText,type InfectionCatalogue} from './model';
import {doseNotes,formatTreatment,validateCompleteGuidance,type CompleteNcdcSection} from './completeNcdcModel';
import './infectionLibrary.css';

function Treatment({title,text}:{title:string;text:string}){
 const notes=doseNotes(text);
 return <section className="ncdc-treatment" aria-label={title}><h4>{title}</h4>
  {text.trim()?formatTreatment(text).map((line,index)=>/^(OR|\+|\+\/-|±)$/.test(line)?<p className="ncdc-operator" key={index}>{line}</p>:<p key={index}>{line}</p>):<p className="infection-caption">Not stated in this NCDC row.</p>}
  {notes.map((note,index)=><p className="ncdc-dose-note" key={index}><strong>Dose note:</strong> {note}</p>)}
 </section>;
}
const normalize=(text:string)=>text.normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
export function CompleteNcdcLibrary({patient,encounter,data,catalogue=infectionCatalogue,unconfirmed=false}:{patient:string;encounter:string;data:unknown;catalogue?:InfectionCatalogue|null;unconfirmed?:boolean}){
 const complete=useMemo(()=>validateCompleteGuidance(data)?data:null,[data]);
 const [groupId,setGroupId]=useState(()=>catalogue?.groups.find(g=>/respiratory/i.test(g.name))?.id??catalogue?.groups[0]?.id??'');
 const [query,setQuery]=useState(''),[infectionId,setInfectionId]=useState(''),[rowId,setRowId]=useState(''),[referenceId,setReferenceId]=useState('');
 const terms=normalize(query).split(' ').filter(Boolean);
 const matches=(catalogue?.infections??[]).filter(infection=>infection.groupId===groupId&&terms.every(term=>normalize([infection.name,...infection.aliases,...(complete?.sections.find(s=>s.infectionId===infection.id)?.rows.map(r=>r.label)??[])].join(' ')).includes(term)));
 const infection=matches.find(i=>i.id===infectionId)??matches[0];
 const section=complete?.sections.find(s=>s.infectionId===infection?.id);
 const row=section?.rows.find(r=>r.id===rowId)??section?.rows[0];
 const canonicalReference=infection?.cases.find(c=>c.reference&&normalize(c.label)===normalize(row?.label??''))?.reference;
 const reference=canonicalReference?complete?.sections.find(s=>s.infectionId===canonicalReference.infectionId):undefined;
 const treatmentRow=reference?reference.rows.find(r=>r.id===referenceId):row;
 const reset=()=>{setRowId('');setReferenceId('');};
 if(!catalogue||!complete)return <section><h2>NCDC library unavailable</h2><p role="alert">The NCDC source could not be verified. No treatment guidance is displayed.</p></section>;
 const source=complete.source;
 const originalImages=(current:CompleteNcdcSection)=><details className="ncdc-original"><summary>Original NCDC section · source details</summary><p>{source.name} · {source.version}</p>{current.figures.filter(f=>!f.primary).map((figure,index)=><figure key={index}><img src={figure.imagePath} alt={figure.caption} loading="lazy"/><figcaption>{figure.caption}</figcaption></figure>)}<p><a href={'/assets/infection-sources/ncdc-2025.pdf#page='+current.pdfPages[0]} target="_blank" rel="noopener noreferrer">Open retained NCDC PDF · page {current.pdfPages[0]} ↗</a></p><p><a href={source.url+'#page='+current.pdfPages[0]} target="_blank" rel="noopener noreferrer">Open publisher’s source ↗</a></p><details><summary>Source identity</summary><code>{source.sha256}</code></details></details>;
 return <section className="infection-library" aria-label="Infection-based antibiotic library">
  <div className="infection-title"><div><p className="infection-eyebrow">Reference library</p><h2>Infections &amp; treatment</h2><p className="infection-subtitle">{patient} · Encounter {encounter}</p></div><span className="infection-badge">Unreviewed · reference only</span></div>
  <p className="infection-rule">NCDC guidance only. Reference only — not a prescription or a patient-specific recommendation.</p>
  {unconfirmed&&<p className="infection-note">Patient evidence is unconfirmed. This general reference library is not matched to this patient.</p>}
  <div className="infection-layout"><aside className="infection-browser" aria-label="Browse infections">
   <label>Clinical group<select value={groupId} onChange={e=>{setGroupId(e.target.value);setQuery('');setInfectionId('');reset();}}>{catalogue.groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select></label>
   <label>Find an infection<input type="search" value={query} placeholder="Infection, syndrome or clinical situation" onChange={e=>{setQuery(e.target.value);setInfectionId('');reset();}}/></label>
   <p role="status" className="infection-count">{matches.length?`${matches.length} infections in this group`:'No matching infections. Try another search or clinical group.'}</p>
   <div className="infection-list">{matches.map(i=><button key={i.id} type="button" aria-pressed={i.id===infection?.id} onClick={()=>{setInfectionId(i.id);reset();}}><span>{i.name}</span>{' '}<small>NCDC</small></button>)}</div>
  </aside><div className="infection-selected" aria-live="polite">
   {!infection?<div className="infection-empty"><h3>No infection selected</h3><p>No previous treatment is retained when the search has no match.</p></div>:!section?<div className="infection-empty"><h3>{infection.name}</h3><p role="alert">This NCDC section is unavailable.</p></div>:<article className="infection-detail" key={infection.id}>
    <header><div className="infection-detail-title"><h3>{infection.name}</h3><span className="infection-badge">NCDC guidance</span></div><p className="infection-subtitle">NCDC section {section.section} · {section.name}</p></header>
    {section.rows.length>1&&<div className="infection-context"><label>Clinical situation<select value={row?.id??''} onChange={e=>{setRowId(e.target.value);setReferenceId('');}}>{section.rows.map(r=><option key={r.id} value={r.id}>{formatSourceText(r.label)||'Source treatment row'}</option>)}</select></label></div>}
    {section.rows.length===1&&row?.label&&<div className="infection-context"><p><strong>Clinical situation:</strong> {formatSourceText(row.label)}</p></div>}
    {reference&&<div className="infection-context"><p className="infection-note">Empirical treatment referenced from NCDC acute osteomyelitis guidance.</p><label>Acute osteomyelitis context<select value={referenceId} onChange={e=>setReferenceId(e.target.value)}><option value="">Choose the applicable acute context</option>{reference.rows.map(r=><option key={r.id} value={r.id}>{formatSourceText(r.label)}</option>)}</select></label></div>}
    {reference&&!treatmentRow&&<p className="ncdc-reference-prompt">Choose the applicable acute context to display its treatment here.</p>}
    {treatmentRow&&<><Treatment title="First-line treatment" text={treatmentRow.firstLine}/><Treatment title="Alternative treatment" text={treatmentRow.alternative}/></>}
    {(row?.comments||reference||treatmentRow?.comments)&&<section className="infection-management" aria-label="Comments"><h4>Comments</h4>{[...new Set([...(reference?[row?.firstLine??'',row?.alternative??'']:[]),row?.comments??'',treatmentRow?.comments??''])].filter(Boolean).map((text,index)=><p key={index}>{formatSourceText(text)}</p>)}</section>}
    {reference&&treatmentRow&&<p className="ncdc-reference-prompt">Referenced treatment: NCDC section {reference.section} · PDF page {treatmentRow.pdfPages.join(', ')} · <a href={'/assets/infection-sources/ncdc-2025.pdf#page='+treatmentRow.pdfPages[0]} target="_blank" rel="noopener noreferrer">Open referenced treatment source ↗</a></p>}
    {!!section.notes.length&&<section className="infection-management" aria-label="Additional NCDC guidance"><h4>Additional guidance</h4>{section.notes.map((note,index)=><p key={index}>{formatSourceText(note.text)}</p>)}</section>}
    {section.figures.filter(f=>f.primary).map((figure,index)=><figure className="ncdc-primary-figure" key={index}><img src={figure.imagePath} alt={figure.caption} loading="lazy"/><figcaption>{figure.caption}</figcaption></figure>)}
    {!section.rows.length&&!section.figures.some(f=>f.primary)&&<section className="infection-management">{section.figures.length?section.figures.map((figure,index)=><figure key={index}><img className="ncdc-fallback-image" src={figure.imagePath} alt={figure.caption} loading="lazy"/><figcaption>{figure.caption}</figcaption></figure>):<p>{formatSourceText(section.sourceText)}</p>}</section>}
    <div className="infection-evidence"><p className="infection-source-label">{source.name} · {source.version} · PDF page {section.pdfPages.join(', ')}</p>{originalImages(section)}</div>
   </article>}
  </div></div>
 </section>;
}
