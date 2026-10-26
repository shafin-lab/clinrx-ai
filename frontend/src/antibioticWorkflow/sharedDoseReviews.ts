import {stable} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {parsePatientDoseContext,type AutomaticRenalModel,type ContextAssessment} from './automaticRenalModel';
import {readReviewLog,type SavedDoseReview} from './savedDoseReviews';
export interface SharedReviewScope {repository:string;patient:string;encounter:string}
export interface SharedAssessment {version:1;id:string;reviewer:string;savedAt:string;context:ContextAssessment;reviews:{orderId:string;review:SavedDoseReview}[]}
export interface SharedReviewLog {version:1;scope:SharedReviewScope;assessments:SharedAssessment[]}
export const sharedScope=(model:AutomaticRenalModel):SharedReviewScope|undefined=>model.scope?{repository:model.scope.repository,patient:model.scope.patient,encounter:model.scope.encounter}:undefined;
export const sharedReviewKey=(scope:SharedReviewScope)=>'clinrx.shared-dose-reviews.v1.'+encodeURIComponent(stable(scope));
function exact(value:unknown,keys:string[]):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join()!==[...keys].sort().join())throw Error('Saved assessment structure is invalid. Existing bytes were preserved.');return value as Record<string,unknown>;}
const text=(v:unknown,n=256):v is string=>typeof v==='string'&&v.length>0&&v.length<=n;
export function readSharedLog(bytes:string,scope:SharedReviewScope):SharedReviewLog {
 if(bytes.length>4*1048576)throw Error('Browser assessment log is full. Existing bytes were preserved.');
 const log=exact(parseRF2JSON(bytes),['version','scope','assessments']);exact(log.scope,['repository','patient','encounter']);
 if(log.version!==1||stable(log.scope)!==stable(scope)||!Array.isArray(log.assessments)||!log.assessments.length||log.assessments.length>50)throw Error('Saved assessment scope or version is invalid. Existing bytes were preserved.');
 const ids=new Set<string>();
 for(const raw of log.assessments){
  const a=exact(raw,['version','id','reviewer','savedAt','context','reviews']),c=exact(a.context,['id','scope','context','sources','baseContext']),s=exact(c.scope,['repository','patient','encounter','start','end','cutoff']);
  if(a.version!==1||!text(a.id,128)||ids.has(a.id)||!text(a.reviewer,128)||a.reviewer.trim()!==a.reviewer||!text(a.savedAt)||compare(a.savedAt,a.savedAt)!==0||Date.parse(a.savedAt)>Date.now()+1000||c.id!==a.id||!parsePatientDoseContext(stable(c.context))||!text(c.baseContext,8192)||stable(parseRF2JSON(c.baseContext))!==c.baseContext||s.repository!==scope.repository||s.patient!==scope.patient||s.encounter!==scope.encounter||!Number.isSafeInteger(s.cutoff)||Number(s.cutoff)<1||typeof s.start!=='string'||typeof s.end!=='string'||compare(s.start,s.end)!== -1||!Array.isArray(a.reviews)||!a.reviews.length||a.reviews.length>100)throw Error('Saved assessment receipt is invalid. Existing bytes were preserved.');
  ids.add(a.id);const orders=new Set<string>();
  for(const rawReview of a.reviews){const row=exact(rawReview,['orderId','review']);if(!text(row.orderId)||orders.has(row.orderId))throw Error('Repeated or invalid medicine review.');orders.add(row.orderId);const decoded=readReviewLog(JSON.stringify({version:1,scope:{...scope,orderId:row.orderId},reviews:[row.review]}),{...scope,orderId:row.orderId}).reviews[0];if(decoded.reviewer!==a.reviewer||decoded.savedAt!==a.savedAt||decoded.cutoff!==s.cutoff||decoded.reviewEnd!==s.end||stable(decoded.evidence)!==stable(c.sources))throw Error('Medicine and shared assessment differ. Existing bytes were preserved.');}
 }
 return log as unknown as SharedReviewLog;
}
export async function appendSharedReview(scope:SharedReviewScope,assessment:SharedAssessment,expected:string|null,legacyExpected:Record<string,string|null>,current:()=>boolean){
 if(!navigator.locks)throw Error('Web Locks are required for this browser assessment.');
 const key=sharedReviewKey(scope);
 return navigator.locks.request(key,()=>{
  if(!current())throw Error('Patient or treatment context changed while the assessment waited to save.');
  const previous=localStorage.getItem(key);if(previous!==expected||Object.entries(legacyExpected).some(([k,v])=>localStorage.getItem(k)!==v))throw Error('Another tab changed a saved review. Existing data was preserved; reload its assessment.');
  const rows=previous===null?[]:readSharedLog(previous,scope).assessments;if(rows.length>=50)throw Error('Browser assessment log is full. Existing history was preserved.');
  const bytes=JSON.stringify({version:1,scope,assessments:[...rows,assessment]});readSharedLog(bytes,scope);
  if(!current())throw Error('Patient or treatment context changed before the assessment was saved.');
  localStorage.setItem(key,bytes);if(localStorage.getItem(key)!==bytes)throw Error('Save completion is unconfirmed. Reload the saved assessment before retrying.');return bytes;
 });
}
