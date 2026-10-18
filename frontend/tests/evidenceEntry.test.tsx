import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {EvidenceEntryWorkspace} from '../src/demo/EvidenceEntryWorkspace';
import {EvidenceEntryClient,type Draft,type Evidence} from '../src/api/evidenceEntryClient';
afterEach(cleanup);
function setup(enabled=false){
 const state=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:enabled});
 const client={circulatoryState:vi.fn().mockResolvedValue({data:state}),circulatoryHistory:vi.fn().mockResolvedValue({data:{revisions:[]}})};
 const entry={validate:vi.fn(async(body:Draft)=>({repository_id:body.repository_id,fact:body.fact,expected_digest:'a'.repeat(64),canonical_fact:JSON.stringify(body.fact),ingestion:null} as Evidence)),save:vi.fn(),lookup:vi.fn()};
 render(<EvidenceEntryWorkspace client={client as unknown as CirculatoryClient} entry={entry as unknown as EvidenceEntryClient} config={{start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'}}/>);
 return {state,client,entry};
}
async function draft(){
 const filter=await screen.findByRole('textbox',{name:'Find evidence'});fireEvent.change(filter,{target:{value:'fs-PH-60'}});
 const selected=await screen.findByRole('button',{name:/pH.*fs-PH-60/});fireEvent.click(selected);
 fireEvent.change(screen.getByLabelText('Actor name'),{target:{value:'Synthetic reviewer'}});
 fireEvent.change(screen.getByLabelText('Reason for correction or withdrawal'),{target:{value:'Transcription correction'}});
 fireEvent.change(screen.getByLabelText('Recorded numeric value (raw unit preserved)'),{target:{value:'7.36'}});
 fireEvent.click(screen.getByRole('button',{name:'Validate and review draft'}));
 await screen.findByRole('button',{name:'Confirm append to local database'});
}
it('reviews a reasoned exact correction before any append and preserves original time and sample context',async()=>{
 const {entry,state}=setup();await draft();expect(screen.getByText('Proposed recorded result: 7.36 1')).toBeInTheDocument();expect(screen.getByText('Reason: Transcription correction')).toBeInTheDocument();expect(entry.save).not.toHaveBeenCalled();
 const body=entry.validate.mock.calls[0][0],original=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;
 expect(body.predecessor_digest).toBe(original.expected_digest);expect(body.fact.supersedes).toEqual({kind:original.fact.kind,id:original.fact.id,version:original.fact.revision});
 expect(body.fact.occurred).toEqual(original.fact.occurred);expect(body.fact.blood_gas_context).toEqual(original.fact.blood_gas_context);
 expect(body.fact.provenance).toMatchObject({actor:'Synthetic reviewer',lineage:'incomplete'});
 expect(JSON.stringify(original.fact)).toContain('7.35');expect(JSON.stringify(body.fact)).toContain('7.36');
});
it('retains the exact reviewed draft after a lost response and requires explicit absent-case retry',async()=>{
 const {entry}=setup();await draft();entry.save.mockRejectedValueOnce(Error('unconfirmed'));
 fireEvent.click(screen.getByRole('button',{name:'Confirm append to local database'}));
 await screen.findByRole('button',{name:'Check exact saved revision'});expect(entry.save).toHaveBeenCalledTimes(1);
 expect(screen.getByRole('button',{name:'New source entry'})).toBeDisabled();
 entry.lookup.mockResolvedValue({status:'absent'});fireEvent.click(screen.getByRole('button',{name:'Check exact saved revision'}));
 await screen.findByRole('button',{name:'Explicitly retry the same revision'});expect(entry.save).toHaveBeenCalledTimes(1);
 const pending=entry.save.mock.calls[0][0];expect(entry.lookup).toHaveBeenCalledWith(pending);
 entry.save.mockResolvedValue({fact:pending.fact,ingestion:{ingestion_sequence:164}});
 fireEvent.click(screen.getByRole('button',{name:'Explicitly retry the same revision'}));
 await screen.findByText(/Exact revision saved and confirmed/);expect(entry.save.mock.calls[1][0]).toBe(pending);
});
it('recovers a committed exact revision without another save',async()=>{
 const {entry}=setup();await draft();entry.save.mockRejectedValueOnce(Error('unconfirmed'));
 fireEvent.click(screen.getByRole('button',{name:'Confirm append to local database'}));await screen.findByRole('button',{name:'Check exact saved revision'});
 entry.lookup.mockResolvedValue({status:'committed_match',evidence:{fact:entry.validate.mock.calls[0][0].fact,ingestion:{ingestion_sequence:164}}});
 fireEvent.click(screen.getByRole('button',{name:'Check exact saved revision'}));await screen.findByText(/Exact revision saved and confirmed/);expect(entry.save).toHaveBeenCalledTimes(1);
});
it('does not append an invalid draft or offer entry with an unconfirmed execution gate',async()=>{
 const {entry}=setup(true);await screen.findByRole('alert');expect(screen.queryByRole('button',{name:'New source entry'})).not.toBeInTheDocument();expect(entry.save).not.toHaveBeenCalled();
});
it('keeps a stale conflict in review without automatic replacement or retry',async()=>{
 const {entry}=setup();await draft();entry.save.mockRejectedValueOnce(Error('conflict'));
 fireEvent.click(screen.getByRole('button',{name:'Confirm append to local database'}));await screen.findByRole('alert');
 await waitFor(()=>expect(screen.getByRole('button',{name:'Discard draft and reload'})).toBeEnabled());
 expect(entry.save).toHaveBeenCalledTimes(1);expect(entry.lookup).not.toHaveBeenCalled();
});
