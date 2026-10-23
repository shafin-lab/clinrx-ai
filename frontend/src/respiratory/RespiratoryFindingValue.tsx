import {useRef,useState} from 'react';

/** Wording shortcuts only. Empty by default; these never interpret a patient or image. */
const choices:Record<string,string[]>={
 air_entry_right:['Good','Reduced','Absent','Unable to assess'],
 air_entry_left:['Good','Reduced','Absent','Unable to assess'],
 breath_sounds:['Vesicular','Bronchial','Diminished','Unable to assess'],
 adventitious_sounds:['No added sounds','Crackles','Wheeze','Rhonchi','Pleural rub','Unable to assess'],
 chest_expansion:['Symmetrical','Reduced on right','Reduced on left','Reduced bilaterally','Unable to assess'],
 percussion:['Resonant','Dull','Hyperresonant','Unable to assess'],
 work_of_breathing:['No increased work observed','Increased effort','Accessory muscle use','Unable to assess'],
 lung_sliding:['Present','Absent','Reduced','Indeterminate','Not assessed'],
 b_lines:['Not seen in assessed zones','Focal','Multifocal','Diffuse','Not assessed'],
 consolidation_findings:['Seen','Not seen in assessed area','Indeterminate','Not assessed'],
 pleural_findings:['Effusion described','No effusion in assessed area','Pleural thickening described','Indeterminate','Not assessed'],
 diaphragm_findings:['Movement observed','Reduced movement described','Paradoxical movement described','Indeterminate','Not assessed'],
 report_findings:['Consolidation reported','Atelectasis reported','Pleural effusion reported','Pulmonary oedema reported','Pneumothorax reported','No acute abnormality reported','Limited or indeterminate study'],
 study_status:['Performed','Pending','Not performed','Cancelled','Unavailable'],
};
export function RespiratoryFindingValue({concept,label,value,allowChoices,onChange}:{concept:string;label:string;value:string;allowChoices:boolean;onChange:(value:string)=>void}){
 const input=useRef<HTMLInputElement>(null),[ownWording,setOwnWording]=useState(false),options=allowChoices?choices[concept]??[]:[];
 const selected=ownWording||value&&!options.includes(value)?'__free_text__':value;
 return <div className="resp-finding-value">{options.length>0&&<label>{label} · quick choice<select value={selected} onChange={event=>{const next=event.target.value;if(next==='__free_text__'){setOwnWording(true);input.current?.focus();return;}setOwnWording(false);onChange(next);}}><option value="">Choose a common finding</option>{options.map(option=><option key={option} value={option}>{option}</option>)}<option value="__free_text__">Other / free text</option></select></label>}<label>{label} · result<input ref={input} value={value} placeholder={options.length?'Choose above or write your own finding':''} onChange={event=>{setOwnWording(true);onChange(event.target.value);}}/></label></div>;
}
