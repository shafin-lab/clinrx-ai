import {useState} from 'react';
import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {PatientDoseContext} from '../src/antibioticWorkflow/PatientDoseContext';
import {AntibioticWorkspace} from '../src/antibioticWorkflow/AntibioticWorkspace';
import {RF2Client} from '../src/api/rf2Client';
import {AntibioticClient} from '../src/api/antibioticClient';
import {automaticRenalModel} from '../src/antibioticWorkflow/automaticRenalModel';
import {contextPendingKey} from '../src/antibioticWorkflow/contextRecovery';
import {bundle,requested} from './helpers/prescriptionFixtures';
it('releases the workspace guard after successful legacy recovery and refresh',async()=>{
 const b=await bundle(),c=b.renal,guard=vi.fn();
 const action=vi.spyOn(RF2Client.prototype,'action').mockImplementation(async(kind,body)=>{if(kind==='save')throw Error('response lost');return {status:kind==='lookup'?'saved':'validated',evidence:kind==='lookup'?{}:undefined,source_review:body.note!.pins.map(p=>({selected:p.reference,terminal:p.reference,terminal_digest:p.digest,terminal_ingestion:p.ingestion,record_status:'recorded',retain_historical:false})),execution_enabled:false} as never;});
 const seed=render(<PatientDoseContext catalog={c} model={automaticRenalModel(c)} current disabled={false} onGuardChange={()=>{}} onRefresh={async()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Review patient dosing context'}));fireEvent.change(screen.getByLabelText('Context reviewer'),{target:{value:'Demo reviewer'}});fireEvent.click(screen.getByRole('button',{name:'Validate context review'}));fireEvent.click(await screen.findByRole('button',{name:'Save reviewed patient context'}));await screen.findByRole('button',{name:'Look up pending context'});seed.unmount();
 vi.spyOn(AntibioticClient.prototype,'courseHistory').mockResolvedValue(b.micro);
 function Host(){const [loading,setLoading]=useState(false);return <AntibioticWorkspace bundle={b} requested={requested} loading={loading} error='' onRefresh={async()=>{setLoading(true);await new Promise(resolve=>setTimeout(resolve,1));setLoading(false);}} onGuardChange={guard} onKidney={()=>{}}/>;}
 render(<Host/>);fireEvent.click(await screen.findByRole('button',{name:'Look up pending context'}));
 await waitFor(()=>expect(localStorage.getItem(contextPendingKey(c.repository))).toBeNull());
 await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh patient evidence'})).toBeEnabled());
 expect(guard).toHaveBeenLastCalledWith(false);
});
