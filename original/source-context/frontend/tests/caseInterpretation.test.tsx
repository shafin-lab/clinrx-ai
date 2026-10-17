import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,cleanup,fireEvent} from '@testing-library/react';
import expanded from './fixtures/comprehensive.json';
import collision from './fixtures/authoredCaseHpiCollision.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import type {CirculatoryItem} from '../src/api/circulatoryTypes';
import {record} from '../src/demo/evidencePresentation';
import {matchesAuthoredCase} from '../src/demo/syntheticCaseInterpretation';
import {PatientCaseInterpretation} from '../src/demo/PatientCaseInterpretation';
const scope={patientId:'synthetic-p1',encounterId:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const items=()=>decodeCirculatoryState(structuredClone(expanded)).assembly.snapshot.items;
afterEach(cleanup);

function withRealHpi(order:'first'|'last'){return decodeCirculatoryState(structuredClone(collision[order])).assembly.snapshot.items;}
it('matches only the complete authored case, without mutating inputs or assigning clinical eligibility',()=>{
  const sources=items(),before=JSON.stringify(sources);expect(matchesAuthoredCase(sources,scope)).toBe(true);
  expect(matchesAuthoredCase([...sources].reverse(),scope)).toBe(true);expect(JSON.stringify(sources)).toBe(before);
  expect(sources.find(i=>i.fact.id==='m7-PICCO-CO')!.fact.acquisition).toEqual(expect.objectContaining({quality:expect.objectContaining({status:'unknown'})}));
});
const mutations:[string,(i:CirculatoryItem)=>void][]=[
  ['revision',i=>{i.fact.revision='2';}],
  ['digest',i=>{i.expected_digest='sha256:'+'a'.repeat(64);}],
  ['value',i=>{record(record(i.fact.result).quantity).value='7.40';}],
  ['unit',i=>{record(record(record(i.fact.result).quantity).unit).raw='changed';}],
  ['time',i=>{record(i.fact.occurred).source_timestamp='2026-10-08T08:01:00Z';}],
  ['binding provenance',i=>{record(i.fact.binding).new_provenance='changed';}],
  ['quality',i=>{record(record(i.fact.acquisition).quality).status='suspect';}],
  ['artifact',i=>{record(record(i.fact.acquisition).quality).artifacts=['new artifact'];}],
  ['withdrawal',i=>{i.fact.record_status='withdrawn';}],
  ['placement',i=>{i.inclusion='contextual';}],
  ['contextual link',i=>{i.contextual_for=[{kind:'circulatory_echo',id:'other',version:'1'}];}],
  ['view caveat',i=>{i.disclosures.push('new disclosure');}],
  ['source caveat',i=>{i.fact.disclosures=['new source limitation'];}],
  ['sample setting',i=>{record(record(i.fact.blood_gas_context).fio2).value='50';}],
];
it.each(mutations)('withholds authored possibilities after %s changes, even without a digest update',(_name,mutate)=>{
  const sources=items(),source=sources.find(i=>i.fact.id==='m7-ABG-PH')!;mutate(source);
  expect(matchesAuthoredCase(sources,scope)).toBe(false);
});
it('withholds after missing, duplicate or additional non-HPI records',()=>{
  const sources=items();expect(matchesAuthoredCase(sources.slice(1),scope)).toBe(false);
  expect(matchesAuthoredCase([...sources.slice(1),sources[1]],scope)).toBe(false);
  const extra=structuredClone(sources[0]);extra.fact.id='new-observation';expect(matchesAuthoredCase([...sources,extra],scope)).toBe(false);
});
it('does not carry the narrative across patients, encounters or review windows',()=>{
  for(const changed of [{patientId:'other'},{encounterId:'other'},{start:'2026-10-08T07:00:00Z'},{end:'2026-10-08T11:00:00Z'}])expect(matchesAuthoredCase(items(),{...scope,...changed})).toBe(false);
  const sources=items();sources[0].fact.binding.target.patient_id='other';expect(matchesAuthoredCase(sources,scope)).toBe(false);
});
it('allows equivalent fixture window spellings and object-key order without numerical or date coercion',()=>{
  const sources=items();sources[0].fact=Object.fromEntries(Object.entries(sources[0].fact).reverse()) as CirculatoryItem['fact'];
  expect(matchesAuthoredCase(sources,{...scope,start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00'})).toBe(true);
});
it('keeps a legitimate decoded HPI optional and unconsumed while requiring patient correspondence',()=>{
 const sources=withRealHpi('last');expect(matchesAuthoredCase(sources,scope)).toBe(true);
 sources.find(i=>i.fact.kind==='circulatory_device_prediction')!.fact.binding.target.encounter_id='other';
 expect(matchesAuthoredCase(sources,scope)).toBe(false);
});
it.each(['first','last'] as const)('never replaces pinned ABG evidence with a decoded colliding HPI placed %s',order=>{
 const sources=withRealHpi(order),before=JSON.stringify(sources),onInspect=vi.fn();
 const original=sources.find(i=>i.fact.kind==='circulatory_oxygen'&&i.fact.id==='m7-ABG-PH')!;
 const hpi=sources.find(i=>i.fact.kind==='circulatory_device_prediction')!;
 expect(hpi.fact.concept).toBe('hpi');expect(hpi.fact.id).toBe(original.fact.id);expect(matchesAuthoredCase(sources,scope)).toBe(true);
 render(<PatientCaseInterpretation {...scope} items={sources} onInspect={onInspect}/>);
 expect(screen.getByRole('region',{name:'Possible combined interpretation'})).toBeInTheDocument();
 const button=screen.getByRole('button',{name:'Case source pH m7-ABG-PH'});expect(button).toHaveTextContent('7.31 (unit: 1)');
 expect(screen.getByText(/Arterial pH source context/)).toHaveTextContent('Sample type: arterial');
 expect(screen.getByText(/Arterial pH source context/)).toHaveTextContent('Sample-time FiO₂: 40 %');
 fireEvent.click(button);expect(onInspect).toHaveBeenCalledWith(original,button);expect(onInspect.mock.calls[0][0].fact.kind).toBe('circulatory_oxygen');expect(JSON.stringify(sources)).toBe(before);
});
it('separates source facts from hypotheses and opens the exact original record',()=>{
  const sources=items(),onInspect=vi.fn();render(<PatientCaseInterpretation {...scope} items={sources} onInspect={onInspect}/>);
  expect(screen.getByRole('region',{name:'Possible combined interpretation'})).toHaveTextContent('remain unconfirmed');
  expect(screen.getAllByRole('heading',{name:'Recorded findings — source assertions'})).toHaveLength(3);
  expect(screen.getAllByRole('heading',{name:'Possible meaning — unconfirmed'})).toHaveLength(3);
  expect(screen.getAllByRole('heading',{name:'What prevents confirmation'})).toHaveLength(3);
  expect(screen.getByText(/Confirmed here means only/)).toHaveTextContent('source records are present');
  const button=screen.getByRole('button',{name:'Case source PaCO₂ m7-ABG-PACO2'});expect(button).toHaveTextContent('48.0 mmHg');fireEvent.click(button);
  expect(onInspect).toHaveBeenCalledWith(sources.find(i=>i.fact.id==='m7-ABG-PACO2'),button);
  expect(screen.getByRole('button',{name:'Case source Cardiac output m7-PICCO-CO'})).toHaveTextContent('Quality: unknown');
  expect(screen.getByText(/Arterial pH source context/)).toHaveTextContent('Sample-time FiO₂: 40 %');
});
it('removes stale possibilities on source change and leaves a visible explanation of withholding',()=>{
  const sources=items(),props={...scope,onInspect:vi.fn()};const view=render(<PatientCaseInterpretation {...props} items={sources}/>);
  expect(screen.getByRole('region',{name:'Possible combined interpretation'})).toBeInTheDocument();
  const changed=structuredClone(sources);changed.find(i=>i.fact.id==='m7-RVSP')!.fact.revision='2';
  view.rerender(<PatientCaseInterpretation {...props} items={changed}/>);
  expect(screen.queryByRole('region',{name:'Possible combined interpretation'})).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('previous possibilities are withheld');
  expect(screen.queryByRole('button',{name:/Case source/})).not.toBeInTheDocument();
});
