import {afterEach,it,expect,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import expanded from './fixtures/comprehensive.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {sourceUncertainties,recordedViewCaveats} from '../src/demo/explanationSources';
import {EvidenceExplanation} from '../src/demo/PatientEvidenceExplanation';
const items=()=>decodeCirculatoryState(structuredClone(expanded)).assembly.snapshot.items;
afterEach(cleanup);
it('keeps source-specific quality, placement, missing context and estimate caveats distinct',()=>{
  const sources=items(),before=JSON.stringify(sources),notes=sourceUncertainties(sources),byId=Object.fromEntries(notes.map(n=>[n.item.fact.id,n]));
  expect(byId['m7-PICCO-CO'].reasons.join(' ')).toContain('Recorded quality: unknown');
  expect(byId['m7-CONTEXT-CO'].reasons.join(' ')).toContain('Placement: contextual');
  expect(byId['m7-UNPLACED'].reasons.join(' ')).toContain('Result unavailable: unknown');
  expect(byId['m7-SVO2'].reasons.join(' ')).toContain('Sample-time FiO₂');
  expect(byId['m7-RVSP'].notes.join(' ')).toContain('RVOT obstruction not documented');
  expect(byId['m7-RVSP'].reasons.join(' ')).toContain('Source-calculated echo estimate');
  expect(byId['m7-EF']).toBeUndefined();expect(JSON.stringify(sources)).toBe(before);
});
it('does not upgrade withdrawn, invalid or suspect source measurements',()=>{
  const sources=items().filter(i=>['m7-CO','m7-VTI'].includes(i.fact.id));
  sources[0].fact.record_status='withdrawn';sources[0].fact.acquisition={quality:{status:'invalid'}};
  sources[1].fact.acquisition={quality:{status:'suspect',artifacts:['Recorded acquisition artifact.']}};
  const notes=sourceUncertainties(sources);
  expect(notes.map(n=>n.reasons.join(' ')).join(' ')).toContain('withdrawn');
  expect(notes.map(n=>n.reasons.join(' ')).join(' ')).toContain('invalid');
  expect(notes.map(n=>n.reasons.join(' ')).join(' ')).toContain('suspect');
  expect(notes.flatMap(n=>n.notes)).toContain('Recorded acquisition artifact.');
});
it('keeps uncertainty in the overall relationship even when source flags are absent',()=>{
  const sources=items().filter(i=>i.fact.id==='m7-EF');render(<EvidenceExplanation items={sources} onInspect={vi.fn()}/>);
  expect(screen.getByText('Patient-level relationship: not established')).toBeInTheDocument();
  expect(screen.getByText(/No additional flags were identified/)).toHaveTextContent('does not establish reliable measurements, clinical agreement or a combined interpretation');
  expect(screen.getAllByText(/No records for this stream/)).toHaveLength(2);
});
it('empty input invents neither patient findings nor clinical agreement',()=>{
  render(<EvidenceExplanation items={[]} onInspect={vi.fn()}/>);
  expect(screen.getByText(/0 of 3 evidence streams/)).toBeInTheDocument();
  expect(screen.getAllByText(/No records for this stream/)).toHaveLength(3);
  expect(screen.queryByRole('button',{name:/Explain source/})).not.toBeInTheDocument();
});

it('deduplicates repeated view caveats while retaining every associated source',()=>{
  const sources=items(),groups=recordedViewCaveats(sources);
  expect(groups).toHaveLength(1);expect(groups[0].sources).toHaveLength(41);
  expect(new Set(groups[0].sources.map(i=>i.fact.id)).size).toBe(41);
  expect(groups[0].note).toBe(sources[0].disclosures[0]);
});
