import type { Prepared, Execution } from '../api/types';
import type { ApiFailure } from '../api/client';
export type Phase = 'viewing'|'preparing'|'prepared'|'executing'|'completed'|'completion_unknown'|'reconciling'|'committed_match'|'absent'|'error'|'preparation_unknown';
export interface ReviewState { phase: Phase; prepared?: Prepared; result?: Execution; error?: ApiFailure }
export type Action = {type:'reset'}|{type:'preparing'}|{type:'prepared';value:Prepared}|{type:'executing'}|{type:'completed';value:Execution}|{type:'unknown';error:ApiFailure}|{type:'preparation_unknown';error:ApiFailure}|{type:'reconciling'}|{type:'matched';value:Execution}|{type:'absent'}|{type:'error';error:ApiFailure};
export function reviewReducer(state:ReviewState,action:Action):ReviewState {
  switch(action.type) {
    case 'reset': return {phase:'viewing'};
    case 'preparing': return {phase:'preparing'};
    case 'prepared': return {phase:'prepared',prepared:action.value};
    case 'executing': return {...state,phase:'executing',result:undefined,error:undefined};
    case 'completed': return {...state,phase:'completed',result:action.value,error:undefined};
    case 'unknown': return {...state,phase:'completion_unknown',error:action.error};
    case 'preparation_unknown': return {phase:'preparation_unknown',error:action.error};
    case 'reconciling': return {...state,phase:'reconciling',error:undefined};
    case 'matched': return {...state,phase:'committed_match',result:action.value,error:undefined};
    case 'absent': return {...state,phase:'absent',error:undefined};
    case 'error': return {...state,phase:'error',error:action.error};
  }
}
