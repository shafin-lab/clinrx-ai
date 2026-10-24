import {describe,expect,it} from 'vitest';
import {blankDoseContext,renalDose,recordedClearanceInputs,type DoseContext} from '../src/antibioticWorkflow/renalDoseModel';
import {clearance,type ClearanceInputs} from '../src/antibioticWorkflow/patientModel';
const stable:ClearanceInputs={age:'62',weight:'74',creatinine:'2.1',factor:'male'};
const reviewed: DoseContext={...blankDoseContext,medicine:'Cefepime',indication:'severe',route:'IV',infusion:'short',phase:'maintenance',bodySize:'standard',hepatic:'reviewed',special:'none',safetyReviewed:true,cultureReviewed:true,empiricReviewed:true,renalFunction:'stable',support:'none'};
const estimate=()=>((140-62)*74)/(72*2.1);
const inputsAt=(value:number):ClearanceInputs=>({...stable,creatinine:String((78*74)/(72*value))});
describe('source matched renal dose suggestions',()=>{
 it('selects a stable adult CrCl band without rounding and preserves indication scope',()=>{
  expect(renalDose(stable,reviewed,estimate())).toMatchObject({status:'suggested',medicine:'Cefepime',band:`CrCl ${estimate().toFixed(2)} mL/min (unrounded value used)`,maintenance:{display:'2 g IV · Every 12 hours'}});
  expect(renalDose(stable,{...reviewed,indication:'nonsevere'},estimate()).maintenance?.display).toBe('2 g IV · Every 24 hours');
  const boundary=inputsAt(29.5);expect(renalDose(boundary,reviewed,clearance(boundary).value)).toMatchObject({status:'review',reason:expect.stringContaining('source gap')});
 });
 it('withholds CrCl-based suggestions for changing renal function, missing calculation or incomplete safety review',()=>{
  expect(renalDose(stable,{...reviewed,renalFunction:'changing'},estimate()).status).toBe('review');
  expect(renalDose(stable,reviewed).status).toBe('review');
  expect(renalDose(stable,{...reviewed,safetyReviewed:false},estimate()).status).toBe('review');
  expect(renalDose(stable,{...reviewed,route:''},estimate()).status).toBe('review');
 });
 it('requires exact final susceptibility or explicit empiric review and rejects a mismatched AST',()=>{
  expect(renalDose(stable,{...reviewed,empiricReviewed:false,cultureReviewed:false},estimate()).status).toBe('review');
  expect(renalDose(stable,{...reviewed,empiricReviewed:false,cultureSource:'Ceftriaxone|culture-1|susceptible'},estimate())).toMatchObject({status:'review',reason:expect.stringContaining('different antibiotic')});
  expect(renalDose(stable,{...reviewed,empiricReviewed:false,cultureSource:'Cefepime|culture-1|susceptible'},estimate()).notes?.join(' ')).toContain('culture-1');
 });
 it('matches CRRT only to the exact CVVHD flow and residual-function source profile',()=>{
  const c: DoseContext={...reviewed,cvvhMode:'cvvhd',flow:'2',flowDefinitionReviewed:true,residual:'lt10',downtime:'none'};
  expect(renalDose(stable,{...c,support:'crrt',renalFunction:'changing'})).toMatchObject({status:'suggested',maintenance:{display:'1 g IV · Every 8 hours'}});
  expect(renalDose(stable, {...c,support:'crrt',cvvhMode:'cvvh'}).status).toBe('review');
  expect(renalDose(stable, {...c,support:'crrt',flow:'2.5'}).status).toBe('review');
  expect(renalDose(stable, {...c,support:'crrt',downtime:'present'}).status).toBe('review');
 });
 it('uses a separate high-flux iHD schedule without using Cockcroft–Gault',()=>{
  const c: DoseContext={...reviewed,medicine:'Cefazolin',indication:'complicated',hdFlux:'high',hdStable:'stable',hdInterval:'72',hdTimingReviewed:true,phase:'initiation'};
  expect(renalDose(stable,{...c,support:'ihd',renalFunction:'changing'})).toMatchObject({status:'suggested',initial:'2 g IV once now (check prior doses)',maintenance:{display:'3 g IV · After HD, before the next 72-hour interval'}});
  expect(renalDose(stable, {...c,support:'ihd',hdFlux:'other'}).status).toBe('review');
  expect(renalDose(stable,{...c,support:'sled'}).status).toBe('review');
 });
 it('withholds unsupported antibiotics rather than inheriting an adjacent profile',()=>{
  expect(renalDose(stable,{...reviewed,medicine:'Vancomycin'},estimate()).reason).toContain('Timed concentrations');
  expect(renalDose(stable,{...reviewed,medicine:'Cefiderocol'},estimate()).status).toBe('review');
  const c: DoseContext={...reviewed,medicine:'Ceftriaxone',indication:'standard',cvvhMode:'cvvhd',flow:'2',flowDefinitionReviewed:true,residual:'lt10',downtime:'none'};
  expect(renalDose(stable,{...c,support:'crrt'}).reason).toContain('no ceftriaxone CRRT row');
 });
 it('keeps the systemic ciprofloxacin PO renal interval distinct from standard dosing',()=>{
  const c: DoseContext={...reviewed,medicine:'Ciprofloxacin',indication:'systemic',route:'PO'};
  const low=inputsAt(20);expect(renalDose(low,c,clearance(low).value).maintenance?.display).toBe('500 mg PO · Every 12 hours');
  expect(renalDose(low,{...c,indication:'standard'},clearance(low).value).maintenance?.display).toBe('500 mg PO · Every 24 hours');
 });
});

import workflow from './fixtures/antibiotic-workflow.json';
import {AntibioticClient} from '../src/api/antibioticClient';
import {chartDefaults,type Evidence} from '../src/api/rf2Client';
async function recordedCatalog(){const b=await new AntibioticClient(async()=>new Response(JSON.stringify(workflow.bundle))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');const c=b.renal;c.items=c.items.filter(e=>e.fact.concept_id==='synthetic-serum-creatinine').slice(0,1);const cr=c.items[0];const weight={...structuredClone(cr),fact:{...structuredClone(cr.fact),kind:'circulatory_event',id:'measured-weight',record_status:'recorded',occurred:{recorded:{status:'known',precision:'instant',value:'2026-10-08T09:00:00Z'},source_timestamp:'2026-10-08T09:00:00Z'},recorded_amount:{value:'74000',unit:{raw:'g'}}},metadata:{version:1,chart:{...chartDefaults,category:'weight',amount:'74000',unit:'g',point:'2026-10-08T09:00:00Z',acquisition:'measured'},note:null}} as Evidence;weight.terminal_reference={kind:weight.fact.kind,id:weight.fact.id,version:weight.fact.revision};c.items.push(weight);return c;}
it('selects one supported recorded creatinine and measured weight with exact provenance and conversion',async()=>{const c=await recordedCatalog(),r=recordedClearanceInputs(c);expect(r.weight?.value).toBe('74');expect(r.creatinine?.value).toBe('1.00');expect(r.weight?.source.reference.id).toBe('measured-weight');expect(r.weight?.conversion).toContain('1000');expect(r.weight?.time).toBe('2026-10-08T09:00:00Z');});
it.each(['ambiguous','unknown','unit','dosing','superseded','scope'])('holds automatic selection for %s weight',async(reason)=>{const c=await recordedCatalog(),w=c.items[1];if(reason==='ambiguous')c.items.push({...structuredClone(w),fact:{...w.fact,id:'second-weight'}});if(reason==='unknown')w.metadata!.chart!.acquisition='unknown';if(reason==='unit')w.metadata!.chart!.unit='lb';if(reason==='dosing')w.metadata!.chart!.category='dosing_weight';if(reason==='superseded')w.superseded=true;if(reason==='scope')w.fact.binding.target.patient_id='other';const r=recordedClearanceInputs(c);expect(r.weight).toBeUndefined();expect(r.reasons.weight.length).toBeGreaterThan(0);});

it.each(['unknown','incompatible','ambiguous','conflicting'])('holds automatic creatinine for %s sources',async(reason)=>{const c=await recordedCatalog(),f=c.items[0].fact as any;if(reason==='unknown')f.value.status='unknown';if(reason==='incompatible')f.value.value.unit={raw:'mmol/L',code:'mmol/L',system:'UCUM',status:'assessed'};if(reason==='ambiguous')c.items.push({...structuredClone(c.items[0]),fact:{...f,id:'other-creatinine'}});if(reason==='conflicting')c.items.push({...structuredClone(c.items[0]),digest:'b'.repeat(64)});expect(recordedClearanceInputs(c).creatinine).toBeUndefined();});
it('converts explicitly assessed umol/L and does not conflate distinct source identities',async()=>{const c=await recordedCatalog(),f=c.items[0].fact as any;f.value.value={value:'88.4',unit:{raw:'umol/L',code:'umol/L',system:'UCUM',status:'assessed'}};expect(recordedClearanceInputs(c).creatinine).toMatchObject({value:'1',conversion:'Source µmol/L ÷ 88.4 → mg/dL'});});
