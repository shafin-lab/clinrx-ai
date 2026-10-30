import {expect,it} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import respiratory from './fixtures/respiratory-record.json';
import {type Catalog,type Evidence,pin} from '../src/api/rf2Client';
import {resolveRespiratoryEvaluation} from '../src/respiratory/respiratoryEvaluation';
import {calculateRespiratoryPhysiology} from '../src/respiratory/physiology';
import type {RespiratoryRecord} from '../src/respiratory/respiratoryTypes';
function setup(){
 const catalog=structuredClone(fixture.catalog) as unknown as Catalog;
 const record=structuredClone(respiratory) as unknown as RespiratoryRecord;
 for(const m of record.measurements)if(m.result.kind==='numeric'&&m.result.unit)m.result.unit.namespace='UCUM';
 const support=structuredClone(record);support.id='support';support.category='support';support.times.occurred=structuredClone(record.times.collected);support.measurements=record.measurements.filter(m=>m.concept==='fio2');
 record.measurements=record.measurements.filter(m=>m.concept!=='fio2');record.linked_sources=[{kind:support.kind,id:support.id,version:support.revision}];
 const evidence=(fact:RespiratoryRecord):Evidence=>({repository:catalog.repository,fact,canonical_fact:JSON.stringify(fact),digest:'a'.repeat(64),ingestion:{repository_id:catalog.repository,ingestion_sequence:1},cutoff:catalog.cutoff.fact_watermark,terminal_reference:{kind:fact.kind,id:fact.id,version:fact.revision},superseded:false,metadata:null});
 const sample=evidence(record),source=evidence(support);catalog.respiratory_records=[sample,source];return {catalog,record,support,sample,source};
}
it('supplies only missing FiO2 from exact linked same-instant support with full source pin and no source mutation',()=>{
 const {catalog,record,source}=setup(),before=JSON.stringify(catalog);const evaluation=resolveRespiratoryEvaluation(record,catalog);
 expect(evaluation.issues).toEqual([]);expect(evaluation.inputs.get('fio2')?.source).toBe(source);
 const pf=calculateRespiratoryPhysiology(record,evaluation).find(x=>x.id==='pf_ratio')!;expect(pf.value).toBe('200');expect(pf.inputs.join(' ')).toContain(JSON.stringify(pin(source)));expect(pf.inputs.join(' ')).toContain('component=fio2');expect(JSON.stringify(catalog)).toBe(before);
});
it.each(['late','ambiguous','encounter','revision','unknown-time','unconfirmed','repository','cutoff','quality','unit','role','superseded','unresolved','fractional-time'])('withholds linked support when %s',cause=>{
 const {catalog,record,support,source}=setup();
 if(cause==='late')support.times.occurred.value='2026-10-08T09:05:00Z';
 if(cause==='ambiguous'){const second=structuredClone(source);second.fact.id='support2';second.terminal_reference.id='support2';catalog.respiratory_records!.push(second);record.linked_sources.push({kind:second.fact.kind,id:second.fact.id,version:second.fact.revision});}
 if(cause==='encounter')support.binding.target.encounter_id='other';if(cause==='revision')record.linked_sources[0].version='stale';if(cause==='unknown-time')support.times.occurred.precision='approximate';if(cause==='unconfirmed')record.context.settings_confirmed_at_sample=null;if(cause==='repository')source.repository='other';if(cause==='cutoff')source.cutoff++;if(cause==='quality')support.measurements[0].quality='unknown';if(cause==='unit'&&support.measurements[0].result.kind==='numeric')support.measurements[0].result.unit!.code='L/min';if(cause==='role')support.measurements[0].role='unknown';if(cause==='superseded')source.superseded=true;if(cause==='unresolved')record.linked_sources[0].id='missing';if(cause==='fractional-time')support.times.occurred.value=record.times.collected.value!.replace('Z','.000001Z');
 const evaluation=resolveRespiratoryEvaluation(record,catalog);expect(evaluation.inputs.size).toBe(0);expect(evaluation.issues.length).toBeGreaterThan(0);const pf=calculateRespiratoryPhysiology(record,evaluation).find(x=>x.id==='pf_ratio')!;expect(pf.value).toBeNull();expect(pf.reason).toContain(cause==='unconfirmed'?'confirmed':evaluation.issues[0]);
});
it.each(['suspect','unknown'] as const)('never rescues own %s FiO2 from external support',quality=>{const {record,catalog,support}=setup();record.measurements.push({...support.measurements[0],quality});const evaluation=resolveRespiratoryEvaluation(record,catalog);expect(evaluation.inputs.size).toBe(0);expect(calculateRespiratoryPhysiology(record,evaluation).find(x=>x.id==='pf_ratio')!.reason).toContain(quality);});

it('does not extend automatic source pairing beyond a gas sample',()=>{const {catalog,record}=setup();record.category='mechanics';expect(resolveRespiratoryEvaluation(record,catalog).inputs.size).toBe(0);});

it('resolves missing FiO2 from captured real current gateway catalog envelopes',async()=>{
 const {default:captured}=await import('./fixtures/respiratory-linked-catalog.json');
 const catalog=structuredClone(captured) as unknown as Catalog;
 const gas=catalog.respiratory_records!.find(e=>(e.fact as RespiratoryRecord).category==='blood_gas')!;
 const support=catalog.respiratory_records!.find(e=>(e.fact as RespiratoryRecord).category==='support')!;
 expect(gas.cutoff).toBe(catalog.cutoff.fact_watermark);expect(support.cutoff).toBe(gas.cutoff);
 const before=JSON.stringify(catalog),evaluation=resolveRespiratoryEvaluation(gas.fact as RespiratoryRecord,catalog);
 expect(evaluation.issues).toEqual([]);expect(calculateRespiratoryPhysiology(gas.fact as RespiratoryRecord,evaluation).find(r=>r.id==='pf_ratio')?.value).toBe('200');expect(JSON.stringify(catalog)).toBe(before);
 support.cutoff=support.ingestion.ingestion_sequence;
 expect(resolveRespiratoryEvaluation(gas.fact as RespiratoryRecord,catalog).issues.join(' ')).toContain('cutoff');
});

it.each(['support','blood_gas'])('withholds external FiO2 when the captured %s has an explicit unresolved conflict',async category=>{
 const {default:captured}=await import('./fixtures/respiratory-linked-catalog.json');
 const catalog=structuredClone(captured) as unknown as Catalog;
 const sample=catalog.respiratory_records!.find(e=>(e.fact as RespiratoryRecord).category==='blood_gas')!.fact as RespiratoryRecord;
 const conflicted=catalog.respiratory_records!.find(e=>(e.fact as RespiratoryRecord).category===category)!.fact as RespiratoryRecord;
 conflicted.conflict='unresolved';const before=JSON.stringify(catalog),evaluation=resolveRespiratoryEvaluation(sample,catalog);
 expect(evaluation.inputs.size).toBe(0);expect(evaluation.issues.join(' ')).toMatch(/unresolved.*conflict/);
 const pf=calculateRespiratoryPhysiology(sample,evaluation).find(r=>r.id==='pf_ratio')!;
 expect(pf.value).toBeNull();expect(pf.reason).toContain(evaluation.issues[0]);expect(JSON.stringify(catalog)).toBe(before);
});
