// Response types come from the same backend-derived contracts used at the transport boundary.
import type {Decoded} from './decoding';
export type ExactReference=Decoded<'ExactReference'>;
export type Cutoff=Decoded<'CutoffView'>;
export type Scope=Decoded<'ScopeView'>;
export type Source=Decoded<'SourceView'>;
export type Times=Decoded<'TimesView'>;
export type Quantity=Decoded<'QuantityView'>;
export type Evidence=Laboratory|Medication;
export type Laboratory=Decoded<'LaboratoryView'>;
export type Medication=Decoded<'MedicationView'>;
export type Coverage=Decoded<'CoverageView'>;
export type Domain=Coverage['domain'];
export type MappingIssue=Decoded<'MappingIssueView'>;
export type PatientState=Decoded<'PatientStateViewResponse'>;
export interface Pin { reference:ExactReference; expected_digest:string }
export interface PreparationRequest { execution_id:string; state_context:string; earlier_laboratory:Pin; later_laboratory:Pin; medication:Pin }
export type Prepared=Decoded<'PreparedTemporalReviewResponse'>;
export type Inference=Decoded<'InferenceView'>;
export type Provenance=Decoded<'ProvenanceView'>;
export type Governance=Decoded<'GovernanceView'>;
export type Execution=Decoded<'TemporalExecutionResponse'>;
export type Reconciliation=Decoded<'ReconciliationResponse'>;
export interface CompletionUnknown { status:'completion_unknown'; execution_id:string; next_action:'reconcile'; automatic_retry:false; correlation_id:string }
export interface FieldError { path:string; code:'missing'|'extra_forbidden'|'invalid_type'|'invalid_value'|'too_long' }
export interface ApiError { code:string; message:string; correlation_id:string; fields:FieldError[] }
