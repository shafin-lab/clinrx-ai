import {afterAll,beforeAll,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,type Evidence} from '../src/api/rf2Client';
import {LaboratoryEntryDialog} from '../src/demo/LaboratoryEntryDialog';
const priorCrypto=globalThis.crypto;const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:priorCrypto,configurable:true}));
it('records fibrinogen method and source units through the shared laboratory owner',async()=>{
 const catalog=await new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 const save=vi.fn(async(_repo:string,_fact:Record<string,unknown>)=>({}) as Promise<Evidence>);
 render(<LaboratoryEntryDialog catalog={catalog} transport={{importLaboratory:save}} onClose={vi.fn()} onRefresh={vi.fn(async()=>{})}/>);
 for(const [label,value] of [['Issuer namespace','hospital.lab'],['Source report ID','coag-1'],['Source version','1'],['Specimen type','Citrated plasma'],['Test code','FIB'],['Source test display','Fibrinogen'],['Result exactly as reported','150.00'],['Source unit','mg/dL'],['Source assay or method','Clauss'],['Collected at · source time with offset','2026-10-08T09:00:00+00:00'],['Available at · source time with offset','2026-10-08T09:15:00+00:00']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
 fireEvent.change(screen.getByLabelText('Shared mapping'),{target:{value:'fibrinogen'}});fireEvent.click(screen.getByRole('button',{name:'Save source report'}));await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));
 const fact=save.mock.calls[0][1] as Record<string,any>;expect(fact.components[0]).toMatchObject({mapped_concept:'fibrinogen',assay:{raw_display:'Clauss'},result:{raw_value:'150.00',unit:{raw_display:'mg/dL'}}});
 expect(screen.getByRole('option',{name:'Ionised calcium'})).toHaveValue('ionised_calcium');expect(screen.getByRole('option',{name:'Total calcium'})).toHaveValue('total_calcium');
});
