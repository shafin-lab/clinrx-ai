import {describe,expect,it} from 'vitest';
import {blankDoseContext,renalDose,type DoseContext} from '../src/antibioticWorkflow/renalDoseModel';
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
