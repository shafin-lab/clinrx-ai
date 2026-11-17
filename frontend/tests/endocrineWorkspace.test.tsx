import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {beforeEach, expect, it, vi} from 'vitest';
import {RF2Client, type Catalog, type Evidence} from '../src/api/rf2Client';
import {EndocrineSummary, EndocrineWorkspace} from '../src/endocrine/EndocrineWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
type EndocrineCatalog = Catalog & {endocrine_records: Evidence[]; medication_orders: Evidence[]; medication_administrations: Evidence[]};

function source(id: string, kind: string, fact: object): Evidence {
  return {
    ...fixture.weight,
    fact: {...fixture.weight.fact, id, kind, revision: '1', ...fact},
    terminal_reference: {kind, id, version: '1'},
    metadata: null,
  };
}

const instant = (value: string) => ({status: 'known', precision: 'instant', value});
const time = (hour: string) => '2026-10-08T' + hour + ':00Z';
function glucose(id: string, hour: string, value: string, specimen = 'Capillary blood') {
  return source(id, 'laboratory_report', {
    record_status: 'recorded', report_status: 'final', specimen: {specimen_type: {raw_display: specimen}},
    times: {collected: instant(time(hour)), reported: instant(time(hour)), available: instant(time(hour))},
    components: [{source_component_id: id, mapped_concept: 'glucose', mapping_status: 'mapped',
      result: {kind: 'numeric', raw_value: value, comparator: '=', unit: {raw_display: 'mg/dL'}}}],
  });
}

function event(id: string, hour: string, category: string, fact: object) {
  return source(id, 'endocrine_record', {
    title: id, category, record_status: 'recorded', report_status: 'final',
    times: {occurred: instant(time(hour)), reported: instant(time(hour)), available: instant(time(hour))}, ...fact,
  });
}

function catalog(): EndocrineCatalog {
  const c = structuredClone(fixture.catalog) as unknown as EndocrineCatalog;
  c.laboratory_reports = [
    glucose('first-glucose', '08:00', '242'),
    glucose('second-glucose', '08:30', '198'),
    glucose('venous-glucose', '09:00', '183', 'Serum'),
    glucose('third-glucose', '09:30', '162'),
  ];
  c.endocrine_records = [
    event('Feed interrupted', '09:10', 'nutrition', {nutrition: {status: 'paused', route: 'Enteral'}}),
    event('Scheduled insulin held', '09:40', 'insulin_non_delivery', {insulin: {name: 'Insulin lispro', status: 'held', reason: 'Feed paused'}}),
  ];
  const administration = (name: string) => source(name, 'medication_administration', {
    medication: {ingredient_ids: [name], product_id: name}, administered_at: time('08:40'),
    time: {recorded: time('08:42')}, route: 'subcutaneous',
    administered_dose: {amount: {value: '2', unit: {raw: 'units'}}},
  });
  c.medication_administrations = [administration('insulin-lispro'), administration('fentanyl')];
  c.medication_orders = [source('Insulin prescription', 'medication_order', {
    medication: {ingredient_ids: ['insulin lispro']}, order_status: 'active', route: 'subcutaneous',
    time: {event: time('08:05'), recorded: time('08:05')}, prescribed_dose: {amount: {value: '2', unit: {raw: 'units'}}},
  })];
  return c;
}

function page(c: EndocrineCatalog) {
  return <>
    <EndocrineSummary catalog={c} requested={requested} current onOpen={() => {}}/>
    <EndocrineWorkspace catalog={c} requested={requested} current loading={false} onRefresh={async () => {}}/>
  </>;
}

beforeEach(() => { localStorage.clear(); });

it('shows source-separated glucose with insulin and feeding events in recorded chronological order', async () => {
  const c = catalog();
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([]);
  render(page(c));
  const summary = screen.getByRole('region', {name: 'Endocrine summary'});
  expect(within(summary).getByText(/162 mg\/dL.*Insulin.*held/i)).toBeVisible();
  expect(screen.getByText('242 → 198 → 162 mg/dL')).toBeVisible();
  expect(screen.getByText(/Last confirmed administration/)).toHaveTextContent(/08:40/);

  fireEvent.click(screen.getByRole('tab', {name: 'Glucose & insulin'}));
  const rows = within(screen.getByRole('table', {name: 'Glucose, insulin and nutrition timeline'})).getAllByRole('row').slice(1);
  expect(rows.map(row => row.textContent)).toEqual([
    expect.stringMatching(/242 mg\/dL.*Capillary blood/),
    expect.stringMatching(/Ordered.*insulin lispro/i),
    expect.stringMatching(/198 mg\/dL.*Capillary blood/),
    expect.stringMatching(/Given.*insulin-lispro · 2 units/i),
    expect.stringMatching(/183 mg\/dL.*Serum/),
    expect.stringMatching(/Enteral.*paused/i),
    expect.stringMatching(/162 mg\/dL.*Capillary blood/),
    expect.stringMatching(/Held.*Insulin lispro.*Feed paused/i),
  ]);
  expect(screen.queryByText(/fentanyl/i)).toBeNull();
  fireEvent.click(within(rows[5]).getByRole('button', {name: 'Open source'}));
  expect(await screen.findByRole('dialog', {name: 'Feed interrupted'})).toBeVisible();
});

function fillReview() {
  fireEvent.click(screen.getByRole('tab', {name: 'Review & plan'}));
  fireEvent.change(screen.getByLabelText('Reviewer'), {target: {value: 'Fictional reviewer'}});
  fireEvent.change(screen.getByLabelText('Assessment'), {target: {value: 'Glucose and feed events reviewed.'}});
  fireEvent.change(screen.getByLabelText('Next review'), {target: {value: '11:00 UTC'}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
}

it('retains a review across reload and flags a corrected result while preserving the reviewed version', async () => {
  const original = catalog();
  const view = render(page(original));
  fillReview();
  await screen.findByText('Review saved in this browser.');
  view.unmount();

  const restored = render(page(original));
  expect(await within(screen.getByRole('region', {name: 'Endocrine summary'})).findByText(/Next review 11:00 UTC/)).toBeVisible();
  const updated = structuredClone(original);
  const glucoseSource = updated.laboratory_reports[3];
  glucoseSource.fact.revision = '2';
  glucoseSource.terminal_reference.version = '2';
  glucoseSource.digest = 'a'.repeat(64);
  restored.rerender(page(updated));
  expect(within(screen.getByRole('region', {name: 'Endocrine summary'})).getByText(/Review needed/)).toBeVisible();
  fireEvent.click(screen.getByRole('tab', {name: 'Review & plan'}));
  expect(screen.getByText('Historical evidence review')).toBeVisible();

  const reviewed = original.laboratory_reports[3];
  vi.spyOn(RF2Client.prototype, 'resolve').mockResolvedValue([reviewed]);
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([reviewed]);
  fireEvent.click(screen.getByText('Reviewed source revisions'));
  fireEvent.click(screen.getByRole('button', {name: 'third-glucose · Revision 1'}));
  expect(await screen.findByRole('dialog')).toHaveTextContent('third-glucose');
});

it('keeps the review current when the repository advances for a non-insulin administration', async () => {
  const c = catalog();
  const view = render(page(c));
  fillReview();
  await screen.findByText('Review saved in this browser.');

  const next = structuredClone(c);
  next.cutoff.fact_watermark++;
  next.combined.context.scope.repository_cutoff.fact_watermark = next.cutoff.fact_watermark;
  const unrelated = next.medication_administrations[1];
  unrelated.fact.revision = '2';
  unrelated.terminal_reference.version = '2';
  unrelated.digest = 'e'.repeat(64);
  next.laboratory_reports[0].cutoff = next.cutoff.fact_watermark;
  view.rerender(page(next));
  const summary = screen.getByRole('region', {name: 'Endocrine summary'});
  expect(within(summary).getByText(/Next review 11:00 UTC/)).toBeVisible();
  expect(within(summary).queryByText(/Review needed/)).toBeNull();
});

it('labels a corrected glucose in place and excludes a withdrawn result from the summary', () => {
  const c = catalog();
  const corrected = c.laboratory_reports[3];
  corrected.fact.revision = '2';
  corrected.terminal_reference.version = '2';
  corrected.fact.report_status = 'corrected';
  const view = render(page(c));

  const summary = screen.getByRole('region', {name: 'Endocrine summary'});
  expect(within(summary).getByText(/162 mg\/dL.*Corrected/)).toBeVisible();
  fireEvent.click(screen.getByRole('tab', {name: 'Glucose & insulin'}));
  const timeline = screen.getByRole('table', {name: 'Glucose, insulin and nutrition timeline'});
  expect(within(timeline).getAllByText('162 mg/dL')).toHaveLength(1);
  expect(within(timeline).getByText('Corrected source result')).toBeVisible();

  const next = structuredClone(c);
  next.laboratory_reports[3].fact.record_status = 'withdrawn';
  next.laboratory_reports[3].fact.report_status = 'withdrawn';
  view.rerender(page(next));
  expect(within(summary).getByText(/Latest glucose unconfirmed/)).toBeVisible();
  expect(within(timeline).queryByText('162 mg/dL')).toBeNull();
  expect(within(timeline).getByText('Withdrawn source result')).toBeVisible();
});

it('rechecks the evidence after a queued review save acquires its lock', async () => {
  let release: (() => void) | undefined;
  vi.spyOn(navigator.locks, 'request').mockImplementation(((_name: string, callback: () => unknown) =>
    new Promise<unknown>((resolve, reject) => {
      release = () => { try { resolve(callback()); } catch (error) { reject(error); } };
    })) as typeof navigator.locks.request);
  const c = catalog();
  const view = render(page(c));
  fillReview();
  await waitFor(() => expect(release).toBeTypeOf('function'));

  const updated = structuredClone(c);
  updated.endocrine_records[0].digest = 'b'.repeat(64);
  view.rerender(page(updated));
  await act(async () => release?.());
  expect(await screen.findByText(/Evidence changed before the review could be saved/)).toBeVisible();
  expect(localStorage.length).toBe(0);
});
