import {afterEach,expect,it,vi} from 'vitest';
import {loadSavedReviews,appendSavedReview,reviewStoragePrefix,type SavedReview,type ReviewScope,type ReviewLockManager} from '../src/clinical/savedReviewStore';

const scope:ReviewScope={domain:'M7',patient:'synthetic-p1',encounter:'synthetic-e1',repository:'repo-a'};
function review(id:string,overrides:Partial<SavedReview<{action:string;reviewer:string;rationale:string;nextReview:string}>>={}):SavedReview<{action:string;reviewer:string;rationale:string;nextReview:string}>{
 return {format:'clinrx-local-review',version:1,id,domain:scope.domain,patient:scope.patient,encounter:scope.encounter,repository:scope.repository,period:{start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'},snapshot:{signature:'snapshot-a',cutoff:{repository_id:'repo-a',fact_watermark:12,captured_at:'2026-10-08T10:00:00Z'},pins:[{reference:{kind:'circulatory_pressure',id:'map-1',version:'2'},expected_digest:'a'.repeat(64)}]},draft:{action:'review_pressure',reviewer:'Test reviewer',rationale:'Source review',nextReview:'After next sample'},recordedAt:'2026-10-08T10:01:00Z',...overrides};
}
function locks():ReviewLockManager{let tail=Promise.resolve();return {request:async(_name,callback)=>{const current=tail.then(callback);tail=current.then(()=>undefined,()=>undefined);return current;}};}
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();});

it('appends a completed review and restores it after a fresh read without replacing its evidence pins',async()=>{
 const saved=review('review-a');
 await appendSavedReview(scope,saved,()=>true,{storage:localStorage,locks:locks()});
 const restored=loadSavedReviews(scope,localStorage);
 expect(restored.reviews).toEqual([saved]);
 expect(localStorage.getItem(reviewStoragePrefix(scope)+'review-a')).toContain('map-1');
});

it('isolates saved reviews by domain, patient, encounter and repository',async()=>{
 await appendSavedReview(scope,review('review-a'),()=>true,{storage:localStorage,locks:locks()});
 for(const other of [{...scope,domain:'M8' as const},{...scope,patient:'synthetic-p2'},{...scope,encounter:'synthetic-e2'},{...scope,repository:'repo-b'}]){
  expect(loadSavedReviews(other,localStorage).reviews).toEqual([]);
 }
});

it('serializes concurrent appends and rejects a duplicate identifier without overwriting its first record',async()=>{
 const manager=locks(),first=review('same-id'),second=review('same-id',{snapshot:{...first.snapshot,signature:'snapshot-b'}});
 const outcomes=await Promise.allSettled([appendSavedReview(scope,first,()=>true,{storage:localStorage,locks:manager}),appendSavedReview(scope,second,()=>true,{storage:localStorage,locks:manager})]);
 expect(outcomes.filter(result=>result.status==='fulfilled')).toHaveLength(1);
 expect(loadSavedReviews(scope,localStorage).reviews).toEqual([first]);
});

it('checks the evidence snapshot after acquiring the lock before writing',async()=>{
 await expect(appendSavedReview(scope,review('review-a'),()=>false,{storage:localStorage,locks:locks()})).rejects.toThrow(/evidence changed/i);
 expect(loadSavedReviews(scope,localStorage).reviews).toEqual([]);
});

it('preserves corrupt or incompatible records and reports them instead of clearing storage',()=>{
 const key=reviewStoragePrefix(scope)+'broken',raw='{"version":1,"version":2}';localStorage.setItem(key,raw);
 const result=loadSavedReviews(scope,localStorage);
 expect(result.reviews).toEqual([]);expect(result.issue).toBeTruthy();expect(localStorage.getItem(key)).toBe(raw);
});

it('reports storage write failure without returning a saved review',async()=>{
 let writes=0;const storage={length:0,key:()=>null,getItem:()=>null,setItem:()=>{writes++;throw new DOMException('quota','QuotaExceededError');}};
 const outcome=appendSavedReview(scope,review('review-a'),()=>true,{storage,locks:locks()});
 await expect(outcome).rejects.toThrow(/storage/i);
 expect(writes).toBe(1);
});
