import {expect,it} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import {gastrointestinalModel,giReviewIdentity} from '../src/gastrointestinal/model';
const scope={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const catalog=()=>structuredClone(fixture.catalog) as unknown as Catalog;
function lab(c:Catalog,id:string,version='1'):Evidence{
 const at={status:'known',precision:'instant',value:'2026-10-08T09:00:00Z'};
 return {repository:c.repository,ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,digest:(version==='1'?'a':'b').repeat(64),canonical_fact:'{}',superseded:false,terminal_reference:{kind:'laboratory_report',id,version},metadata:null,fact:{kind:'laboratory_report',id,revision:version,binding:{target:{patient_id:scope.patient,encounter_id:scope.encounter}},times:{collected:at,reported:at,available:at},source_identity:{issuer_namespace:'lab',source_report_id:id,source_version:version},specimen:{source_specimen_id:id,specimen_type:{raw_display:'Serum'}},report_status:version==='1'?'final':'corrected',record_status:'recorded',components:[{source_component_id:'bili',mapping_status:'mapped',mapped_concept:'total_bilirubin',mapping_version:'1',test_code:{raw_display:'Total bilirubin'},result:{kind:'numeric',raw_value:'2.4',comparator:'=',unit:{namespace:'source',code:'odd',raw_display:'source-unit'}}},{source_component_id:'na',test_code:{raw_display:'Sodium'},mapping_status:'mapped',mapped_concept:'sodium',result:{kind:'numeric',raw_value:'140',comparator:'=',unit:null}}]}};
}
it('shows each admitted component once, keeps equal values from distinct specimens and original unknown unit',()=>{
 const c=catalog();c.laboratory_reports=[lab(c,'sample-a'),lab(c,'sample-b')];const m=gastrointestinalModel(c,scope);
 expect(m.valid).toBe(true);expect(m.labs).toHaveLength(2);expect(m.labs.map(x=>x.evidence.fact.id)).toEqual(['sample-a','sample-b']);expect(m.labs[0].text).toBe('2.4 source-unit');expect(m.labs[0].component.source_component_id).toBe('bili');
});
it('same-value correction changes review identity; unrelated source watermark does not',()=>{
 const c=catalog();c.laboratory_reports=[lab(c,'same')];const original=giReviewIdentity(gastrointestinalModel(c,scope));
 c.laboratory_reports=[lab(c,'same','2')];expect(giReviewIdentity(gastrointestinalModel(c,scope))).not.toBe(original);
 const revised=giReviewIdentity(gastrointestinalModel(c,scope));c.cutoff.fact_watermark++;c.combined.context.scope.repository_cutoff.fact_watermark++;c.items.forEach(e=>e.cutoff++);c.laboratory_reports.forEach(e=>e.cutoff++);
 expect(giReviewIdentity(gastrointestinalModel(c,scope))).toBe(revised);
});
it('rejects foreign binding and excludes future source availability',()=>{
 const c=catalog(),e=lab(c,'future');c.laboratory_reports=[e];(e.fact.times as any).available.value='2026-10-08T11:00:00Z';expect(gastrointestinalModel(c,scope).labs).toHaveLength(0);
 e.fact.binding.target.patient_id='foreign';expect(gastrointestinalModel(c,scope).valid).toBe(false);
});
it('keeps withdrawal and unsupported mapping qualified without showing the old value as current',()=>{
 const c=catalog(),e=lab(c,'withdrawn');e.fact.record_status='withdrawn';c.laboratory_reports=[e];expect(gastrointestinalModel(c,scope).labs[0].text).toMatch(/Withdrawn/);
 e.fact.record_status='recorded';(e.fact.components as any)[0].mapping_status='unsupported';expect(gastrointestinalModel(c,scope).labs).toHaveLength(0);expect(gastrointestinalModel(c,scope).unmapped).toHaveLength(1);
});

it('shares liver components without classifying them as renal investigations',async()=>{
 const {renalBedsideModel}=await import('../src/renal/renalBedsideModel');const c=catalog();c.laboratory_reports=[lab(c,'gi-only')];
 const model=renalBedsideModel(c.combined,scope,c);expect(model.valid).toBe(true);expect(model.sources.some(s=>s.mappedConcept==='total_bilirubin')).toBe(false);expect(model.sources.some(s=>s.mappedConcept==='sodium')).toBe(true);
});
