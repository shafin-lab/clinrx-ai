import {parseRF2JSON} from '../api/rf2JSON';

export type ReviewDomain='M7'|'M8';
export interface ReviewScope {domain:ReviewDomain;patient:string;encounter:string;repository:string}
export interface SavedReview<T=Record<string,unknown>> {
 format:'clinrx-local-review';version:1;id:string;domain:ReviewDomain;patient:string;encounter:string;repository:string;
 period:{start:string;end:string};snapshot:{signature:string;cutoff:unknown;pins:unknown[]};draft:T;recordedAt:string;
}
export interface ReviewLockManager {request<T>(name:string,callback:()=>T|Promise<T>):Promise<T>}
export interface ReviewStorage {getItem(key:string):string|null;setItem(key:string,value:string):void;key(index:number):string|null;readonly length:number}
const MAX_RECORD_BYTES=524288,MAX_PINS=500;
const ownRecord=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
const validTime=(value:unknown)=>typeof value==='string'&&value.length<=80&&Number.isFinite(Date.parse(value));
const nonempty=(value:unknown,limit:number)=>typeof value==='string'&&value.trim().length>0&&value.length<=limit;

export function reviewStoragePrefix(scope:ReviewScope){
 return 'clinrx.local-review/v1/'+scope.domain+'/'+[scope.patient,scope.encounter,scope.repository].map(encodeURIComponent).join('/')+'/';
}
export const reviewLockName=(scope:ReviewScope)=>'clinrx-local-review:'+reviewStoragePrefix(scope);
function validPin(pin:unknown){
 if(!ownRecord(pin))return false;
 if(ownRecord(pin.reference))return nonempty(pin.reference.kind,160)&&nonempty(pin.reference.id,240)&&nonempty(pin.reference.version,160)&&typeof pin.expected_digest==='string'&&/^[a-f0-9]{64}$/i.test(pin.expected_digest);
 return nonempty(pin.repository,240)&&nonempty(pin.kind,160)&&nonempty(pin.id,240)&&nonempty(pin.version,160)&&typeof pin.digest==='string'&&/^[a-f0-9]{64}$/i.test(pin.digest)&&Number.isSafeInteger(pin.ingestion)&&Number.isSafeInteger(pin.cutoff);
}
function validReview(value:unknown,scope:ReviewScope,id:string):value is SavedReview{
 if(!ownRecord(value)||value.format!=='clinrx-local-review'||value.version!==1||value.id!==id||value.domain!==scope.domain||value.patient!==scope.patient||value.encounter!==scope.encounter||value.repository!==scope.repository)return false;
 if(!ownRecord(value.period)||!validTime(value.period.start)||!validTime(value.period.end)||Date.parse(value.period.end as string)<=Date.parse(value.period.start as string))return false;
 if(!ownRecord(value.snapshot)||!nonempty(value.snapshot.signature,32768)||value.snapshot.cutoff===null||value.snapshot.cutoff===undefined||!Array.isArray(value.snapshot.pins)||value.snapshot.pins.length>MAX_PINS||!value.snapshot.pins.every(validPin))return false;
 if(!ownRecord(value.draft)||!nonempty(value.draft.reviewer,120)||!nonempty(value.draft.rationale,2000)||!nonempty(value.draft.nextReview,250)||!validTime(value.recordedAt))return false;
 try{return JSON.stringify(value).length<=MAX_RECORD_BYTES;}catch{return false;}
}
function getStorage(storage?:ReviewStorage):ReviewStorage{
 try{const value=storage??globalThis.localStorage;if(!value)throw Error();return value;}catch{throw new Error('Browser review storage is unavailable. No review was saved.');}
}

/** Invalid bytes stay in place and are reported; a valid, differently-scoped review is never returned. */
export function loadSavedReviews<T=Record<string,unknown>>(scope:ReviewScope,storageArg?:ReviewStorage):{reviews:SavedReview<T>[];issue?:string}{
 let storage:ReviewStorage;try{storage=getStorage(storageArg);}catch(error){return {reviews:[],issue:error instanceof Error?error.message:'Browser review storage is unavailable.'};}
 const prefix=reviewStoragePrefix(scope),reviews:SavedReview<T>[]=[];let issue=false;
 try{for(let index=0;index<storage.length;index++){
  const key=storage.key(index);if(!key?.startsWith(prefix))continue;
  const raw=storage.getItem(key);if(raw===null||raw.length>MAX_RECORD_BYTES){issue=true;continue;}
  const id=key.slice(prefix.length);
  try{const value=parseRF2JSON(raw);if(!validReview(value,scope,id)){issue=true;continue;}reviews.push(value as SavedReview<T>);}catch{issue=true;}
 }}catch{return {reviews:[],issue:'Saved reviews could not be read. Existing browser data was preserved.'};}
 reviews.sort((a,b)=>b.recordedAt.localeCompare(a.recordedAt));
 return {reviews,...(issue?{issue:'Some saved review data is unreadable or incompatible. It was preserved and was not shown.'}:{})};
}

/** Append-only single-key writes are protected by a same-scope Web Lock; existing reviews cannot be replaced. */
export async function appendSavedReview<T>(scope:ReviewScope,review:SavedReview<T>,stillCurrent:()=>boolean,options:{storage?:ReviewStorage;locks?:ReviewLockManager}={}):Promise<void>{
 const storage=getStorage(options.storage),locks=options.locks??globalThis.navigator?.locks;
 if(!locks)throw new Error('Safe cross-tab review storage is unavailable. No review was saved.');
 if(!validReview(review,scope,review.id))throw new Error('The review does not match the confirmed patient, repository or evidence format. No review was saved.');
 try{await locks.request(reviewLockName(scope),async()=>{
  if(!stillCurrent())throw new Error('Evidence changed before the review could be saved. Review the current sources again.');
  const key=reviewStoragePrefix(scope)+review.id;
  if(storage.getItem(key)!==null)throw new Error('This review identifier already exists. The earlier record was preserved.');
  const raw=JSON.stringify(review);if(raw.length>MAX_RECORD_BYTES)throw new Error('This review exceeds the browser storage limit. No review was saved.');
  storage.setItem(key,raw);
  if(storage.getItem(key)!==raw)throw new Error('Review storage could not confirm the saved record. No saved confirmation is available.');
 });}catch(error){
  if(error instanceof Error&&/Evidence changed|already exists|exceeds the browser storage limit|could not confirm|No review was saved|No saved confirmation/.test(error.message))throw error;
  throw new Error('Review storage failed. No saved confirmation is available.');
 }
}
