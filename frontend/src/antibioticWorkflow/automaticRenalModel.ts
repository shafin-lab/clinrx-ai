import {pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import {record} from '../demo/evidencePresentation';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {clearance,type ClearanceInputs} from './patientModel';
import {doseScope,type DoseSource} from './renalDoseModel';

export const DOSE_CONTEXT_QUESTION='Patient medication dosing context/v1';
export interface PatientDoseContext {version:1;birthDate:string;factor:''|'male'|'female';renalFunction:'unknown'|'stable'|'changing';support:'unknown'|'none'|'ihd'|'crrt'|'other';weightReviewed:boolean;bodySize:''|'standard'|'complex';hepatic:''|'reviewed'|'unresolved';special:''|'none'|'present';safetyReviewed:boolean}
export const blankPatientDoseContext:PatientDoseContext={version:1,birthDate:'',factor:'',renalFunction:'unknown',support:'unknown',weightReviewed:false,bodySize:'',hepatic:'',special:'',safetyReviewed:false};
export function parsePatientDoseContext(text:string):PatientDoseContext|undefined {
 try{const v=record(parseRF2JSON(text));if(Object.keys(v).sort().join()!==Object.keys(blankPatientDoseContext).sort().join()||v.version!==1)return;
  if(typeof v.birthDate!=='string'||v.birthDate!==''&&(!/^\d{4}-\d{2}-\d{2}$/.test(v.birthDate)||!Number.isFinite(Date.parse(v.birthDate))||new Date(v.birthDate).toISOString().slice(0,10)!==v.birthDate))return;
  for(const [k,values] of Object.entries({factor:['','male','female'],renalFunction:['unknown','stable','changing'],support:['unknown','none','ihd','crrt','other'],bodySize:['','standard','complex'],hepatic:['','reviewed','unresolved'],special:['','none','present']}))if(!values.includes(String(v[k])))return;
  if(typeof v.weightReviewed!=='boolean'||typeof v.safetyReviewed!=='boolean')return;
  return v as unknown as PatientDoseContext;
 }catch{return;}
}
export interface AutomaticInput {value:string;raw:string;time:string;source:DoseSource;conversion:string;entry:Evidence;reasons:string[]}
type Candidate=AutomaticInput&{role:'weight'|'creatinine';available:string;trendEligible:boolean};
const exact=(t:unknown)=>{const r=record(t);return r.status==='known'&&r.precision==='instant'&&typeof r.value==='string'&&compare(r.value,r.value)===0?r.value:'';};
export const evidenceEventTime=(e:Evidence)=>String(e.metadata?.chart?.point??record(e.fact.occurred).source_timestamp??record(e.fact.time).event??'');
const positive=(s:string)=>/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(s)&&Number.isFinite(Number(s))&&Number(s)>0;
export function automaticRenalModel(catalog?:Catalog){
 const inputs:ClearanceInputs={age:'',factor:'',weight:'',creatinine:''},reasons:string[]=[],candidates:Candidate[]=[],contextEntries:{entry:Evidence;time:string;context?:PatientDoseContext}[]=[];
 const signature=stable(catalog?[doseScope(catalog),catalog.items.map(e=>[pin(e),e.superseded,e.fact,e.metadata]),catalog.laboratory_reports.map(e=>[pin(e),e.superseded,e.fact])]:[]);
 const scope=catalog?doseScope(catalog):undefined;
 function scoped(e:Evidence){const t=e.fact.binding.target;return !!scope&&e.repository===scope.repository&&e.ingestion.repository_id===scope.repository&&e.cutoff===scope.cutoff&&Number.isSafeInteger(e.ingestion.ingestion_sequence)&&e.ingestion.ingestion_sequence>0&&e.ingestion.ingestion_sequence<=scope.cutoff&&t.patient_id===scope.patient&&t.encounter_id===scope.encounter;}
 const seen=new Map<string,string>(),conflicting=new Set<string>();
 for(const e of [...catalog?.items??[],...catalog?.laboratory_reports??[]]){const id=stable([e.fact.kind,e.fact.id,e.fact.revision]);if(seen.has(id)&&seen.get(id)!==e.digest)conflicting.add(id);seen.set(id,e.digest);}
 const visited=new Set<string>();
 for(const e of [...catalog?.items??[],...catalog?.laboratory_reports??[]]){
  const f=e.fact,identity=stable([f.kind,f.id,f.revision]);if(visited.has(identity)||e.superseded)continue;visited.add(identity);
  const common:string[]=[];if(!scoped(e))common.push('Source scope is not confirmed');if(conflicting.has(identity))common.push('Conflicting exact source bytes');if(e.terminal_reference.version!==f.revision)common.push('Terminal source revision not confirmed');
  if(e.metadata?.note?.question===DOSE_CONTEXT_QUESTION){const time=evidenceEventTime(e);if(scope&&compare(time,scope.end)!==null&&compare(time,scope.end)!<=0)contextEntries.push({entry:e,time,context:!common.length&&f.record_status==='recorded'?parsePatientDoseContext(e.metadata.note.findings):undefined});else if(compare(time,time)===null)reasons.push('Patient dosing context timing is unresolved');continue;}
  function add(role:Candidate['role'],value:string,unit:string,time:string,available:string,extra:string[]=[],component?:string){
   if(!scope)return;
   if(compare(time,time)===null){reasons.push('A '+role+' source has unresolved timing; review before using an older value');return;}
   if(compare(time,scope.end)!>0||available&&compare(available,scope.end)!>0)return;
   const why=[...common,...extra];if(!positive(value))why.push('Known positive numeric result required');
   let conversion='Source unit retained';const raw=value+' '+unit;
   if(role==='weight'){if(unit==='g'){value=String(Number(value)/1000);conversion='Source g ÷ 1000 → kg';}else if(unit!=='kg')why.push('Supported weight unit required');}
   else if(unit==='umol/L'){value=String(Number(value)/88.4);conversion='Source µmol/L ÷ 88.4 → mg/dL';}else if(unit!=='mg/dL')why.push('Supported creatinine unit required');
   const trendEligible=!why.length;
   if(role==='creatinine'&&Date.parse(scope.end)-Date.parse(time)>24*3600000)why.push('Latest creatinine exceeds the 24-hour preview limit');
   if(role==='weight'&&Date.parse(scope.end)-Date.parse(time)>7*86400000)why.push('Latest weight exceeds the 7-day preview limit');
   const p=pin(e);candidates.push({role,value,raw,time,available,entry:e,conversion,reasons:why,trendEligible,source:{role,reference:p.reference,digest:p.digest,ingestion:p.ingestion,...component?{component}:{}}});
  }
  if(f.kind==='observation'&&f.concept_id==='synthetic-serum-creatinine'){
   const v=record(f.value),q=record(v.value),u=record(q.unit),t=record(f.time),why:string[]=[];
   if(v.status!=='known'||!['verified','clinician_confirmed'].includes(String(f.verification))||f.conflict!=='none_known'||f.record_status==='withdrawn'||f.record_status==='invalid')why.push('Known verified non-conflicting creatinine required');
   if(u.status!=='assessed'||u.system!=='UCUM'||u.code!==u.raw)why.push('Assessed creatinine unit required');
   if(t.precision==='instant')add('creatinine',String(q.value??''),String(u.code??''),String(t.event??''),String(t.event??''),why);else reasons.push('A creatinine source has unresolved timing; review before using an older value');
  }
  const c=e.metadata?.chart;
  if(c?.category==='weight'||c?.category==='dosing_weight'||f.kind==='observation'&&f.concept_id==='body-weight'){
   const why:string[]=[];
   if(f.kind==='observation'){
    const v=record(f.value),q=record(v.value),u=record(q.unit),t=record(f.time);
    if(v.status!=='known'||!['verified','clinician_confirmed'].includes(String(f.verification))||f.conflict!=='none_known'||u.status!=='assessed'||u.system!=='UCUM'||u.raw!==u.code)why.push('Verified measured body-weight observation and unit required');
    if(t.precision==='instant')add('weight',String(q.value??''),String(u.code??''),String(t.event??''),String(t.event??''),why);
   }else if(c){if(c.category!=='weight'||c.acquisition!=='measured'||c.purpose!==null||f.record_status!=='recorded')why.push('True measured body weight required; dosing weight excluded');add('weight',c.amount??'',c.unit??'',c.point??'',c.point??'',why);}
  }
  if(f.kind==='laboratory_report'){
   const times=record(f.times),collected=exact(times.collected),available=exact(times.available),specimen=record(record(f.specimen).specimen_type),components=Array.isArray(f.components)?f.components:[];
   // Unknown availability is a visible gap, never permission to use a report early.
   const hasCreatinine=components.some(c=>record(c).mapped_concept==='creatinine');
   if(!collected||!available){if(hasCreatinine&&!(available&&scope&&compare(available,scope.end)!>0)&&!(collected&&scope&&compare(collected,scope.end)!>0))reasons.push('Creatinine report collection or availability time is unresolved');continue;}
   for(const raw of components){const c=record(raw);if(c.mapped_concept!=='creatinine')continue;
    const result=record(c.result),unit=record(result.unit),why:string[]=[];
    if(c.mapping_status!=='mapped'||!c.mapping_version||!['final','corrected'].includes(String(f.report_status))||f.record_status!=='recorded'||f.change_state==='superseded'||result.kind!=='numeric'||result.comparator!=='=')why.push('Final mapped numeric creatinine required');
    if(!['verified','clinician_confirmed'].includes(String(f.verification))||f.conflict!=='none_known'||record(record(f.binding).verification).status!=='verified')why.push('Verified patient-bound report required');
    if(!['serum','plasma','119364003','119361006'].includes(String(specimen.code??specimen.raw_display??'').toLowerCase()))why.push('Serum or plasma specimen required');
    if(unit.namespace!=='UCUM')why.push('Explicit UCUM unit mapping required');
    if(compare(collected,available)!>0)why.push('Collection follows result availability');
    add('creatinine',String(result.raw_value??''),String(unit.code??''),collected,available,why,String(c.source_component_id));
   }
  }
 }
 function latest(role:Candidate['role']):AutomaticInput|undefined{
  const rows=candidates.filter(x=>x.role===role).sort((a,b)=>compare(b.time,a.time)??0);const top=rows[0];
  if(!top){reasons.push(role==='weight'?'No eligible measured weight':'No eligible creatinine result');return;}
  if(rows.filter(x=>compare(x.time,top.time)===0).length!==1){reasons.push('Multiple '+role+' sources at the latest time; review required');return;}
  if(top.reasons.length){reasons.push(...top.reasons);return;}
  return top;
 }
 const weight=latest('weight'),creatinine=latest('creatinine');inputs.weight=weight?.value??'';inputs.creatinine=creatinine?.value??'';
 contextEntries.sort((a,b)=>compare(b.time,a.time)??0);const selected=contextEntries[0],context=selected&&contextEntries.filter(x=>compare(x.time,selected.time)===0).length===1?selected.context:undefined;
 if(context&&scope){
  const date=scope.end.slice(0,10),birth=context.birthDate;
  if(birth){const age=Number(date.slice(0,4))-Number(birth.slice(0,4))-(date.slice(5)<birth.slice(5)?1:0);if(age>=18&&age<140)inputs.age=String(age);else reasons.push('Explicit adult date of birth required');}
  inputs.factor=context.factor;
 }
 if(!context)reasons.push('Patient dosing context is not recorded or is ambiguous');
 if(!inputs.age)reasons.push('Date of birth required');if(!inputs.factor)reasons.push('Equation coefficient required');
 const result=clearance(inputs),crcl=result.error?undefined:result.value;
 if(context){
  if(context.renalFunction!=='stable')reasons.push('Stable renal function has not been confirmed');
  if(context.support!=='none')reasons.push('Kidney replacement therapy is present or not assessed');
  if(!context.weightReviewed)reasons.push('Calculation weight applicability has not been reviewed');
  if(scope&&selected&&(Date.parse(scope.end)-Date.parse(selected.time)>24*3600000))reasons.push('Patient renal review exceeds the 24-hour preview limit');
  const oldWeight=selected?.entry.metadata?.note?.pins.find(p=>p.reference.kind===weight?.source.reference.kind&&p.reference.id===weight?.source.reference.id);
  if(weight&&(!oldWeight||oldWeight.digest!==weight.source.digest||oldWeight.reference.version!==weight.source.reference.version))reasons.push('Weight changed or its exact source was not retained in the patient dosing review');
 }
 if(creatinine){const latest=Number(creatinine.value),at=Date.parse(creatinine.time);for(const old of candidates.filter(x=>x.role==='creatinine'&&x.trendEligible&&compare(x.time,creatinine.time)!<0)){const hours=(at-Date.parse(old.time))/3600000;if(hours<=48&&latest-Number(old.value)>=0.3-1e-10||hours<=168&&latest/Number(old.value)>=1.5-1e-10){reasons.push('Creatinine rise requires clinical review; routine steady-state dosing is paused');break;}}}
 const sources:DoseSource[]=[...weight?[weight.source]:[],...creatinine?[creatinine.source]:[]];
 if(context&&selected){const p=pin(selected.entry);sources.push({role:'patient_context',reference:p.reference,digest:p.digest,ingestion:p.ingestion});}
 return {inputs,crcl,weight,creatinine,context,contextEntry:context?selected?.entry:undefined,reasons:[...new Set(reasons)],routineEligible:!!crcl&&!reasons.length,sources,signature,scope,candidates};
}
export type AutomaticRenalModel=ReturnType<typeof automaticRenalModel>;
