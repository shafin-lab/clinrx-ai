import {expect,it} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import {respiratoryModel} from '../src/respiratory/respiratoryModel';
import type {Catalog,Evidence} from '../src/api/rf2Client';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const catalog=()=>structuredClone(fixture.catalog) as unknown as Catalog;
function gas(c:Catalog,id:string,concept:string,value:string,specimen='sample-1',fio2:string|null='40'):Evidence {
 const point={recorded:{status:'known',precision:'instant',value:'2026-10-08T09:00:00Z'},source_timestamp:'2026-10-08T09:00:00Z'};
 return {repository:c.repository,digest:'a'.repeat(64),canonical_fact:'{}',ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:'circulatory_oxygen',id,version:'1'},superseded:false,metadata:null,fact:{kind:'circulatory_oxygen',id,revision:'1',binding:{target:{patient_id:requested.patient,encounter_id:requested.encounter}},concept,sample_type:'arterial',specimen:{namespace:'lab',code:specimen,version:'1'},record_status:'recorded',available:point,occurred:point,acquisition:{method:'blood_gas',quality:{status:'acceptable'}},blood_gas_context:{collected:point,fio2:fio2?{value:fio2,unit:{raw:'%'}}:null,peep:{value:'5',unit:{raw:'cmH2O'}}},result:{result_type:'numeric',quantity:{value,unit:{raw:concept==='ph'?'1':'mmHg'}},comparator:'='}}};
}
it('groups only exact specimen, collection time and sample type without cloning sources',()=>{
 const c=catalog();const a=gas(c,'ph','ph','7.30'),b=gas(c,'co2','paco2','50.0'),d=gas(c,'o2','pao2','80.0','sample-2');c.items=[a,b,d];
 const before=JSON.stringify(c),model=respiratoryModel(c,requested);
 expect(model.valid).toBe(true);expect(model.samples).toHaveLength(2);expect(model.samples[0].evidence).toHaveLength(2);expect(model.samples[0].record.measurements.find(x=>x.concept==='fio2')?.result).toMatchObject({raw_value:'40'});expect(JSON.stringify(c)).toBe(before);
});
it('never supplies a gas FiO2 from another sample or a later support record',()=>{
 const c=catalog();c.items=[gas(c,'old','pao2','80','sample-1',null),gas(c,'later','pao2','100','sample-2','60')];
 const model=respiratoryModel(c,requested);expect(model.samples.find(s=>s.evidence.some(e=>e.fact.id==='old'))?.record.measurements.some(m=>m.concept==='fio2')).toBe(false);
});
it('marks contradictory sample-time settings unusable for calculation',()=>{
 const c=catalog();c.items=[gas(c,'o2','pao2','80','sample-1','40'),gas(c,'co2','paco2','50','sample-1','60')];
 const sample=respiratoryModel(c,requested).samples[0];expect(sample.issues.join(' ')).toMatch(/conflict/i);expect(sample.record.context.settings_confirmed_at_sample).not.toBe(true);
});
it('rejects a mismatched patient or cutoff rather than claiming current evidence',()=>{
 const c=catalog();c.items=[gas(c,'o2','pao2','80')];c.items[0].fact.binding.target.patient_id='other';expect(respiratoryModel(c,requested).valid).toBe(false);
});
it('keeps source times outside the requested period as context rather than current observations',()=>{
 const c=catalog();const e=gas(c,'early','pao2','80');(e.fact.occurred as any).recorded.value='2026-10-08T07:00:00Z';(e.fact.blood_gas_context as any).collected.recorded.value='2026-10-08T07:00:00Z';c.items=[e];const m=respiratoryModel(c,requested);expect(m.samples).toHaveLength(0);expect(m.contextItems).toHaveLength(1);
});
it('does not turn legacy sample context into independently confirmed support alignment',()=>{
 const c=catalog();c.items=[gas(c,'legacy-o2','pao2','80')];
 const sample=respiratoryModel(c,requested).samples[0];
 expect(sample.record.context.settings_confirmed_at_sample).not.toBe(true);
 expect(sample.record.measurements.find(m=>m.concept==='fio2')?.result).toMatchObject({raw_value:'40'});
});
it('does not group approximate legacy collection times as an exact blood-gas sample',()=>{
 const c=catalog(),e=gas(c,'approximate-o2','pao2','80');(e.fact.blood_gas_context as any).collected.recorded.precision='approximate';c.items=[e];
 const model=respiratoryModel(c,requested);expect(model.samples).toHaveLength(0);expect(model.contextItems).toHaveLength(1);
});
