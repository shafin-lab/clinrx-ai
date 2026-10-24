import {expect,it} from 'vitest';
import type {Fact} from '../src/api/rf2Client';
import {investigationGroups,investigationPresentation,searchInvestigationCatalog} from '../src/clinical/sharedInvestigations';

const fact=(extra:Record<string,unknown>):Fact=>({kind:'observation',id:'source-result',revision:'v1',binding:{target:{patient_id:'p',encounter_id:'e'}},...extra});
it('keeps KFT and RFT as aliases of one product group without admitting any source assay',()=>{
 expect(searchInvestigationCatalog('KFT').map(g=>g.id)).toEqual(['kidney-electrolytes']);
 expect(searchInvestigationCatalog('RFT').map(g=>g.id)).toEqual(['kidney-electrolytes']);
 for(const concept_id of ['KFT','RFT','creatinine','Creatinine','troponin','unknown-assay'])expect(investigationPresentation(fact({concept_id}))).toBeUndefined();
});
it('maps the existing decoded creatinine discriminant without changing any source content',()=>{
 const source=fact({concept_id:'synthetic-serum-creatinine',value:{value:'2.000',unit:'mg/dL'},specimen:null,status:'corrected'}),before=structuredClone(source);
 expect(investigationPresentation(source)).toMatchObject({label:'Creatinine',groupId:'kidney-electrolytes'});
 expect(source).toEqual(before);
 expect(investigationPresentation(fact({concept_id:'body-weight'}))).toBeUndefined();
});
it('keeps pulse oximetry and calculated oxygen transport outside the investigation mappings',()=>{
 for(const concept of ['spo2','do2','vo2','extraction_ratio'])expect(investigationPresentation(fact({kind:'circulatory_oxygen',concept}))).toBeUndefined();
 expect(investigationPresentation(fact({kind:'circulatory_oxygen',concept:'ph'}))).toMatchObject({label:'pH',groupId:'gases'});
 expect(investigationPresentation(fact({kind:'circulatory_cardiac',concept:'ph'}))).toBeUndefined();
});
it('does not map unknown or lookalike source discriminants by spelling or display text',()=>{
 expect(investigationPresentation(fact({concept_id:'future-assay',display:'Creatinine'}))).toBeUndefined();
 expect(investigationPresentation(fact({concept_id:'Synthetic-Serum-Creatinine'}))).toBeUndefined();
 expect(investigationPresentation(fact({kind:'__proto__',concept_id:'synthetic-serum-creatinine'}))).toBeUndefined();
});
it('preserves specimen, method, comparator, status and timing even when labels share a presentation group',()=>{
 const a=fact({kind:'circulatory_oxygen',concept:'ph',sample_type:'arterial',result:{comparator:'<',quantity:{value:'7.2000'}},collected:{precision:'approximate'},record_status:'preliminary'});
 const b=fact({...a,id:'second-result',sample_type:'peripheral_venous',result:{quantity:{value:'7.20'}},record_status:'withdrawn'});
 const before=structuredClone([a,b]);
 expect(investigationPresentation(a)?.groupId).toBe(investigationPresentation(b)?.groupId);
 expect([a,b]).toEqual(before);expect(a.sample_type).not.toBe(b.sample_type);
});
it('covers routine, endocrine, nutritional and rare reports while retaining distinct assay families',()=>{
 const tests=investigationGroups.flatMap(g=>g.plannedTests);
 for(const name of ['Sodium','Potassium','Albumin','High-sensitivity troponin I','High-sensitivity troponin T','NT-proBNP','Protein C activity','Protein C antigen','Antithrombin activity','ADAMTS13 activity','TSH','ACTH','Urinary total nitrogen','Other original investigation report'])expect(tests).toContain(name);
 expect(new Set(investigationGroups.map(g=>g.id)).size).toBe(investigationGroups.length);
 expect(investigationGroups.every(g=>g.modules.every(m=>/^M(?:[6-9]|1[0-9]|2[01])$/.test(m)))).toBe(true);
 const modules=Object.fromEntries(investigationGroups.map(g=>[g.id,g.modules]));
 expect(modules['blood-count']).toEqual(['M10','M17']);
 expect(modules.liver).toEqual(['M10','M11','M17']);
 expect(modules.coagulation).toEqual(['M8','M10','M12']);
 expect(modules['blood-bank']).toEqual(['M10','M12','M21']);
 expect(modules.inflammation).toEqual(['M6','M9','M20']);
 expect(modules.glucose).toEqual(['M14','M17']);
 expect(modules.thyroid).toEqual(['M12','M14']);
 expect(modules['pituitary-reproductive']).toEqual(['M12','M14']);
 expect(modules.haematinics).toEqual(['M10','M17']);
 expect(modules.immunology).toEqual(['M8','M16','M20']);
 expect(modules.paraprotein).toEqual(['M8','M10']);
 expect(modules['drug-levels']).toEqual(['M6','M8','M13','M18']);
 expect(modules['osmolality-urine']).toEqual(['M8','M14']);
 expect(modules['body-fluids']).toEqual(['M6','M8','M9','M11','M12','M13','M16']);
});
