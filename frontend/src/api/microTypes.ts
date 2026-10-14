import type { ExactReference, Cutoff, Scope, Pin, Governance } from './types';
export type Role = 'S'|'I'|'U'|'D';
export interface RecordedTime { status:string; precision:string; value:string|null; lower:string|null; upper:string|null }
export interface Concept { raw_display:string|null }
export interface RecordedQuantity { value:string; unit:{raw:string; status:string} }
export interface Identity { raw_display:string; canonical_id:string|null; mapping_status:string; source_code:{code:string; version:string|null}; ingredient_ids:string[] }
export interface Binding { role:string; status:string; exact:ExactReference|null; candidates:ExactReference[] }
export interface Fact {
  kind:string; id:string; revision:string; origin:string; verification:string; conflict:string;
  provenance:{source:{namespace:string; identifier:string; version:string|null}; recorded_at:string; limitations:string[]};
  domain_bindings:Binding[]; uncertainty:string[]; correction_reason:string|null;
  collected?:RecordedTime; received?:RecordedTime; administered?:RecordedTime; occurred?:RecordedTime; created?:RecordedTime;
  report?:{status:string; change:string; reported:RecordedTime; available:RecordedTime};
  specimen_type?:Concept; organism?:Concept; identification_state?:string; result_status?:string;
  antimicrobial?:Identity; administered_dose?:{amount:RecordedQuantity; basis:string}; prescribed_dose?:{amount:RecordedQuantity; basis:string};
  mic?:{comparator:string; quantity:RecordedQuantity}|null; interpretation?:{raw:string|null; category:string}|null;
  order_status?:string; status?:string; result?:string; growth?:string; target?:Concept; examination_type?:string;
}
export interface Item { fact:Fact; expected_digest:string; inclusion:string; contextual_for:ExactReference[]; disclosures:string[]; ingestion:{ingested_at:string; ingestion_sequence:number}|null }
export interface MicroState {
  state_context:string;
  assembly:{request:{profile_id:string; profile_version:string; scope:Scope}; bindings:{owner:ExactReference; role:string; status:string; disposition:string; declared:ExactReference|null; candidates:ExactReference[]}[];
    snapshot:{items:Item[]; disclosures:string[]; coverage:{domain:string; mapping_support:string; retrieval:string; limitations:string[]}[]; issues:{reference:ExactReference; reason:string}[];
      microbiology:{references:ExactReference[]; specimens:{specimen:ExactReference; examinations:ExactReference[]; cultures:ExactReference[]; isolates:ExactReference[]; molecular_results:ExactReference[]}[]; isolates:{isolate:ExactReference; susceptibilities:ExactReference[]; resistance_findings:ExactReference[]}[]};
      antimicrobial:{orders:ExactReference[]; administrations:ExactReference[]; non_delivery:ExactReference[]}}};
}
export interface MicroInference { kind:string; id:string; revision:string; method:ExactReference; statement:string; applicability:string; validation_limitations:string; uncertainty:string[]; inputs:ExactReference[]; provenance:{limitations:string[]; upstream:{target:ExactReference; relationship:string}[]} }
export interface MicroPreparation { execution_id:string; state_context:string; specimen_ref:Pin; isolate_ref:Pin; susceptibility_ref:Pin; administration_ref:Pin }
export interface MicroPrepared { status:'prepared'; execution_id:string; inference:MicroInference; command:string }
export interface Witness { role:Role; consumed:ExactReference; terminal:ExactReference; source_digest:string; terminal_source_digest:string; item_digest:string; suitability:string }
export interface MicroExecution { status:'completed'; execution_id:string; statement:string|null; finalized_at:string; ingested_at:string; governance:Governance;
  provenance:{inference:MicroInference; consumed:Item[]; original_cutoff:Cutoff; inference_cutoff:Cutoff; witness_statuses:('current'|'superseded')[]; governance_policy:ExactReference;
    final_recheck:{final_cutoff:Cutoff; evidence:Witness[]; terminal_facts:Fact[]}; specimen_binding_matches:boolean; isolate_binding_matches:boolean; antimicrobial_identity_matches:boolean; recheck_reasons:string[]}}
export type MicroReconciliation = {status:'absent';execution:null}|{status:'committed_match';execution:MicroExecution};
