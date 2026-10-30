import {AntibioticClient,type AntibioticBundle} from '../api/antibioticClient';
import {RF2Client,type Catalog} from '../api/rf2Client';
import {RenalFluidClient} from '../api/renalFluidClient';
import type {RenalFluidState} from '../api/renalFluidTypes';
import {useCallback,useEffect,useRef,useState} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import type {CirculatoryState} from '../api/circulatoryTypes';
import {M10Client,matchesM10Snapshot} from '../transfusion/client';
import type {M10Read} from '../transfusion/types';
export interface PatientEvidenceState {antibiotics?:AntibioticBundle;antibioticError?:string;rf2?:Catalog;retainedRF2?:Catalog;state?:CirculatoryState;renalFluid?:RenalFluidState;retainedState?:CirculatoryState;m10:M10Read;loading:boolean;error:string;refresh:()=>Promise<void>}
export function usePatientEvidenceState(client:CirculatoryClient,config:{patient:string;encounter:string;start:string;end:string}):PatientEvidenceState{
 const [antibiotics,setAntibiotics]=useState<AntibioticBundle>();const [antibioticError,setAntibioticError]=useState('');
 const [rf2,setRF2]=useState<Catalog>();const retainedRF2=useRef<Catalog|undefined>(undefined);const [renalFluid,setRenalFluid]=useState<RenalFluidState>();
 const [state,setState]=useState<CirculatoryState>(),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [m10Client]=useState(()=>new M10Client()),[m10,setM10]=useState<M10Read>({loading:import.meta.env.VITE_SYNTHETIC_M10==='true'});
 const generation=useRef(0),retained=useRef<CirculatoryState|undefined>(undefined);
 const refresh=useCallback(async()=>{
  const m10Enabled=import.meta.env.VITE_SYNTHETIC_M10==='true';
  const token=++generation.current;setLoading(true);setM10({loading:m10Enabled});setAntibiotics(undefined);setAntibioticError('');setState(undefined);setRenalFluid(undefined);setRF2(undefined);setError('');
  let abx:AntibioticBundle|undefined,catalog:Catalog|undefined,abxFailure='';
  if(import.meta.env.VITE_SYNTHETIC_ANTIBIOTICS==='true')try{abx=await new AntibioticClient().catalog(config.start,config.end);}catch{abxFailure='The antibiotic patient bundle is unavailable. Antibiotic review, culture matching and source actions are blocked until it can be confirmed.';}
  const rf2Enabled=import.meta.env.VITE_SYNTHETIC_RF2==='true';
  if(!abx&&rf2Enabled)try{catalog=await new RF2Client().catalog(config.start,config.end);}catch{/* Core circulatory retrieval can still be checked independently. */}
  if(abx)catalog=abx.renal;
  let renalFluid:RenalFluidState|undefined;
  let reply:{data:CirculatoryState}|undefined;
  try{
   if(catalog)renalFluid=catalog.combined;
   else if(client instanceof RenalFluidClient&&!rf2Enabled)try{renalFluid=(await client.combinedState(config.start,config.end)).data;}catch{/* M7 remains independently available through circulatoryState. */}
   if(renalFluid)reply={data:renalFluid.circulatory};else reply=await client.circulatoryState(config.start,config.end);
   const scope=reply.data.assembly.request.scope;
   if(reply.data.execution_enabled!==false||scope.patient_id!==config.patient||scope.encounter_id!==config.encounter)throw Error('unconfirmed_scope_or_gate');
   if(renalFluid){const combinedScope=renalFluid.context.scope;if(renalFluid.execution_enabled!==false||combinedScope.patient_id!==config.patient||combinedScope.encounter_id!==config.encounter||combinedScope.repository_cutoff.repository_id!==scope.repository_cutoff.repository_id||JSON.stringify(combinedScope.repository_cutoff)!==JSON.stringify(scope.repository_cutoff))throw Error('unconfirmed_renal_scope_or_cutoff');}
   if(token!==generation.current)return;
   if(abx)setAntibiotics(abx);else if(abxFailure)setAntibioticError(abxFailure);
   if(catalog){setRF2(catalog);retainedRF2.current=catalog;}retained.current=reply.data;setState(reply.data);setRenalFluid(renalFluid);
   setLoading(false);
   if(m10Enabled){
    try{
     if(!catalog||catalog.repository!==scope.repository_cutoff.repository_id||catalog.cutoff.fact_watermark!==scope.repository_cutoff.fact_watermark||catalog.execution_enabled!==false)throw Error('unconfirmed_m10_scope');
     const readScope={repository:catalog.repository,cutoff:catalog.cutoff.fact_watermark},snapshot=await m10Client.catalog(config.start,config.end,readScope);
     if(!matchesM10Snapshot(snapshot,config,readScope,true))throw Error('unconfirmed_m10_scope');
     if(token===generation.current)setM10({snapshot,loading:false});
    }catch{if(token===generation.current)setM10({loading:false,error:'The hematologic evidence read is unconfirmed or unavailable. Recording and interpretation are blocked until refresh confirms it.'});}
   }
  }catch{
   if(token===generation.current){if(m10Enabled)setM10({loading:false,error:'Shared patient evidence is unconfirmed; hematologic actions are unavailable.'});if(abxFailure)setAntibioticError(abxFailure);setError('The patient evidence or disabled execution gate could not be confirmed. Refresh to check again; no source was replaced.');}
   throw Error('patient_evidence_unconfirmed');
  }finally{if(token===generation.current)setLoading(false);}
 },[client,m10Client,config.patient,config.encounter,config.start,config.end]);
 useEffect(()=>{void refresh().catch(()=>{});return()=>{generation.current++;};},[refresh]);
 return {antibiotics,antibioticError,rf2,retainedRF2:retainedRF2.current,state,renalFluid,retainedState:retained.current,m10,loading,error,refresh};
}
