import type {CirculatoryItem} from '../api/circulatoryTypes';
import {method,record,sourceTime,title,value,words} from './evidencePresentation';

/** Search recorded display fields only; never infer sample type or convert source times. */
export function matchesEvidenceSearch(item:CirculatoryItem,query:string){
 const sample=words(item.fact.sample_type),specimen=record(item.fact.specimen);
 const gas=item.fact.kind==='circulatory_oxygen';
 const aliases=gas&&sample==='arterial'?'ABG arterial blood gas':gas&&sample.includes('venous')?'VBG venous blood gas':'';
 const text=[title(item),method(item),item.fact.id,item.fact.revision,value(item).text,sourceTime(item),sample,specimen.raw_display,aliases].filter(v=>typeof v==='string').join(' ').toLowerCase();
 return query.trim().toLowerCase().split(/\s+/).filter(Boolean).every(term=>{
  if(term==='abg')return gas&&sample==='arterial';
  if(term==='vbg')return gas&&sample.includes('venous');
  if(/^\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(term))return sourceTime(item).toLowerCase().includes(term);
  return text.includes(term);
 });
}
export function bloodGasLabel(item:CirculatoryItem){
 const sample=words(item.fact.sample_type);
 return item.fact.kind==='circulatory_oxygen'&&sample?sample==='arterial'?'Arterial blood gas (ABG)':sample+' sample':undefined;
}
