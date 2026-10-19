import {CirculatoryClient} from './circulatoryClient';
import {decodeRenalFluid,decodeRenalHistory} from './renalFluidDecoders';
import type {RenalFluidState,RenalObservation} from './renalFluidTypes';
export class RenalFluidClient extends CirculatoryClient {
 async combinedState(start:string,end:string){const reply=await this.request('/synthetic-renal-fluid?'+new URLSearchParams({review_start:start,review_end:end}),v=>v);return {...reply,data:await decodeRenalFluid(reply.data,{...this.scope,start,end})};}
 async renalHistory(state:RenalFluidState,item:RenalObservation){const reference={kind:item.fact.kind,id:item.fact.id,version:item.fact.revision};const reply=await this.request('/synthetic-renal-fluid/history',v=>v,{state_context:state.state_context,reference});return {...reply,data:await decodeRenalHistory(reply.data,state.context,reference)};}
}
