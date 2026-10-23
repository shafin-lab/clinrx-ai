import {useEffect,useRef,useState} from 'react';
import type {CirculatoryState} from '../api/circulatoryTypes';
import type {HandoverSelection} from './HandoverReview';
import {decodeSavedHandover,handoverScope,handoverStorageKey,pinKey,resolveHandover,selectionPin,type HandoverPin,type SavedHandover} from './localHandover';
export function useLocalHandover(state:CirculatoryState|undefined){
 const key=state&&state.execution_enabled===false?handoverStorageKey(state):undefined;
 const [activeKey,setActiveKey]=useState<string>(),[selections,setSelections]=useState<HandoverSelection[]>([]),[unavailable,setUnavailable]=useState<HandoverPin[]>([]);
 const [message,setMessage]=useState(''),[error,setError]=useState(''),[dirty,setDirty]=useState(false);
 const initialized=useRef<string|undefined>(undefined),lastRaw=useRef<string|null>(null);
 useEffect(()=>{
  if(!key||!state||initialized.current===key)return;initialized.current=key;lastRaw.current=null;setActiveKey(key);setSelections([]);setUnavailable([]);setDirty(false);setMessage('');setError('');
  try{const raw=window.localStorage.getItem(key);lastRaw.current=raw;if(raw!==null){const saved=decodeSavedHandover(raw,state),resolved=resolveHandover(saved.pins,state);setSelections(resolved.selections);setUnavailable(resolved.unavailable);setMessage('Restored saved handover: '+saved.pins.length+' selection(s). Saved '+saved.savedAt+'.');}}
  catch{setError('Saved handover could not be restored. No saved data was changed. Newly selected records can be saved as an explicit replacement.');}
 },[key,state]);
 const ready=!!key&&activeKey===key;
 function change(next:HandoverSelection[]){if(!ready)return;setSelections(next);setUnavailable(old=>old.filter(p=>!next.some(s=>pinKey(selectionPin(s))===pinKey(p))));setDirty(true);setMessage('Unsaved handover changes. Save locally before reloading.');}
 function removeUnavailable(p:HandoverPin){if(!ready)return;setUnavailable(old=>old.filter(i=>pinKey(i)!==pinKey(p)));setDirty(true);setMessage('Unsaved handover changes. Save locally before reloading.');}
 function save(){
  if(!ready||!state||state.execution_enabled!==false)return;setError('');setMessage('');
  const pins=[...selections.map(selectionPin),...unavailable];
  try{if(pins.length>32)throw Error('limit');if(window.localStorage.getItem(key!)!==lastRaw.current){setError('The saved handover changed in another tab. Current selections are still in memory. Reload to read the saved version before replacing it.');return;}
   const saved:SavedHandover={version:1,...handoverScope(state),savedAt:new Date().toISOString(),pins};const raw=JSON.stringify(saved);decodeSavedHandover(raw,state);window.localStorage.setItem(key!,raw);if(window.localStorage.getItem(key!)!==raw)throw Error('readback');lastRaw.current=raw;setDirty(false);setMessage('Saved locally in this browser: '+pins.length+' selection(s). They will be restored after reload.');
  }catch{setError('Handover was not confirmed saved. Keep this page open; current selections remain in memory. Browser storage may be unavailable or the 32-selection limit exceeded.');}
 }
 return {selections:ready?selections:[],unavailable:ready?unavailable:[],change,removeUnavailable,save,ready,message:ready?message:'',error:ready?error:'',dirty,hasSaved:ready&&lastRaw.current!==null&&!error};
}
