import type {MicroState} from '../api/microTypes';
import {recordSummary,antibioticLabel,microKey,microTime} from './patientModel';
export function AntibioticOverview({state,current,onOpen}:{state?:MicroState;current:boolean;onOpen:()=>void}){
 if(!state)return null;const items=(state.assembly.snapshot.items??[]),meds=items.filter(i=>String(i.fact.kind).startsWith('antimicrobial_')),ast=items.filter(i=>i.fact.kind==='microbiology_susceptibility');
 return <section aria-label="Patient antibiotics and cultures" className="connected-antibiotics"><h3>Antibiotics and cultures</h3><p>{meds.length} prescription/administration sources · {ast.length} susceptibility reports in this patient view.</p>{meds.map(i=><p key={microKey(i)}>{recordSummary(i)}</p>)}{ast.length>0&&<details><summary>Recorded susceptibility reports</summary>{ast.map(i=><p key={microKey(i)}>{antibioticLabel(i)} · {microTime(i)} · source {i.fact.id} / {i.fact.revision}</p>)}</details>}<button type="button" disabled={!current} onClick={onOpen}>Open antibiotic review</button></section>;
}
