import {fireEvent, render, screen} from '@testing-library/react';
import {expect, it, vi} from 'vitest';
import {RF2Client, type Catalog} from '../src/api/rf2Client';
import {SedationWorkspace} from '../src/sedation/SedationWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
const time = {status: 'known', precision: 'instant', value: '2026-10-08T09:00:00Z'};

function catalog(): Catalog {
  const result = structuredClone(fixture.catalog) as unknown as Catalog;
  result.neurological_records = [{
    ...fixture.weight, metadata: null, cutoff: result.cutoff.fact_watermark,
    terminal_reference: {kind: 'neurological_record', id: 'exam', version: '2'},
    fact: {...fixture.weight.fact, kind: 'neurological_record', id: 'exam', revision: '2',
      title: 'Neurological observation', category: 'exam', record_status: 'recorded', report_status: 'corrected',
      times: {occurred: time, reported: time, available: time}, exam: {rass: 0}},
  }];
  return result;
}

function workspace(c: Catalog, current = true, scope = requested) {
  return <SedationWorkspace catalog={c} requested={scope} current={current} loading={false} onRefresh={async () => {}}/>;
}

it('preserves recorded zero and opens the exact source revision with explicit gaps', async () => {
  const c = catalog();
  const history = vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue(c.neurological_records!);
  try {
    render(workspace(c));
    expect(screen.getByText('RASS 0')).toBeVisible();
    expect(screen.getByText(/Pain assessment unavailable/)).toBeVisible();
    expect(screen.getByText(/Delirium assessment and assessability unavailable/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Open exam source'}));
    expect(history).toHaveBeenCalledWith(c.neurological_records![0]);
    expect(await screen.findByText(/Version 2/)).toBeVisible();
  } finally {
    history.mockRestore();
  }
});

it('withholds scores from withdrawn, conflicted, unconfirmed and wrong-encounter evidence', () => {
  const c = catalog();
  const row = c.neurological_records![0];
  const {rerender} = render(workspace(c, false));
  expect(screen.queryByText('RASS 0')).toBeNull();
  expect(screen.getByText('Current evidence is unconfirmed.')).toBeVisible();
  rerender(workspace(c, true, {...requested, encounter: 'other'}));
  expect(screen.queryByRole('button', {name: 'Open exam source'})).toBeNull();
  rerender(workspace({...c, neurological_records: [{...row, fact: {...row.fact, record_status: 'withdrawn'}}]}));
  expect(screen.getByText('RASS unavailable')).toBeVisible();
  rerender(workspace({...c, neurological_records: [{...row, fact: {...row.fact, conflict: 'unresolved'}}]}));
  expect(screen.getByText('RASS unavailable')).toBeVisible();
});

it('uses the selected review period and cutoff for exam and medication observations', () => {
  const c = catalog();
  const exam = c.neurological_records![0];
  const medication = {
    ...exam,
    fact: {...exam.fact, id: 'medication', category: 'medication_status', medication: {name: 'Propofol', status: 'paused'}},
    terminal_reference: {...exam.terminal_reference, id: 'medication'},
  };
  c.neurological_records = [
    {...exam, cutoff: c.cutoff.fact_watermark + 1},
    medication,
    {...medication, fact: {...medication.fact, id: 'later', medication: {name: 'Midazolam', status: 'running'},
      times: {occurred: {...time, value: '2026-10-08T10:01:00Z'}}}},
  ];
  render(workspace(c));
  expect(screen.getByText('Propofol · paused')).toBeVisible();
  expect(screen.queryByText(/Midazolam/)).toBeNull();
  expect(screen.queryByText('RASS 0')).toBeNull();
});
