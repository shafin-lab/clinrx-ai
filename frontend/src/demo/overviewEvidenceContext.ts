import type {CirculatoryItem} from '../api/circulatoryTypes';
import {record,words} from './evidencePresentation';
import {quantityText} from './HemodynamicContext';
/** Display only this source's assertions; never borrow sample context or interpret findings. */
export function overviewEvidenceContext(item:CirculatoryItem):string[]{
 const f=item.fact,a=record(f.acquisition),gas=f.kind==='circulatory_oxygen'&&a.method==='blood_gas';
 if(!gas&&f.kind!=='circulatory_echo')return [];
 const b=record(f.blood_gas_context),q=record(a.quality),notes:string[]=[];
 if(gas){
  notes.push('Sample: '+(words(f.sample_type)||'not recorded'));
  notes.push('Sample FiO₂: '+quantityText(b.fio2));
 }else notes.push('Source production: '+(words(f.production)||'not recorded'));
 for(const source of [f.disclosures,f.uncertainty,a.limitations,q.limitations,b.limitations]){
  if(Array.isArray(source))for(const note of source)if(typeof note==='string'&&note.trim())notes.push('Source caveat: '+note);
 }
 return [...new Set(notes)];
}
