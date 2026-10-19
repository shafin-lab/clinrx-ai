import {useCallback,useEffect,useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryState} from '../api/circulatoryTypes';
export interface PatientEvidenceState {state?:CirculatoryState;retainedState?:CirculatoryState;loading:boolean;error:string;refresh:()=>Promise<void>}
export function usePatientEvidenceState(client:CirculatoryClient,config:{patient:string;encounter:string;start:string;end:string}):PatientEvidenceState{
 const [state,setState]=useState<CirculatoryState>(),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const generation=useRef(0),retained=useRef<CirculatoryState|undefined>(undefined);
 const refresh=useCallback(async()=>{
  const token=++generation.current;setLoading(true);setState(undefined);setError('');
  try{const reply=await client.circulatoryState(config.start,config.end);if(token!==generation.current)return;
   const scope=reply.data.assembly.request.scope;
   if(reply.data.execution_enabled!==false||scope.patient_id!==config.patient||scope.encounter_id!==config.encounter)throw Error('unconfirmed_scope_or_gate');
   retained.current=reply.data;setState(reply.data);
  }catch(error){if(token===generation.current)setError('The patient evidence or disabled execution gate could not be confirmed. Refresh to check again; no source was replaced.');throw error;}
  finally{if(token===generation.current)setLoading(false);}
 },[client,config.patient,config.encounter,config.start,config.end]);
 useEffect(()=>{void refresh().catch(()=>{});return()=>{generation.current++;};},[refresh]);
 return {state,retainedState:retained.current,loading,error,refresh};
}
