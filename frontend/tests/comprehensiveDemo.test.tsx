import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import fixtures from './fixtures/circulatory.json';
import {ComprehensiveDemo} from '../src/demo/ComprehensiveDemo';
import {decodeCirculatoryState,decodeCirculatoryExecution} from '../src/api/circulatoryDecoders';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {value,sourceTime} from '../src/demo/evidencePresentation';
const config={start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00',releasedExample:'released',withheldExample:'withheld'};
function setup(){
  const state=decodeCirculatoryState({...fixtures.state,execution_enabled:false});
  const client={circulatoryState:vi.fn().mockResolvedValue({data:state}),circulatoryHistory:vi.fn().mockResolvedValue({data:fixtures.history}),circulatoryLookup:vi.fn().mockResolvedValue({data:decodeCirculatoryExecution(fixtures.released)}),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn()};
  render(<ComprehensiveDemo client={client as unknown as CirculatoryClient} config={config}/>);return {client,state};
}
async function ready(){await screen.findByRole('heading',{name:'Cardiac output + echo'});}
afterEach(cleanup);
describe('comprehensive read-only synthetic demo',()=>{
  it('opens with cardiac output and echo, preserves exact values and makes no execution request',async()=>{
    const {client}=setup();await ready();expect(screen.getByRole('button',{name:'Inspect Cardiac output m7-CO'})).toHaveTextContent('4.50');
    expect(screen.getByRole('button',{name:'Inspect TAPSE m7-ECHO'})).toHaveTextContent('18');expect(screen.getByText('New reviews: disabled.')).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Prepare P\/L\/V/})).not.toBeInTheDocument();expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
  });
  it('browses all fifteen families and filters by source, family and method without hiding unknowns',async()=>{
    setup();await ready();fireEvent.click(screen.getByRole('button',{name:'Evidence library'}));expect(screen.getByLabelText('Evidence family').querySelectorAll('option')).toHaveLength(16);
    expect(screen.getByRole('heading',{name:'Echo and POCUS'})).toBeInTheDocument();expect(screen.getByRole('heading',{name:'Signal manifests'})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search recorded evidence'),{target:{value:'PiCCO'}});expect(screen.getByRole('button',{name:'Inspect Cardiac output m7-PICCO-CO'})).toHaveTextContent('Quality: unknown');
    fireEvent.change(screen.getByLabelText('Evidence family'),{target:{value:'circulatory_echo'}});expect(screen.getByText('0 recorded items in this view')).toBeInTheDocument();expect(screen.getByText(/No matching records/)).toBeInTheDocument();
  });
  it('guided gaps retain unknown-quality and unplaced evidence',async()=>{
    setup();await ready();fireEvent.click(screen.getByRole('button',{name:/Find the evidence gaps/}));expect(screen.getByRole('button',{name:'Inspect Cardiac output m7-PICCO-CO'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'Inspect Central venous pressure m7-UNPLACED'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Inspect Vasopressor event m7-V'})).not.toBeInTheDocument();
  });
  it('inspects real bounded history using the exact signed context and selected reference',async()=>{
    const {client,state}=setup();await ready();fireEvent.click(screen.getByRole('button',{name:'Inspect Mean arterial pressure m7-P'}));fireEvent.click(screen.getByRole('button',{name:'Inspect revision history'}));await screen.findByText('2 retained revisions at this cutoff');
    expect(client.circulatoryHistory).toHaveBeenCalledWith(state.state_context,{kind:'circulatory_pressure',id:'m7-P',version:'1'});
  });
  it('does not attach a late history response to a different selected source',async()=>{
    const {client}=setup();await ready();let resolve!:(value:unknown)=>void;client.circulatoryHistory.mockImplementation(()=>new Promise(r=>{resolve=r;}));
    fireEvent.click(screen.getByRole('button',{name:'Inspect Mean arterial pressure m7-P'}));fireEvent.click(screen.getByRole('button',{name:'Inspect revision history'}));fireEvent.click(screen.getByRole('button',{name:'Inspect TAPSE m7-ECHO'}));resolve({data:fixtures.history});await waitFor(()=>expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('m7-ECHO / 1'));expect(screen.queryByRole('region',{name:'Bounded source revision history'})).not.toBeInTheDocument();
  });
  it('reads retained examples and clears an old receipt before a failed new lookup',async()=>{
    const {client}=setup();await ready();fireEvent.click(screen.getByRole('button',{name:'Retained examples'}));fireEvent.click(screen.getByRole('button',{name:/Open the released example/}));await screen.findByRole('heading',{name:'Retained outcome: released'});
    client.circulatoryLookup.mockRejectedValueOnce(new Error('not found'));fireEvent.click(screen.getByRole('button',{name:/Open the withheld example/}));await screen.findByRole('alert');expect(screen.queryByRole('region',{name:'Retained demonstration receipt'})).not.toBeInTheDocument();expect(client.circulatoryExecute).not.toHaveBeenCalled();
  });
  it('timeline explicitly uses ingestion order and preserves source timestamp spelling',async()=>{
    const {state}=setup();await ready();fireEvent.click(screen.getByRole('button',{name:'Recording timeline'}));expect(screen.getByText(/Ordered by repository ingestion sequence/)).toBeInTheDocument();const item=state.assembly.snapshot.items.find(i=>i.fact.id==='m7-L')!;expect(sourceTime(item)).toBe('2026-10-08T08:01:00+00:00');expect(value(item).text).toBe('2.000');
  });
  it('failed state loading offers an explicit refresh instead of fabricated patient data',async()=>{
    const {client}=setup();await ready();client.circulatoryState.mockRejectedValueOnce(new Error('offline'));fireEvent.click(screen.getByRole('button',{name:'Refresh recorded state'}));await screen.findByRole('alert');expect(screen.queryByRole('button',{name:'Inspect Cardiac output m7-CO'})).not.toBeInTheDocument();
  });
});
