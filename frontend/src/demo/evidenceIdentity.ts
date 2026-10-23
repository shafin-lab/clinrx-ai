import type {CirculatoryItem} from '../api/circulatoryTypes';
/** IDs and revisions may contain slashes; encode components without delimiters. */
export const evidenceKey=(fact:Pick<CirculatoryItem['fact'],'kind'|'id'|'revision'>)=>JSON.stringify([fact.kind,fact.id,fact.revision]);
export function resolveEvidenceKey(items:CirculatoryItem[],value:string):CirculatoryItem|undefined{
 let tuple:unknown;try{tuple=JSON.parse(value);}catch{return undefined;}
 if(!Array.isArray(tuple)||tuple.length!==3||!tuple.every(part=>typeof part==='string'))return undefined;
 const [kind,id,revision]=tuple;
 return items.find(item=>item.fact.kind===kind&&item.fact.id===id&&item.fact.revision===revision);
}
