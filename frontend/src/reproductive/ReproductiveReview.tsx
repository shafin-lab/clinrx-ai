import {useRef,useState,type FormEvent} from 'react';
import {useSavedReviews} from '../clinical/useSavedReviews';
import type {ReviewScope,SavedReview} from '../clinical/savedReviewStore';
import type {Catalog} from '../api/rf2Client';
import type {reproductiveModel,ReproductiveScope} from './model';

type Draft={reviewer:string;rationale:string;plan:string;nextReview:string};
const blank=():Draft=>({reviewer:'',rationale:'',plan:'',nextReview:''});
export function useReproductiveReview(catalog:Catalog|undefined,requested:ReproductiveScope){
 const scope:ReviewScope|undefined=catalog?{domain:'M12',patient:requested.patient,encounter:requested.encounter,repository:catalog.repository}:undefined;
 return {scope,...useSavedReviews<Draft>(scope)};
}

export function ReproductiveReview({catalog,requested,model,current,saved}:{
 catalog?:Catalog;requested:ReproductiveScope;model:ReturnType<typeof reproductiveModel>;
 current:boolean;saved:ReturnType<typeof useReproductiveReview>;
}){
 const [draft,setDraft]=useState(blank),[started,setStarted]=useState(''),[busy,setBusy]=useState(false);
 const [status,setStatus]=useState(''),[error,setError]=useState('');
 const latest=useRef({current,identity:model.identity}),saving=useRef(false);
 latest.current={current,identity:model.identity};
 function change(field:keyof Draft,value:string){
  if(!started)setStarted(model.identity);
  setDraft(previous=>({...previous,[field]:value}));setStatus('');setError('');
 }
 async function submit(event:FormEvent){
  event.preventDefault();
  if(saving.current)return;
  setStatus('');setError('');
  const scope=saved.scope;
  if(!current||!scope||!catalog||started!==model.identity||!model.pins.length){
   setError('Review the current source records before saving.');return;
  }
  if(!draft.reviewer.trim()||!draft.rationale.trim()||!draft.nextReview.trim()){
   setError('Enter the reviewer, assessment and next review.');return;
  }
  if(model.pins.length>500){setError('The evidence set exceeds the browser review limit.');return;}
  const review:SavedReview<Draft>={...scope,format:'clinrx-local-review',version:1,id:crypto.randomUUID(),
   period:{start:requested.start,end:requested.end},snapshot:{signature:model.signature,cutoff:catalog.cutoff,pins:model.pins},
   draft,recordedAt:new Date().toISOString()};
  saving.current=true;setBusy(true);
  try{
   await saved.save(review,()=>latest.current.current&&latest.current.identity===started);
   setDraft(blank());setStarted('');setStatus('Review saved');
  }catch(e){setError(e instanceof Error?e.message:'Review storage could not confirm the save.');}
  finally{saving.current=false;setBusy(false);}
 }
 return <section className="m12-card" aria-label="Obstetric and gynecology review">
  <h3>Review &amp; plan</h3>
  <form onSubmit={event=>void submit(event)}>
   <fieldset disabled={!current||!model.pins.length||busy||!saved.ready}>
    <div className="m12-form">
     <label>Reviewer<input maxLength={120} value={draft.reviewer} onChange={e=>change('reviewer',e.target.value)}/></label>
     <label>Next review<input maxLength={250} value={draft.nextReview} onChange={e=>change('nextReview',e.target.value)}/></label>
     <label className="m12-wide">Assessment<textarea maxLength={2000} value={draft.rationale} onChange={e=>change('rationale',e.target.value)}/></label>
     <label className="m12-wide">Plan &amp; missing information<textarea maxLength={2000} value={draft.plan} onChange={e=>change('plan',e.target.value)}/></label>
    </div>
    <button type="submit" className="m12-primary" disabled={!!started&&started!==model.identity}>{busy?'Saving…':'Save review'}</button>
    {started&&<button type="button" onClick={()=>{setDraft(blank());setStarted('');setError('');}}>Clear draft</button>}
   </fieldset>
  </form>
  {started&&started!==model.identity&&<p role="alert">Evidence changed after this draft began. Clear the draft and review the new sources.</p>}
  {(error||saved.issue)&&<p role="alert">{error||saved.issue}</p>}
  {status&&<p role="status">{status}</p>}
  <h3>Saved reviews</h3>
  {!saved.reviews.length&&<p>No review saved in this browser for this encounter.</p>}
  {saved.reviews.map(review=><article className="m12-row" key={review.id}>
   <strong>{current&&model.matches(review)?'Matches current evidence':'Historical evidence review'}</strong>
   <p>{review.draft.rationale}</p>{review.draft.plan&&<p>{review.draft.plan}</p>}
   <small>{review.draft.reviewer} · Next review {review.draft.nextReview} · Saved {review.recordedAt}</small>
   <details><summary>Reviewed source revisions</summary><pre>{JSON.stringify(review.snapshot.pins,null,2)}</pre></details>
  </article>)}
  <small>Reviews are saved in this browser.</small>
 </section>;
}
