import {useState} from 'react';
import type {Catalog} from '../api/rf2Client';
import {CG_SOURCE,clearance,type ClearanceInputs} from './patientModel';
import {RenalDoseAdvisor} from './RenalDoseAdvisor';
import type {PrescriptionSeed} from './renalDoseModel';
import type {cultureOptions} from './patientModel';
const blank:ClearanceInputs={age:'',weight:'',creatinine:'',factor:''};
export function CreatinineClearance({catalog,current,cultures=[],onUseSuggestion=()=>{}}:{catalog?:Catalog;current:boolean;cultures?:ReturnType<typeof cultureOptions>;onUseSuggestion?:(seed:PrescriptionSeed)=>void}){
 const [inputs,setInputs]=useState<ClearanceInputs>(blank),[calculated,setCalculated]=useState<{signature:string;inputs:ClearanceInputs;value:number}>(),[error,setError]=useState('');
 const signature=catalog?JSON.stringify(catalog.cutoff):'';
 function change(key:keyof ClearanceInputs,value:string){setInputs(old=>({...old,[key]:value}));setCalculated(undefined);setError('');}
 const stale=calculated&&calculated.signature!==signature;
 return <><section className="abx-clearance" aria-labelledby="crcl-title"><p className="m7-eyebrow">Renal function · explicit inputs</p><h2 id="crcl-title">Creatinine clearance</h2><p className="m7-caption">Cockcroft–Gault · mL/min · estimate, not measured clearance or eGFR.</p>
 <div className="abx-clearance-result" role="status">{calculated&&!stale?calculated.value.toFixed(1)+' mL/min':'Not calculated'}{stale&&<small>Evidence refreshed. Recheck inputs and calculate again.</small>}</div>
 <fieldset disabled={!current}><div className="abx-input-grid"><label>Age (years)<input inputMode="numeric" value={inputs.age} onChange={e=>change('age',e.target.value)}/></label><label>Equation sex coefficient<select value={inputs.factor} onChange={e=>change('factor',e.target.value)}><option value="">Select coefficient</option><option value="male">Male · ×1</option><option value="female">Female · ×0.85</option></select></label>
 <label>Weight used (kg)<input inputMode="decimal" value={inputs.weight} onChange={e=>change('weight',e.target.value)}/></label>
 <label>Serum creatinine (mg/dL)<input inputMode="decimal" value={inputs.creatinine} onChange={e=>change('creatinine',e.target.value)}/></label></div>
 <button type="button" className="m7-secondary" onClick={()=>{const result=clearance(inputs);if(result.error){setError(result.error);setCalculated(undefined);}else{setCalculated({signature,inputs:{...inputs},value:result.value!});setError('');}}}>Calculate CrCl</button></fieldset>
 {error&&<p role="alert">{error}</p>}{calculated&&!stale&&<p>Estimate only; body size, muscle mass, assay and weight selection affect reliability. No antibiotic dose is selected from this number.</p>}
 <details><summary>Equation, inputs and limitations</summary><p>(140 − age) × weight (kg) × coefficient ÷ (72 × serum creatinine in mg/dL).</p><p>Enter the values to use in the equation. This estimate is not measured clearance or eGFR. It does not assess renal stability or kidney support, and it does not select a dosing weight. Original source records remain unchanged.</p>{calculated&&<pre>{JSON.stringify(calculated.inputs,null,2)}</pre>}<a href={CG_SOURCE} target="_blank" rel="noopener noreferrer">Equation reference · University of Washington ↗</a></details>
 </section><RenalDoseAdvisor current={current} inputs={inputs} calculatedCrCl={calculated&&!stale?calculated.value:undefined} cultures={cultures} onUseSuggestion={onUseSuggestion}/></>;
}
