export interface ExactRef {kind:string;id:string;version:string}
export interface CirculatoryItem {
  fact:{kind:string;id:string;revision:string;binding:{target:{patient_id:string;encounter_id:string}};[key:string]:unknown};
  expected_digest:string;ingestion:{repository_id:string;ingestion_sequence:number;ingested_at:string};
  inclusion:'in_window'|'contextual'|'unplaced';contextual_for:ExactRef[];disclosures:string[];
}
export interface CirculatoryInference {kind:'inference';id:string;revision:string;statement:string;inputs:ExactRef[];[key:string]:unknown}
export interface CirculatoryState {
  transport_version:'m7-c/1';state_context:string;execution_enabled:boolean;assembly_digest:string;
  assembly:{request:{scope:{patient_id:string;encounter_id:string;review_start:string;review_end:string;repository_cutoff:{repository_id:string;fact_watermark:number;captured_at:string}}};
    snapshot:{items:CirculatoryItem[];issues:{reference:ExactRef;reason:string}[];coverage:unknown}};
}
export interface CirculatoryPin {reference:ExactRef;expected_digest:string}
export interface CirculatoryPreparation {execution_id:string;state_context:string;pressure:CirculatoryPin;lactate:CirculatoryPin;vasopressor:CirculatoryPin;supporting:CirculatoryPin[]}
export interface CirculatoryPrepared {transport_version:'m7-c/1';status:'prepared';execution_id:string;inference:CirculatoryInference;command:string}
export interface CirculatoryExecution {transport_version:'m7-c/1';execution_id:string;statement:string|null;ingested_at:string;record:Record<string,unknown>}
export interface CirculatoryReconciliation {status:'committed_match'|'absent';execution:CirculatoryExecution|null}
export interface CirculatoryHistory {transport_version:'m7-c/1';reference:ExactRef;revisions:{fact:CirculatoryItem['fact'];ingestion:CirculatoryItem['ingestion']}[]}
