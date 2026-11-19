import {fireEvent, render, screen} from '@testing-library/react';
import {expect, test} from 'vitest';
import type {AntibioticBundle} from '../src/api/antibioticClient';
import type {Catalog, Evidence} from '../src/api/rf2Client';
import {PreventionSummary, PreventionWorkspace} from '../src/infectionPrevention/PreventionWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z'};
const precaution = {
  ...fixture.weight,
  fact: {...fixture.weight.fact, kind: 'precaution_record', id: 'ipc-contact', revision: '1',
    precaution: 'Contact precautions', status: 'in_place', narrative: 'Fictional precaution.',
    record_status: 'recorded', report_status: 'final', times: {occurred: {value: requested.start}}},
  terminal_reference: {kind: 'precaution_record', id: 'ipc-contact', version: '1'},
} as Evidence;
const catalog = {...fixture.catalog, precaution_records: [precaution]} as unknown as Catalog;
function bundle(revision: string, result: string): AntibioticBundle {
  return {renal: catalog, execution_enabled: false, micro: {assembly: {snapshot: {items: [{
    fact: {kind: 'microbiology_molecular', id: 'screen', revision, target: {raw_display: 'Screening PCR'}, result},
    expected_digest: revision.repeat(64), inclusion: 'in_window',
  }]}}}} as unknown as AntibioticBundle;
}

test('restores the prevention review and flags only evidence changes in both views', async () => {
  const common = {catalog, requested, current: true, guarded: false};
  const page = (revision: string, result: string) => {
    const props = {...common, bundle: bundle(revision, result)};
    return <><PreventionSummary {...props} onOpen={() => {}}/>
      <PreventionWorkspace {...props} onRefresh={async () => {}}/></>;
  };
  const first = render(page('1', 'negative'));
  expect(screen.getByText(/Contact precautions · in place/)).toBeVisible();
  expect(screen.getByRole('heading', {name: 'Screening PCR'})).toBeVisible();
  for (const [label, value] of Object.entries({Reviewer: 'Dr Fictional', Assessment: 'Reviewed sources.', 'Next review': 'Next handover'})) {
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  }
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
  expect(await screen.findByText('Review saved in this browser.')).toBeVisible();
  first.unmount();

  const reloaded = render(page('1', 'negative'));
  expect(await screen.findByText('Matches current evidence')).toBeVisible();
  expect(screen.queryByText(/Evidence changed/)).toBeNull();
  reloaded.rerender(page('2', 'positive'));
  expect(screen.getByText('Historical evidence review')).toBeVisible();
  expect(screen.getAllByText('Prevention review needed · Evidence changed.')).toHaveLength(2);
  expect(screen.getByText(/Contact precautions · in place/)).toBeVisible();
});
