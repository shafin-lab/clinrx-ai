import {describe,it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import fixtures from './fixtures/circulatory.json';
import {CirculatoryClient} from '../src/api/circulatoryClient';
import {CirculatoryReview} from '../src/patient/CirculatoryReview';
import {decodeCirculatoryState as state,decodeCirculatoryPrepared as prepared,decodeCirculatoryExecution as execution,decodeCirculatoryReconciliation as reconciliation,decodeCirculatoryHistory as history} from '../src/api/circulatoryDecoders';
const scope={patient_id:'synthetic-p1',encounter_id:'synthetic-e1'};
const clone=<T,>(v:T):T=>structuredClone(v);
const config={start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00'};
afterEach(()=>{cleanup();vi.useRealTimers();});
describe('M7 complete runtime decoders',()=>{
  it('accepts authoritative state, preparation, released/withheld, reconciliation and correction history',()=>{
    expect(state(fixtures.state,scope).assembly.snapshot.items).toHaveLength(21);
    expect(prepared(fixtures.prepared,scope).inference.inputs).toHaveLength(3);
    expect(execution(fixtures.released,{...scope,execution_id:fixtures.prepared.execution_id}).statement).toContain('Pressure acquisition occurred');
    expect(execution(fixtures.withheld,scope).statement).toBeNull();
    expect(reconciliation({status:'absent',execution:null},scope).status).toBe('absent');
    expect(reconciliation({status:'committed_match',execution:fixtures.released},scope).execution?.execution_id).toBe(fixtures.prepared.execution_id);
    expect(history(fixtures.history,scope).revisions).toHaveLength(2);
  });
  it.each(['binding','quality','quantity','device','time','family'])('rejects malformed nested evidence: %s',part=>{
    const v:any=clone(fixtures.state),f=v.assembly.snapshot.items.find((i:any)=>i.fact.id==='m7-P').fact;
    if(part==='binding')f.binding.target.patient_id='foreign';
    if(part==='quality')f.acquisition.quality.status='perfect';
    if(part==='quantity')f.result.quantity.value=65;
    if(part==='device')f.acquisition.device={technology:'PiCCO'};
    if(part==='time')f.occurred.recorded.value='2026-10-08T08:00:00';
    if(part==='family')f.kind='unsupported';
    expect(()=>state(v,scope)).toThrow('could not be read safely');
  });
  it.each(['scope','uuid','input','terminal','receipt','statement','nested','pin'])('rejects malformed retained response: %s',part=>{
    const v:any=clone(fixtures.released);
    if(part==='scope')v.record.request.inference_request.scope.patient_id='foreign';
    if(part==='uuid')v.execution_id='not-uuid';
    if(part==='input')v.record.evidence.inference.inputs[0].id='substitute';
    if(part==='terminal')v.record.final_recheck.terminal_facts[0].id='foreign';
    if(part==='receipt')v.record.runtime.finalized_at=null;
    if(part==='statement')v.statement='invented';
    if(part==='nested')v.record.evidence.facts[0].acquisition.quality.status='perfect';
    if(part==='pin')v.record.request.inference_request.pressure.expected_digest='0'.repeat(64);
    expect(()=>execution(v,scope)).toThrow('could not be read safely');
  });
  it('rejects wrong expected identity and malformed recovery',()=>{
    expect(()=>execution(fixtures.released,{execution_id:fixtures.prepared2.execution_id})).toThrow();
    expect(()=>prepared(fixtures.prepared,{...scope,patient_id:'foreign'})).toThrow();
    expect(()=>reconciliation({status:'absent',execution:fixtures.released},scope)).toThrow();
    expect(()=>reconciliation({status:'committed_match',execution:null},scope)).toThrow();
    expect(()=>history(fixtures.history,{...scope,reference:{kind:'circulatory_pressure',id:'other',version:'1'}})).toThrow();
  });
  it('preserves Decimal/source time strings and accepts every family',()=>{
    const v=state(fixtures.state,scope);
    expect(new Set(v.assembly.snapshot.items.map(i=>i.fact.kind)).size).toBe(15);
    const l:any=v.assembly.snapshot.items.find(i=>i.fact.id==='m7-L')!.fact;
    expect(l.result.quantity.value).toBe('2.000');expect(l.collected.source_timestamp).toBe('2026-10-08T08:01:00+00:00');
  });
});
function mockClient(){return {circulatoryState:vi.fn().mockResolvedValue({data:state(fixtures.state,scope)}),circulatoryPrepare:vi.fn().mockResolvedValue({data:prepared(fixtures.prepared,scope)}),circulatoryExecute:vi.fn().mockResolvedValue({data:execution(fixtures.released,scope)}),circulatoryReconcile:vi.fn().mockResolvedValue({data:reconciliation({status:'committed_match',execution:fixtures.released},scope)}),circulatoryHistory:vi.fn().mockResolvedValue({data:history(fixtures.history,scope)}),circulatoryLookup:vi.fn().mockResolvedValue({data:execution(fixtures.released,scope)})};}
async function loaded(client:ReturnType<typeof mockClient>){
  const mounted=render(<CirculatoryReview client={client as unknown as CirculatoryClient} config={config}/>);
  fireEvent.click(screen.getByRole('button',{name:'Load circulatory evidence'}));await screen.findByText('m7-P · revision 1');return mounted;
}
async function chosen(client:ReturnType<typeof mockClient>){
  const mounted=await loaded(client);
  for(const [role,id,kind] of [['pressure','m7-P','circulatory_pressure'],['lactate','m7-L','circulatory_lactate'],['vasopressor','m7-V','circulatory_vasoactive']])fireEvent.change(screen.getByLabelText('Select '+role),{target:{value:JSON.stringify([kind,id,'1'])}});
  fireEvent.click(screen.getByRole('button',{name:'Prepare P/L/V review'}));await screen.findByText('Prepared descriptive inference');return mounted;
}
describe('M7 explicit review state',()=>{
  it('browses all families and corrections even with execution gate closed',async()=>{
    const client=mockClient();client.circulatoryState.mockResolvedValue({data:{...state(fixtures.state,scope),execution_enabled:false}});await loaded(client);
    expect(screen.getByText('Cardiac output and performance')).toBeTruthy();expect(screen.getByText('Edwards / PiCCO and monitoring context')).toBeTruthy();expect(screen.getByText('Echo and POCUS')).toBeTruthy();
    expect(screen.getByRole('button',{name:'Prepare P/L/V review'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Inspect corrections for m7-P'}));await screen.findByText('Exact revision history: m7-P');expect(client.circulatoryPrepare).not.toHaveBeenCalled();
  });
  it.each(['network loss','timeout','malformed receipt','post-commit projection failure'])('retains command and reconciles after %s',async reason=>{
    const client=mockClient();client.circulatoryExecute.mockRejectedValue(new Error(reason));await chosen(client);
    fireEvent.click(screen.getByRole('button',{name:'Execute prepared P/L/V review'}));await screen.findByText(/Completion is uncertain/);
    expect(client.circulatoryExecute).toHaveBeenCalledTimes(1);expect(client.circulatoryExecute.mock.calls[0][0]).toEqual(prepared(fixtures.prepared,scope));
    expect(screen.getByRole('button',{name:'Load circulatory evidence'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Reconcile original circulatory command'}));await screen.findByText('Retained decision');
    expect(client.circulatoryReconcile.mock.calls[0][0]).toEqual(prepared(fixtures.prepared,scope));expect(client.circulatoryExecute).toHaveBeenCalledTimes(1);
  });
  it('preserves uncertainty after failed reconciliation and retries only explicitly after absence',async()=>{
    const client=mockClient();client.circulatoryExecute.mockRejectedValueOnce(new Error('lost'));client.circulatoryReconcile.mockRejectedValueOnce(new Error('bad response')).mockResolvedValueOnce({data:{status:'absent',execution:null}} as any);
    await chosen(client);fireEvent.click(screen.getByRole('button',{name:'Execute prepared P/L/V review'}));await screen.findByText(/Completion is uncertain/);
    fireEvent.click(screen.getByRole('button',{name:'Reconcile original circulatory command'}));await screen.findByText(/Completion is uncertain/);
    fireEvent.click(screen.getByRole('button',{name:'Reconcile original circulatory command'}));await screen.findByText(/Absence is not proof of rollback/);
    expect(client.circulatoryExecute).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Explicitly retry same command'}));await screen.findByText('Retained decision');
    expect(client.circulatoryExecute).toHaveBeenCalledTimes(2);expect(client.circulatoryExecute.mock.calls[1][0]).toEqual(prepared(fixtures.prepared,scope));
  });
  it('prevents duplicate execution and discards late responses after unmount',async()=>{
    const client=mockClient();let resolve!:(value:unknown)=>void;client.circulatoryExecute.mockImplementation(()=>new Promise(done=>{resolve=done;}));const mounted=await chosen(client);
    const button=screen.getByRole('button',{name:'Execute prepared P/L/V review'});fireEvent.click(button);fireEvent.click(button);expect(client.circulatoryExecute).toHaveBeenCalledTimes(1);
    const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);
    mounted.unmount();resolve({data:execution(fixtures.released,scope)});await Promise.resolve();expect(screen.queryByText('Retained decision')).toBeNull();
  });
  it('locks view changes during delayed retained-history requests',async()=>{
    const client=mockClient();let resolve!:(v:unknown)=>void;client.circulatoryHistory.mockImplementation(()=>new Promise(done=>{resolve=done;}));await loaded(client);
    fireEvent.click(screen.getByRole('button',{name:'Inspect corrections for m7-P'}));
    expect(screen.getByLabelText('Circulatory review start')).toBeDisabled();
    expect(screen.getByRole('button',{name:'Load circulatory evidence'})).toBeDisabled();
    resolve({data:history(fixtures.history,scope)});await screen.findByText('Exact revision history: m7-P');
    expect(screen.getByLabelText('Circulatory review start')).not.toBeDisabled();
  });
  it('invalidates selections when the window changes',async()=>{const client=mockClient();await loaded(client);fireEvent.change(screen.getByLabelText('Circulatory review start'),{target:{value:'2026-10-08T07:00:00Z'}});expect(screen.queryByLabelText('Select pressure')).toBeNull();expect(client.circulatoryPrepare).not.toHaveBeenCalled();});
});
describe('M7 transport uncertainty',()=>{
  it('does not retry failed POST and sanitizes malformed response',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({private:'payload'}),{status:200}));
    const client=new CirculatoryClient('http://127.0.0.1:8000',scope.patient_id,scope.encounter_id,fetcher);
    await expect(client.circulatoryExecute(prepared(fixtures.prepared,scope))).rejects.toMatchObject({code:'invalid_response'});expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('times out once without interpreting rollback',async()=>{
    vi.useFakeTimers();const fetcher=vi.fn().mockImplementation(()=>new Promise(()=>{}));const client=new CirculatoryClient('http://127.0.0.1:8000',scope.patient_id,scope.encounter_id,fetcher,10);
    const result=client.circulatoryExecute(prepared(fixtures.prepared,scope));const assertion=expect(result).rejects.toMatchObject({code:'request_timeout'});await vi.advanceTimersByTimeAsync(11);await assertion;expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
