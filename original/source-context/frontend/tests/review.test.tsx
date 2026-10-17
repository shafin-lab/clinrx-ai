import { describe,it,expect,vi } from 'vitest';
import { render,screen,within,waitFor,act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReviewClient } from '../src/api/client';
import type { PatientState,Execution } from '../src/api/types';
import { PatientReviewPage } from '../src/patient/PatientReviewPage';
import fixture from './fixtures.json';
const state=fixture.state, result=fixture.execution;
const id=result.execution_id, command='opaque.command.DO_NOT_DECODE';
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:state.scope.review_start,end:state.scope.review_end};
const prepared={status:'prepared',execution_id:id,inference_reference:result.provenance.inference.reference,command};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','X-ClinRx-Mode':'historical-synthetic-simulation'}});
function setup(tail:Array<Response|Error>=[],timeoutMs=30_000) {
  const replies=[json(state),json(prepared),...tail];
  const fetcher=vi.fn<typeof fetch>().mockImplementation(async()=>{const reply=replies.shift();if(reply instanceof Error)throw reply;if(!reply)throw Error('No response queued');return reply;});
  vi.spyOn(crypto,'randomUUID').mockReturnValue(id as `${string}-${string}-${string}-${string}-${string}`);
  const rendered=render(<PatientReviewPage client={new ReviewClient('http://127.0.0.1:8000',config.patient,config.encounter,fetcher,timeoutMs)} config={config}/>);
  return {fetcher,user:userEvent.setup(),...rendered};
}
async function select(user:ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button',{name:'Load state'}));
  await user.click(await screen.findByRole('radio',{name:'Select A demo-creatinine-A revision 1'}));
  await user.click(screen.getByRole('radio',{name:'Select B demo-creatinine-B revision 1'}));
  await user.click(screen.getByRole('radio',{name:'Select M demo-medication-M revision 1'}));
}
async function prepare(user:ReturnType<typeof userEvent.setup>) {await select(user);await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByRole('button',{name:'Run protected review'});}
describe('evidence and preparation',()=>{
  it('loads exact strings and ten explicit coverage entries',async()=>{
    const {user}=setup();await select(user);
    expect(screen.getByText('1.00')).toBeVisible();expect(screen.getByText('2.000')).toBeVisible();
    await user.click(screen.getByText('Domain coverage · 10 domains'));
    expect(screen.getAllByText('Not mapped')).toHaveLength(8);
    expect(screen.getByText('Medication order')).toBeVisible();
    expect(screen.getByText('Historical synthetic simulation')).toBeVisible();
  });
  it('requires all pins and sends exact refs/digests without automatic execution',async()=>{
    const {user,fetcher}=setup();await user.click(screen.getByRole('button',{name:'Load state'}));
    expect(await screen.findByRole('button',{name:'Prepare review'})).toBeDisabled();
    await user.click(screen.getByRole('radio',{name:'Select A demo-creatinine-A revision 1'}));
    expect(screen.getByRole('radio',{name:'Select B demo-creatinine-A revision 1'})).toBeDisabled();
    await user.click(screen.getByRole('radio',{name:'Select B demo-creatinine-B revision 1'}));
    await user.click(screen.getByRole('radio',{name:'Select M demo-medication-M revision 1'}));
    await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByText(/Prepared. The exact/);
    const body=JSON.parse(fetcher.mock.calls[1][1]!.body as string);
    expect(body).toEqual({execution_id:id,state_context:state.state_context,earlier_laboratory:{reference:state.laboratory[0].reference,expected_digest:state.laboratory[0].selection_digest},later_laboratory:{reference:state.laboratory[1].reference,expected_digest:state.laboratory[1].selection_digest},medication:{reference:state.medication[0].reference,expected_digest:state.medication[0].selection_digest}});
    expect(fetcher).toHaveBeenCalledTimes(2);expect(document.body.textContent).not.toContain(command);expect(document.body.textContent).not.toContain(state.state_context);
  });
  it('does not implement temporal eligibility: reversed A/B still reaches backend',async()=>{
    const {user,fetcher}=setup();await user.click(screen.getByRole('button',{name:'Load state'}));
    await user.click(await screen.findByRole('radio',{name:'Select A demo-creatinine-B revision 1'}));await user.click(screen.getByRole('radio',{name:'Select B demo-creatinine-A revision 1'}));await user.click(screen.getByRole('radio',{name:'Select M demo-medication-M revision 1'}));
    await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByText(/Prepared. The exact/);expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it('invalidates old evidence when the review window is edited',async()=>{const {user}=setup();await select(user);await user.type(screen.getByLabelText('Review end'),'0');expect(screen.queryByRole('button',{name:'Prepare review'})).not.toBeInTheDocument();});
  it.each(['completion_unknown','network_error'])('preparation %s never offers execution reconciliation',async(code)=>{
    const {user,fetcher}=setup();fetcher.mockImplementationOnce(async()=>json(state)).mockImplementationOnce(async()=>{if(code==='network_error')throw Error('PRIVATE');return json({code,message:'PRIVATE'},503);});
    await select(user);await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByText('Preparation completion could not be confirmed.');
    expect(screen.queryByRole('button',{name:'Reconcile execution'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(2);expect(document.body.textContent).not.toContain('PRIVATE');
    await user.click(screen.getByRole('button',{name:'Abandon preparation and start again'}));expect(screen.getByRole('button',{name:'Prepare review'})).toBeEnabled();
  });
  it('shows bounded preparation rejection and no execution',async()=>{const {user,fetcher}=setup();fetcher.mockImplementationOnce(async()=>json(state)).mockImplementationOnce(async()=>json({code:'unsupported_review_input',message:'PRIVATE'},422));await select(user);await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByRole('alert');expect(fetcher).toHaveBeenCalledTimes(2);expect(screen.queryByRole('button',{name:'Run protected review'})).not.toBeInTheDocument();});
});
describe('execution and recovery',()=>{
  it('renders exact released statement and retries the identical command',async()=>{const {user,fetcher}=setup([json(result),json(result)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByText(result.provenance.inference.statement!);await user.click(screen.getByRole('button',{name:'Retry same prepared review'}));await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(4));expect(fetcher.mock.calls.slice(2).map(c=>c[1]?.body)).toEqual([JSON.stringify({command}),JSON.stringify({command})]);});
  it('renders a valid withheld receipt with no released statement',async()=>{const withheld={...result,governance:{...result.governance,outcome:'withheld',reasons:['evidence_changed']},provenance:{...result.provenance,inference:{...result.provenance.inference,statement:null}}};const {user}=setup([json(withheld)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByText('Withheld');expect(screen.queryByText(result.provenance.inference.statement!)).not.toBeInTheDocument();expect(screen.queryByRole('alert')).not.toBeInTheDocument();await user.click(screen.getByRole('button',{name:'Why am I seeing this?'}));expect(within(screen.getByRole('dialog')).queryByText(result.provenance.inference.statement!)).not.toBeInTheDocument();});
  it.each(['completion_unknown','network_error','invalid_response'])('holds command after %s and reconciles only explicitly',async(code)=>{
    const unknown=code==='network_error'?Error('PRIVATE'):code==='invalid_response'?new Response('PRIVATE',{status:200}):json({status:'completion_unknown',execution_id:id,next_action:'reconcile',automatic_retry:false},503);
    const {user,fetcher}=setup([unknown,json({status:'committed_match',execution:result})]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByRole('button',{name:'Reconcile execution'});expect(fetcher).toHaveBeenCalledTimes(3);expect(screen.queryByRole('button',{name:'Run protected review'})).not.toBeInTheDocument();await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByText(result.provenance.inference.statement!);expect(fetcher.mock.calls[3][1]?.body).toBe(JSON.stringify({command}));
  });
  it('absent never auto-executes and explicit action reuses exact command',async()=>{const {user,fetcher}=setup([json({status:'completion_unknown'},503),json({status:'absent',execution:null}),json(result)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await user.click(await screen.findByRole('button',{name:'Reconcile execution'}));const run=await screen.findByRole('button',{name:'Run same prepared review'});expect(fetcher).toHaveBeenCalledTimes(4);await user.click(run);await screen.findByText(result.provenance.inference.statement!);expect(fetcher.mock.calls[4][1]?.body).toBe(JSON.stringify({command}));});
  it('reconciliation error preserves uncertainty and command',async()=>{const {user,fetcher}=setup([json({status:'completion_unknown'},503),json({code:'storage_unavailable'},503)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await user.click(await screen.findByRole('button',{name:'Reconcile execution'}));await screen.findByText('storage_unavailable');expect(screen.getByRole('button',{name:'Reconcile execution'})).toBeEnabled();expect(screen.queryByRole('button',{name:'Run same prepared review'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(4);});
  it.each([['execution_conflict',409],['transaction_failed',503]] as const)('renders %s without auto-retry',async(code,status)=>{const {user,fetcher}=setup([json({code,message:'PRIVATE'},status)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));expect(await screen.findByRole('alert')).toHaveTextContent(code);expect(fetcher).toHaveBeenCalledTimes(3);expect(document.body.textContent).not.toContain('PRIVATE');});
});
describe('retained provenance and session lookup',()=>{
  it('opens accessible retained-only provenance without any state request',async()=>{const {user,fetcher}=setup([json(result)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));const button=await screen.findByRole('button',{name:'Why am I seeing this?'});await user.click(button);const dialog=screen.getByRole('dialog',{name:'Why am I seeing this?'});expect(within(dialog).getAllByText('Consumed revision')).toHaveLength(3);expect(within(dialog).getAllByText('Terminal revision')).toHaveLength(3);for(const name of ['A · Earlier laboratory','B · Later laboratory','M · Medication event','Original input cutoff','Inference cutoff','Protected final cutoff','Direct derived_from dependencies'])expect(within(dialog).getByText(name)).toBeVisible();expect(fetcher).toHaveBeenCalledTimes(3);await user.click(within(dialog).getByRole('button',{name:'Close provenance'}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(button).toHaveFocus();});
  it('looks up only a known scoped session ID',async()=>{const {user,fetcher}=setup([json(result),json(result)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByText(result.provenance.inference.statement!);await user.click(screen.getByRole('button',{name:'Retrieve execution '+id}));await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(4));expect(String(fetcher.mock.calls[3][0]).endsWith('/patients/synthetic-p1/encounters/synthetic-e1/temporal-executions/'+id)).toBe(true);expect(screen.getByText(/not the encounter’s complete/)).toBeVisible();});
  it('renders lookup absence as bounded unavailable',async()=>{const {user}=setup([json({code:'not_found',message:'PRIVATE'},404)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Retrieve execution '+id}));expect(await screen.findByRole('alert')).toHaveTextContent('not_found');});
  it('does not persist or console-log clinical payloads or envelopes',async()=>{const log=vi.spyOn(console,'log');const storage=vi.spyOn(Storage.prototype,'setItem');const {user}=setup([json(result)]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByText(result.provenance.inference.statement!);expect(log).not.toHaveBeenCalled();expect(storage).not.toHaveBeenCalled();expect(document.body.textContent).not.toContain(command);});
});

it('rejects malformed state before rendering any evidence',async()=>{
  const {user,fetcher}=setup();fetcher.mockResolvedValueOnce(json({...state,laboratory:null,private:'PRIVATE'}));
  await user.click(screen.getByRole('button',{name:'Load state'}));expect(await screen.findByRole('alert')).toHaveTextContent('invalid_response');
  expect(screen.queryByRole('radio')).not.toBeInTheDocument();expect(document.body.textContent).not.toContain('PRIVATE');expect(fetcher).toHaveBeenCalledTimes(1);
});
it('malformed preparation never becomes an executable command',async()=>{
  const {user,fetcher}=setup();fetcher.mockResolvedValueOnce(json(state)).mockResolvedValueOnce(json({...prepared,inference_reference:null,command:'PRIVATE.COMMAND'}));
  await select(user);await user.click(screen.getByRole('button',{name:'Prepare review'}));await screen.findByText('Preparation completion could not be confirmed.');
  expect(screen.queryByRole('button',{name:'Run protected review'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Reconcile execution'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(2);expect(document.body.textContent).not.toContain('PRIVATE');
});
it.each(['released','withheld'])('malformed committed %s receipt keeps UUID/command for explicit reconciliation',async(outcome)=>{
  const stored=outcome==='released'?result:{...result,governance:{...result.governance,outcome:'withheld'},provenance:{...result.provenance,inference:{...result.provenance.inference,statement:null}}};
  const malformed={...stored,provenance:{private:'PRIVATE'}};
  const {user,fetcher}=setup([json(malformed),json({status:'committed_match',execution:stored})]);let committed=false;
  const implementation=fetcher.getMockImplementation()!;fetcher.mockImplementation(async(input,init)=>{if(String(input).endsWith('/temporal-reviews'))committed=true;return implementation(input,init);});
  await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByRole('button',{name:'Reconcile execution'});
  expect(committed).toBe(true);expect(screen.getByText(/Prepared execution:/)).toHaveTextContent(id);expect(screen.getByText(/Review status:/)).toHaveTextContent('completion unknown');
  expect(screen.queryByRole('region',{name:'Review result'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Retry same prepared review'})).not.toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(3);expect(document.body.textContent).not.toContain('PRIVATE');expect(document.body.textContent).not.toContain(command);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByRole('region',{name:'Review result'});
  expect(fetcher).toHaveBeenCalledTimes(4);expect(fetcher.mock.calls[3][0]).toContain(id+'/reconcile');expect(fetcher.mock.calls[3][1]?.body).toBe(JSON.stringify({command}));
  expect(fetcher.mock.calls.filter(c=>String(c[0]).endsWith('/temporal-reviews'))).toHaveLength(1);
  expect(screen.getByRole('region',{name:'Review result'})).toHaveTextContent(outcome==='released'?'Released':'Withheld');
});
it.each([{status:'absent',execution:result},{status:'committed_match',execution:{}}])('malformed reconciliation %# cannot establish completion or absence',async(malformed)=>{
  const {user,fetcher}=setup([json({status:'completion_unknown'},503),json(malformed),json({status:'committed_match',execution:result})]);
  await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await user.click(await screen.findByRole('button',{name:'Reconcile execution'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('invalid_response');expect(screen.getByText(/Review status:/)).toHaveTextContent('completion unknown');
  expect(screen.queryByRole('button',{name:'Run same prepared review'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(4);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByRole('region',{name:'Review result'});expect(fetcher).toHaveBeenCalledTimes(5);
  expect(fetcher.mock.calls.slice(3).map(c=>c[1]?.body)).toEqual([JSON.stringify({command}),JSON.stringify({command})]);
});
it('malformed retained lookup displays bounded failure without rendering a receipt',async()=>{
  const {user,fetcher}=setup([json({...result,governance:null})]);await prepare(user);await user.click(screen.getByRole('button',{name:'Retrieve execution '+id}));
  expect(await screen.findByRole('alert')).toHaveTextContent('invalid_response');expect(screen.queryByRole('region',{name:'Review result'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(3);
});
it('renders backend-optional missing fields without modifying the response',async()=>{
  const optional=structuredClone(state) as unknown as Record<string,unknown>;
  const labs=optional.laboratory as Record<string,unknown>[];delete labs[0].provenance_limitations;delete labs[0].provenance_actor;delete labs[0].domain;
  const {user,fetcher}=setup();fetcher.mockResolvedValueOnce(json(optional));await select(user);expect(screen.getByText('1.00')).toBeVisible();expect(screen.queryByRole('alert')).not.toBeInTheDocument();expect(labs[0]).not.toHaveProperty('domain');
});

it.each([['projection error',500,'internal_error'],['projection validation error',422,'invalid_request']] as const)('M5 %s after commit remains uncertain until explicit recovery',async(_,status,code)=>{
  const {user,fetcher}=setup([json({code,message:'PRIVATE'},status),json({status:'committed_match',execution:result})]);
  await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));
  expect(await screen.findByRole('alert')).toHaveTextContent(code);expect(screen.getByText(/Review status:/)).toHaveTextContent('completion unknown');
  expect(screen.getByText(/Prepared execution:/)).toHaveTextContent(id);expect(screen.queryByRole('button',{name:'Start a new review'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(3);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByRole('region',{name:'Review result'});
  expect(fetcher).toHaveBeenCalledTimes(4);expect(fetcher.mock.calls[3][1]?.body).toBe(JSON.stringify({command}));expect(document.body.textContent).not.toContain('PRIVATE');
});
it('M5 committed network loss and reconciliation network failure keep the exact command',async()=>{
  const {user,fetcher}=setup([Error('PRIVATE committed connection loss'),Error('PRIVATE reconcile loss'),json({status:'committed_match',execution:result})]);
  let committed=false;const original=fetcher.getMockImplementation()!;fetcher.mockImplementation(async(input,init)=>{if(String(input).endsWith('/temporal-reviews'))committed=true;return original(input,init);});
  await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByRole('button',{name:'Reconcile execution'});expect(committed).toBe(true);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));expect(await screen.findByRole('alert')).toHaveTextContent('network_error');expect(screen.getByText(/Review status:/)).toHaveTextContent('completion unknown');
  expect(fetcher).toHaveBeenCalledTimes(4);await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByRole('region',{name:'Review result'});
  expect(fetcher.mock.calls.slice(3).map(c=>c[1]?.body)).toEqual([JSON.stringify({command}),JSON.stringify({command})]);expect(fetcher).toHaveBeenCalledTimes(5);
});
it('M5 timeout and late released response cannot overwrite newer reconciled withholding',async()=>{
  const retained={...result,governance:{...result.governance,outcome:'withheld'},provenance:{...result.provenance,inference:{...result.provenance.inference,statement:null}}};
  const {user,fetcher}=setup([],50);let finish!:(response:Response)=>void;
  fetcher.mockResolvedValueOnce(json(state)).mockResolvedValueOnce(json(prepared)).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValueOnce(json({status:'committed_match',execution:retained}));
  await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));expect(await screen.findByRole('alert')).toHaveTextContent('request_timeout');
  expect(screen.getByText(/Prepared execution:/)).toHaveTextContent(id);expect(fetcher).toHaveBeenCalledTimes(3);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));const region=await screen.findByRole('region',{name:'Review result'});expect(region).toHaveTextContent('Withheld');
  await act(async()=>{finish(json(result));await new Promise(resolve=>setTimeout(resolve,0));});expect(region).toHaveTextContent('Withheld');expect(screen.queryByText(result.provenance.inference.statement!)).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(4);
});
it('M5 warns during pending/uncertain work and prevents duplicate execution while pending',async()=>{
  const {user,fetcher}=setup();let finish!:(response:Response)=>void;
  fetcher.mockResolvedValueOnce(json(state)).mockResolvedValueOnce(json(prepared)).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  await prepare(user);let leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(false);
  await user.dblClick(screen.getByRole('button',{name:'Run protected review'}));expect(fetcher).toHaveBeenCalledTimes(3);
  leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(true);expect(screen.getByLabelText('Review start')).toBeDisabled();
  finish(json(result));await screen.findByRole('region',{name:'Review result'});
  leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(false);
});
it('M5 unmount invalidates late preparation',async()=>{
  const {user,fetcher,unmount}=setup();let finish!:(response:Response)=>void;
  fetcher.mockResolvedValueOnce(json(state)).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  await select(user);await user.click(screen.getByRole('button',{name:'Prepare review'}));unmount();
  render(<PatientReviewPage client={new ReviewClient('http://localhost:8000',config.patient,config.encounter)} config={config}/>);
  finish(json(prepared));await waitFor(()=>expect(screen.queryByRole('button',{name:'Run protected review'})).not.toBeInTheDocument());
  expect(screen.queryByText(/Prepared execution:/)).not.toBeInTheDocument();
});
it('M5 failed reconciliation retains navigation warning until valid absence',async()=>{
  const {user}=setup([Error('loss'),Error('loss'),json({status:'absent',execution:null})]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));
  await user.click(await screen.findByRole('button',{name:'Reconcile execution'}));await screen.findByRole('alert');let leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(true);
  await user.click(screen.getByRole('button',{name:'Reconcile execution'}));await screen.findByRole('button',{name:'Run same prepared review'});leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(false);
});

it('M5 removes unresolved beforeunload guard on unmount',async()=>{
  const {user,unmount}=setup([Error('loss')]);await prepare(user);await user.click(screen.getByRole('button',{name:'Run protected review'}));await screen.findByRole('button',{name:'Reconcile execution'});
  unmount();const leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(false);
});
