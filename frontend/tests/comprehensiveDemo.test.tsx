import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,within} from '@testing-library/react';
import fixtures from './fixtures/circulatory.json';
import expanded from './fixtures/comprehensive.json';
import flowsheet from './fixtures/icuFlowsheet.json';
import {ComprehensiveDemo} from '../src/demo/ComprehensiveDemo';
import {decodeCirculatoryState,decodeCirculatoryExecution,decodeCirculatoryHistory} from '../src/api/circulatoryDecoders';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import {value,sourceTime,bloodGasSummary} from '../src/demo/evidencePresentation';
const config={start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00',releasedExample:'released',withheldExample:'withheld'};
function setup(hosted=false,executionEnabled=false,raw:object=fixtures.state){
  const state=decodeCirculatoryState({...raw,execution_enabled:executionEnabled});
  const client={circulatoryState:vi.fn().mockResolvedValue({data:state}),circulatoryHistory:vi.fn().mockResolvedValue({data:decodeCirculatoryHistory(fixtures.history)}),circulatoryLookup:vi.fn().mockResolvedValue({data:decodeCirculatoryExecution(fixtures.released)}),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn()};
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
    setup();await ready();fireEvent.click(screen.getByRole('button',{name:/Find the evidence gaps/}));expect(screen.getByRole('button',{name:'Inspect Cardiac output m7-PICCO-CO'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'Inspect Central venous pressure m7-UNPLACED'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Inspect Vasoactive event m7-V'})).not.toBeInTheDocument();
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


it('combines ABG, cardiac output and echo in one patient summary with exact source inspection',async()=>{
  const {client,state}=setup(false,false,expanded);await ready();
  fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  const summary=screen.getByRole('region',{name:'Combined patient evidence summary'});
  for(const name of ['ABG and oxygen transport','Cardiac output and pressures','Echo and right-heart findings','Perfusion and circulatory support'])expect(within(summary).getByRole('region',{name})).toBeInTheDocument();
  expect(within(summary).getByRole('button',{name:'Open summary source pH m7-ABG-PH'})).toHaveTextContent('7.31 (unit: 1)');
  expect(within(summary).getByRole('button',{name:'Open summary source Cardiac output m7-CO'})).toHaveTextContent('4.50 L/min');
  expect(within(summary).getByRole('button',{name:'Open summary source LVOT VTI m7-VTI'})).toHaveTextContent('17.5 cm');
  const item=state.assembly.snapshot.items.find(i=>i.fact.id==='m7-RVSP')!;
  const reference={kind:'circulatory_echo',id:'m7-RVSP',version:'1'};
  const history=decodeCirculatoryHistory({...fixtures.history,
    context:{...fixtures.history.context,assembly_request:expanded.assembly_request,assembly_digest:expanded.assembly_digest},
    reference,revisions:[{fact:item.fact,ingestion:item.ingestion}]},{reference,patient_id:'synthetic-p1',encounter_id:'synthetic-e1'});
  client.circulatoryHistory.mockResolvedValueOnce({data:history});
  fireEvent.click(within(summary).getByRole('button',{name:'Open summary source Estimated RVSP m7-RVSP'}));
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveFocus();
  fireEvent.click(screen.getByRole('button',{name:'Inspect revision history'}));await screen.findByText('1 retained revision at this cutoff');
  expect(screen.getByRole('region',{name:'Bounded source revision history'})).toHaveTextContent('m7-RVSP / 1');
  expect(client.circulatoryHistory).toHaveBeenCalledWith(state.state_context,{kind:'circulatory_echo',id:'m7-RVSP',version:'1'});
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});

it('summary keeps methods, uncertain quality, earlier and unplaced evidence visible without selecting a preferred flow',async()=>{
  setup(false,false,expanded);await ready();fireEvent.click(screen.getByRole('button',{name:/Open combined patient summary/}));
  const flow=screen.getByRole('region',{name:'Cardiac output and pressures'});
  for(const id of ['m7-CO','m7-FLOTRAC','m7-PICCO-CO','m7-VOLUMEVIEW','m7-CONTEXT-CO'])expect(within(flow).getByRole('button',{name:'Open summary source Cardiac output '+id})).toBeInTheDocument();
  const picco=within(flow).getByRole('button',{name:'Open summary source Cardiac output m7-PICCO-CO'}).closest('li')!;
  expect(picco).toHaveTextContent('Quality: unknown');expect(picco).toHaveTextContent('pulse contour');
  expect(within(flow).getByRole('button',{name:'Open summary source Cardiac output m7-CONTEXT-CO'}).closest('li')).toHaveTextContent('contextual');
  expect(within(flow).getByRole('button',{name:'Open summary source Central venous pressure m7-UNPLACED'}).closest('li')).toHaveTextContent('Time not established');
});

it('summary preserves sample-specific settings and distinguishes source PH reports from diagnosis',async()=>{
  setup(false,false,expanded);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  const gases=screen.getByRole('region',{name:'ABG and oxygen transport'});
  expect(within(gases).getByRole('button',{name:'Open summary source PaCO₂ m7-ABG-PACO2'}).closest('li')).toHaveTextContent('Sample-time FiO₂: 40 %');
  expect(within(gases).getByRole('button',{name:'Open summary source Mixed venous oxygen saturation m7-SVO2'}).closest('li')).toHaveTextContent('Sample-time FiO₂: Not recorded');
  const echo=screen.getByRole('region',{name:'Echo and right-heart findings'});
  expect(within(echo).getByRole('button',{name:'Open summary source Pulmonary hypertension report finding m7-PH'}).closest('li')).toHaveTextContent('Source report finding');
  expect(within(echo).getByRole('button',{name:'Open summary source Estimated RVSP m7-RVSP'}).closest('li')).toHaveTextContent('Source-reported estimate; not recalculated by ClinRx.');
  expect(screen.getByRole('complementary',{name:'Summary limitations'})).toHaveTextContent('no PH diagnosis or PAH subtype is inferred');
});

it('summary shows empty families without filling absent measurements or requiring HPI',async()=>{
  const raw=structuredClone(expanded);raw.assembly.snapshot.items=raw.assembly.snapshot.items.filter(i=>i.fact.kind!=='circulatory_echo');
  raw.assembly.snapshot.coverage.retained_count=raw.assembly.snapshot.items.length;
  setup(false,false,raw);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  expect(screen.getByRole('region',{name:'Echo and right-heart findings'})).toHaveTextContent('No records in this bounded view. Clinical absence is not established.');
  expect(screen.queryByRole('button',{name:/Open summary source Estimated RVSP/})).not.toBeInTheDocument();
  expect(screen.getByRole('complementary',{name:'Summary limitations'})).toHaveTextContent('HPI is optional: not recorded in this case.');
});

it('does not render a summary if execution is enabled or the state cannot be trusted',async()=>{
  setup(true,true,expanded);await screen.findByRole('alert');fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  expect(screen.queryByRole('region',{name:'Combined patient evidence summary'})).not.toBeInTheDocument();
});


it('labels qualitative PH source wording without presenting its preserved raw tag as a measured diagnosis',async()=>{
  setup(false,false,expanded);await ready();
  fireEvent.click(screen.getByRole('button',{name:'Inspect Pulmonary hypertension report finding m7-PH'}));
  const inspector=screen.getByRole('complementary',{name:'Selected source evidence'});
  expect(inspector).toHaveTextContent('Recorded production tag: direct measurement.');
  expect(inspector).toHaveTextContent('Qualitative echo findings are source-report assertions, not directly measured diagnoses.');
  expect(inspector).not.toHaveTextContent('Source assertion: direct measurement');
  expect(inspector).toHaveTextContent('no invasive confirmation or PAH subtype established');
});


it('explains complementary streams with source-linked uncertainty and no execution',async()=>{
  const {client,state}=setup(false,false,expanded);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  const explanation=screen.getByRole('region',{name:'How the evidence fits together'});
  expect(explanation).toHaveTextContent('Patient-level relationship: not established');
  expect(explanation).toHaveTextContent('3 of 3 evidence streams have records');
  expect(explanation).toHaveTextContent('Source quality labels are not confidence in a combined interpretation.');
  const uncertainty=within(explanation).getByRole('region',{name:'What remains uncertain'});
  expect(uncertainty).toHaveTextContent('Recorded quality: unknown');
  expect(uncertainty).toHaveTextContent('Sample context not recorded');
  expect(uncertainty).toHaveTextContent('RVOT obstruction not documented');
  fireEvent.click(within(uncertainty).getByRole('button',{name:'Inspect uncertainty Cardiac output m7-PICCO-CO'}));
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('m7-PICCO-CO / 1');
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('unknown');
  expect(client.circulatoryState).toHaveBeenCalledTimes(1);expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
  expect(state.execution_enabled).toBe(false);
});

it('explanation source links preserve exact value spelling and open the original source',async()=>{
  setup(false,false,expanded);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  const gases=screen.getByRole('region',{name:'Blood sample and oxygen context'});
  const details=within(gases).getByText('Recorded sources behind this explanation (8)');fireEvent.click(details);
  const source=await within(gases).findByRole('button',{name:'Explain source PaCO₂ m7-ABG-PACO2'});
  expect(source).toHaveTextContent('48.0 mmHg');fireEvent.click(source);
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('m7-ABG-PACO2 / 1');
  expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('40 %');
});

it('explanation is withheld with the rest of summary browsing when execution is enabled',async()=>{
  setup(true,true,expanded);await screen.findByRole('alert');fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  expect(screen.queryByRole('region',{name:'How the evidence fits together'})).not.toBeInTheDocument();
  expect(screen.queryByRole('region',{name:'Patient-specific possibilities'})).not.toBeInTheDocument();
});


it('shows case-specific possibilities through read-only browsing and preserves exact source inspection',async()=>{
  const {client}=setup(false,false,expanded);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  expect(screen.getByRole('region',{name:'Possible combined interpretation'})).toHaveTextContent('possible RV pressure loading');
  fireEvent.click(screen.getByRole('button',{name:'Case source Estimated RVSP m7-RVSP'}));
  expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('m7-RVSP / 1');
  expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});
it('withholds case-specific possibilities on changed records while keeping recorded browsing available',async()=>{
  const raw=structuredClone(expanded);raw.assembly.snapshot.items.find(i=>i.fact.id==='m7-ABG-PH')!.fact.revision='2';
  setup(false,false,raw);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
  expect(screen.getByText(/Case interpretation unavailable/)).toBeInTheDocument();
  expect(screen.queryByRole('region',{name:'Possible combined interpretation'})).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Open summary source pH m7-ABG-PH'})).toBeInTheDocument();
});

it('opens the persisted flowsheet with exact infusion inspection without preparing or executing',async()=>{
 const {client,state}=setup(false,false,flowsheet);await ready();fireEvent.click(screen.getByRole('button',{name:'ICU flowsheet'}));
 expect(screen.getByRole('region',{name:'Read-only ICU flowsheet'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Chart source fs-D-CHANGE revision 1'}));
 expect(screen.getByRole('region',{name:'Recorded infusion event details'})).toHaveTextContent('3.0 mcg/kg/min');
 expect(screen.getByRole('complementary',{name:'Selected source evidence'})).toHaveTextContent('Vasoactive event');
 expect(screen.getByRole('complementary',{name:'Selected source evidence'})).not.toHaveTextContent('Vasopressor event');
 const reference={kind:'circulatory_vasoactive',id:'fs-D-CHANGE',version:'1'},item=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
 client.circulatoryHistory.mockResolvedValueOnce({data:decodeCirculatoryHistory({...fixtures.history,context:{...fixtures.history.context,assembly_request:flowsheet.assembly_request,assembly_digest:flowsheet.assembly_digest},reference,revisions:[{fact:item.fact,ingestion:item.ingestion}]},{reference,patient_id:'synthetic-p1',encounter_id:'synthetic-e1'})});
 fireEvent.click(screen.getByRole('button',{name:'Inspect revision history'}));await screen.findByText('1 retained revision at this cutoff');
 expect(screen.getByRole('region',{name:'Bounded source revision history'})).toHaveTextContent('fs-D-CHANGE / 1');
 expect(client.circulatoryHistory).toHaveBeenCalledWith(state.state_context,reference);
 expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});
it('blocks flowsheet browsing when execution is enabled',async()=>{
 setup(true,true,flowsheet);await screen.findByRole('alert');fireEvent.click(screen.getByRole('button',{name:'ICU flowsheet'}));
 expect(screen.queryByRole('region',{name:'Read-only ICU flowsheet'})).not.toBeInTheDocument();
});
it('uses the separately authored expanded case rather than reusing the old case',async()=>{
 setup(false,false,flowsheet);await ready();fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
 expect(screen.getByText(/Expanded ICU · 156 source records/)).toBeInTheDocument();expect(screen.queryByText(/Original comprehensive · 41 source records/)).not.toBeInTheDocument();expect(screen.getByRole('region',{name:'Infusions and perfusion: response is unconfirmed'})).toBeInTheDocument();
});

it('opens expanded authored possibilities and serial sources without preparing or executing a review',async()=>{
 const {client}=setup(true,false,flowsheet);await ready();
 fireEvent.click(screen.getByRole('button',{name:'Patient summary'}));
 expect(screen.getByText(/Expanded ICU · 156 source records/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Case source pH fs-PH-60'}));
 expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('arterial');
 expect(screen.getByRole('region',{name:'Blood gas sample context'})).toHaveTextContent('40 %');
 expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});
