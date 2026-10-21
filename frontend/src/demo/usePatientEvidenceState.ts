import {AntibioticClient,type AntibioticBundle} from '../api/antibioticClient';
import {RF2Client,type Catalog} from '../api/rf2Client';
import {RenalFluidClient} from '../api/renalFluidClient';
import type {RenalFluidState} from '../api/renalFluidTypes';
import {useCallback,useEffect,useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryState} from '../api/circulatoryTypes';
export interface PatientEvidenceState {antibiotics?:AntibioticBundle;rf2?:Catalog;retainedRF2?:Catalog;state?:CirculatoryState;renalFluid?:RenalFluidState;retainedState?:CirculatoryState;loading:boolean;error:string;refresh:()=>Promise<void>}
export function usePatientEvidenceState(client:CirculatoryClient,config:{patient:string;encounter:string;start:string;end:string}):PatientEvidenceState{
 const [antibiotics,setAntibiotics]=useState<AntibioticBundle>();
 const [rf2,setRF2]=useState<Catalog>();const retainedRF2=useRef<Catalog|undefined>(undefined);
 const [renalFluid,setRenalFluid]=useState<RenalFluidState>();
 const [state,setState]=useState<CirculatoryState>(),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const generation=useRef(0),retained=useRef<CirculatoryState|undefined>(undefined);
 const refresh=useCallback(async()=>{
  const token=++generation.current;setLoading(true);setAntibiotics(undefined);setState(undefined);setRenalFluid(undefined);setRF2(undefined);setError('');
  try{const abx=import.meta.env.VITE_SYNTHETIC_ANTIBIOTICS==='true'?await new AntibioticClient().catalog(config.start,config.end):undefined;const catalog=abx?abx.renal:import.meta.env.VITE_SYNTHETIC_RF2==='true'?await new RF2Client().catalog(config.start,config.end):undefined;const combined=catalog?{data:catalog.combined}:client instanceof RenalFluidClient?await client.combinedState(config.start,config.end):undefined;const reply=combined?{...combined,data:combined.data.circulatory}:await client.circulatoryState(config.start,config.end);if(token!==generation.current)return;
   const scope=reply.data.assembly.request.scope;
   if(reply.data.execution_enabled!==false||scope.patient_id!==config.patient||scope.encounter_id!==config.encounter)throw Error('unconfirmed_scope_or_gate');
   if(abx)setAntibiotics(abx);if(catalog){setRF2(catalog);retainedRF2.current=catalog;}retained.current=reply.data;setState(reply.data);setRenalFluid(combined?.data);
  }catch(error){if(token===generation.current)setError('The patient evidence or disabled execution gate could not be confirmed. Refresh to check again; no source was replaced.');throw error;}
  finally{if(token===generation.current)setLoading(false);}
 },[client,config.patient,config.encounter,config.start,config.end]);
 useEffect(()=>{void refresh().catch(()=>{});return()=>{generation.current++;};},[refresh]);
 return {antibiotics,rf2,retainedRF2:retainedRF2.current,state,renalFluid,retainedState:retained.current,loading,error,refresh};
}
