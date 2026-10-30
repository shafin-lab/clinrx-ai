import {useEffect,useMemo,useState,useId} from 'react';
import data from '../data/antibiotic-profiles.json';
import type {Library,Profile} from './profileTypes';
import {Citations,EvidenceTable,FactTable,uniqueReferences} from './ProfileEvidence';
import './ClinRxAntibioticProfileBrowser.css';
const library=data as Library;
const tabs=[['overview','Overview'],['uses','Uses & spectrum'],['dosing','Dosing'],['pkpd','PK/PD'],['safety','Safety'],['practice','Administration & monitoring'],['references','References']] as const;
type View=typeof tabs[number][0];
const groups:Record<View,string[]>={overview:['overview','mechanism'],uses:['indications','spectrum'],dosing:['dosing','adjustments'],pkpd:['pharmacokinetics','pharmacodynamics'],safety:['safety','interactions','populations'],practice:['administration','monitoring','stewardship'],references:[]};
const normalized=(value:string)=>value.toLowerCase().replace(/[^a-z0-9]/g,'');
const matchesIdentity=(record:Profile,name:string)=>normalized(record.name)===normalized(name)||normalized(record.id)===normalized(name);
const exactMatches=(name:string)=>library.records.filter(r=>matchesIdentity(r,name));
function SourceSections({profile,keys}:{profile:Profile;keys:string[]}){
 return <>{keys.map(key=>{const section=profile.sections[key];if(!section)return null;return <section className="rx-source-section" key={key}><h3>{library.section_labels[key]||key}</h3>{section.status==='gap'&&<p className="rx-gap">Evidence limit · {section.source_inclusion_approval?.status==='approved_by_user_for_module_inclusion'?'Source inclusion approved; clinical evidence remains incomplete.':'Information remains incomplete.'}</p>}<p className="rx-source-text">{section.text}</p><Citations profile={profile} ids={section.source_ids||[]}/></section>})}</>
}
function ProfileBody({profile,view}:{profile:Profile;view:View}){
 const x=profile.expanded;
 let retained:string[]=[];
 const parts:React.ReactNode[]=[];
 if(view==='references')return <section className="rx-panel"><h3>References</h3><ol className="rx-reference-list">{uniqueReferences(profile.references).map(r=><li key={r.id}><a href={r.url} target="_blank" rel="noreferrer">{r.title} ↗</a><small>{r.jurisdiction}{r.accessed_date?` · Checked ${r.accessed_date}`:''}</small></li>)}</ol></section>;
 if(view==='overview')parts.push(<SourceSections key="overview" profile={profile} keys={groups.overview}/>);
 if(view==='uses'){
  parts.push(<SourceSections key="uses" profile={profile} keys={['indications']}/>);
  if(x?.spectrum.length){parts.push(...x.spectrum.map((t,i)=><EvidenceTable key={'s'+i} table={t} profile={profile}/>));retained=['spectrum'];}
  else parts.push(<SourceSections key="spectrum" profile={profile} keys={['spectrum']}/>);
 }
 if(view==='dosing'){
  if(x?.dosing.length){parts.push(...x.dosing.map((t,i)=><EvidenceTable key={'d'+i} table={t} profile={profile}/>));retained.push('dosing');}
  else parts.push(<SourceSections key="dosing" profile={profile} keys={['dosing']}/>);
  if(x?.renal.length){parts.push(...x.renal.map((t,i)=><EvidenceTable key={'r'+i} table={t} profile={profile}/>));retained.push('adjustments');}
  else parts.push(<SourceSections key="adjustments" profile={profile} keys={['adjustments']}/>);
 }
 if(view==='pkpd'){
  if(x?.pk.length){parts.push(<FactTable key="pk" title="PK" facts={x.pk} profile={profile}/>);retained.push('pharmacokinetics');}
  else parts.push(<SourceSections key="pk" profile={profile} keys={['pharmacokinetics']}/>);
  if(x?.pd.length){parts.push(<FactTable key="pd" title="PD" facts={x.pd} profile={profile}/>);retained.push('pharmacodynamics');}
  else parts.push(<SourceSections key="pd" profile={profile} keys={['pharmacodynamics']}/>);
 }
 if(view==='safety'){
  parts.push(<SourceSections key="safety" profile={profile} keys={['safety']}/>);
  if(x?.interactions.length)parts.push(...x.interactions.map((t,i)=><EvidenceTable key={'i'+i} table={t} profile={profile}/>));
  parts.push(<SourceSections key="interactions" profile={profile} keys={['interactions']}/>);
  parts.push(<details className="rx-details" key="populations"><summary>Special populations</summary><SourceSections profile={profile} keys={['populations']}/></details>);
 }
 if(view==='practice')parts.push(<SourceSections key="practice" profile={profile} keys={groups.practice}/>);
 const advanced=(x?.advanced||[]).filter(a=>{const isPK=/pharmacokinetic|pharmacodynamic|pharmacology|exposure/i.test(a.title);return view==='pkpd'?isPK:view==='dosing'?!isPK:false});
 return <div className="rx-panel">
  {parts}
  {advanced.map((a,i)=><details className="rx-details" key={'a'+i}><summary>{a.title}</summary><div className="rx-advanced"><p className="rx-source-text">{a.text}</p>{a.tables.map((t,j)=><EvidenceTable key={j} table={t} profile={profile}/>)}<Citations profile={profile} ids={a.source_ids}/></div></details>)}
  {!!retained.length&&<details className="rx-details"><summary>Full source summaries</summary><SourceSections profile={profile} keys={retained}/></details>}
  {view==='dosing'&&!!x?.audit.limitations.length&&<details className="rx-details rx-limits"><summary>Evidence limits</summary><ul>{x.audit.limitations.map((limit,i)=><li key={i}>{limit}</li>)}</ul></details>}
 </div>
}
export const ClinRxAntibioticProfileBrowser=({initialMedicine,onReturn,patientLabel}:{initialMedicine?:string;onReturn?:()=>void;patientLabel?:string})=>{
 const instanceId=useId(), searchId=instanceId+'-search', contentId=instanceId+'-content';
 const [query,setQuery]=useState(initialMedicine||'');
 const [scope,setScope]=useState('all');
 const [selected,setSelected]=useState(initialMedicine?exactMatches(initialMedicine)[0]?.id||'':'meropenem');
 const [view,setView]=useState<View>('overview');
 useEffect(()=>{if(initialMedicine){const found=exactMatches(initialMedicine);setQuery(initialMedicine);setSelected(found.length===1?found[0].id:'');setScope('all');setView('overview')}},[initialMedicine]);
 const missingRequested=!!initialMedicine&&query===initialMedicine&&exactMatches(initialMedicine).length!==1;
 const matches=useMemo(()=>missingRequested?[]:library.records.filter(r=>{if(scope!=='all'&&r.scope!==scope)return false;const q=query.trim().toLowerCase();return !q||matchesIdentity(r,q)||[r.id,r.name,r.class,...r.forms,...Object.values(r.sections).map(s=>s.text)].join(' ').toLowerCase().includes(q)}).sort((a,b)=>Number(matchesIdentity(b,query))-Number(matchesIdentity(a,query))),[query,scope,missingRequested]);
 const active=matches.find(r=>r.id===selected)||matches[0];
 function searchAntibiotics(value:string){setQuery(value);setView('overview');const exact=exactMatches(value);if(exact.length===1)setSelected(exact[0].id)}
 return <div className="rx-reference-app">
  {onReturn&&<div className="rx-return"><button type="button" onClick={onReturn}>← Return to patient review</button><span>{patientLabel||'Patient review retained'}</span></div>}
  <header className="rx-topbar"><div className="rx-brand">ClinRx<small>ANTIBIOTIC REFERENCE</small></div><span>{library.records.length} profiles · International & Indian sources</span></header>
  <div className="rx-layout">
   <aside className="rx-sidebar"><h1>Antibiotics</h1><label className="rx-search-label" htmlFor={searchId}>Find an antibiotic</label><div className="rx-search"><input id={searchId} aria-label="Search antibiotics and profile details" placeholder="Name, class or clinical detail" value={query} onChange={e=>searchAntibiotics(e.target.value)}/>{query&&<button type="button" aria-label="Clear search" onClick={()=>setQuery('')}>×</button>}</div>
   <label className="rx-filter">Category<select value={scope} onChange={e=>{setScope(e.target.value);setView('overview')}}><option value="all">All antibiotics</option><option value="systemic">Systemic</option><option value="antimycobacterial">TB & antimycobacterial</option><option value="local">Local use</option><option value="mixed">Multiple routes</option></select></label>
   <nav className="rx-directory" aria-label="Antibiotic directory">{matches.map(r=><button type="button" key={r.id} aria-pressed={r.id===active?.id} onClick={()=>{setSelected(r.id);setView('overview')}}><strong>{r.name}</strong><small>{r.class}</small></button>)}</nav>{!matches.length&&<p className="rx-directory-empty">No matching antibiotics.</p>}
   </aside>
   <main className="rx-main">{!active?<div className="rx-empty" role="status">{missingRequested?`No dedicated profile matches ${initialMedicine}. No other drug has been substituted. Clear the search to browse.`:'No matching profile. Change the search or category.'}</div>:<>
    <div className="rx-profile-heading"><div><div className="rx-breadcrumb">Reference library / Antibiotics</div><h2>{active.name}</h2><p>{active.class}</p></div><span className="rx-draft">Clinical review pending</span></div>
    <details className="rx-formulations"><summary>Preparations & regional information</summary><ul>{active.forms.map((f,i)=><li key={i}>{f}</li>)}</ul><p>{active.india_evidence.note}</p></details>
    <nav className="rx-tabs" role="tablist" aria-label="Profile sections">{tabs.map(([id,label])=><button role="tab" type="button" key={id} id={instanceId+'-tab-'+id} aria-controls={contentId} aria-selected={view===id} onClick={()=>setView(id)}>{label}</button>)}</nav>
    <div role="tabpanel" id={contentId} aria-labelledby={instanceId+'-tab-'+view} key={active.id+'-'+view}><ProfileBody profile={active} view={view}/></div>
    <footer className="rx-footer">Draft reference · Source conditions apply · No patient dose or prescription is changed.</footer>
   </>}</main>
  </div>
 </div>
};
