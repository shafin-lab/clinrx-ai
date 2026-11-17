import {fireEvent, render, screen} from '@testing-library/react';
import {expect, test, vi} from 'vitest';
import {pin, type Catalog, type Evidence} from '../src/api/rf2Client';
import {CatalogMskWorkspace} from '../src/msk/CatalogMskWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
const original = {
  ...fixture.weight, metadata: null,
  fact: {...fixture.weight.fact, kind: 'musculoskeletal_record', id: 'fictional-xray', revision: '1',
    category: 'imaging', title: 'Ankle radiograph', narrative: 'Original fictional report.',
    record_status: 'recorded', report_status: 'final'},
  terminal_reference: {kind: 'musculoskeletal_record', id: 'fictional-xray', version: '1'},
} as Evidence;
const correction: Evidence = {...original, digest: 'a'.repeat(64),
  fact: {...original.fact, revision: '2', narrative: 'Corrected fictional report.'},
  terminal_reference: {...original.terminal_reference, version: '2'}};

function catalog(source: Evidence) {
  return {...structuredClone(fixture.catalog), musculoskeletal_records: [source]} as unknown as Catalog;
}

test('reloads a historical review and resolves only the reviewed revision', async () => {
  const transport = {resolve: vi.fn(async () => [correction]), history: vi.fn(async () => [original])};
  const page = (source: Evidence) => <CatalogMskWorkspace catalog={catalog(source)} requested={requested}
    current guarded={false} transport={transport}/>;
  const first = render(page(original));
  for (const [label, value] of Object.entries({Reviewer: 'Dr Fictional', Assessment: 'Reviewed original report.', 'Next review': '16:30'}))
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
  expect(await screen.findByText('Review saved in this browser.')).toBeVisible();
  first.unmount();

  render(page(correction));
  expect(await screen.findByText('Historical evidence review')).toBeVisible();
  expect(screen.getByText('Corrected fictional report.')).toBeVisible();
  fireEvent.click(screen.getByText('Reviewed source revisions'));
  fireEvent.click(screen.getByRole('button', {name: 'fictional-xray · Revision 1'}));
  expect(await screen.findByText('The exact reviewed revision could not be retrieved.')).toBeVisible();
  expect(screen.queryByRole('dialog')).toBeNull();

  transport.resolve.mockResolvedValueOnce([original]);
  fireEvent.click(screen.getByRole('button', {name: 'fictional-xray · Revision 1'}));
  expect(await screen.findByRole('dialog', {name: 'Ankle radiograph'})).toBeVisible();
  expect(screen.getAllByText('Original fictional report.').length).toBeGreaterThan(0);
  expect(transport.resolve).toHaveBeenCalledWith(original.repository, [pin(original)]);
});

test('blocks a draft when the shared evidence changes', () => {
  const page = (source: Evidence) => <CatalogMskWorkspace catalog={catalog(source)} requested={requested}
    current guarded={false}/>;
  const {rerender} = render(page(original));
  fireEvent.change(screen.getByLabelText('Assessment'), {target: {value: 'Draft on revision 1.'}});
  rerender(page(correction));
  expect(screen.getByText('Evidence changed after this draft began. Clear the draft and review the new sources.')).toBeVisible();
  expect(screen.getByLabelText('Assessment')).toHaveValue('Draft on revision 1.');
  expect(screen.getByRole('button', {name: 'Save review'})).toBeDisabled();
});
