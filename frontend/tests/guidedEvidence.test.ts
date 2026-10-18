import {it,expect} from 'vitest';
import {buildGuided,type GuidedFamily,type Fields} from '../src/demo/guidedEvidence';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import fixture from './fixtures/icuFlowsheet.json';
import admittedExamples from './fixtures/guidedEntries.json';
import {record} from '../src/demo/evidencePresentation';
const items=decodeCirculatoryState(structuredClone(fixture)).assembly.snapshot.items;
const defaults:Fields={time:'2026-10-08T09:15:00.123456Z',available:'',value:'7.3600',unit:'1',uncertainty:'Fictional source; context requires review',production:'direct_measurement',quality:'unknown',method:'unknown',resultType:'numeric'};
const cases:[GuidedFamily,Fields][]=[['pressure',{concept:'systemic_mean',value:'71.00',unit:'mmHg',method:'automated_cuff'}],['gas',{concept:'ph',sample:'arterial',specimen:'local-sample',fio2:'40',fio2Unit:'%',peep:'5',peepUnit:'cmH2O'}],['gas',{concept:'svo2',sample:'mixed_venous',value:'62.0',unit:'%'}],['gas',{concept:'lactate',sample:'arterial',value:'2.10',unit:'mmol/L',reportStatus:'final'}],['cardiac',{concept:'co',value:'4.70',unit:'L/min',method:'bolus_thermodilution',quality:'suspect',methodContext:'PAC source-recorded three-injection basis; no ClinRx averaging'}],['echo',{concept:'estimated_rvsp',value:'45.0',unit:'mmHg',production:'source_calculated',productionBasis:'Source TR velocity / estimated RAP; RVOT obstruction context unknown',study:'study-local',report:'report-local',reportRevision:'1'}],['echo',{concept:'rv_function',resultType:'qualitative',finding:'Source-reported reduced RV function',study:'study-local',report:'report-local',reportRevision:'1'}],['infusion',{drug:'noradrenaline',action:'order',sourceStatus:'Source prescribed order; no administration',series:'local-N',rate:'7.00',rateUnit:'mcg/min',concentration:'0.08',concentrationUnit:'mg/mL'}],['infusion',{drug:'vasopressin',action:'initiation',sourceStatus:'Source documented start',series:'local-V',rate:'1.8',rateUnit:'units/h'}],['infusion',{drug:'dobutamine',action:'pause',sourceStatus:'Source documented pause',series:'local-D',interruption:'Source recorded reason'}],['perfusion',{concept:'capillary_refill',value:'3.0',unit:'s',method:'bedside_examination'}],['reassessment',{question:'Review documented intervention and separately recorded findings',baseline:'circulatory_pressure/fs-MAP-15/1',intervention:'circulatory_vasoactive/fs-N-CHANGE/1',followup:'circulatory_cardiac/fs-CO-60/1',findings:'Recorded MAP and CO have distinct times and methods.',possibilities:'Relationship unconfirmed; no causal attribution',nextReview:'Clinician to review sample and echo context'}]];

const vectors=cases.map(([family,fields],n)=>({family,fields:{...defaults,...fields},fact:buildGuided(family,{...defaults,...fields},'Synthetic reviewer',items,'guided-validation-'+n,'2026-10-18T06:00:00Z')}));
it.each(vectors)('constructs $family with exact source time, unverified binding and disclosed uncertainty',({fact})=>{
 expect(fact.occurred).toMatchObject({source_timestamp:defaults.time,clock:'unknown'});
 expect(fact.available).toMatchObject({recorded:{status:'not_recorded'}});
 expect(record(fact.binding).verification).toMatchObject({status:'unresolved'});
 expect(record(fact.provenance).actor).toBe('Synthetic reviewer');
 expect(fact.uncertainty).toEqual([defaults.uncertainty]);
});
it('preserves decimal text and does not transfer arterial respiratory context to mixed venous results',()=>{
 const arterial=vectors[1].fact,venous=vectors[2].fact;
 expect(arterial.result).toMatchObject({quantity:{value:'7.3600',unit:{status:'unresolved'}}});
 expect(arterial.blood_gas_context).toMatchObject({fio2:{value:'40'},peep:{value:'5'}});
 expect(venous.blood_gas_context).not.toHaveProperty('fio2');
 expect(venous.blood_gas_context).not.toHaveProperty('peep');
});
it('retains distinct prescribed/delivered/pause events and unresolved drug mappings without conversion',()=>{
 expect(vectors[7].fact.action).toMatchObject({event_type:'order',prescribed:{rate:{value:'7.00',unit:{raw:'mcg/min'}},concentration:{value:'0.08'}}});
 expect(vectors[8].fact.action).toMatchObject({event_type:'initiation',delivery:{rate:{value:'1.8'}}});
 expect(vectors[9].fact.action).toMatchObject({event_type:'pause'});
 expect(vectors[7].fact.drug).toMatchObject({mapping:'unknown'});
});
it('keeps source estimate basis and qualitative echo findings distinct',()=>{
 expect(vectors[5].fact.production).toBe('source_calculated');
 expect(vectors[5].fact.calculation_method).toMatchObject({raw_display:expect.stringContaining('RVOT')});
 expect(vectors[6].fact.result).toMatchObject({result_type:'qualitative',finding:{raw_display:'Source-reported reduced RV function'}});
});
it('retains stage-labelled exact reassessment references without replacing revisions or generating conclusions',()=>{
 const fact=vectors[11].fact;
 expect(fact.kind).toBe('circulatory_event');expect(fact.associations).toHaveLength(3);
 expect(fact.external_evidence).toEqual(expect.arrayContaining([expect.objectContaining({namespace:'clinrx.local.reassessment.followup/v1',code:JSON.stringify({kind:'circulatory_cardiac',id:'fs-CO-60',version:'1'})})]));
 expect(record(fact.description).raw_display).toContain('Unconfirmed possibilities: Relationship unconfirmed; no causal attribution');
 expect(()=>buildGuided('reassessment',{...vectors[11].fields,baseline:'circulatory_pressure/fs-MAP-15/2'},'Reviewer',items,'bad','2026-10-18T06:00:00Z')).toThrow();
});
it('rejects incomplete required fields and does not invent an actor, echo report or raw unit',()=>{
 for(const field of ['study','report','reportRevision','unit','uncertainty'])expect(()=>buildGuided('echo',{...vectors[5].fields,[field]:''},'Reviewer',items,'bad','2026-10-18T06:00:00Z')).toThrow();
 expect(()=>buildGuided('pressure',vectors[0].fields,'',items,'bad','2026-10-18T06:00:00Z')).toThrow();
});
it('matches the exact generated form records exercised by real API admission tests',()=>{expect(vectors).toEqual(admittedExamples);});
it('rejects promoting RVSP to a direct measurement or using a measurement as an intervention',()=>{
 expect(()=>buildGuided('echo',{...vectors[5].fields,production:'direct_measurement'},'Reviewer',items,'bad','2026-10-18T06:00:00Z')).toThrow(/estimate/);
 expect(()=>buildGuided('reassessment',{...vectors[11].fields,intervention:'circulatory_cardiac/fs-CO-60/1'},'Reviewer',items,'bad','2026-10-18T06:00:00Z')).toThrow(/intervention/);
});
