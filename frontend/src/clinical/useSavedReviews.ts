import {useCallback,useEffect,useMemo,useState} from 'react';
import {appendSavedReview,loadSavedReviews,reviewStoragePrefix,type ReviewScope,type SavedReview} from './savedReviewStore';

export function useSavedReviews<T extends object>(scope:ReviewScope|undefined){
 const key=scope?reviewStoragePrefix(scope):'';
 const domain=scope?.domain,patient=scope?.patient,encounter=scope?.encounter,repository=scope?.repository;
 const [loadedKey,setLoadedKey]=useState(''),[reviews,setReviews]=useState<SavedReview<T>[]>([]),[issue,setIssue]=useState('');
 const refresh=useCallback(()=>{
  if(!domain||!patient||!encounter||!repository){setReviews([]);setIssue('');setLoadedKey('');return;}
  const result=loadSavedReviews<T>({domain,patient,encounter,repository});setReviews(result.reviews);setIssue(result.issue??'');setLoadedKey(key);
 },[domain,encounter,key,patient,repository]);
 useEffect(()=>{refresh();if(!key)return;const onStorage=(event:StorageEvent)=>{if(event.key?.startsWith(key))refresh();};window.addEventListener('storage',onStorage);return()=>window.removeEventListener('storage',onStorage);},[key,refresh]);
 const save=useCallback(async(review:SavedReview<T>,stillCurrent:()=>boolean)=>{
  if(!scope)throw new Error('Patient evidence scope is unavailable. No review was saved.');
  await appendSavedReview(scope,review,stillCurrent);refresh();
 },[domain,encounter,patient,refresh,repository]);
 return useMemo(()=>({reviews:loadedKey===key?reviews:[],issue:loadedKey===key?issue:'',save,ready:loadedKey===key}),[issue,key,loadedKey,reviews,save]);
}
