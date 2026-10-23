import {render,screen,fireEvent,waitFor,within,cleanup} from '@testing-library/react';
import {it,expect,vi,afterEach,beforeEach} from 'vitest';
import {TransfusionWorkspace} from '../src/transfusion/TransfusionWorkspace';
import {extractLaboratory} from '../src/transfusion/model';
import type {M10Transport} from '../src/transfusion/types';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const snapshot={repository:'repo',cutoff:1,patient_id:requested.patient,encounter_id:requested.encounter,items:[],totals:{groups:[],complete:true},evidence:[],execution_enabled:false};
const shared:any={repository:'repo',cutoff:{fact_watermark:1},items:[],laboratory_reports:[],respiratory_records:[]};
const props={catalog:shared,requested,current:true,loading:false,onRefresh:vi.fn().mockResolvedValue(undefined)};
function transport(){return {catalog:vi.fn().mockResolvedValue(snapshot),profiles:vi.fn().mockResolvedValue({devices:[{id:'teg6s',label:'TEG 6s Global Hemostasis',device:'TEG 6s',configuration:'Global Hemostasis',channels:[{assay:'CK',label:'CK',parameters:[{name:'R',unit:'min'},{name:'MA',unit:'mm'}]}],source_ids:[],mapping_status:'verified'}],protocols:[]}),validate:vi.fn().mockResolvedValue({status:'validated'}),save:vi.fn().mockResolvedValue({status:'saved'}),lookup:vi.fn().mockResolvedValue({status:'absent'}),history:vi.fn().mockResolvedValue({items:[]})} as unknown as M10Transport;}
const fill=(d:HTMLElement,rows:string[][])=>rows.forEach(([label,value])=>fireEvent.change(within(d).getByLabelText(label),{target:{value}}));
async function save(d:HTMLElement){fireEvent.click(within(d).getByRole('button',{name:'Review record'}));fireEvent.click(await within(d).findByRole('button',{name:'Confirm and save record'}));await within(d).findByText('Record saved and evidence refreshed.');}
beforeEach(()=>{localStorage.clear();sessionStorage.clear();});afterEach(cleanup);
it('offers seven products and starts a clean next transfusion after confirmed save',async()=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);
 for(const label of ['PRBC','Fresh frozen plasma (FFP)','RDP','SDP','Cryoprecipitate','PCC','Human fibrinogen concentrate'])expect(await screen.findByRole('button',{name:'Record '+label})).toBeEnabled();
 fireEvent.click(screen.getByRole('button',{name:'Record PRBC'}));let d=screen.getByRole('dialog');expect(within(d).getByLabelText('Product')).toHaveValue('prbc');
 fill(d,[['Source record ID','first-bag'],['Source institution or issuer','Bank'],['Documented by','Clinician'],['Indication','Bleeding'],['Delivered count','10'],['Leukodepleted','yes'],['Irradiated','yes']]);await save(d);
 fireEvent.click(within(d).getByRole('button',{name:'Record another transfusion'}));d=screen.getByRole('dialog');
 expect(within(d).getByLabelText('Source record ID')).toHaveValue('');expect(within(d).getByLabelText('Delivered count')).toHaveValue('');expect(within(d).getByLabelText('Leukodepleted')).toHaveValue('unknown');expect(within(d).getByLabelText('Irradiated')).toHaveValue('unknown');
 fill(d,[['Source record ID','second-product'],['Source institution or issuer','Bank'],['Documented by','Clinician'],['Indication','Bleeding'],['Product','ffp'],['Delivered count','10']]);await save(d);
 const [a,b]=(t.save as any).mock.calls.map((x:any)=>x[0]);expect(a.id).not.toBe(b.id);expect(a.command_id).not.toBe(b.command_id);expect(a.data.delivery_id).not.toBe(b.data.delivery_id);expect(b.predecessor).toBeNull();expect(b.data.product.preparation).toBe('ffp');
});
it('shows plain PRBC and separate processing attributes while retaining source wording',async()=>{
 const t=transport();(t.catalog as any).mockResolvedValue({...snapshot,items:[{fact:{kind:'transfusion_administration',id:'prbc1',revision:'1',data:{title:'PRBC leukodepleted and irradiated',product:{family:'prbc',preparation:'prbc',label:'Leukodepleted irradiated PRBC',modifications:[{name:'leukodepleted',value:'yes'},{name:'irradiated',value:'yes'}]},status:'completed',amounts:[]}},digest:'a'.repeat(64)}]});
 render(<TransfusionWorkspace {...props} transport={t}/>);expect(await screen.findByRole('heading',{name:'PRBC'})).toBeVisible();expect(screen.getByText('Leukodepleted: Yes')).toBeVisible();expect(screen.getByText('Irradiated: Yes')).toBeVisible();expect(screen.getByText('PRBC leukodepleted and irradiated')).toBeInTheDocument();
});
it('shows the seven product subtotals without conflating dose and unit counts',async()=>{
 const t=transport();(t.catalog as any).mockResolvedValue({...snapshot,totals:{complete:false,groups:[['prbc','prbc','10','units','component units'],['plasma','ffp','10','units','component units'],['platelets','platelets_sdp','1','units','apheresis units'],['platelets','platelets_rdp','6','units','component units'],['cryoprecipitate','cryo','10','units','component units'],['pcc','pcc','1000','IU','factor IX'],['fibrinogen_concentrate','fibrinogen_concentrate','2','g','fibrinogen_concentrate']].map(([family,preparation,known_subtotal,unit,basis])=>({family,preparation,known_subtotal,unit,basis,dimension:unit==='IU'||unit==='g'?'dose':'count'}))}});
 render(<TransfusionWorkspace {...props} transport={t}/>);const table=await screen.findByRole('table',{name:'Received products by type'});
 for(const [product,value] of [['PRBC','10 units'],['Fresh frozen plasma (FFP)','10 units'],['SDP','1 units'],['RDP','6 units'],['Cryoprecipitate','10 units'],['PCC','1000 IU'],['Human fibrinogen concentrate','2 g']]){const row=within(table).getAllByRole('row').find(r=>within(r).queryByRole('rowheader',{name:product}));expect(row).toBeDefined();expect(row!).toHaveTextContent(value);}
});
it('separates ROTEM assays and marks missing cartridge parameters unreported',async()=>{
 const t=transport();(t.profiles as any).mockResolvedValue({devices:[{id:'sigma-hep',device:'ROTEM sigma',label:'ROTEM sigma Complete + HEP',channels:['EXTEM C','INTEM C','FIBTEM C','HEPTEM C'].map(assay=>({assay,label:assay,parameters:[{name:'A5',unit:'mm'},{name:'MCF',unit:'mm'}]}))}],protocols:[]});
 (t.catalog as any).mockResolvedValue({...snapshot,items:[{fact:{kind:'viscoelastic_report',id:'rotem1',revision:'1',data:{title:'ROTEM source',device:'ROTEM sigma',cartridge:'Complete + HEP',profile_id:'sigma-hep',observations:[{id:'e',assay:'EXTEM C',parameter:'A5',value:'38',unit:'mm',state:'final'},{id:'f',assay:'FIBTEM C',parameter:'A5',value:'7',unit:'mm',state:'final'}]}},digest:'a'.repeat(64)}]});
 render(<TransfusionWorkspace {...props} transport={t}/>);fireEvent.click(screen.getByRole('tab',{name:'TEG & ROTEM'}));
 for(const assay of ['EXTEM C','INTEM C','FIBTEM C','HEPTEM C'])expect(await screen.findByRole('region',{name:assay})).toBeVisible();
 expect(within(screen.getByRole('region',{name:'EXTEM C'})).getByRole('row',{name:/A5/})).toHaveTextContent('38');expect(within(screen.getByRole('region',{name:'INTEM C'})).getByRole('row',{name:/MCF/})).toHaveTextContent('Not reported');expect(within(screen.getByRole('region',{name:'FIBTEM C'})).getByRole('row',{name:/A5/})).toHaveTextContent('7');
});
it('groups every selected TEG cartridge entry parameter inside its assay',async()=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);fireEvent.click(screen.getByRole('tab',{name:'TEG & ROTEM'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Record TEG or ROTEM report'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Record TEG or ROTEM report'}));const d=screen.getByRole('dialog');fill(d,[['Device and cartridge','teg6s']]);
 const assay=within(d).getByRole('group',{name:'CK'});expect(within(assay).getByLabelText('CK R · value')).toBeVisible();expect(within(assay).getByLabelText('CK MA · value')).toBeVisible();
});
it('offers manual laboratory source entry from the laboratory-only view',async()=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);fireEvent.click(screen.getByRole('tab',{name:'Coagulation & calcium'}));const button=await screen.findByRole('button',{name:'Enter laboratory result'});await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button);expect(await screen.findByRole('dialog',{name:'Record a laboratory source result'})).toBeVisible();
});
it('never displays a calcium medication dose as a calcium laboratory result',()=>{
 const medicine:any={fact:{id:'calcium-dose',revision:'1',kind:'medication_administration',concept:'calcium',result:{quantity:{value:'1000',unit:{raw:'mg'}}}}};
 expect(extractLaboratory({items:[medicine],laboratory_reports:[],respiratory_records:[]} as any)).toEqual([]);
});
it('constrains fibrinogen to grams and submits the exact entered dose',async()=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Record product or event'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Record product or event'}));const d=screen.getByRole('dialog');
 fill(d,[['Source record ID','dose-unit'],['Source institution or issuer','Chart'],['Documented by','Clinician'],['Indication','Bleeding'],['Product','fibrinogen_concentrate'],['Delivered medicine dose · PCC IU / fibrinogen grams','2']]);
 const unit=within(d).getByLabelText('Original medicine dose unit');expect(unit).toHaveValue('g');expect(within(unit).queryByRole('option',{name:'mg'})).not.toBeInTheDocument();await save(d);
 expect((t.save as any).mock.calls[0][0].data.amounts).toContainEqual({dimension:'dose',value:'2',unit:'g',basis:'fibrinogen_concentrate'});
});
it.each([
 ['PRBC','prbc','10','count','units'],['Fresh frozen plasma (FFP)','ffp','10','count','units'],
 ['SDP','platelets_sdp','1','count','units'],['RDP','platelets_rdp','6','count','units'],
 ['Cryoprecipitate','cryo','10','count','units'],['PCC','pcc','1000','dose','IU'],
 ['Human fibrinogen concentrate','fibrinogen_concentrate','2','dose','g'],
])('records %s from its shortcut with the correct quantity dimension',async(label,product,value,dimension,unit)=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);const button=screen.getByRole('button',{name:'Record '+label});await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button);const d=screen.getByRole('dialog');expect(within(d).getByLabelText('Product')).toHaveValue(product);
 fill(d,[['Source record ID','separate-'+product],['Source institution or issuer','Source chart'],['Documented by','Clinician'],['Indication','Bleeding'],[dimension==='count'?'Delivered count':'Delivered medicine dose · PCC IU / fibrinogen grams',value]]);
 if(product==='pcc')fill(d,[['PCC labelled factor basis','factor IX']]);await save(d);
 const command=(t.save as any).mock.calls[0][0];expect(command.data.product.preparation).toBe(product);expect(command.data.amounts).toEqual([expect.objectContaining({dimension,value,unit})]);expect(command.kind).toBe(dimension==='dose'?'haemostatic_medication_course':'transfusion_administration');
});
it('keeps TEG 6s GH, Lysis and HN cartridge masks separate in report review',async()=>{
 const {VetResults}=await import('../src/transfusion/VetResults');
 const {default:devices}=await import('../../knowledge/m10/device-profiles.json');
 for(const [id,expected] of [
  ['teg6s_gh',{CK:['R','K','alpha','MA'],CKH:['R'],CRT:['MA'],CFF:['MA','FLEV']}],
  ['teg6s_gh_lysis',{CK:['R','LY30'],CRT:['MA'],CFF:['MA']}],
  ['teg6s_gh_hn',{CK:['R','MA'],CKH:['R','LY30'],CRTH:['MA'],CFFH:['MA']}],
 ] as const){
  const profile=devices.find(p=>p.id===id)!;const view=render(<VetResults profile={profile as any} observations={[]}/>);
  for(const [assay,parameters] of Object.entries(expected)){const region=screen.getByRole('region',{name:assay});expect(within(region).getAllByRole('rowheader').map(x=>x.textContent)).toEqual([...parameters]);expect(within(region).getAllByRole('cell').some(x=>x.textContent==='0')).toBe(false);}
  expect(screen.getAllByRole('region')).toHaveLength(Object.keys(expected).length);view.unmount();
 }
});
it('starts an SDP shortcut with the apheresis-unit basis rather than a generic component basis',async()=>{
 const t=transport();render(<TransfusionWorkspace {...props} transport={t}/>);const button=screen.getByRole('button',{name:'Record SDP'});await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button);expect(within(screen.getByRole('dialog')).getByLabelText('Count basis')).toHaveValue('apheresis units');
});
it('retains original M9 haemoglobin from the shared circulatory oxygen blood-gas owner',()=>{
 const source:any={fact:{id:'m7-ABG-HB',revision:'1',kind:'circulatory_oxygen',concept:'hemoglobin',acquisition:{method:'blood_gas'},result:{quantity:{value:'10.2',unit:{raw:'g/dL'}}}}};
 const rows=extractLaboratory({items:[source],laboratory_reports:[],respiratory_records:[]} as any);expect(rows).toHaveLength(1);expect(rows[0].value).toBe('10.2 g/dL');expect(rows[0].source).toBe(source);
});
it.each(['transfusion_request','blood_product_disposition'])('preserves original mg quantities on an unrelated %s correction',async(kind)=>{
 const t=transport();(t.catalog as any).mockResolvedValue({...snapshot,items:[{fact:{kind,id:'request-mg',revision:'1',source_record:'external-request',source_issuer:'Source chart',data:{title:'Historical fibrinogen source',product:{family:'fibrinogen_concentrate',preparation:'fibrinogen_concentrate',label:'Fibrinogen',modifications:[]},status:kind==='blood_product_disposition'?'issued':undefined,indication:'Bleeding',quantities:[{dimension:'dose',value:'2000',unit:'mg',basis:'source requested dose'}]}},digest:'a'.repeat(64)}]});
 render(<TransfusionWorkspace {...props} transport={t}/>);await screen.findByRole('button',{name:'Correct source'});fireEvent.click(screen.getByRole('button',{name:'Correct source'}));const d=screen.getByRole('dialog');expect(within(d).getByLabelText('Original medicine dose unit')).toHaveValue('mg');fill(d,[['Documented by','Clinician'],['Source correction reason','Clarify original source narrative'],['Original notes or narrative','Request detail clarified without changing quantity']]);await save(d);
 expect((t.save as any).mock.calls[0][0].data.quantities).toEqual([{dimension:'dose',value:'2000',unit:'mg',basis:'source requested dose'}]);
});
it.each(['transfusion_request','blood_product_disposition'])('keeps the displayed mg unit coherent with a numeric %s correction',async(kind)=>{
 const t=transport();(t.catalog as any).mockResolvedValue({...snapshot,items:[{fact:{kind,id:'request-number',revision:'1',source_record:'external-request',source_issuer:'Source chart',data:{title:'Original mg request',product:{family:'fibrinogen_concentrate',preparation:'fibrinogen_concentrate',label:'Fibrinogen',modifications:[]},status:kind==='blood_product_disposition'?'issued':undefined,indication:'Bleeding',quantities:[{dimension:'dose',value:'2000',unit:'mg',basis:'source requested dose'}]}},digest:'a'.repeat(64)}]});
 render(<TransfusionWorkspace {...props} transport={t}/>);fireEvent.click(await screen.findByRole('button',{name:'Correct source'}));const d=screen.getByRole('dialog');expect(within(d).getByLabelText('Original medicine dose unit')).toHaveValue('mg');fill(d,[['Documented by','Clinician'],['Source correction reason','Correct source numeric transcription'],['Requested / issued medicine dose','2200']]);await save(d);
 expect((t.save as any).mock.calls[0][0].data.quantities).toEqual([{dimension:'dose',value:'2200',unit:'mg',basis:'source requested dose'}]);
});
