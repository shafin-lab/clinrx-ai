import type {Decoded} from './decoding';
import type {Pin} from './types';
export type Role='S'|'I'|'U'|'D';
export type RecordedTime=Decoded<'RecordedTime'>;
export type Concept=Decoded<'RecordedConcept'>;
export type RecordedQuantity=Decoded<'PositiveQuantity'>|Decoded<'NonnegativeQuantity'>;
export type Identity=Decoded<'AntimicrobialIdentity'>;
export type Binding=Decoded<'DomainBinding'>;
export type Item=Decoded<'RetainedStateItemV2'>;
export type MicroState=Decoded<'MicroStateResponse'>;
export type MicroInference=Decoded<'ClinicalInference'>;
export interface MicroPreparation { execution_id:string; state_context:string; specimen_ref:Pin; isolate_ref:Pin; susceptibility_ref:Pin; administration_ref:Pin }
export type MicroPrepared=Decoded<'MicroPreparedResponse'>;
export type Witness=Decoded<'MicroAntimicrobialEvidenceWitness'>;
export type MicroExecution=Decoded<'MicroExecutionResponse'>;
export type MicroReconciliation=Decoded<'MicroReconciliationResponse'>;
// Read-only presentation of variant fields. Every field type is derived from the wire union;
// optional fields remain optional, and this view neither adds nor transforms received data.
type UnionKeys<U>=U extends unknown?keyof U:never;
type Value<U,K>=U extends unknown?K extends keyof U?U[K]:never:never;
type Fields<U>={[K in UnionKeys<U> as [U] extends [Record<K,unknown>]?K:never]:Value<U,K>}
  & {[K in UnionKeys<U> as [U] extends [Record<K,unknown>]?never:K]?:Value<U,K>};
export type Fact=Fields<Item['fact']|MicroExecution['provenance']['final_recheck']['terminal_facts'][number]>;
