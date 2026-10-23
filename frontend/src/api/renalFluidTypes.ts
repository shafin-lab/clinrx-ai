import type {CirculatoryItem,CirculatoryState,ExactRef} from './circulatoryTypes';
export interface RenalObservation {
 fact:{kind:'observation';id:string;revision:string;concept_id:string;binding:CirculatoryItem['fact']['binding'];time:{event:string|null;recorded:string|null;precision:string;[key:string]:unknown};value:{status:string;value:{value:string;unit:{raw:string|null;status:string;[key:string]:unknown}}|string|boolean|null;reason:string|null};verification:string;conflict:string;temporal_status:string;uncertainty:string[];supersedes:ExactRef|null;correction_reason:string|null;[key:string]:unknown};
 expected_digest:string;canonical_fact:string;ingestion:CirculatoryItem['ingestion'];inclusion:'in_window'|'outside_window'|'unplaced';
}
export interface RenalFluidContext {transport_version:'SyntheticRenalFluidReview/v1';scope:CirculatoryState['assembly']['request']['scope'];circulatory_digest:string;observations_digest:string}
export interface RenalFluidState {context:RenalFluidContext;state_context:string;circulatory:CirculatoryState;laboratory:{scope:RenalFluidContext['scope'];observations:RenalObservation[]};canonical_assembly:string;canonical_laboratory:string;execution_enabled:false}
export interface RenalHistory {context:RenalFluidContext;reference:ExactRef;revisions:RenalObservation[]}
