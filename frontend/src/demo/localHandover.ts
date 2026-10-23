import type {CirculatoryState,ExactRef} from '../api/circulatoryTypes';
import type {HandoverSelection} from './HandoverReview';
export interface HandoverPin {reference:ExactRef;digest:string;cutoff:number;ingestion:number}
export interface SavedHandover {version:1;repository:string;patient:string;encounter:string;savedAt:string;pins:HandoverPin[]}
export const pinKey=(p:HandoverPin)=>JSON.stringify([p.reference.kind,p.reference.id,p.reference.version]);
export function handoverScope(state:CirculatoryState){const s=state.assembly.request.scope;return {repository:s.repository_cutoff.repository_id,patient:s.patient_id,encounter:s.encounter_id};}
export function handoverStorageKey(state:CirculatoryState){const s=handoverScope(state);return 'clinrx.synthetic.handover.v1:'+JSON.stringify([s.repository,s.patient,s.encounter]);}
export function selectionPin(selection:HandoverSelection):HandoverPin{const i=selection.item;return {reference:{kind:i.fact.kind,id:i.fact.id,version:i.fact.revision},digest:i.expected_digest,cutoff:selection.cutoff,ingestion:i.ingestion.ingestion_sequence};}
export function decodeSavedHandover(raw:string,state:CirculatoryState):SavedHandover{
 if(raw.length>131072)throw Error('handover_bounds');
 const v=JSON.parse(raw) as SavedHandover,s=handoverScope(state);
 // Only accept the exact serialization emitted by this bounded local format. This also rejects duplicate JSON members.
 if(JSON.stringify(v)!==raw||!v||v.version!==1||Object.keys(v).sort().join()!=='encounter,patient,pins,repository,savedAt,version'||v.repository!==s.repository||v.patient!==s.patient||v.encounter!==s.encounter||typeof v.savedAt!=='string'||!Number.isFinite(Date.parse(v.savedAt))||!Array.isArray(v.pins)||v.pins.length>32)throw Error('handover_shape');
 const keys=new Set<string>();
 for(const p of v.pins){
  if(!p||Object.keys(p).sort().join()!=='cutoff,digest,ingestion,reference'||!p.reference||Object.keys(p.reference).sort().join()!=='id,kind,version'||!Object.values(p.reference).every(x=>typeof x==='string'&&x.length>0&&x.length<=2048)||!/^circulatory_/.test(p.reference.kind)||typeof p.digest!=='string'||!/^[a-f0-9]{64}$/.test(p.digest)||!Number.isSafeInteger(p.cutoff)||!Number.isSafeInteger(p.ingestion)||p.ingestion<1||p.cutoff<p.ingestion||keys.has(pinKey(p)))throw Error('handover_pin');keys.add(pinKey(p));
 }
 return v;
}
export function resolveHandover(pins:HandoverPin[],state:CirculatoryState){
 const selections:HandoverSelection[]=[],unavailable:HandoverPin[]=[];const scope=state.assembly.request.scope;
 for(const p of pins){const matches=state.assembly.snapshot.items.filter(i=>i.fact.kind===p.reference.kind&&i.fact.id===p.reference.id&&i.fact.revision===p.reference.version&&i.expected_digest===p.digest&&i.ingestion.repository_id===scope.repository_cutoff.repository_id&&i.ingestion.ingestion_sequence===p.ingestion&&i.fact.binding.target.patient_id===scope.patient_id&&i.fact.binding.target.encounter_id===scope.encounter_id);
  if(p.cutoff<=scope.repository_cutoff.fact_watermark&&matches.length===1)selections.push({item:matches[0],repository:scope.repository_cutoff.repository_id,cutoff:p.cutoff});else unavailable.push(p);
 }
 return {selections,unavailable};
}
