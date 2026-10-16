import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import fixtures from './fixtures/circulatory.json';
import expanded from './fixtures/comprehensive.json';
import {ComprehensiveDemo} from '../src/demo/ComprehensiveDemo';
import {decodeCirculatoryState,decodeCirculatoryExecution} from '../src/api/circulatoryDecoders';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {value,sourceTime,bloodGasSummary} from '../src/demo/evidencePresentation';
const config={start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00',releasedExample:'released',withheldExample:'withheld'};
function setup(hosted=false,executionEnabled=false,raw:object=fixtures.state){
  const state=decodeCirculatoryState({...raw,execution_enabled:executionEnabled});
  const client={circulatoryState:vi.fn().mockResolvedValue({data:state}),circulatoryHistory:vi.fn().mockResolvedValue({data:fixtures.history}),circulatoryLookup:vi.fn().mockResolvedValue({data:decodeCirculatoryExecution(fixtures.released)}),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn()};
  render(<ComprehensiveDemo client={client as unknown as CirculatoryClient} config={{...config,hosted}}/>);return {client,state};
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

it('hosted presentation identifies the preview and hides legacy execution tools',async()=>{setup(true);await ready();expect(screen.getByText('SYNTHETIC PREVIEW')).toBeInTheDocument();expect(screen.queryByRole('link',{name:/Existing review tools/})).not.toBeInTheDocument();});

it('blocks evidence browsing and replaces the disabled badge if the server reports execution enabled',async()=>{const {client}=setup(true,true);await screen.findByRole('alert');expect(screen.getByText('Browsing is blocked: the server did not confirm that new execution is disabled.')).toBeInTheDocument();expect(screen.getByText('Execution configuration unverified — browsing blocked')).toBeInTheDocument();expect(screen.queryByText('New execution disabled in this demo')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Inspect Cardiac output m7-CO'})).not.toBeInTheDocument();expect(client.circulatoryPrepare).not.toHaveBeenCalled();});

it('moves keyboard focus to selected source details and returns it when closed',async()=>{setup(true);await ready();const trigger=screen.getByRole('button',{name:'Inspect Cardiac output m7-CO'});trigger.focus();fireEvent.click(trigger);expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveFocus();fireEvent.click(screen.getByRole('button',{name:'Close source'}));expect(trigger).toHaveFocus();});


it('shows broader source echo evidence and estimate limitations without inferring PH or PAH',async()=>{
  const {client}=setup(false,false,expanded);await ready();
  for(const name of ['Inspect LVOT VTI m7-VTI','Inspect Estimated RVSP m7-RVSP','Inspect TR peak velocity m7-TRV','Inspect RV function m7-RVFUNCTION','Inspect Pulmonary hypertension report finding m7-PH'])expect(screen.getByRole('button',{name})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Inspect Estimated RVSP m7-RVSP'}));
  expect(screen.getByRole('region',{name:'Echo study context'})).toHaveTextContent('Echo estimates remain separate from invasive pressure measurements. No PH diagnosis or PAH subtype is inferred.');
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('45.0 mmHg');
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});

it('browses ABG independently of lactate, retains exact quantities and sample context',async()=>{
  setup(false,false,expanded);await ready();
  fireEvent.click(screen.getByRole('button',{name:/ABG \+ oxygen transport/}));
  for(const name of ['Inspect pH m7-ABG-PH','Inspect PaCO₂ m7-ABG-PACO2','Inspect PaO₂ m7-ABG-PAO2','Inspect Bicarbonate m7-ABG-HCO3','Inspect Base excess m7-ABG-BE','Inspect Haemoglobin m7-ABG-HB','Inspect Lactate m7-L'])expect(screen.getByRole('button',{name})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Inspect pH m7-ABG-PH'})).toHaveTextContent('7.31 (unit: 1)');
  expect(screen.getByRole('button',{name:'Inspect Base excess m7-ABG-BE'})).toHaveTextContent('-2.0');
  fireEvent.click(screen.getByRole('button',{name:'Inspect PaCO₂ m7-ABG-PACO2'}));
  expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('arterial');
  expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('synthetic-arterial-sample-1');
  expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('40 %');
  expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('5 cmH2O');
  const summary=screen.getByText('Sample-time oxygen and ventilation settings');fireEvent.click(summary);fireEvent(summary.closest('details')!,new Event('toggle'));
  await screen.findAllByText('Volume assist-control');expect(screen.getByText('40')).toBeInTheDocument();expect(screen.getByText('cmH2O')).toBeInTheDocument();
});

it('keeps missing HPI optional and exposes all supported families without inventing a prediction',async()=>{
  const {client}=setup(true,false,expanded);await ready();
  expect(screen.getByText('HPI is optional.',{exact:false})).toHaveTextContent('Not recorded in this case');
  expect(screen.getByRole('region',{name:'Recorded-state coverage'})).toHaveTextContent('14 / 15');
  fireEvent.click(screen.getByRole('button',{name:'Evidence library'}));
  fireEvent.change(screen.getByLabelText('Evidence family'),{target:{value:'circulatory_device_prediction'}});
  expect(screen.getByText('0 recorded items in this view')).toBeInTheDocument();expect(screen.queryByRole('button',{name:/Inspect Source HPI/})).not.toBeInTheDocument();
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});


it('does not substitute arterial ABG settings into a mixed-venous record lacking sample context',()=>{
  const state=decodeCirculatoryState(expanded),item=state.assembly.snapshot.items.find(i=>i.fact.id==='m7-SVO2')!;
  const summary=Object.fromEntries(bloodGasSummary(item));
  expect(summary['Sample type']).toBe('mixed venous');
  for(const field of ['Collected','Sample-time FiO₂','Ventilator mode','Sample-time PEEP'])expect(summary[field]).toBe('Not recorded');
});
