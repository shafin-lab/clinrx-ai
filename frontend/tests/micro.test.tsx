import { it,expect,vi } from 'vitest';
import { render,screen,within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MicroReviewClient } from '../src/api/microClient';
import { PatientReviewPage } from '../src/patient/PatientReviewPage';
import { ReviewClient } from '../src/api/client';
import { MicroReview } from '../src/patient/MicroReview';
import type { MicroState,MicroPrepared,MicroExecution } from '../src/api/microTypes';
import fixture from './microFixtures.json';
const state=fixture.state as unknown as MicroState, prepared=fixture.prepared as unknown as MicroPrepared;
const released=fixture.released as unknown as MicroExecution;
const withheld={...fixture.withheld,execution_id:prepared.execution_id} as unknown as MicroExecution;
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:state.assembly.request.scope.review_start,end:state.assembly.request.scope.review_end};
const json=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','X-ClinRx-Mode':'historical-synthetic-simulation'}});
function setup(tail:Array<Response|Error>=[],view=state) {
  const replies=[json(view),json(prepared),...tail];
  const fetcher=vi.fn<typeof fetch>().mockImplementation(async()=>{const r=replies.shift();if(r instanceof Error)throw r;if(!r)throw Error('No response queued');return r;});
  vi.spyOn(crypto,'randomUUID').mockReturnValue(prepared.execution_id as `${string}-${string}-${string}-${string}-${string}`);
  const client=new MicroReviewClient('http://127.0.0.1:8000',config.patient,config.encounter,fetcher);
  const rendered=render(<MicroReview client={client} config={config}/>);
  return {fetcher,client,user:userEvent.setup(),...rendered};
}
async function select(user:ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button',{name:'Load microbiology state'}));
  await screen.findByRole('combobox',{name:'S · Specimen'});
  for(const role of ['S','I','U','D']) {
    const select=screen.getByRole('combobox',{name:new RegExp('^'+role+' ·')});
    await user.selectOptions(select,within(select).getAllByRole('option')[1]);
  }
}
async function prepare(user:ReturnType<typeof userEvent.setup>) {await select(user);await user.click(screen.getByRole('button',{name:'Prepare S/I/U/D review'}));await screen.findByRole('button',{name:'Execute S/I/U/D review'});}
async function execute(user:ReturnType<typeof userEvent.setup>) {await prepare(user);await user.click(screen.getByRole('button',{name:'Execute S/I/U/D review'}));}

it('renders backend hierarchy, source precision, and separate antimicrobial categories',async()=>{
  const {user}=setup();await select(user);
  await user.click(screen.getByText('Specimen demo-S · revision 1'));await user.click(screen.getByText('Isolate demo-I · revision 1'));
  expect(screen.getByText('Recorded MIC: <= 1.000 mg/L')).toBeVisible();
  expect(screen.getByText('Identification: final')).toBeVisible();
  for(const title of ['Orders (1)','Completed administrations (1)','Non-delivery events (1)']) expect(screen.getByText(title)).toBeVisible();
  const d=screen.getByRole('combobox',{name:'D · Completed administration'});
  expect(within(d).getAllByRole('option').map(o=>o.textContent)).toEqual(['Select an exact record','demo-D · revision 1']);
  expect(screen.getByText('Profile: SyntheticMicrobiologyAntimicrobialState / 2')).toBeVisible();
});
it('prepares four exact pins without executing or exposing opaque command',async()=>{
  const {user,fetcher}=setup();const storage=vi.spyOn(Storage.prototype,'setItem');await prepare(user);
  const body=JSON.parse(fetcher.mock.calls[1][1]!.body as string);
  expect(Object.keys(body)).toEqual(['execution_id','state_context','specimen_ref','isolate_ref','susceptibility_ref','administration_ref']);
  expect(['specimen_ref','isolate_ref','susceptibility_ref','administration_ref'].map(k=>body[k].reference.id)).toEqual(['demo-S','demo-I','demo-U','demo-D']);
  expect(body.susceptibility_ref.expected_digest).toBe(state.assembly.snapshot.items.find(i=>i.fact.id==='demo-U')!.expected_digest);
  expect(fetcher).toHaveBeenCalledTimes(2);expect(document.body.textContent).not.toContain(prepared.command);expect(document.body.textContent).not.toContain(state.state_context);expect(storage).not.toHaveBeenCalled();
  expect(screen.getByRole('status')).toHaveFocus();
});
it.each(['S','I','U','D'])('invalidates prepared command on %s change',async(role)=>{
  const {user,fetcher}=setup();await prepare(user);await user.selectOptions(screen.getByRole('combobox',{name:new RegExp('^'+role+' ·')}),'');
  expect(screen.queryByRole('button',{name:'Execute S/I/U/D review'})).not.toBeInTheDocument();
  expect(screen.queryByRole('region',{name:'Prepared descriptive preview'})).not.toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(2);
});
it.each(['Microbiology review start','Microbiology review end'])('invalidates view and command on %s change',async(name)=>{
  const {user}=setup();await prepare(user);await user.clear(screen.getByRole('textbox',{name}));
  expect(screen.queryByRole('button',{name:'Execute S/I/U/D review'})).not.toBeInTheDocument();expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});
it('sends preliminary/mismatched source evidence to backend without clinical filtering',async()=>{
  const view=structuredClone(state);const i=view.assembly.snapshot.items.find(i=>i.fact.id==='demo-I')!;i.fact.identification_state='provisional';
  view.assembly.snapshot.items.find(i=>i.fact.id==='demo-U')!.fact.antimicrobial!.canonical_id='other';
  const {user,fetcher}=setup([],view);await prepare(user);expect(fetcher).toHaveBeenCalledTimes(2);
});
it('shows released content with exact provenance and command-only execution',async()=>{
  const {user,fetcher}=setup([json(released)]);await execute(user);await screen.findByText('Protected descriptive review released');
  const region=screen.getByRole('region',{name:'Microbiology protected result'});expect(within(region).getByText(released.statement!)).toBeVisible();
  await user.click(screen.getByText('Retained provenance · consumed versus final checked'));expect(screen.getByText('S: Unchanged')).toBeVisible();
  expect(JSON.parse(fetcher.mock.calls[2][1]!.body as string)).toEqual({command:prepared.command});
});
it('withholds main statement while preserving original history and terminal correction',async()=>{
  const {user}=setup([json(withheld)]);await execute(user);await screen.findByText('Protected descriptive review withheld');
  expect(screen.queryByText(withheld.provenance.inference.statement,{exact:true})).not.toBeInTheDocument();
  await user.click(screen.getByText('Retained provenance · consumed versus final checked'));
  expect(screen.getByText('U: Corrected / changed')).toBeVisible();expect(screen.getByText('Original inference statement: '+withheld.provenance.inference.statement)).toBeVisible();
  expect(screen.getAllByText('microbiology_susceptibility / demo-U / revision 2').length).toBeGreaterThan(0);
});
it.each([released,withheld])('explicitly reconciles committed $governance.outcome without auto retry',async(result)=>{
  const {user,fetcher}=setup([json({status:'completion_unknown'},503),json({status:'committed_match',execution:result})]);await execute(user);
  await screen.findByText('Execution completion unknown');expect(fetcher).toHaveBeenCalledTimes(3);
  expect(screen.queryByRole('button',{name:'Explicitly execute same command'})).not.toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Reconcile S/I/U/D execution'}));await screen.findByText('Protected descriptive review '+result.governance.outcome);
  expect(fetcher).toHaveBeenCalledTimes(4);expect(fetcher.mock.calls[3][0]).toContain('micro-antimicrobial-review-reconciliations');
});
it('absent reconciliation requires explicit action to execute again',async()=>{
  const {user,fetcher}=setup([json({status:'completion_unknown'},503),json({status:'absent',execution:null}),json(released)]);await execute(user);
  await user.click(await screen.findByRole('button',{name:'Reconcile S/I/U/D execution'}));await screen.findByText(/No retained execution found at reconciliation/);
  expect(fetcher).toHaveBeenCalledTimes(4);await user.click(screen.getByRole('button',{name:'Explicitly execute same command'}));await screen.findByText('Protected descriptive review released');expect(fetcher).toHaveBeenCalledTimes(5);
});
it('network loss becomes unknown only after an actual execution attempt',async()=>{
  const {user,fetcher}=setup([new Error('PRIVATE')]);await execute(user);await screen.findByText('Execution completion unknown');expect(fetcher).toHaveBeenCalledTimes(3);expect(document.body.textContent).not.toContain('PRIVATE');
});
it('preparation error stays separate from execution uncertainty',async()=>{
  const {user,fetcher}=setup();fetcher.mockImplementationOnce(async()=>json(state)).mockImplementationOnce(async()=>json({code:'completion_unknown'},503));
  await select(user);await user.click(screen.getByRole('button',{name:'Prepare S/I/U/D review'}));await screen.findByText('Preparation completion unknown');expect(screen.queryByRole('button',{name:'Reconcile S/I/U/D execution'})).not.toBeInTheDocument();
});
it('retrieves retained session IDs without enriching from current state',async()=>{
  const {user,fetcher}=setup([json(released),json(released)]);await execute(user);await screen.findByText('Protected descriptive review released');
  await user.click(screen.getByText('S/I/U/D reviews in this session (1)'));await user.click(screen.getByRole('button',{name:'Retrieve S/I/U/D execution '+released.execution_id}));
  await screen.findByText('Protected descriptive review released');expect(fetcher).toHaveBeenCalledTimes(4);expect(fetcher.mock.calls[3][1]!.method).toBe('GET');expect(fetcher.mock.calls[3][1]!.cache).toBe('no-store');
});
it('remount clears ephemeral command and history',async()=>{
  const {user,unmount,client}=setup();await prepare(user);unmount();render(<MicroReview client={client} config={config}/>);
  expect(screen.queryByRole('button',{name:'Execute S/I/U/D review'})).not.toBeInTheDocument();expect(screen.getByText('S/I/U/D reviews in this session (0)')).toBeVisible();
});

it('does not hide susceptibility when its isolate has no specimen grouping',async()=>{
  const view=structuredClone(state);view.assembly.snapshot.microbiology.specimens=[];
  const {user}=setup([],view);await select(user);expect(screen.getByText('Recorded MIC: <= 1.000 mg/L')).toBeVisible();
});
it('does not allow an in-flight response to restore a command after unmount',async()=>{
  let finish:(value:Response)=>void=()=>{};
  const {user,fetcher,unmount,client}=setup();
  fetcher.mockImplementationOnce(async()=>json(state)).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  await select(user);await user.click(screen.getByRole('button',{name:'Prepare S/I/U/D review'}));unmount();
  render(<MicroReview client={client} config={config}/>);finish(json(prepared));
  expect(screen.queryByRole('button',{name:'Execute S/I/U/D review'})).not.toBeInTheDocument();
});
it('rejects malformed response identity, withholding contradictions, and reconciliation shape',async()=>{
  for(const value of [{...released,execution_id:'other'},{...withheld,statement:'not released'},{status:'absent',execution:released}]) {
    const fetcher=vi.fn<typeof fetch>().mockResolvedValue(json(value));
    const client=new MicroReviewClient('http://127.0.0.1:8000',config.patient,config.encounter,fetcher);
    await expect(value.status==='absent'?client.microReconcile(prepared):client.microExecute(prepared)).rejects.toMatchObject({code:'invalid_response'});
  }
});

it.each(['unsupported_review_input','storage_integrity_failure'])('keeps %s a distinct bounded UI error',async(code)=>{
  const {user,fetcher}=setup();fetcher.mockImplementationOnce(async()=>json(state)).mockImplementationOnce(async()=>json({code,message:'PRIVATE'},code==='storage_integrity_failure'?500:422));
  await select(user);await user.click(screen.getByRole('button',{name:'Prepare S/I/U/D review'}));await screen.findByText(code);
  expect(document.body.textContent).not.toContain('PRIVATE');expect(screen.queryByText('Execution completion unknown',{exact:true})).not.toBeInTheDocument();
});
it('shows idle, loading, incomplete selection, and ready states distinctly',async()=>{
  const {user}=setup();expect(screen.getByRole('status')).toHaveTextContent('idle');
  await user.click(screen.getByRole('button',{name:'Load microbiology state'}));await screen.findByRole('combobox',{name:'S · Specimen'});
  expect(screen.getByRole('status')).toHaveTextContent('state ready');
  const s=screen.getByRole('combobox',{name:'S · Specimen'});await user.selectOptions(s,within(s).getAllByRole('option')[1]);
  expect(screen.getByRole('status')).toHaveTextContent('selection incomplete');
});

it.each(['patient','encounter'])('scope change in %s clears the prepared command and result',async(field)=>{
  const {unmount}=setup();unmount();
  const replies=[json(state),json(prepared)];const fetcher=vi.fn<typeof fetch>().mockImplementation(async()=>replies.shift()!);
  const client=new ReviewClient('http://127.0.0.1:8000',config.patient,config.encounter,fetcher);
  const microClient=new MicroReviewClient('http://127.0.0.1:8000',config.patient,config.encounter,fetcher);
  const page=render(<PatientReviewPage client={client} microClient={microClient} config={config}/>);const user=userEvent.setup();
  await prepare(user);page.rerender(<PatientReviewPage client={client} microClient={microClient} config={{...config,[field]:'other-scope'}}/>);
  expect(screen.queryByRole('button',{name:'Execute S/I/U/D review'})).not.toBeInTheDocument();expect(screen.getByText('S/I/U/D reviews in this session (0)')).toBeVisible();
});
