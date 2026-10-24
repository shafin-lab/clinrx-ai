import {parseRF2JSON} from '../api/rf2JSON';
import type {M10Item} from './types';
export interface SessionDraft {identity:string;evidenceScope:string;kind:string;v:Record<string,string>;observations:Record<string,any>[];attachments:{digest:string;name:string}[]}
export type DraftRead={status:'absent'}|{status:'valid';raw:string;draft:SessionDraft}|{status:'damaged';raw:string};
const record=(v:unknown):v is Record<string,any>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const supportedKinds=new Set(['transfusion_administration','haemostatic_medication_course','transfusion_request','transfusion_prescription','blood_product_disposition','transfusion_compatibility','viscoelastic_report','haemorrhage_episode','transfusion_reaction','m10_assessment','transfusion_coverage_link','fluid_administration_link']);
const optionalText=(v:unknown)=>v===undefined||v===null||typeof v==='string';
function observation(v:unknown):v is Record<string,any>{
 if(!record(v)||!['id','assay','parameter','state'].every(k=>typeof v[k]==='string'))return false;
 if(!['value','unit','raw_value','result_type','comparator','source_label','reference_low','reference_high','elapsed_seconds','timing_origin','maturation'].every(k=>optionalText(v[k])))return false;
 return ['observed_at','available_at'].every(k=>v[k]===undefined||v[k]===null||record(v[k])&&typeof v[k].status==='string'&&typeof v[k].precision==='string'&&['value','lower','upper','uncertainty'].every(n=>optionalText(v[k][n])));
}

// Recovery belongs to the record owner. Evidence freshness is a separate save gate.
export function draftIdentity(repository:string,requested:{patient:string;encounter:string},kind:string,prior?:M10Item,product?:string){return JSON.stringify([repository,requested.patient,requested.encounter,kind,prior?[prior.fact.kind,prior.fact.id,prior.fact.revision,prior.digest]:null,product??null]);}
export function decodeDraft(raw:string|null,identity:string,legacyScope?:string):DraftRead {
 if(raw===null)return {status:'absent'};
 try{const d:unknown=parseRF2JSON(raw);if(!record(d)||!record(d.v)||!Object.values(d.v).every(v=>typeof v==='string')||typeof d.kind!=='string'||!supportedKinds.has(d.kind)||!Array.isArray(d.observations)||!d.observations.every(observation)||d.attachments!==undefined&&(!Array.isArray(d.attachments)||!d.attachments.every((a:unknown)=>record(a)&&typeof a.digest==='string'&&typeof a.name==='string')))return {status:'damaged',raw};
  if(legacyScope===undefined&&(d.identity!==identity||typeof d.evidenceScope!=='string'))return {status:'damaged',raw};
  return {status:'valid',raw,draft:{identity,evidenceScope:legacyScope??d.evidenceScope,kind:d.kind,v:d.v,observations:d.observations,attachments:d.attachments??[]}};
 }catch{return {status:'damaged',raw};}
}
