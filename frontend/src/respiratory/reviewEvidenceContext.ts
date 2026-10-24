import {pin,stable,type Catalog,type Evidence} from '../api/rf2Client';
import type {MicroState} from '../api/microTypes';
import type {RenalFluidState} from '../api/renalFluidTypes';
import {renalBedsideModel} from '../renal/renalBedsideModel';
import type {CirculatoryState} from '../api/circulatoryTypes';
import {bedsideModel,exactPin,type BedsideScope} from '../hemodynamics/bedsideModel';
import {sharedPatientContext,sharedEvidencePins,uniqueSharedEvidence} from './patientContextModel';
import {compareRespiratoryInstants} from './exactTime';
/** Full exact-pin keys stay in memory. Only scope/coverage flags are persisted in signature. */
export const reviewPinSetKey=(pins:unknown[])=>stable(pins.map(p=>stable(p)).sort());
export const sameReviewPins=(a:unknown[],b:unknown[])=>reviewPinSetKey(a)===reviewPinSetKey(b);
export function reviewEvidenceIdentity(base:string,pins:unknown[],coverage:Record<string,boolean>){const signature=JSON.stringify([base,'shared-evidence/v1',coverage]);return {signature,identity:JSON.stringify([signature,reviewPinSetKey(pins)]),pins};}
export function m7ReviewEvidence(state:CirculatoryState|undefined,requested:BedsideScope,catalog?:Catalog){
 const model=bedsideModel(state,requested),shared=sharedPatientContext(catalog,requested);
 const pins=[...model.items.map(exactPin),...sharedEvidencePins(shared.evidence.filter(e=>!model.items.some(i=>i.fact.kind===e.fact.kind&&i.fact.id===e.fact.id&&i.fact.revision===e.fact.revision)))];
 return reviewEvidenceIdentity(model.signature,pins,{sharedCatalog:!!catalog&&shared.valid});
}
export function m9ReviewEvidence(catalog:Catalog|undefined,requested:BedsideScope,micro?:MicroState){
 const shared=sharedPatientContext(catalog,requested),scope=micro?.assembly.request.scope;
 const microConfirmed=!!scope&&!!catalog&&scope.repository_cutoff.repository_id===catalog.repository&&scope.repository_cutoff.fact_watermark===catalog.cutoff.fact_watermark&&scope.patient_id===requested.patient&&scope.encounter_id===requested.encounter&&compareRespiratoryInstants(scope.review_start,requested.start)===0&&compareRespiratoryInstants(scope.review_end,requested.end)===0;
 const microEvidence:Evidence[]=microConfirmed?(micro!.assembly.snapshot.items??[]).map(item=>({repository:catalog!.repository,fact:item.fact as Evidence['fact'],canonical_fact:stable(item.fact),digest:item.expected_digest,ingestion:item.ingestion as Evidence['ingestion'],cutoff:catalog!.cutoff.fact_watermark,terminal_reference:{kind:String(item.fact.kind),id:item.fact.id,version:item.fact.revision},superseded:false,metadata:null})):[];
 const evidence=uniqueSharedEvidence([...shared.evidence,...microEvidence]);
 return {...reviewEvidenceIdentity(shared.signature,sharedEvidencePins(evidence),{sharedCatalog:shared.valid,microbiology:microConfirmed}),microConfirmed,evidence};
}

/** Renal sources and the bounded shared catalog context; separate daily-fluid windows are excluded. */
export function m8ReviewEvidence(state:RenalFluidState|undefined,requested:BedsideScope,catalog?:Catalog){
 const model=renalBedsideModel(state,requested,catalog),shared=sharedPatientContext(catalog,requested);
 const pins=[...new Map([...model.sources.map(s=>s.pin),...sharedEvidencePins(shared.evidence)].map(p=>[stable(p),p])).values()];
 return reviewEvidenceIdentity(model.signature,pins,{renal:model.valid,sharedCatalog:!!catalog&&shared.valid});
}
