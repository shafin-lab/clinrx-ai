import {fireEvent, render, screen} from '@testing-library/react';
import {expect, test, vi} from 'vitest';
import {pin, type Catalog, type Evidence} from '../src/api/rf2Client';
import {CatalogNutritionWorkspace} from '../src/nutrition/CatalogNutritionWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
const original = {
  ...fixture.weight, metadata: null,
  fact: {...fixture.weight.fact, kind: 'nutrition_record', id: 'fictional-intake', revision: '1',
    category: 'intake', title: 'Enteral intake chart', narrative: 'Original fictional report.',
    record_status: 'recorded', report_status: 'final'},
  terminal_reference: {kind: 'nutrition_record', id: 'fictional-intake', version: '1'},
} as Evidence;
const correction: Evidence = {...original, digest: 'a'.repeat(64),
  fact: {...original.fact, revision: '2', narrative: 'Corrected fictional report.'},
  terminal_reference: {...original.terminal_reference, version: '2'}};

function catalog(source: Evidence) {
  return {...structuredClone(fixture.catalog), nutrition_records: [source]} as unknown as Catalog;
}

test('reloads a historical review and resolves only the reviewed revision', async () => {
  const transport = {resolve: vi.fn(async () => [correction]), history: vi.fn(async () => [original])};
  const page = (source: Evidence) => <CatalogNutritionWorkspace catalog={catalog(source)} requested={requested}
    current guarded={false} transport={transport}/>;
  const first = render(page(original));
  fireEvent.click(screen.getByRole('button', {name: 'Tolerance & review'}));
  for (const [label, value] of Object.entries({Reviewer: 'Dr Fictional', Assessment: 'Reviewed original report.', 'Next review': '16:30'}))
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
  expect(await screen.findByText('Review saved in this browser.')).toBeVisible();
  first.unmount();

  render(page(correction));
  fireEvent.click(screen.getByRole('button', {name: 'Tolerance & review'}));
  expect(await screen.findByText('Historical evidence review')).toBeVisible();
  fireEvent.click(screen.getByRole('button', {name: 'Support & intake'}));
  expect(screen.getByText('Corrected fictional report.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', {name: 'Tolerance & review'}));
  fireEvent.click(screen.getByText('Reviewed source revisions'));
  fireEvent.click(screen.getByRole('button', {name: 'fictional-intake · Revision 1'}));
  expect(await screen.findByText('The exact reviewed revision could not be retrieved.')).toBeVisible();
  expect(screen.queryByRole('dialog')).toBeNull();

  transport.resolve.mockResolvedValueOnce([original]);
  fireEvent.click(screen.getByRole('button', {name: 'fictional-intake · Revision 1'}));
  expect(await screen.findByRole('dialog', {name: 'Enteral intake chart'})).toBeVisible();
  expect(screen.getAllByText('Original fictional report.').length).toBeGreaterThan(0);
  expect(transport.resolve).toHaveBeenCalledWith(original.repository, [pin(original)]);
});

test('blocks a draft when the shared evidence changes', () => {
  const page = (source: Evidence) => <CatalogNutritionWorkspace catalog={catalog(source)} requested={requested}
    current guarded={false}/>;
  const {rerender} = render(page(original));
  fireEvent.click(screen.getByRole('button', {name: 'Tolerance & review'}));
  fireEvent.change(screen.getByLabelText('Assessment'), {target: {value: 'Draft on revision 1.'}});
  rerender(page(correction));
  expect(screen.getByText('Evidence changed after this draft began. Clear the draft and review the new sources.')).toBeVisible();
  expect(screen.getByLabelText('Assessment')).toHaveValue('Draft on revision 1.');
  expect(screen.getByRole('button', {name: 'Save review'})).toBeDisabled();
});

test('reuses the shared feed interruption and electrolyte records', () => {
  const data = catalog(original);
  data.endocrine_records = [{...original, fact: {...original.fact, kind: 'endocrine_record',
    id: 'feed-pause', category: 'nutrition', title: 'Feed paused', narrative: 'Paused for imaging.'}}];
  data.laboratory_reports = [{...original, fact: {...original.fact, kind: 'laboratory_report',
    id: 'electrolytes', source_panel: {raw_display: 'Electrolyte panel'},
    components: [{mapping_status: 'mapped', mapped_concept: 'phosphate', test_code: {raw_display: 'Phosphate'},
      result: {kind: 'numeric', raw_value: '0.72', comparator: '=', unit: {raw_display: 'mmol/L'}}}]}}];
  render(<CatalogNutritionWorkspace catalog={data} requested={requested} current guarded={false}/>);
  fireEvent.click(screen.getByRole('button', {name: 'Tolerance & review'}));
  expect(screen.getByText('Paused for imaging.')).toBeVisible();
  expect(screen.getByText(/Phosphate.*0\.72 mmol\/L/)).toBeVisible();
});
