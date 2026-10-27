import {pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import type {RecordedTime,RespiratoryMeasurement,RespiratoryRecord} from './respiratoryTypes';
import {compareRespiratoryInstants} from './exactTime';
import {ventilatorModeProfile} from './ventilatorModes';
import {supportAtTime} from './supportModel';
export interface RespiratoryEvaluation {inputs:ReadonlyMap<string,{measurement:RespiratoryMeasurement;source:Evidence}>;issues:string[];settingsConflict?:boolean}
const exact=(t:RecordedTime)=>t.status==='known'&&t.precision==='instant'&&t.value!==null&&compareRespiratoryInstants(t.value,t.value)===0;
/** Resolve missing FiO2 only; never alter any source or infer a support episode. */
export function resolveRespiratoryEvaluation(sample:RespiratoryRecord,catalog:Catalog):RespiratoryEvaluation{
 const inputs=new Map<string,{measurement:RespiratoryMeasurement;source:Evidence}>(),issues:string[]=[];
 const conflict=(reason:string)=>({inputs,issues:[`Sample/support conflict: ${reason}`],settingsConflict:true});
 const held=(reason:string)=>{issues.push(`FiO2 support link: ${reason}`);return {inputs,issues};};
 if(sample.category!=='blood_gas')return held('automatic support resolution is limited to blood-gas samples.');
 const ownFiO2=sample.measurements.some(m=>m.concept==='fio2');
 const scope=catalog.combined.context.scope,cutoff=catalog.cutoff.fact_watermark;
 if(catalog.execution_enabled!==false||catalog.combined.execution_enabled!==false||catalog.repository!==catalog.cutoff.repository_id||scope.repository_cutoff.repository_id!==catalog.repository||scope.repository_cutoff.fact_watermark!==cutoff||sample.binding.target.patient_id!==scope.patient_id||sample.binding.target.encounter_id!==scope.encounter_id)return held('patient, encounter, repository or selected cutoff is unconfirmed.');
 const records=catalog.respiratory_records??[];
 const sameRef=(e:Evidence,ref:{kind:string;id:string;version:string})=>e.fact.kind===ref.kind&&e.fact.id===ref.id&&e.fact.revision===ref.version;
 const current=(e:Evidence)=>e.repository===catalog.repository&&e.ingestion.repository_id===catalog.repository&&e.cutoff===cutoff&&e.ingestion.ingestion_sequence<=cutoff&&!e.superseded&&sameRef(e,e.terminal_reference)&&e.fact.binding.target.patient_id===scope.patient_id&&e.fact.binding.target.encounter_id===scope.encounter_id;
 const origins=records.filter(e=>sameRef(e,{kind:sample.kind,id:sample.id,version:sample.revision}));
 if(origins.length!==1||!current(origins[0])||stable(origins[0].fact)!==stable(sample))return held('sample revision is unresolved, historical or outside the confirmed evidence scope.');
 if(sample.conflict==='unresolved')return held('sample has an unresolved source conflict.');
 if(!exact(sample.times.collected))return held('sample collection time is not a known exact instant.');
 if(sample.context.settings_confirmed_at_sample===false)return conflict('sample-time settings are explicitly not confirmed.');
 const automatic=sample.linked_sources.length===0?supportAtTime(catalog,sample.times.collected.value!):undefined;
 if(automatic?.source){const disagreement=supportContextConflict(sample,automatic.source.fact as RespiratoryRecord);if(disagreement)return conflict(disagreement);}
 if(ownFiO2){
  for(const ref of sample.linked_sources.filter(r=>r.kind==='respiratory_record')){const linked=records.find(e=>sameRef(e,ref)&&current(e));if(linked&&(linked.fact as RespiratoryRecord).category==='support'){const disagreement=supportContextConflict(sample,linked.fact as RespiratoryRecord);if(disagreement)return conflict(disagreement);}}
  return {inputs,issues};
 }
 if(automatic?.status==='matched'&&(automatic.source!.fact as RespiratoryRecord).context.support_episode){
  const source=automatic.source!,record=source.fact as RespiratoryRecord;
  if(['nasal_cannula','simple_mask','reservoir_mask','venturi_mask','other','unknown'].includes(record.context.support_episode!.type))return held('this device does not establish an exact delivered FiO2 for calculation.');
  const values=record.measurements.filter(m=>m.concept==='fio2'),m=values[0],r=m?.result;
  if(values.length!==1||m.quality!=='usable'||!['set','measured','reported'].includes(m.role)||r?.kind!=='numeric'||r.comparator!=='='||!r.unit||!['UCUM','ucum','http://unitsofmeasure.org'].includes(r.unit.namespace)||!['%','1'].includes(r.unit.code))return held('episode FiO2 needs one usable exact result, compatible role and standard unit.');
  const fraction=Number(r.raw_value)*(r.unit.code==='%'?0.01:1);if(!Number.isFinite(fraction)||fraction<0.21||fraction>1)return held('episode FiO2 is outside the permitted physiologic range.');
  inputs.set('fio2',{measurement:m,source});return {inputs,issues};
 }
 if(sample.context.settings_confirmed_at_sample!==true)return held('settings are not explicitly confirmed at this exact sample.');
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
 const disagreement=supportContextConflict(sample,record);if(disagreement)return conflict(disagreement);
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

/** Compare explicit source context; neither source is overwritten or treated as a correction. */
function supportContextConflict(sample:RespiratoryRecord,support:RespiratoryRecord):string|null {
 const normal=(s:string)=>s.toLowerCase().replace(/[^a-z0-9]/g,'');
 const device=(s:string)=>{const n=normal(s);const aliases:Record<string,string>={roomair:'roomair',nasalprongscannula:'nasalcannula',nasalprongs:'nasalcannula',simplefacemask:'simplemask',reservoirnonrebreathermask:'reservoirmask',nonrebreathermask:'reservoirmask',highflownasalcannula:'hfnc',noninvasiveventilation:'niv',invasiveventilation:'invasive'};return aliases[n]??n;};
 const a=sample.context.oxygen_device,b=support.context.support_episode?.type??support.context.oxygen_device;
 if(a&&b&&device(a)!==device(b))return 'reported oxygen devices disagree; retain both sources and review alignment.';
 const am=sample.context.ventilator_mode,bm=support.context.ventilator_mode;
 if(am&&bm&&(ventilatorModeProfile(am).id??normal(am))!==(ventilatorModeProfile(bm).id??normal(bm)))return 'reported ventilator modes disagree; review sample-time alignment.';
 const fraction=(m:RespiratoryMeasurement)=>{const r=m.result;if(r.kind!=='numeric'||r.comparator!=='='||!r.unit||!['%','1'].includes(r.unit.code))return null;return Number(r.raw_value)*(r.unit.code==='%'?0.01:1);};
 const own=sample.measurements.filter(m=>m.concept==='fio2'),external=support.measurements.filter(m=>m.concept==='fio2');
 if(own.length===1&&external.length===1){const x=fraction(own[0]),y=fraction(external[0]);if(x!==null&&y!==null&&Number.isFinite(x)&&Number.isFinite(y)&&Math.abs(x-y)>0.000001)return 'reported FiO2 values disagree; review sample-time alignment.';}
 return null;
}
