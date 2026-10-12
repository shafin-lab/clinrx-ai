// M5.2 transport only: numeric clinical representations remain opaque strings.
export interface ExactReference { kind: string; id: string; version: string }
export interface Cutoff { repository_id: string; fact_watermark: number; captured_at: string }
export interface Scope { patient_id: string; encounter_id: string; review_start: string; review_end: string; repository_cutoff: Cutoff }
export interface Source { namespace: string; identifier: string; version: string | null; channel: string }
export interface Times { event: string | null; effective_start: string | null; effective_end: string | null; recorded: string | null; retrieved: string | null; processed: string | null; precision: string; uncertainty: string | null }
export interface Quantity { value: string; unit_raw: string; unit_code: string | null; unit_system: string | null; unit_status: string }
export interface Evidence { reference: ExactReference; selection_digest: string; time: Times; source: Source; origin: 'observed' | 'reported'; verification: string; conflict: string; temporal_status: string; provenance_recorded_at: string; provenance_actor: string | null; provenance_limitations: string[]; provenance_completeness: string; ingested_at: string; disclosures: string[] }
export interface Laboratory extends Evidence { domain: 'laboratory'; concept_id: string; quantity: Quantity }
export interface Medication extends Evidence { domain: 'medication'; event_type: 'medication_order' | 'medication_administration'; product_id: string | null; ingredient_ids: string[]; formulation: string | null; status: string; dose: Quantity | null; dose_basis: string | null; route: string | null; schedule_text: string | null; frequency_occurrences: number | null; frequency_interval: Quantity | null }
export type Domain = 'laboratory' | 'medication' | 'antimicrobial' | 'hemodynamic_support' | 'respiratory_support' | 'renal_support' | 'fluid_output' | 'microbiology' | 'procedure' | 'history_event';
export interface Coverage { domain: Domain; mapping_support: 'supported' | 'partial' | 'unsupported'; retrieval: 'completed' | 'not_attempted'; candidate_count: number | null; retained_count: number | null; unsuitable_count: number | null; source_completeness: 'unknown'; limitations: string[] }
export interface MappingIssue { reference: ExactReference; domain: 'laboratory' | 'medication' | null; reason: string }
export interface PatientState { transport_version: '1'; scope: Scope; state_context: string; profile_id: 'SyntheticLaboratoryMedicationState'; profile_version: '1'; laboratory: Laboratory[]; medication: Medication[]; coverage: Coverage[]; issues: MappingIssue[]; disclosures: string[] }
export interface Pin { reference: ExactReference; expected_digest: string }
export interface PreparationRequest { execution_id: string; state_context: string; earlier_laboratory: Pin; later_laboratory: Pin; medication: Pin }
export interface Prepared { status: 'prepared'; execution_id: string; inference_reference: ExactReference; command: string }
export interface Inference { reference: ExactReference; method: ExactReference; statement: string | null; applicability: string; uncertainty: string[]; limitations: string[]; inputs: [ExactReference, ExactReference, ExactReference] }
export interface Provenance { inference: Inference; earlier_laboratory: Laboratory; later_laboratory: Laboratory; medication: Medication; terminal_references: [ExactReference, ExactReference, ExactReference]; inference_terminal_reference: ExactReference; direct_dependencies: {target: ExactReference; relationship: 'derived_from'}[]; input_cutoff: Cutoff; inference_cutoff: Cutoff; final_cutoff: Cutoff; final_recheck: 'unchanged' | 'materially_changed' | 'unavailable'; recheck_reasons: string[] }
export interface Governance { outcome: 'released' | 'withheld'; decision_reference: ExactReference; decided_at: string; assessed_at?: string | null; reasons: string[]; safety_status: string; fidelity_status: string; freshness_status: string; authority_status: string; limitations: string[] }
export interface Execution { transport_version: '1'; execution_id: string; status: 'completed'; finalized_at: string; ingested_at: string; context: {reference: ExactReference; completeness: 'partial'; evidence_references: [ExactReference, ExactReference, ExactReference, ExactReference]; limitations: string[]}; governance: Governance; provenance: Provenance }
export type Reconciliation = { status: 'committed_match'; execution: Execution } | { status: 'absent'; execution: null };
export interface CompletionUnknown { status: 'completion_unknown'; execution_id: string; next_action: 'reconcile'; automatic_retry: false; correlation_id: string }
export interface FieldError { path: string; code: 'missing' | 'extra_forbidden' | 'invalid_type' | 'invalid_value' | 'too_long' }
export interface ApiError { code: string; message: string; correlation_id: string; fields: FieldError[] }
