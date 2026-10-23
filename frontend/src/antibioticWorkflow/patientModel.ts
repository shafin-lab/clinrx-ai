import type {MicroState,Item} from '../api/microTypes';
import type {Ref} from '../api/rf2Client';
import {record} from '../demo/evidencePresentation';
export const CG_SOURCE='https://www.hepatitisc.uw.edu/page/clinical-calculators/crcl';
export interface ClearanceInputs{age:string;weight:string;creatinine:string;factor:string}
export function clearance(inputs:ClearanceInputs){
 const {age,weight,creatinine,factor}=inputs;
 if(![age,weight,creatinine].every(s=>/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(s)))return {error:'Enter age, weight in kg and serum creatinine in mg/dL.'};
 const a=Number(age),w=Number(weight),c=Number(creatinine);
 if(![a,w,c].every(Number.isFinite)||a<18||a>=140||w<=0||c<=0||!['male','female'].includes(factor))return {error:'Enter an adult age, positive weight and serum creatinine, and an equation coefficient.'};
 const value=(140-a)*w*(factor==='female'?0.85:1)/(72*c);
 if(!Number.isFinite(value))return {error:'The inputs do not produce a finite estimate.'};
 return {value};
}
export const microReference=(item:Item):Ref=>({kind:String(item.fact.kind),id:item.fact.id,version:item.fact.revision});
export const microKey=(item:Item)=>JSON.stringify(microReference(item));
export function microSnapshotKey(state:MicroState){return JSON.stringify([state.assembly.request.scope.repository_cutoff,(state.assembly.snapshot.items??[]).map(i=>[i.fact.kind,i.fact.id,i.fact.revision,i.expected_digest])]);}
export function microTime(item:Item){const f=item.fact as unknown as Record<string,unknown>,stamp=record(f.administered??f.occurred??f.created??f.collected??record(f.report).available);return typeof stamp.value==='string'?stamp.value:'Time not established';}
export function antibioticLabel(item:Item){const f=item.fact as unknown as Record<string,unknown>,identity=record(f.antimicrobial);return String(identity.raw_display??f.kind);}
export function recordSummary(item:Item){const f=item.fact as unknown as Record<string,unknown>,dose=record(f.administered_dose??f.prescribed_dose),amount=record(dose.amount);return [antibioticLabel(item),typeof amount.value==='string'?amount.value+' '+String(record(amount.unit).raw??''):'No administered dose',f.kind==='antimicrobial_order'?'Prescription':f.kind==='antimicrobial_administration'?'Given':String(f.status??'Source record'),String(record(f.route).raw_display??''),String(f.schedule??''),microTime(item)].filter(Boolean).join(' · ');}
function exactParent(item:Item,role:string,items:Item[]){const bindings=(item.fact.domain_bindings??[]).filter(b=>b.role===role);if(bindings.length!==1||bindings[0].status!=='resolved'||!bindings[0].exact)return;const ref=bindings[0].exact;return items.find(i=>i.fact.kind===ref.kind&&i.fact.id===ref.id&&i.fact.revision===ref.version);}
export function cultureOptions(state:MicroState|undefined){
 const items=state?.assembly.snapshot.items??[];
 return items.filter(i=>i.fact.kind==='microbiology_susceptibility').map(item=>{
  const f=item.fact as unknown as Record<string,unknown>,isolate=exactParent(item,'isolate',items),specimen=isolate&&exactParent(isolate,'specimen',items),report=record(f.report),interpretation=record(f.interpretation),breakpoint=record(f.breakpoint);
  const isolateFact=isolate?.fact as unknown as Record<string,unknown>|undefined;
  const reasons:string[]=[];
  if(item.inclusion!=='in_window'||report.status!=='final'||report.change==='superseded')reasons.push('Final in-window AST not confirmed');
  if(!isolate||!specimen||isolateFact?.identification_state!=='final'||record(isolateFact?.report).status!=='final')reasons.push('Exact final isolate/specimen link not confirmed');
  if(!breakpoint.authority||!breakpoint.version)reasons.push('AST standard/edition not supplied');
  if(record(f.antimicrobial).mapping_status!=='mapped')reasons.push('Antibiotic identity mapping not confirmed');
  const conflicts=items.some(other=>other!==item&&other.fact.kind==='microbiology_susceptibility'&&exactParent(other,'isolate',items)===isolate&&antibioticLabel(other)===antibioticLabel(item)&&record(record(other.fact).interpretation).category!==interpretation.category);
  if(conflicts)reasons.push('Conflicting susceptibility reports need reconciliation');
  if(f.result_status!=='reported')reasons.push('Susceptibility result incomplete');
  const category=String(interpretation.category??'unknown');
  const positiveMarker=items.some(i=>i.fact.kind==='microbiology_resistance'&&record(i.fact).result==='positive'&&(exactParent(i,'isolate',items)===isolate||exactParent(i,'specimen',items)===specimen));
  if(positiveMarker)reasons.push('Resistance mechanism requires specialist review');
  if(category!=='susceptible')reasons.push(category==='resistant'?'Reported resistant':category==='intermediate'?'Intermediate / increased-exposure interpretation needs source-specific review':'No susceptible category reported');
  return {item,isolate,specimen,medicine:antibioticLabel(item),organism:String(record(isolateFact?.organism).raw_display??'Not established'),specimenName:String(record(record(specimen?.fact).specimen_type).raw_display??'Not established'),raw:String(interpretation.raw??'Not reported'),category,standard:[breakpoint.authority,breakpoint.version].filter(Boolean).join(' · '),candidate:!reasons.length,reasons};
 });
}
