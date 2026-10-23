import {afterAll,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {RF2Client,RF2ReviewChanged,pin,stable,hash,type Draft,type SourceReview,type Evidence,type Result} from '../src/api/rf2Client';
import {RenalFluidEntryWorkspace} from '../src/demo/RenalFluidEntryWorkspace';
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');const old=globalThis.crypto;
beforeAll(()=>Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true}));afterAll(()=>Object.defineProperty(globalThis,'crypto',{value:old,configurable:true}));beforeEach(()=>localStorage.clear());
async function setup(changed=true){
 const catalog=await new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(fixture.catalog)))).catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');
 const selected=catalog.items.find(x=>x.fact.id===fixture.weight.fact.id)!;
 const review:SourceReview={selected:pin(selected).reference,terminal:{...pin(selected).reference,version:changed?'later-withdrawn-revision':selected.fact.revision},terminal_digest:'a'.repeat(64),terminal_ingestion:selected.ingestion.ingestion_sequence+Number(changed),record_status:changed?'withdrawn':'recorded',retain_historical:false};
 const action=vi.fn().mockImplementation(async(kind:string,b:Draft)=>({status:kind==='lookup'?'absent':'validated',source_review:b.source_review??[review],fact:fixture.note.fact,execution_enabled:false}));
 const transport={action,resolve:vi.fn(),history:vi.fn()} as unknown as RF2Client;
 const rendered=render(<RenalFluidEntryWorkspace catalog={catalog} gateConfirmed onGuardChange={()=>{}} onRefresh={async()=>{}} onLegacyCorrect={()=>{}} transport={transport}/>);
 const row=screen.getByRole('row',{name:new RegExp(selected.fact.id)});fireEvent.click(within(row).getByRole('button',{name:'Reuse for reassessment'}));fireEvent.change(screen.getByLabelText('Actor'),{target:{value:'Synthetic reviewer'}});
 for(const k of ['question','findings','possibilities','gaps','plan'])fireEvent.change(screen.getByLabelText(k),{target:{value:k}});
 fireEvent.click(screen.getByRole('button',{name:'Validate RF2 draft'}));await screen.findByRole('region',{name:'Review selected source changes'});
 return {action,selected,review,catalog,rendered,transport};
}
it('requires explicit historical retention and retains the original reviewed request through uncertainty',async()=>{
 const {action,selected}=await setup();const confirm=screen.getByRole('button',{name:'Validate reviewed sources'});expect(confirm).toBeDisabled();expect(screen.queryByRole('button',{name:'Confirm RF2 append'})).not.toBeInTheDocument();
 const region=screen.getByRole('region',{name:'Review selected source changes'});expect(region).toHaveTextContent(selected.fact.revision);expect(region).toHaveTextContent('later-withdrawn-revision');expect(region).toHaveTextContent('withdrawn');
 fireEvent.click(within(region).getByRole('checkbox'));fireEvent.click(confirm);await screen.findByRole('button',{name:'Confirm RF2 append'});
 const accepted=action.mock.calls[1][1] as Draft;expect(accepted.source_review?.[0].retain_historical).toBe(true);expect(accepted.note?.pins[0]).toEqual(pin(selected));
 action.mockImplementation(async kind=>{if(kind==='save')throw Error('lost delivery');return {status:'absent',execution_enabled:false};});fireEvent.click(screen.getByRole('button',{name:'Confirm RF2 append'}));fireEvent.click(await screen.findByRole('button',{name:'Check exact RF2 saved result'}));
 const retry=await screen.findByRole('button',{name:'Explicitly retry identical RF2 request'});expect(action.mock.calls.filter(x=>x[0]==='save')).toHaveLength(1);fireEvent.click(retry);await screen.findByRole('button',{name:'Check exact RF2 saved result'});
 for(const call of action.mock.calls.slice(2))expect(call[1]).toBe(accepted);
});
it('unchanged selections still pass an explicit source-review step without a historical checkbox',async()=>{
 const {action}=await setup(false);expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Validate reviewed sources'}));await screen.findByRole('button',{name:'Confirm RF2 append'});expect(action.mock.calls[1][1].source_review[0].retain_historical).toBe(false);expect(action.mock.calls.filter(x=>x[0]==='save')).toHaveLength(0);
});
it('a changed review cannot silently reuse an acknowledgement; refresh is explicit and resets it',async()=>{
 const {action,review,selected}=await setup();fireEvent.click(screen.getByRole('checkbox'));action.mockRejectedValueOnce(Error('Source changed again'));fireEvent.click(screen.getByRole('button',{name:'Validate reviewed sources'}));await screen.findByText(/Selected sources changed or the review could not be confirmed/);expect(screen.queryByRole('button',{name:'Confirm RF2 append'})).not.toBeInTheDocument();
 action.mockResolvedValueOnce({status:'validated',source_review:[{...review,terminal:{...review.terminal,version:'newer-revision'},retain_historical:false}],execution_enabled:false});fireEvent.click(screen.getByRole('button',{name:'Refresh selected-source review'}));await screen.findByText(/Current terminal newer-revision/);expect(screen.getByRole('checkbox')).not.toBeChecked();expect(screen.getByRole('button',{name:'Validate reviewed sources'})).toBeDisabled();expect((action.mock.calls.at(-1)![1] as Draft).note?.pins[0]).toEqual(pin(selected));expect(action.mock.calls.filter(x=>x[0]==='save')).toHaveLength(0);
});
it('rejects a contradictory selected-source review before treating validation as confirmed',async()=>{
 const b=structuredClone(fixture.note_draft) as Draft;const canonical=stable(b);const review=b.note!.pins.map(p=>({selected:p.reference,terminal:p.reference,terminal_digest:p.digest,terminal_ingestion:p.ingestion,record_status:'recorded',retain_historical:false}));review[0].selected={...review[0].selected,id:'foreign-record'};
 const response:Result={status:'validated',request_canonical:canonical,request_digest:await hash(canonical),source_review:review,fact:fixture.note.fact as Evidence['fact'],replay_reference:null,execution_enabled:false};
 const api=new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(response))));await expect(api.action('validate',b)).rejects.toThrow();
});

it('decodes real-API validation, persisted review decisions and shared catalog without rewriting legacy notes',async()=>{
 const actual=(await import('./fixtures/rf2-reviewed-api.json')).default;
 const send=vi.fn<typeof fetch>().mockResolvedValueOnce(new Response(JSON.stringify(actual.validated))).mockResolvedValueOnce(new Response(JSON.stringify(actual.saved))).mockResolvedValueOnce(new Response(JSON.stringify(actual.catalog)));
 const api=new RF2Client(send);const draft=actual.draft as Draft;
 const validation=await api.action('validate',draft);expect(validation.source_review).toEqual(draft.source_review);
 const out=await api.action('save',draft);expect(out.evidence?.metadata?.source_review).toEqual(draft.source_review);
 const c=await api.catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');const note=c.items.find(x=>x.fact.id===draft.id)!;expect(note.metadata?.source_review).toEqual(draft.source_review);expect(note.metadata?.note?.pins).toEqual(draft.note?.pins);
});

it.each([true,false])('accepts a definitive pre-append review rejection only with matching command digest: %s',async matching=>{
 const b=structuredClone(fixture.note_draft) as Draft;
 const response={code:'rf2_source_review_changed',request_digest:matching?await hash(stable(b)):'a'.repeat(64),execution_enabled:false};
 const api=new RF2Client(vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(response),{status:409})));
 try{await api.action('save',b);throw Error('Unexpected success');}catch(error){expect(error instanceof RF2ReviewChanged).toBe(matching);}
});
it('preserves a definitively rejected pending request until explicit re-review resets historical consent',async()=>{
 const {action,review,selected}=await setup();fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Validate reviewed sources'}));await screen.findByRole('button',{name:'Confirm RF2 append'});
 const pending=action.mock.calls[1][1];action.mockRejectedValueOnce(new RF2ReviewChanged());fireEvent.click(screen.getByRole('button',{name:'Confirm RF2 append'}));const button=await screen.findByRole('button',{name:'Explicitly re-review rejected request sources'});
 expect(action.mock.calls.at(-1)![1]).toBe(pending);expect(action.mock.calls.filter(x=>x[0]==='save')).toHaveLength(1);expect(screen.queryByRole('button',{name:'Explicitly retry identical RF2 request'})).not.toBeInTheDocument();
 action.mockResolvedValueOnce({status:'validated',source_review:[{...review,terminal:{...review.terminal,version:'newer-reviewed-terminal'},retain_historical:false}],execution_enabled:false});fireEvent.click(button);await screen.findByText(/Current terminal newer-reviewed-terminal/);
 expect(screen.getByRole('checkbox')).not.toBeChecked();expect(screen.getByRole('button',{name:'Validate reviewed sources'})).toBeDisabled();expect(action.mock.calls.at(-1)![1].note.pins[0]).toEqual(pin(selected));expect(action.mock.calls.filter(x=>x[0]==='save')).toHaveLength(1);
});
