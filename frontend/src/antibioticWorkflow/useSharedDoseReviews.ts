import {useEffect,useMemo,useRef,useState} from 'react';
import {stable,type Catalog} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import type {Item} from '../api/microTypes';
import {record} from '../demo/evidencePresentation';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {automaticRenalModel,blankPatientDoseContext,contextSourceIdentity,type ContextAssessment,type PatientDoseContext} from './automaticRenalModel';
import {medicationDoseReview,type MedicineAssessment} from './medicationDoseModel';
import {dependenciesFor,evaluateReview,initialMedicineAssessment,readReviewLog,reviewKey,scopeFor,type SavedDoseReview,type ReviewDependencies} from './savedDoseReviews';
import {appendSharedReview,readSharedLog,sharedReviewKey,sharedScope,type SharedAssessment,type SharedReviewLog} from './sharedDoseReviews';
import type {TherapyCourse} from './therapyModel';
interface Legacy {bytes:string|null;saved?:SavedDoseReview;error?:string}
interface Draft {context:ContextAssessment;expected:string|null;legacy:Record<string,string|null>;reviewer:string}
interface MedicineDraft {assessment:MedicineAssessment;dependencies:ReviewDependencies}
export function useSharedDoseReviews({catalog,courses,cultures,current,blocked,historyItems,historyLoading,historyError,onNeedHistory}:{catalog:Catalog;courses:TherapyCourse[];cultures:Item[];current:boolean;blocked:boolean;historyItems?:Item[];historyLoading?:boolean;historyError?:string;onNeedHistory?:(course:TherapyCourse)=>void}){
 const base=useMemo(()=>automaticRenalModel(catalog),[catalog]),scope=sharedScope(base)!,key=sharedReviewKey(scope),keys=stable([key,courses.map(c=>c.order?.fact.id)]);
 const [stored,setStored]=useState<{key:string;bytes:string|null;log?:SharedReviewLog;legacy:Record<string,Legacy>;error?:string}>({key:'',bytes:null,legacy:{}}),[draft,setDraft]=useState<Draft>(),[medicines,setMedicines]=useState<Record<string,MedicineDraft>>({}),[acks,setAcks]=useState<Record<string,string>>({}),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 const alive=useRef(true),working=useRef(false),runtime=useRef({catalog,courses,cultures,current,blocked,historyItems,historyLoading,historyError,draft,medicines,acks});runtime.current={catalog,courses,cultures,current,blocked,historyItems,historyLoading,historyError,draft,medicines,acks};
 function load(){const now=runtime.current,m=automaticRenalModel(now.catalog),s=sharedScope(m)!;const next:{key:string;bytes:string|null;log?:SharedReviewLog;legacy:Record<string,Legacy>;error?:string}={key:sharedReviewKey(s),bytes:null,legacy:{}};try{next.bytes=localStorage.getItem(next.key);if(next.bytes!==null)next.log=readSharedLog(next.bytes,s);}catch{next.error='Saved shared assessment could not be read safely. Existing bytes were preserved.';}for(const c of now.courses){const cs=scopeFor(c,m);if(!cs)continue;const k=reviewKey(cs);let bytes:string|null=null;try{bytes=localStorage.getItem(k);next.legacy[c.order!.fact.id]={bytes,saved:bytes===null?undefined:readReviewLog(bytes,cs).reviews.at(-1)};}catch{next.legacy[c.order!.fact.id]={bytes,error:'An earlier medicine review could not be read safely. Existing bytes were preserved.'};}}if(alive.current)setStored(next);}
 useEffect(()=>{alive.current=true;load();const listener=(event:StorageEvent)=>{if(event.key===null||event.key.startsWith('clinrx.shared-dose-reviews.')||event.key.startsWith('clinrx.dose-reviews.'))load();};window.addEventListener('storage',listener);return()=>{alive.current=false;window.removeEventListener('storage',listener);};},[keys]);
 const here=stored.key===key?stored:undefined,last=here?.log?.assessments.at(-1),activeDraft=draft?.context.scope.repository===scope.repository&&draft.context.scope.patient===scope.patient&&draft.context.scope.encounter===scope.encounter?draft:undefined;
 const model=useMemo(()=>automaticRenalModel(catalog,activeDraft?.context??last?.context),[catalog,activeDraft?.context,last?.context]);
 const historyReady=historyItems!==undefined&&!historyLoading&&!historyError;
 useEffect(()=>{if(here&&current&&!historyReady&&!historyLoading&&!historyError&&courses.length)onNeedHistory?.(courses[0]);},[keys,here?.key,current,historyReady,historyLoading,historyError]);
 function prior(c:TherapyCourse){const id=c.order?.fact.id;if(!id)return;const shared=here?.log?.assessments.flatMap(g=>g.reviews).filter(r=>r.orderId===id).at(-1)?.review,legacy=here?.legacy[id]?.saved;return shared&&(!legacy||compare(shared.savedAt,legacy.savedAt)!>=0)?shared:legacy;}
 function status(c:TherapyCourse){const id=c.order?.fact.id??c.key,saved=prior(c),edit=activeDraft?medicines[id]:undefined,selection=edit?.assessment??saved?.assessment??initialMedicineAssessment(c),deps=dependenciesFor(c,model,cultures,historyItems??[],selection),evaluation=saved?evaluateReview(saved,deps,model,c):undefined;
  const required=evaluation?.assessment??initialMedicineAssessment(c);
  const assessment=edit?evaluateReview({version:1,id:'draft',reviewer:'draft',savedAt:new Date().toISOString(),cutoff:model.scope!.cutoff,reviewEnd:model.scope!.end,assessment:edit.assessment,dependencies:edit.dependencies,evidence:model.sources},deps,model,c).assessment:evaluation?.assessment??selection;
  const dependencies=dependenciesFor(c,model,cultures,historyItems??[],assessment),result=medicationDoseReview(c.medicine,c.route,model,assessment),error=here?.error??here?.legacy[id]?.error;
  const valid=!!saved&&!!evaluation?.valid&&historyReady&&current&&!error&&!edit;
  let sameDose=false;
  if(saved&&result.status==='suggested'){try{const p=record(parseRF2JSON(saved.dependencies.patient));const old=medicationDoseReview(c.medicine,c.route,{...model,inputs:p.inputs as typeof model.inputs,context:p.context as typeof model.context,crcl:p.crcl as number,routineEligible:p.eligible===true,reasons:[]},saved.assessment);sameDose=old.status==='suggested'&&saved.dependencies.profile===dependencies.profile&&stable([old.maintenance,old.initial])===stable([result.maintenance,result.initial]);}catch{/* Current evidence still controls the candidate. */}}
  const needsAck=!valid&&(!sameDose||!!evaluation?.changed.some(g=>g!=='patient')||!!edit),acknowledged=acks[id]===stable(dependencies);
  return {id,saved,assessment,required,dependencies,result,valid,needsAck,acknowledged,error,reasons:[...error?[error]:[],...!historyReady?[historyError?'Previous-dose history is unconfirmed.':'Confirming previous-dose history…']:[],...evaluation?.reasons??[]],active:!!c.order&&!c.conflict&&record(c.order.fact).order_status==='active'};
 }
 function open(){if(!current||blocked||!here)return;const currentContext=model.context??last?.context.context??blankPatientDoseContext,context={...currentContext};if(!model.routineEligible)context.renalFunction='unknown';const legacy:Record<string,string|null>={};for(const c of courses){const cs=scopeFor(c,base);if(cs)legacy[reviewKey(cs)]=here.legacy[c.order!.fact.id]?.bytes??null;}
  setDraft({context:{id:crypto.randomUUID(),scope:{...base.scope!},context,sources:base.sources,baseContext:contextSourceIdentity(base.contextEntry)},expected:here.bytes,legacy,reviewer:last?.reviewer??courses.map(prior).find(Boolean)?.reviewer??''});setMedicines({});setAcks({});setMessage('');}
 function close(){if(!busy){setDraft(undefined);setMedicines({});setAcks({});}}
 function updateContext(context:PatientDoseContext){if(activeDraft){setDraft({...activeDraft,context:{...activeDraft.context,context}});setAcks({});}}
 function updateMedicine(c:TherapyCourse,assessment:MedicineAssessment){const s=status(c);setMedicines(old=>({...old,[s.id]:{assessment,dependencies:dependenciesFor(c,model,cultures,historyItems??[],assessment)}}));setAcks(old=>{const next={...old};delete next[s.id];return next;});}
 function acknowledge(c:TherapyCourse,yes:boolean){const s=status(c);setAcks(old=>({...old,[s.id]:yes?stable(s.dependencies):''}));}
 const draftCurrent=!!activeDraft&&model.browserAssessment?.id===activeDraft.context.id&&base.scope!.start===activeDraft.context.scope.start&&base.scope!.end===activeDraft.context.scope.end;
 const concurrent=!!activeDraft&&!!here&&(activeDraft.expected!==here.bytes||Object.entries(activeDraft.legacy).some(([k,v])=>{const id=courses.find(c=>{const cs=scopeFor(c,base);return cs&&reviewKey(cs)===k;})?.order?.fact.id;return !!id&&here.legacy[id]?.bytes!==v;}));
 const candidates=courses.filter(c=>{const s=status(c);return s.active&&!s.valid&&!s.error&&s.result.status==='suggested'&&(!s.needsAck||s.acknowledged);});
 const canSave=!!here&&!here.error&&!!activeDraft&&draftCurrent&&!concurrent&&historyReady&&current&&!blocked&&!busy&&model.routineEligible&&candidates.length>0&&!!activeDraft.reviewer.trim();
 async function save(){if(working.current||!canSave||!activeDraft||!here)return;working.current=true;setBusy(true);setMessage('');const atScope={...model.scope!},id=crypto.randomUUID(),at=new Date().toISOString();
  const selected=candidates.map(c=>({course:c,...status(c)}));const context={...activeDraft.context,id,scope:atScope};const receipt:SharedAssessment={version:1,id,reviewer:activeDraft.reviewer.trim(),savedAt:at,context,reviews:selected.map(s=>({orderId:s.id,review:{version:1,id:crypto.randomUUID(),reviewer:activeDraft.reviewer.trim(),savedAt:at,cutoff:atScope.cutoff,reviewEnd:atScope.end,assessment:{...s.assessment},dependencies:s.dependencies,evidence:model.sources}}))};
  try{const bytes=await appendSharedReview(scope,receipt,activeDraft.expected,activeDraft.legacy,()=>{
   const n=runtime.current;if(!alive.current||!n.current||n.blocked||n.historyItems===undefined||n.historyLoading||n.historyError||!n.draft)return false;
   const m=automaticRenalModel(n.catalog,n.draft.context);if(!m.routineEligible||m.browserAssessment?.id!==activeDraft.context.id||m.scope!.cutoff<atScope.cutoff||m.scope!.start!==atScope.start||m.scope!.end!==atScope.end||stable(n.draft.context)!==stable(activeDraft.context)||n.draft.reviewer!==activeDraft.reviewer)return false;
   return selected.every(s=>{const c=n.courses.find(c=>c.order?.fact.id===s.id);if(!c||c.conflict||record(c.order?.fact).order_status!=='active')return false;const a=n.medicines[s.id]?.assessment??s.assessment;const deps=dependenciesFor(c,m,n.cultures,n.historyItems!,a);return stable(a)===stable(s.assessment)&&stable(deps)===stable(s.dependencies)&&(!s.needsAck||n.acks[s.id]===stable(deps));});
  });if(alive.current){setStored({...here,bytes,log:readSharedLog(bytes,scope)});setDraft(undefined);setMedicines({});setAcks({});setMessage('Shared assessment saved in this browser. Prescriptions and administrations unchanged.');}}
  catch(error){if(alive.current)setMessage(error instanceof Error?error.message:'Shared assessment completion could not be confirmed.');}finally{working.current=false;if(alive.current)setBusy(false);}
 }
 return {base,model,status,last,open,close,opened:!!activeDraft,context:activeDraft?.context.context,updateContext,updateMedicine,acknowledge,reviewer:activeDraft?.reviewer??'',setReviewer:(reviewer:string)=>activeDraft&&setDraft({...activeDraft,reviewer}),save,canSave,busy,message,error:here?.error,concurrent,draftCurrent,historyReady,reload:()=>{close();load();},log:here?.log};
}
export type SharedDoseController=ReturnType<typeof useSharedDoseReviews>;
