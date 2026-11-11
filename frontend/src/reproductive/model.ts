import {key,pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import {compareLaboratoryCollections,laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryQualifications,laboratoryResultText} from '../gastrointestinal/laboratoryPresentation';
import {asObject} from '../respiratory/respiratoryModel';
import {compareRespiratoryInstants} from '../respiratory/exactTime';
import type {SavedReview} from '../clinical/savedReviewStore';
import type {MicroState} from '../api/microTypes';

export const reproductiveCategories={
 pregnancy_status:'Pregnancy status and dating',maternal_assessment:'Maternal assessment',
 fetal_assessment:'Fetal assessment',labour_delivery:'Labour and delivery',postpartum:'Postpartum recovery',
 gynecology:'Gynecology',reproductive_care:'Reproductive care',imaging:'Imaging report',procedure:'Procedure report',
} as const;
export const phaseLabels={antepartum:'Pregnant',in_labour:'In labour',postpartum:'Postpartum',
 not_pregnant:'Not pregnant',pregnancy_loss:'Pregnancy loss recorded',unknown:'Pregnancy status unknown'} as const;
export type ReproductiveScope={patient:string;encounter:string;start:string;end:string};
export type Category=keyof typeof reproductiveCategories;
export type Phase=keyof typeof phaseLabels;
const laboratoryLabels:Record<string,string>={
 hemoglobin:'Haemoglobin',hematocrit:'Haematocrit',platelets:'Platelets',creatinine:'Creatinine',
 ast:'AST',alt:'ALT',total_bilirubin:'Total bilirubin',pt:'PT',inr:'INR',aptt:'aPTT',fibrinogen:'Fibrinogen',
};
const positiveReportStatus=['final','corrected','preliminary','interim'];
export const recordedFinding=(e:Evidence)=>e.fact.record_status==='recorded'&&positiveReportStatus.includes(String(e.fact.report_status));
const stringValue=(x:unknown)=>typeof x==='string'?x:'';

function exact(value:unknown) {
 const time=asObject(value),valueText=stringValue(time.value);
 return time.status==='known'&&time.precision==='instant'&&compareRespiratoryInstants(valueText,valueText)===0?valueText:null;
}
export const findingTime=(e:Evidence)=>exact(asObject(e.fact.times).occurred);
export const categoryOf=(e:Evidence)=>String(e.fact.category) as Category;
export const findingText=(e:Evidence)=>recordedFinding(e)?String(e.fact.narrative):
 e.fact.record_status==='withdrawn'?'Withdrawn source record':`Source status: ${String(e.fact.report_status??e.fact.record_status)}`;

function inScope(e:Evidence,catalog:Catalog,requested:ReproductiveScope) {
 return e.repository===catalog.repository&&e.ingestion.repository_id===catalog.repository&&
  e.ingestion.ingestion_sequence<=e.cutoff&&e.cutoff<=catalog.cutoff.fact_watermark&&
  e.fact.binding.target.patient_id===requested.patient&&e.fact.binding.target.encounter_id===requested.encounter;
}
function beforeCutoff(e:Evidence,end:string) {
 const times=asObject(e.fact.times);
 return ['occurred','collected','reported','available'].every(name=>{
  const time=asObject(times[name]),at=time.upper??time.value;
  if(typeof at!=='string'||time.status!=='known'||time.precision==='day')return true;
  const compare=compareRespiratoryInstants(at,end);
  return compare===null||compare<=0;
 });
}
function pressureValue(e:Evidence) {
 const result=asObject(e.fact.result),quantity=asObject(result.quantity);
 return {value:stringValue(quantity.value),unit:stringValue(asObject(quantity.unit).raw)};
}
function pressureRows(items:Evidence[],requested:ReproductiveScope) {
 const groups=new Map<string,Evidence[]>();
 for(const item of items){
  const fact=item.fact,occurred=asObject(fact.occurred);
  const at=stringValue(occurred.source_timestamp||occurred.value);
  const comparedStart=compareRespiratoryInstants(at,requested.start),comparedEnd=compareRespiratoryInstants(at,requested.end);
  if(fact.kind!=='circulatory_pressure'||!['systemic_systolic','systemic_diastolic'].includes(String(fact.concept))||
     comparedStart===null||comparedStart<0||comparedEnd===null||comparedEnd>0)continue;
  const acquisition=asObject(fact.acquisition),episode=asObject(acquisition.episode),unit=pressureValue(item).unit;
  const group=episode.namespace&&episode.code?stable([at,episode,acquisition.method,unit]):key(pin(item));
  groups.set(group,[...(groups.get(group)??[]),item]);
 }
 return [...groups.values()].flatMap(group=>{
  const time=asObject(group[0].fact.occurred),at=String(time.source_timestamp||time.value);
  const [sys,dia]=['systemic_systolic','systemic_diastolic'].map(concept=>group.filter(e=>e.fact.concept===concept));
  if(sys.length===1&&dia.length===1&&group.every(e=>e.fact.record_status==='recorded'&&pressureValue(e).value)){
   return [{at,text:`${pressureValue(sys[0]).value}/${pressureValue(dia[0]).value} ${pressureValue(sys[0]).unit}`,sources:group}];
  }
  return group.map(e=>{const v=pressureValue(e),label=e.fact.concept==='systemic_systolic'?'Systolic':'Diastolic';
   return {at,text:e.fact.record_status==='recorded'&&v.value?`${label} ${v.value} ${v.unit}`:`${label} · ${String(e.fact.record_status)}`,sources:[e]};});
 }).sort((a,b)=>compareLaboratoryCollections(a.at,b.at));
}

export function reproductiveModel(catalog:Catalog|undefined,requested:ReproductiveScope,micro?:MicroState) {
 const scope=catalog?.combined.context.scope;
 const valid=!!catalog&&!!scope&&catalog.execution_enabled===false&&catalog.combined.execution_enabled===false&&
  catalog.repository===catalog.cutoff.repository_id&&scope.repository_cutoff.repository_id===catalog.repository&&
  scope.repository_cutoff.fact_watermark===catalog.cutoff.fact_watermark&&
  scope.patient_id===requested.patient&&scope.encounter_id===requested.encounter&&
  compareRespiratoryInstants(scope.review_start,requested.start)===0&&compareRespiratoryInstants(scope.review_end,requested.end)===0;
 const records=valid? (catalog.reproductive_records??[]).filter(e=>inScope(e,catalog,requested)&&beforeCutoff(e,requested.end))
  .sort((a,b)=>compareLaboratoryCollections(findingTime(a),findingTime(b))):[];
 const statuses=records.filter(e=>categoryOf(e)==='pregnancy_status');
 const status=statuses[0];
 const unique=statuses.length===1||!!status&&!!findingTime(status)&&statuses.slice(1).every(e=>{
  const time=findingTime(e);return !!time&&compareRespiratoryInstants(findingTime(status)!,time)===1;
 });
 const pregnancy=unique&&status&&recordedFinding(status)&&status.fact.conflict!=='unresolved'?asObject(status.fact.pregnancy):{};
 const phase=String(pregnancy.phase??'unknown') as Phase;
 const phaseLabel=phaseLabels[phase]??phaseLabels.unknown;
 const gestation=typeof pregnancy.gestational_weeks==='number'&&typeof pregnancy.gestational_days==='number'?
  `${pregnancy.gestational_weeks} weeks ${pregnancy.gestational_days} days`:'';
 const labs=valid?catalog.laboratory_reports.filter(e=>inScope(e,catalog,requested)&&beforeCutoff(e,requested.end))
  .flatMap(source=>(Array.isArray(source.fact.components)?source.fact.components:[]).flatMap(raw=>{
   const component=asObject(raw),concept=String(component.mapped_concept??'');
   if(component.mapping_status!=='mapped'||!Object.hasOwn(laboratoryLabels,concept))return [];
   const collection=laboratoryCollection(source.fact);
   return [{source,concept,label:laboratoryLabels[concept],component:String(component.source_component_id),
    result:recordedFinding(source)?laboratoryResultText(component):findingText(source),collection,
    qualifications:laboratoryQualifications(source,component,false)}];
  })).sort((a,b)=>compareLaboratoryCollections(a.collection.instant,b.collection.instant)):[];
 const pressures=valid?pressureRows(catalog.items.filter(e=>inScope(e,catalog,requested)),requested):[];
 const microScope=micro?.assembly.request.scope;
 const medicationConfirmed=valid&&!!micro&&!!microScope&&
  microScope.patient_id===requested.patient&&microScope.encounter_id===requested.encounter&&
  compareRespiratoryInstants(microScope.review_start,requested.start)===0&&compareRespiratoryInstants(microScope.review_end,requested.end)===0&&
  stable(microScope.repository_cutoff)===stable(catalog.cutoff);
 const medicationSources=medicationConfirmed?(micro.assembly.snapshot.items??[]).flatMap(item=>{
  const {fact,ingestion}=item,kind=fact.kind;
  if(!kind?.startsWith('antimicrobial_')||!ingestion||ingestion.repository_id!==catalog.repository||
     ingestion.ingestion_sequence>catalog.cutoff.fact_watermark)return [];
  return [{item,sourcePin:{repository:catalog.repository,kind,id:fact.id,version:fact.revision,
   digest:item.expected_digest,ingestion:ingestion.ingestion_sequence,cutoff:catalog.cutoff.fact_watermark}}];
 }):[];
 const sources=[...new Map([...records,...labs.map(r=>r.source),...pressures.flatMap(p=>p.sources)].map(e=>[key(pin(e)),e])).values()];
 const pins=sources.map(e=>({repository:e.repository,kind:e.fact.kind,id:e.fact.id,version:e.fact.revision,
  digest:e.digest,ingestion:e.ingestion.ingestion_sequence,cutoff:e.cutoff}));
 pins.push(...medicationSources.map(source=>source.sourcePin));
 const signature=valid?stable(['m12/v1',requested.patient,requested.encounter,requested.start,requested.end,catalog.repository,medicationConfirmed]):'';
 const pinKey=(value:unknown[])=>stable(value.map(p=>{const {cutoff:_,...identity}=asObject(p);return stable(identity);}).sort());
 const identity=stable([signature,pinKey(pins)]);
 const matches=(review:SavedReview<unknown>)=>{
  const cutoff=asObject(review.snapshot.cutoff);
  return valid&&review.domain==='M12'&&review.patient===requested.patient&&review.encounter===requested.encounter&&
   review.repository===catalog.repository&&compareRespiratoryInstants(review.period.start,requested.start)===0&&
   compareRespiratoryInstants(review.period.end,requested.end)===0&&review.snapshot.signature===signature&&cutoff.repository_id===catalog.repository&&
   Number.isSafeInteger(cutoff.fact_watermark)&&Number(cutoff.fact_watermark)<=catalog.cutoff.fact_watermark&&
   review.snapshot.pins.every(p=>{const v=asObject(p);return v.repository===catalog.repository&&
    Number(v.cutoff)>=Number(v.ingestion)&&Number(v.cutoff)<=Number(cutoff.fact_watermark);})&&
   pinKey(review.snapshot.pins)===pinKey(pins);
 };
 return {valid,records,status,phase,phaseLabel,pregnancy,gestation,labs,pressures,
  medications:medicationSources.map(source=>source.item),medicationConfirmed,pins,signature,identity,matches};
}
