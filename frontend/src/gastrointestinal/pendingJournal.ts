import {stable} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
const owned=(stored:string|null,raw:string)=>{if(stored===null)return false;try{return stable(parseRF2JSON(stored))===raw;}catch{return false;}};
/** One in-flight journal per scope. A late completion can only clear its exact owner. */
export async function reservePending(key:string,value:unknown){
 const locks=globalThis.navigator?.locks;if(!locks)throw Error('Safe pending-request storage is unavailable. No request was sent.');
 const raw=stable(value);await locks.request('clinrx.m11.journal:'+key,()=>{
  const existing=localStorage.getItem(key);if(existing!==null&&!owned(existing,raw))throw Error('Another pending request is already preserved for this patient. Finish or recover it before saving another.');
  if(existing===null)localStorage.setItem(key,raw);if(!owned(localStorage.getItem(key),raw))throw Error('Pending request storage could not confirm its owner. No request was sent.');
 });
}
export async function releasePending(key:string,value:unknown){
 const locks=globalThis.navigator?.locks;if(!locks)throw Error('Pending request ownership could not be confirmed. The request was preserved.');
 const raw=stable(value);await locks.request('clinrx.m11.journal:'+key,()=>{if(owned(localStorage.getItem(key),raw))localStorage.removeItem(key);});
}
