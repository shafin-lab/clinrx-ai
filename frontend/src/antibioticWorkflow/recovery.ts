import {parseRF2JSON} from '../api/rf2JSON';
import {validateAntibioticDraft,type AntibioticDraft} from '../api/antibioticClient';
export interface Pending {version:1;draft:AntibioticDraft}
export const storageKey=(repository:string)=>'clinrx.antibiotic.pending.v1.synthetic-p1.synthetic-e1.'+repository;
export function readPending(text:string,repository:string):Pending {const value=parseRF2JSON(text) as {version:unknown;draft:unknown};if(Object.keys(value).sort().join()!=='draft,version'||value.version!==1)throw Error('Invalid recovery record');validateAntibioticDraft(value.draft);if(value.draft.repository!==repository)throw Error('Recovery scope differs');return {version:1,draft:value.draft};}
export function retainPending(key:string,pending:Pending,expected:string|null){if(localStorage.getItem(key)!==expected)throw Error('Another tab changed this pending record. Reload to recover it before continuing.');const text=JSON.stringify(pending);localStorage.setItem(key,text);if(localStorage.getItem(key)!==text)throw Error('Pending record could not be retained.');return text;}
export function clearPending(key:string,expected:string){if(localStorage.getItem(key)!==expected)throw Error('Another tab changed recovery. Its record was preserved.');localStorage.removeItem(key);}
