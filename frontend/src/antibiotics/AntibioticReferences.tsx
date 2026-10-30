import type {CirculatoryState} from '../api/circulatoryTypes';
import type {BedsideScope} from '../hemodynamics/bedsideModel';
import {CompleteNcdcLibrary} from '../infectionLibrary/CompleteNcdcLibrary';
import completeNcdcGuidance from '../infectionLibrary/data/ncdc-complete-guidance.json';
const Antibiotics=lazy(()=>import('../profiles/ClinRxAntibioticProfileBrowser').then(m=>({default:m.ClinRxAntibioticProfileBrowser})));

// Preserve the workspace integration contract. Browsing never consumes or writes clinical records.
export function AntibioticReferences({requested,loading,retrievalError}: {requested:BedsideScope;state?:CirculatoryState;loading:boolean;retrievalError?:string;onKidney:()=>void}){
 const [collection,setCollection]=useState<'infections'|'antibiotics'>('infections');
 const [profilesOpened,setProfilesOpened]=useState(false);
 return <section className="antibiotic-reference-collections" aria-label="Reference library collections">
  <nav className="rx-collection-nav" aria-label="Reference library collections" style={{display:'flex',gap:8,flexWrap:'wrap',margin:'20px 0'}}>
   <button type="button" aria-pressed={collection==='infections'} onClick={()=>setCollection('infections')}>Infections &amp; treatment</button>
   <button type="button" aria-pressed={collection==='antibiotics'} onClick={()=>{setProfilesOpened(true);setCollection('antibiotics')}}>Antibiotics</button>
  </nav>
  <div hidden={collection!=='infections'}><CompleteNcdcLibrary data={completeNcdcGuidance} patient={requested.patient} encounter={requested.encounter} unconfirmed={loading||!!retrievalError}/></div>
  {profilesOpened&&<div hidden={collection!=='antibiotics'}><Suspense fallback={<p role="status">Loading antibiotic profiles…</p>}><Antibiotics/></Suspense></div>}
 </section>;
}
import {lazy,Suspense,useState} from 'react';
