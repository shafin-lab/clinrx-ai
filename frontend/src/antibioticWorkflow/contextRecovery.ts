import generated from '../api/rf2Schemas.json';
import {validateTransportSchema,type Schema} from '../api/decoding';
import {parseRF2JSON} from '../api/rf2JSON';
import type {Draft} from '../api/rf2Client';
import {DOSE_CONTEXT_QUESTION,parsePatientDoseContext} from './automaticRenalModel';
const schemas=generated as unknown as {roots:Record<string,Schema>;definitions:Record<string,Schema>};
export const contextPendingKey=(repository:string)=>'clinrx.patient-dose-context.pending.v1.synthetic-p1.synthetic-e1.'+repository;
export function readContextPending(text:string,repository:string):{version:1;draft:Draft}{
 if(text.length>131072)throw Error('Recovery exceeds its bound');
 const value=parseRF2JSON(text) as {version:unknown;draft:Draft};if(!value||Object.keys(value).sort().join()!=='draft,version'||value.version!==1)throw Error('Invalid recovery record');
 validateTransportSchema(value.draft,schemas.roots.RF2Draft,schemas.definitions);
 if(value.draft.repository!==repository||value.draft.note?.question!==DOSE_CONTEXT_QUESTION||!parsePatientDoseContext(value.draft.note.findings)||value.draft.note.pins.some(p=>p.repository!==repository))throw Error('Recovery context differs');
 return {version:1,draft:value.draft};
}
export async function retainContextPending(repository:string,draft:Draft,expected:string|null,current:()=>boolean){
 if(!navigator.locks)throw Error('Web Locks are required to retain exact context recovery.');
 return navigator.locks.request(contextPendingKey(repository),()=>{
  if(!current())throw Error('Patient evidence changed while the context waited to save. Review current sources.');
  const key=contextPendingKey(repository);if(localStorage.getItem(key)!==expected)throw Error('Another tab changed context recovery. Its data was preserved.');
  const bytes=JSON.stringify({version:1,draft});readContextPending(bytes,repository);localStorage.setItem(key,bytes);if(localStorage.getItem(key)!==bytes)throw Error('Exact context recovery could not be retained.');return bytes;
 });
}
export function clearContextPending(repository:string,expected:string){const key=contextPendingKey(repository);if(localStorage.getItem(key)!==expected)throw Error('Concurrent context recovery was preserved.');localStorage.removeItem(key);}
