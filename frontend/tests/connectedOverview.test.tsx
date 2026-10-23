import {afterAll,afterEach,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within,waitFor} from '@testing-library/react';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
import fixture from './fixtures/rf2-api.json';
import {RF2Client,pin,type Evidence} from '../src/api/rf2Client';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {PatientOverview,patientOverviewModel} from '../src/demo/PatientOverview';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {reviewStoragePrefix} from '../src/clinical/savedReviewStore';
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <p>Existing evidence viewer</p>}));
vi.mock('../src/demo/EvidenceEntryWorkspace',()=>({EvidenceEntryWorkspace:()=> <p>Existing editor remains mounted</p>}));
const original=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));
afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:original,configurable:true}));
afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();localStorage.clear();});
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'a',withheldExample:'b'};
const load=()=>new RF2Client(async()=>new Response(JSON.stringify(structuredClone(fixture.catalog)))).catalog(config.start,config.end);
function courseEvidence(catalog:Awaited<ReturnType<typeof load>>,id:string,category:string,fact:Record<string,unknown>,note:Record<string,unknown>|null=null):Evidence{
 const kind=String(fact.kind??'circulatory_event');
 const source={...fact,kind,id,revision:'1',binding:{target:{patient_id:config.patient,encounter_id:config.encounter}}};
 return {repository:catalog.repository,fact:source as Evidence['fact'],canonical_fact:'{}',digest:id,ingestion:{repository_id:catalog.repository,ingestion_sequence:1},cutoff:catalog.cutoff.fact_watermark,terminal_reference:{kind,id,version:'1'},superseded:false,metadata:{version:1,chart:{category,amount:null,unit:null,missing_reason:null,point:'2026-10-08T09:00:00Z'} as unknown as NonNullable<Evidence['metadata']>['chart'],note:note as never}};
}
it('groups readings without losing a source, altering its decimal text or inventing a current measurement',async()=>{
 const catalog=await load(),before=JSON.stringify(catalog);const model=patientOverviewModel(catalog,config);expect(model.valid).toBe(true);expect(model.findings.find(g=>g.label==='Creatinine')?.records).toHaveLength(2);expect(model.findings.flatMap(g=>g.records).map(e=>pin(e))).toEqual(expect.arrayContaining(catalog.items.map(e=>pin(e))));expect(model.findings.flatMap(g=>g.records)).toHaveLength(catalog.items.length);expect(JSON.stringify(catalog)).toBe(before);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);expect(screen.getAllByRole('heading',{name:'Creatinine'})).toHaveLength(1);const group=screen.getByRole('heading',{name:'Creatinine'}).closest('article')!;expect(group).toHaveTextContent('2 recorded sources');fireEvent.click(within(group).getByText('View recorded details'));expect(group).toHaveTextContent('1.00 mg/dL');expect(group).toHaveTextContent('2.000 mg/dL');expect(screen.getByText(/A combined clinical interpretation has not been generated/)).toBeVisible();
});
it('organizes the overview as a recorded patient course with explicit clinical areas',async()=>{
 const catalog=await load(),model=patientOverviewModel(catalog,config);
 expect(model).toHaveProperty('courseSections');
 expect(model.courseSections.map(section=>section.label)).toEqual([
  'Kidney function, electrolytes and urine',
  'Cultures and antibiotics',
  'Circulation and support',
  'Other recorded findings',
 ]);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);
 expect(screen.getByRole('region',{name:'Recorded course by area'})).toBeVisible();
 expect(screen.getByRole('heading',{name:'Kidney function, electrolytes and urine'})).toBeVisible();
 expect(screen.getByText(/Expand a finding to inspect each source and its correction history/)).toBeVisible();
});
it('places the live culture and antibiotic summary inside the course section',async()=>{
 const catalog=await load();render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} antibioticOverview={<p>Final culture and administered antibiotic source</p>}/>);
 const infection=screen.getByRole('region',{name:'Cultures and antibiotics'});expect(within(infection).getByText('Final culture and administered antibiotic source')).toBeVisible();expect(within(infection).queryByText(/No culture finding is available/)).not.toBeInTheDocument();
});
it('orders individual course observations by source time and keeps report status visible',async()=>{
 const catalog=await load(),repo=catalog.repository,cutoff=catalog.cutoff.fact_watermark;
 const observation=(id:string,category:string,at:string,sequence:number)=>({repository:repo,cutoff,canonical_fact:'{}',digest:id,ingestion:{repository_id:repo,ingestion_sequence:sequence},terminal_reference:{kind:'observation',id,version:'1'},superseded:false,metadata:{version:1,chart:{category,amount:'1.20',unit:'mg/dL'},note:null},fact:{kind:'observation',id,revision:'1',binding:{target:{patient_id:config.patient,encounter_id:config.encounter}},recorded_amount:{value:'1.20',unit:{raw:'mg/dL'}},occurred:{recorded:{value:at}},record_status:'recorded'}});
 catalog.items=[observation('creatinine-0830','creatinine','2026-10-08T08:30:00Z',1) as unknown as Evidence,observation('creatinine-0930','creatinine','2026-10-08T09:30:00Z',2) as unknown as Evidence,observation('map-0900','mean_arterial_pressure','2026-10-08T09:00:00Z',3) as unknown as Evidence];
 const pending={...observation('potassium-preliminary','laboratory','2026-10-08T09:15:00Z',4),fact:{kind:'laboratory_report',id:'potassium-preliminary',revision:'1',binding:{target:{patient_id:config.patient,encounter_id:config.encounter}},source_identity:{issuer_namespace:'synthetic-lab',source_report_id:'K-1',source_version:'1'},specimen:{specimen_type:{raw_display:'Serum'}},report_status:'preliminary',change_state:'original',components:[{test_code:{raw_display:'Potassium'},mapped_concept:'potassium',result:{kind:'numeric',raw_value:'4.2',unit:{raw_display:'mmol/L'}}}],times:{collected:{status:'known',value:'2026-10-08T09:45:00Z'},reported:{status:'not_recorded'},available:{status:'not_recorded'}}}} as unknown as Evidence;
 catalog.laboratory_reports=[pending];
 const model=patientOverviewModel(catalog,config);
 expect(model.courseSections.find(section=>section.id==='kidney')?.events.map(event=>event.label)).toEqual(['Potassium','Creatinine','Creatinine']);
 expect(model.courseSections.find(section=>section.id==='kidney')?.events.map(event=>event.timestamp)).toEqual(['2026-10-08T09:45:00Z','2026-10-08T09:30:00Z','2026-10-08T08:30:00Z']);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);
 expect(screen.getAllByText('Preliminary')).toHaveLength(2);
 expect(screen.getByText(/Latest recorded in selected period · collected/)).toBeVisible();
});
it('summarizes narrative, categorical, contextual and explicitly missing source content by type',async()=>{
 const catalog=await load();catalog.items=[
  courseEvidence(catalog,'display-rhythm','rhythm',{kind:'circulatory_ecg',rhythm:{raw_display:'Sinus rhythm'}}),
  courseEvidence(catalog,'display-rv-function','rv_function',{kind:'circulatory_echo',finding:{raw_display:'Reduced right ventricular systolic function'}}),
  courseEvidence(catalog,'display-note','clinician_review',{kind:'circulatory_assessment'}, {question:'Is the rhythm change new?',findings:'Source ECG reports atrial ectopy.'}),
  courseEvidence(catalog,'display-event','context_event',{kind:'circulatory_event',event_type:'Ventilator adjustment',description:{raw_display:'PEEP increased to 8 cm H₂O'}}),
  courseEvidence(catalog,'display-missing-creatinine','creatinine',{kind:'observation',concept_id:'synthetic-serum-creatinine',value:{status:'missing',reason:'not_reported'}}),
 ];
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);
 expect(screen.getAllByText(/Sinus rhythm/)[0]).toBeVisible();
 expect(screen.getAllByText(/Reduced right ventricular systolic function/)[0]).toBeVisible();
 expect(screen.getAllByText(/Is the rhythm change new\?/)[0]).toBeVisible();
 expect(screen.getAllByText(/PEEP increased to 8 cm H₂O/)[0]).toBeVisible();
 expect(screen.getAllByText(/Numerical result unavailable: not reported/)[0]).toBeVisible();
 expect(screen.queryByText(/Source amount unavailable; inspect context/)).not.toBeInTheDocument();
});
it('heads a withdrawn numeric source with its withdrawn status and retains the historical amount',async()=>{
 const catalog=await load();catalog.items=[courseEvidence(catalog,'display-withdrawn-iv','input_iv',{kind:'circulatory_event',recorded_amount:{value:'50',unit:{raw:'mL'}},record_status:'withdrawn',withdrawal_reason:'Duplicate chart entry withdrawn by source author.'})];
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);
 const entry=screen.getByRole('heading',{name:'IV fluid input'}).closest('article')!;
 expect(entry).toHaveTextContent('Withdrawn source record');
 expect(entry).toHaveTextContent('Historical value: 50 mL');
 expect(entry).not.toHaveTextContent(/^50 mL Latest recorded/);
 fireEvent.click(within(entry).getByText('View recorded details'));
 expect(entry).toHaveTextContent('Duplicate chart entry withdrawn by source author.');
});
it.each(['patient','period','cutoff','laboratory-scope'] as const)('withholds mismatched %s context rather than presenting unrelated prior data',async change=>{
 const catalog=await load();const requested={...config};if(change==='patient')requested.patient='other';if(change==='period')requested.start='2026-10-07T08:00:00Z';if(change==='cutoff')catalog.cutoff.fact_watermark++;if(change==='laboratory-scope')catalog.combined.laboratory.scope.patient_id='other';
 render(<PatientOverview catalog={catalog} status="current" requested={requested} guarded={false}/>);expect(screen.getByRole('alert')).toHaveTextContent('Overview withheld');expect(screen.queryByRole('heading',{name:'Creatinine'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:/Open recorded source/})).not.toBeInTheDocument();
});
it('labels retained data and prevents stale source opening while keeping old values inspectable',async()=>{const catalog=await load(),history=vi.fn();render(<PatientOverview catalog={catalog} status="retained" requested={config} guarded={false} retrievalMessage="Request failed" transport={{history}}/>);expect(screen.getByRole('alert')).toHaveTextContent('Retained prior data — not confirmed current');for(const toggle of screen.getAllByText('View recorded details'))fireEvent.click(toggle);for(const button of screen.getAllByRole('button',{name:/Open recorded source/})){expect(button).toBeDisabled();fireEvent.click(button);}expect(history).not.toHaveBeenCalled();expect(screen.getByText('35.0000 mL',{selector:'strong'})).toBeVisible();});
it('uses one catalog load and direct exact-source history without legacy workflow destinations',async()=>{
 const catalog=await load(),source=catalog.items.find(e=>e.fact.concept_id==='synthetic-serum-creatinine')!;
 vi.stubEnv('VITE_SYNTHETIC_RF2','true');const send=vi.fn<typeof fetch>().mockImplementation(async(url,init)=>{
  if(String(url).includes('/synthetic-rf2?'))return new Response(JSON.stringify(structuredClone(fixture.catalog)));
  if(String(url).endsWith('/history')){const body=JSON.parse(String(init?.body));expect(body).toEqual({repository:source.repository,pins:[pin(source)]});return new Response(JSON.stringify({repository:source.repository,selected:pin(source),items:[source],execution_enabled:false}));}
  throw Error('Unexpected request');
 });vi.stubGlobal('fetch',send);
 render(<PatientWorkspace client={new RenalFluidClient('http://127.0.0.1:5201',config.patient,config.encounter)} entry={new EvidenceEntryClient()} config={config}/>);
 const overview=await screen.findByRole('region',{name:'Connected patient overview'});await within(overview).findByRole('heading',{name:'Creatinine'});expect(send).toHaveBeenCalledTimes(1);for(const name of ['Source entry and reassessment','Compare notes','Handover','Renal charting and handover'])expect(screen.queryByRole('button',{name})).not.toBeInTheDocument();const group=within(overview).getByRole('heading',{name:'Creatinine'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));const trigger=within(group).getByRole('button',{name:`Open recorded source ${source.fact.id} / ${source.fact.revision}`});fireEvent.click(trigger);
 const dialog=await screen.findByRole('dialog',{name:'Creatinine'});await waitFor(()=>expect(within(dialog).queryByRole('status')).not.toBeInTheDocument());expect(dialog).toHaveTextContent('1.00 mg/dL');expect(send).toHaveBeenCalledTimes(2);fireEvent.click(within(dialog).getByRole('button',{name:'Close source details'}));expect(group.querySelector('details')).toHaveAttribute('open');expect(trigger).toHaveFocus();fireEvent.click(trigger);await waitFor(()=>expect(screen.getByRole('dialog',{name:'Creatinine'})).toBeVisible());expect(within(screen.getByRole('dialog')).getByRole('heading',{name:'Creatinine'})).toHaveFocus();
});
it('keeps the selected source visible if its history fails without substituting another record',async()=>{
 const catalog=await load(),source=catalog.items.find(e=>e.metadata?.chart?.category==='output_urine')!,history=vi.fn(async()=>{throw Error('Unavailable');});render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} transport={{history}}/>);const group=screen.getByRole('heading',{name:'Urine output'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));fireEvent.click(within(group).getByRole('button',{name:/Open recorded source/}));const dialog=await screen.findByRole('dialog',{name:'Urine output'});expect(await within(dialog).findByRole('alert')).toHaveTextContent('no different version was substituted');expect(dialog).toHaveTextContent('35.0000 mL');expect(history).toHaveBeenCalledExactlyOnceWith(source);
});
it('ignores delayed history after closing a source and opening a different one',async()=>{
 const catalog=await load(),sources=catalog.items.filter(e=>e.fact.concept_id==='synthetic-serum-creatinine');let finish:(v:Evidence[])=>void=()=>{};const history=vi.fn().mockImplementationOnce(()=>new Promise<Evidence[]>(resolve=>{finish=resolve;})).mockResolvedValue([sources[1]]);
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} transport={{history}}/>);const group=screen.getByRole('heading',{name:'Creatinine'}).closest('article')!;fireEvent.click(within(group).getByText('View recorded details'));fireEvent.click(within(group).getByRole('button',{name:`Open recorded source ${sources[0].fact.id} / ${sources[0].fact.revision}`}));fireEvent.click(screen.getByRole('button',{name:'Close source details'}));fireEvent.click(within(group).getByRole('button',{name:`Open recorded source ${sources[1].fact.id} / ${sources[1].fact.revision}`}));const dialog=await screen.findByRole('dialog',{name:'Creatinine'});await waitFor(()=>expect(within(dialog).queryByRole('status')).not.toBeInTheDocument());finish([sources[0]]);await waitFor(()=>expect(dialog).toHaveTextContent('2.000 mg/dL'));expect(dialog).not.toHaveTextContent('1.00 mg/dL');
});
it('offers the supported fluid-chart workflow from Add information',async()=>{
 const catalog=await load(),onCharting=vi.fn();render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false} weightEntryEnabled onRefresh={async()=>{}} onCharting={onCharting}/>);
 fireEvent.click(screen.getByRole('button',{name:'Add information'}));const chooser=screen.getByRole('dialog',{name:'Add information'});expect(within(chooser).getByRole('button',{name:'Recorded weight'})).toBeVisible();fireEvent.click(within(chooser).getByRole('button',{name:'Fluid or urine chart entry'}));expect(onCharting).toHaveBeenCalledOnce();expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('surfaces the latest M7 and M8 reviews with current versus historical evidence status',async()=>{
 const catalog=await load(),scope=catalog.combined.context.scope,signature=JSON.stringify([scope.patient_id,scope.encounter_id,scope.review_start,scope.review_end,catalog.repository,catalog.cutoff.fact_watermark]);
 const save=(domain:'M7'|'M8',id:string,recordedAt:string,reviewSignature:string)=>localStorage.setItem(reviewStoragePrefix({domain,patient:config.patient,encounter:config.encounter,repository:catalog.repository})+id,JSON.stringify({format:'clinrx-local-review',version:1,id,domain,patient:config.patient,encounter:config.encounter,repository:catalog.repository,period:{start:config.start,end:config.end},snapshot:{signature:reviewSignature,cutoff:catalog.cutoff,pins:[]},draft:{action:'perfusion',reviewer:id.endsWith('new')?'Latest M7 reviewer':domain+' reviewer',rationale:domain+' source review',nextReview:'After reassessment'},recordedAt}));
 save('M7','m7-old','2026-10-08T08:00:00Z',signature);save('M7','m7-new','2026-10-08T09:00:00Z',signature);save('M8','m8-old','2026-10-08T09:30:00Z','historical-signature');
 render(<PatientOverview catalog={catalog} status="current" requested={config} guarded={false}/>);
 const reviews=screen.getByRole('region',{name:'Clinician reviews and next plans'});
 expect(within(reviews).getByText(/Latest M7 reviewer/)).toBeInTheDocument();expect(within(reviews).queryByText(/M7 reviewer · Reviewed 2026-10-08T08:00:00Z/)).not.toBeInTheDocument();expect(within(reviews).getByText('M7 source review')).toBeInTheDocument();expect(within(reviews).getByText('Current evidence snapshot')).toBeInTheDocument();
 expect(within(reviews).getByText(/M8 reviewer/)).toBeInTheDocument();expect(within(reviews).getByText('Historical · evidence snapshot differs or is unconfirmed')).toBeInTheDocument();expect(within(reviews).getAllByText('After reassessment')).toHaveLength(2);
});
