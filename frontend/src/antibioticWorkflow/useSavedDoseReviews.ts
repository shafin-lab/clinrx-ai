import {useEffect,useRef,useState} from 'react';
import type {Item} from '../api/microTypes';
import {stable} from '../api/rf2Client';
import type {AutomaticRenalModel} from './automaticRenalModel';
import {medicationDoseReview,type MedicineAssessment} from './medicationDoseModel';
import type {TherapyCourse} from './therapyModel';
import {appendReview,dependenciesFor,evaluateReview,initialMedicineAssessment,readReviewLog,reviewKey,scopeFor,type DoseReviewLog,type ReviewDependencies,type SavedDoseReview} from './savedDoseReviews';

interface Retained {bytes:string|null;log?:DoseReviewLog;error?:string}
interface DraftReview {value:MedicineAssessment;dependencies:ReviewDependencies;expected:string|null}
export function useSavedDoseReviews({courses,model,current,blocked,cultures,historyItems,historyLoading,historyError,onNeedHistory}:{courses:TherapyCourse[];model:AutomaticRenalModel;current:boolean;blocked:boolean;cultures:Item[];historyItems?:Item[];historyLoading?:boolean;historyError?:string;onNeedHistory?:(course:TherapyCourse)=>void}){
 const [retained,setRetained]=useState<Record<string,Retained>>({}),[drafts,setDrafts]=useState<Record<string,DraftReview>>({}),[messages,setMessages]=useState<Record<string,string>>({}),[saving,setSaving]=useState<Record<string,boolean>>({});
 const alive=useRef(true),working=useRef(new Set<string>()),keys=stable(courses.map(c=>{const s=scopeFor(c,model);return s?[c.order!.fact.id,reviewKey(s)]:null;}));
 const historyReady=historyItems!==undefined&&!historyLoading&&!historyError;
 const runtime=useRef({courses,model,current,blocked,cultures,historyItems,historyReady,drafts,onNeedHistory});runtime.current={courses,model,current,blocked,cultures,historyItems,historyReady,drafts,onNeedHistory};
 function load(){const next:Record<string,Retained>={};for(const c of runtime.current.courses){const scope=scopeFor(c,runtime.current.model);if(!scope)continue;const key=reviewKey(scope);let bytes:string|null=null;try{bytes=localStorage.getItem(key);next[key]={bytes,...bytes!==null?{log:readReviewLog(bytes,scope)}:{}};}catch{next[key]={bytes,error:'Saved browser review could not be read safely. Existing bytes were preserved.'};}}if(alive.current)setRetained(next);}
 useEffect(()=>{alive.current=true;load();const changed=(event:StorageEvent)=>{if(event.key===null||event.key.startsWith('clinrx.dose-reviews.v1.'))load();};window.addEventListener('storage',changed);return()=>{alive.current=false;window.removeEventListener('storage',changed);};},[keys]);
 useEffect(()=>{if(!current||historyReady||historyLoading||historyError)return;const c=courses.find(c=>{const scope=scopeFor(c,model);return scope&&retained[reviewKey(scope)]?.log;});if(c)runtime.current.onNeedHistory?.(c);},[keys,retained,current,historyReady,historyLoading,historyError]);

 function status(course:TherapyCourse){
  const scope=scopeFor(course,model),key=scope?reviewKey(scope):'',entry=retained[key],saved=entry?.log?.reviews.at(-1),draft=drafts[key];
  const selected=draft?.value??saved?.assessment??initialMedicineAssessment(course),dependencies=dependenciesFor(course,model,cultures,historyItems??[],selected);
  const evaluation=saved?evaluateReview(saved,dependencies,model,course):undefined;
  // An edit is only a draft. Changing evidence resets just incompatible confirmations.
  const draftEvaluation=draft?evaluateReview({version:1,id:'draft',reviewer:'draft',savedAt:new Date().toISOString(),cutoff:model.scope?.cutoff??0,reviewEnd:model.scope?.end??'',assessment:draft.value,dependencies:draft.dependencies,evidence:model.sources},dependencies,model,course):undefined;
  const assessment=draftEvaluation?.assessment??evaluation?.assessment??initialMedicineAssessment(course);
  const changedDraft=!!draft&&(!saved||stable(draft.value)!==stable(saved.assessment));
  const concurrent=!!draft&&!!entry&&draft.expected!==entry.bytes;
  const valid=!!saved&&!!evaluation?.valid&&historyReady&&current&&!changedDraft&&!entry?.error&&!concurrent;
  const reasons=[...entry?.error?[entry.error]:[],...concurrent?['Another tab changed the saved review. Reload its receipt before saving.']:[],...saved&&!historyReady?[historyError?'Previous-dose history is unconfirmed.':historyLoading?'Confirming previous-dose history…':'Previous-dose history must be confirmed before restoring this review.']:[],...evaluation?.reasons??[]];
  return {key,scope,entry,saved,assessment,dependencies,valid,changedDraft,reasons:[...new Set(reasons)],message:messages[key]??'',busy:!!saving[key],canSave:!!scope&&current&&!blocked&&historyReady&&!entry?.error&&!concurrent&&!!entry};
 }
 function change(course:TherapyCourse,value:MedicineAssessment){const s=status(course);setDrafts(old=>({...old,[s.key]:{value:{...value},dependencies:dependenciesFor(course,model,cultures,historyItems??[],value),expected:old[s.key]?old[s.key].expected:s.entry?.bytes??null}}));setMessages(old=>({...old,[s.key]:''}));}
 function reload(course:TherapyCourse){const s=status(course);setDrafts(old=>{const next={...old};delete next[s.key];return next;});setMessages(old=>({...old,[s.key]:''}));load();}
 async function save(course:TherapyCourse,reviewer:string){
  const s=status(course);if(!s.scope||working.current.has(s.key))return;
  working.current.add(s.key);setSaving(old=>({...old,[s.key]:true}));setMessages(old=>({...old,[s.key]:''}));
  try{
   if(!s.canSave)throw Error(s.reasons[0]??'Confirm current patient and previous-dose evidence before saving.');
   const name=reviewer.trim();if(!name||name.length>128)throw Error('Enter the reviewer name or identifier.');
   const result=medicationDoseReview(course.medicine,course.route,model,s.assessment);if(result.status!=='suggested')throw Error(result.reason);
   const assessment={...s.assessment},dependencies=dependenciesFor(course,model,cultures,historyItems??[],assessment),atScope=model.scope!;
   const review:SavedDoseReview={version:1,id:crypto.randomUUID(),reviewer:name,savedAt:new Date().toISOString(),cutoff:atScope.cutoff,reviewEnd:atScope.end,assessment,dependencies,evidence:model.sources.map(p=>({...p,reference:{...p.reference}}))};
   const bytes=await appendReview(s.scope,review,s.entry!.bytes,()=>{
    const now=runtime.current,matching=now.courses.find(c=>{const scope=scopeFor(c,now.model);return scope&&reviewKey(scope)===s.key;});
    if(!alive.current||!now.current||now.blocked||!now.historyReady||!matching||matching.conflict)return false;
    const currentAssessment=now.drafts[s.key]?.value??s.assessment;
    return stable(currentAssessment)===stable(assessment)&&stable(dependenciesFor(matching,now.model,now.cultures,now.historyItems??[],assessment))===stable(dependencies)&&now.model.scope!.cutoff>=atScope.cutoff;
   });
   if(!alive.current)return;
   setRetained(old=>({...old,[s.key]:{bytes,log:readReviewLog(bytes,s.scope!)}}));
   setDrafts(old=>{const next={...old};delete next[s.key];return next;});setMessages(old=>({...old,[s.key]:'Dose review saved in this browser. Prescription and administrations unchanged.'}));
  }catch(error){if(alive.current)setMessages(old=>({...old,[s.key]:error instanceof Error?error.message:'Browser review save could not be confirmed.'}));}
  finally{working.current.delete(s.key);if(alive.current)setSaving(old=>({...old,[s.key]:false}));}
 }
 return {status,change,reload,save,historyReady};
}
