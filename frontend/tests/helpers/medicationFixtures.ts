import {describe,expect,it} from 'vitest';
import fixture from '../fixtures/antibiotic-workflow.json';
import {AntibioticClient} from '../../src/api/antibioticClient';
import {chartDefaults,pin,type Catalog,type Evidence} from '../../src/api/rf2Client';
import {automaticRenalModel,DOSE_CONTEXT_QUESTION,type PatientDoseContext} from '../../src/antibioticWorkflow/automaticRenalModel';

export const patientContext:PatientDoseContext={version:1,birthDate:'1966-10-08',factor:'male',renalFunction:'stable',support:'none',weightReviewed:true,bodySize:'standard',hepatic:'reviewed',special:'none',safetyReviewed:true};
export async function renalCatalog(){
 const c=(await new AntibioticClient(async()=>new Response(JSON.stringify(fixture.bundle))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z')).renal;
 c.items=c.items.filter(e=>e.fact.concept_id==='synthetic-serum-creatinine');c.laboratory_reports=[];
 for(const e of c.items)(e.fact.value as any).value.value='3';
 const base=c.items[0];
 const weight={...structuredClone(base),fact:{...structuredClone(base.fact),kind:'circulatory_event',id:'weight-for-calculation',record_status:'recorded'},metadata:{version:1,chart:{...chartDefaults,category:'weight',amount:'67.5',unit:'kg',point:'2026-10-08T09:00:00Z',acquisition:'measured'},note:null}} as Evidence;
 weight.terminal_reference={kind:weight.fact.kind,id:weight.fact.id,version:weight.fact.revision};c.items.push(weight);
 addContext(c,patientContext);return c;
}
export function addContext(c:Catalog,context:PatientDoseContext){
 const base=c.items[0];const e={...structuredClone(base),fact:{...structuredClone(base.fact),kind:'circulatory_event',id:'00000000-0000-4000-8000-000000000071',record_status:'recorded',occurred:{source_timestamp:'2026-10-08T10:00:00Z',recorded:{status:'known',precision:'instant',value:'2026-10-08T10:00:00Z'}}},metadata:{version:1,chart:null,note:{question:DOSE_CONTEXT_QUESTION,findings:JSON.stringify(context),possibilities:'Explicit clinician review',gaps:'No automated treatment selection',plan:'Review with new results',pins:c.items.filter(e=>e.metadata?.chart?.category==='weight'||e.fact.concept_id==='synthetic-serum-creatinine').map(pin)}}} as Evidence;
 e.terminal_reference={kind:e.fact.kind,id:e.fact.id,version:e.fact.revision};c.items=c.items.filter(x=>x.fact.id!==e.fact.id);c.items.push(e);return e;
}
