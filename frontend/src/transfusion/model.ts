import {stable} from '../api/rf2Client';
import {componentIdentity} from '../clinicalEvidence/componentIdentity';
import type {Catalog,Evidence} from '../api/rf2Client';
export const object=(value:unknown):Record<string,any>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,any>:{};
export const products:Record<string,string>={prbc:'PRBC',ffp:'FFP · fresh frozen plasma',plasma:'Other plasma preparation',platelets_rdp:'RDP · random donor platelets',platelets_pooled:'Pooled platelets',platelets_sdp:'SDP · single donor / apheresis platelets',cryo:'Cryoprecipitate',pcc:'PCC · prothrombin complex concentrate',fibrinogen_concentrate:'Human fibrinogen concentrate',whole_blood:'Whole blood',cell_salvage:'Cell-salvaged blood',factor_concentrate:'Other coagulation factor concentrate',antifibrinolytic:'Antifibrinolytic medicine',protamine:'Protamine',calcium:'Calcium replacement',other:'Other blood or haemostatic product'};
export const productLabel=(value:string)=>products[value]??value.replaceAll('_',' ');
export function quantityText(value:unknown):string {const q=object(value);if(q.value===undefined||q.value===null)return 'Not documented';const unit=typeof q.unit==='string'?q.unit:object(q.unit).raw??object(q.unit).raw_display??'';return `${q.value} ${unit}${q.basis&&q.basis!==unit?' · '+String(q.basis).replaceAll('_',' '):''}`.trim();}
export function validateProductEntry(v:{status:string;count?:string;volume?:string;dose?:string}):string|null {const amounts=[v.count,v.volume,v.dose].filter(x=>x!==undefined&&x!=='') as string[];if(amounts.some(x=>!/^\d+(?:\.\d+)?$/.test(x)))return 'Enter non-negative decimal quantities, or leave unknown amounts blank.';if(v.status==='not_given'&&amounts.some(x=>Number(x)>0))return 'A product not given cannot have a positive delivered quantity.';return null;}
export interface LaboratoryRow {label:string;value:string;source:Evidence;component:string;time:string;status:string;raw:Record<string,any>}
export interface LaboratoryProjection {rows:LaboratoryRow[];valid:boolean;error?:string}
/** Equal values across sources stay distinct; exact source conflicts withhold the projection. */
export function laboratoryProjection(catalog:Catalog|undefined):LaboratoryProjection {
 if(!catalog)return {rows:[],valid:false,error:'Current laboratory evidence is unconfirmed.'};
 const rows:LaboratoryRow[]=[],seen=new Map<string,string>(),sources=new Map<string,{digest:string;fact:string}>();
 const conflict=():LaboratoryProjection=>({rows:[],valid:false,error:'Conflicting laboratory source identity, digest or content. Current laboratory evidence is unconfirmed.'});
 for(const source of [...catalog.laboratory_reports,...(catalog.respiratory_records??[]),...catalog.items]){
  const fact=source.fact;
  if(!['laboratory_report','respiratory_record','circulatory_oxygen'].includes(fact.kind))continue;
  const sourceKey=componentIdentity(source,''),content=stable(fact),prior=sources.get(sourceKey);
  if(prior&&(prior.digest!==source.digest||prior.fact!==content))return conflict();
  sources.set(sourceKey,{digest:source.digest,fact:content});
  const components=Array.isArray(fact.components)?fact.components:Array.isArray(fact.measurements)?fact.measurements:[fact];
  for(const raw of components){
   const m=object(raw),label=String(m.label??object(m.test_code).raw_display??m.mapped_concept??m.concept??m.concept_id??'');
   const id=String(m.source_component_id??m.concept??label),identity=componentIdentity(source,id),componentContent=stable(raw),previousComponent=seen.get(identity);
   if(previousComponent!==undefined){if(previousComponent!==componentContent)return conflict();continue;}
   seen.set(identity,componentContent);
   if(!/ha?emoglobin|ha?ematocrit|platelet|fibrinogen|\binr\b|aptt|prothrombin|thrombin|calcium|anti.?xa|d.?dimer|\bpt\b|\bhb\b|\bhct\b/i.test(label))continue;
   const r=object(m.result),q=object(r.quantity),unit=object(r.unit);
   rows.push({raw:m,label,value:r.kind==='unavailable'?`${r.status}: ${r.reason}`:[r.comparator&&r.comparator!=='='?r.comparator:'',r.raw_value??r.value??q.value??r.status??'Not documented',unit.raw_display??unit.code??object(q.unit).raw??''].filter(Boolean).join(' '),source,component:id,time:String(object(object(fact.times).collected).value??object(object(fact.occurred).recorded).value??'Collection time not documented'),status:String(fact.report_status??fact.record_status??'Unknown')});
  }
 }
 return {rows,valid:true};
}
/** Compatibility for existing row consumers; scope-aware views consume laboratoryProjection. */
export function extractLaboratory(catalog:Catalog|undefined):LaboratoryRow[]{return laboratoryProjection(catalog).rows;}
