import {useState} from 'react';
const methods=[
 ['fractional_cooximetry','Fractional oxyhaemoglobin by co-oximetry (FO₂Hb)'],
 ['functional_cooximetry','Functional oxygen saturation by co-oximetry'],
 ['cooximetry','Co-oximetry · saturation basis not specified'],
 ['constant_inspiratory_flow','Confirmed constant inspiratory flow'],
 ['bohr_volumetric_capnography','Physiologic dead space · Bohr volumetric capnography'],
 ['volumetric_capnography','Volumetric capnography'],
 ['mixed_expired_collection','Mixed expired gas collection'],
 ['blood_gas_analyzer','Blood-gas analyser'],
 ['laboratory_chemistry','Laboratory chemistry assay'],
 ['occlusion_measurement','Recorded airway occlusion measurement'],
] as const;
export function RespiratoryMethodInput({label,value,onChange}:{label:string;value:string;onChange:(value:string)=>void}){
 const [custom,setCustom]=useState(false),known=methods.some(([key])=>key===value),other=custom||!!value&&!known;
 return <div><label>{label}<select value={other?'other':value} onChange={event=>{setCustom(event.target.value==='other');onChange(event.target.value==='other'?'':event.target.value);}}><option value="">Method not established</option>{methods.map(([key,name])=><option key={key} value={key}>{name}</option>)}<option value="other">Other original source method</option></select></label>{other&&<label>Original method wording<input maxLength={4096} value={value} onChange={event=>onChange(event.target.value)}/></label>}</div>;
}
