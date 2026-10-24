import {pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import type {RecordedTime,RespiratoryMeasurement,RespiratoryRecord} from './respiratoryTypes';
import {compareRespiratoryInstants} from './exactTime';
export interface RespiratoryEvaluation {inputs:ReadonlyMap<string,{measurement:RespiratoryMeasurement;source:Evidence}>;issues:string[]}
const exact=(t:RecordedTime)=>t.status==='known'&&t.precision==='instant'&&t.value!==null&&compareRespiratoryInstants(t.value,t.value)===0;
/** Resolve missing FiO2 only; never alter any source or infer a support episode. */
export function resolveRespiratoryEvaluation(sample:RespiratoryRecord,catalog:Catalog):RespiratoryEvaluation{
 const inputs=new Map<string,{measurement:RespiratoryMeasurement;source:Evidence}>(),issues:string[]=[];
 const held=(reason:string)=>{issues.push(`FiO2 support link: ${reason}`);return {inputs,issues};};
 if(sample.category!=='blood_gas')return held('automatic support resolution is limited to blood-gas samples.');
 if(sample.measurements.some(m=>m.concept==='fio2'))return {inputs,issues};
 const scope=catalog.combined.context.scope,cutoff=catalog.cutoff.fact_watermark;
 if(catalog.execution_enabled!==false||catalog.combined.execution_enabled!==false||catalog.repository!==catalog.cutoff.repository_id||scope.repository_cutoff.repository_id!==catalog.repository||scope.repository_cutoff.fact_watermark!==cutoff||sample.binding.target.patient_id!==scope.patient_id||sample.binding.target.encounter_id!==scope.encounter_id)return held('patient, encounter, repository or selected cutoff is unconfirmed.');
 const records=catalog.respiratory_records??[];
 const sameRef=(e:Evidence,ref:{kind:string;id:string;version:string})=>e.fact.kind===ref.kind&&e.fact.id===ref.id&&e.fact.revision===ref.version;
 const current=(e:Evidence)=>e.repository===catalog.repository&&e.ingestion.repository_id===catalog.repository&&e.cutoff===cutoff&&e.ingestion.ingestion_sequence<=cutoff&&!e.superseded&&sameRef(e,e.terminal_reference)&&e.fact.binding.target.patient_id===scope.patient_id&&e.fact.binding.target.encounter_id===scope.encounter_id;
 const origins=records.filter(e=>sameRef(e,{kind:sample.kind,id:sample.id,version:sample.revision}));
 if(origins.length!==1||!current(origins[0])||stable(origins[0].fact)!==stable(sample))return held('sample revision is unresolved, historical or outside the confirmed evidence scope.');
 if(sample.conflict==='unresolved')return held('sample has an unresolved source conflict.');
 if(sample.context.settings_confirmed_at_sample!==true)return held('settings are not explicitly confirmed at this exact sample.');
 if(!exact(sample.times.collected))return held('sample collection time is not a known exact instant.');
 const linked:Evidence[]=[];
 for(const ref of sample.linked_sources.filter(r=>r.kind==='respiratory_record')){
  const matches=records.filter(e=>sameRef(e,ref));
  if(matches.length!==1)return held('exact linked revision is unresolved or ambiguous; a stale revision cannot use its replacement.');
  if((matches[0].fact as RespiratoryRecord).category==='support')linked.push(matches[0]);
 }
 if(linked.length!==1)return held(linked.length?'multiple linked support sources are ambiguous.':'no exact linked support source is recorded.');
 const source=linked[0],record=source.fact as RespiratoryRecord;
 if(!current(source))return held('support source is superseded, stale, or outside the confirmed patient/encounter/repository/cutoff.');
 if(record.conflict==='unresolved')return held('support source has an unresolved source conflict.');
 if(record.record_status!=='recorded'||!['final','corrected','preliminary','interim'].includes(record.report_status)||record.change_state==='superseded')return held('support record/report status is not usable.');
 if(!exact(record.times.occurred))return held('support acquisition time is not a known exact instant.');
 if(compareRespiratoryInstants(record.times.occurred.value!,sample.times.collected.value!)!==0)return held('support acquisition does not exactly equal sample collection; later or nearby settings cannot substitute.');
 const values=record.measurements.filter(m=>m.concept==='fio2');
 if(values.length!==1)return held('support FiO2 is missing or ambiguous.');
 const measurement=values[0],r=measurement.result;
 if(measurement.quality!=='usable')return held(`support FiO2 quality is ${measurement.quality}, not explicitly usable.`);
 if(!['set','measured','reported'].includes(measurement.role))return held(`support FiO2 role ${measurement.role} is incompatible.`);
 if(r.kind!=='numeric'||r.comparator!=='='||!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(r.raw_value.trim()))return held('support FiO2 requires one exact numeric result.');
 if(!r.unit||!['UCUM','ucum','http://unitsofmeasure.org'].includes(r.unit.namespace)||!['%','1'].includes(r.unit.code))return held('support FiO2 unit is unknown or incompatible.');
 const fraction=Number(r.raw_value)*(r.unit.code==='%'?0.01:1);
 if(!Number.isFinite(fraction)||fraction<0.21||fraction>1)return held('support FiO2 is outside the permitted physiologic range.');
 inputs.set('fio2',{measurement,source});return {inputs,issues};
}
export const respiratoryExternalInput=(source:Evidence,concept:string)=>`External source ${JSON.stringify(pin(source))}; component=${concept}`;
