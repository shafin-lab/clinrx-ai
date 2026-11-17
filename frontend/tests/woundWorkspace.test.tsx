import {fireEvent, render, screen, within} from '@testing-library/react';
import {beforeEach, expect, it, vi} from 'vitest';
import {RF2Client, type Catalog, type Evidence} from '../src/api/rf2Client';
import {WoundSummary, WoundWorkspace} from '../src/woundCare/WoundWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
type WoundCatalog = Catalog & {wound_records: Evidence[]};

const instant = (hour: string) => ({status: 'known', precision: 'instant', value: '2026-10-08T' + hour + ':00Z'});

function record(id: string, title: string, hour: string, fields: object): Evidence {
  return {
    ...fixture.weight, terminal_reference: {id, kind: 'wound_record', version: '1'}, metadata: null,
    fact: {...fixture.weight.fact, id, kind: 'wound_record', revision: '1', title,
      report_status: 'final', record_status: 'recorded',
      times: {occurred: instant(hour), reported: instant(hour), available: instant(hour)}, ...fields},
  };
}

function catalog(): WoundCatalog {
  const snapshot = structuredClone(fixture.catalog) as unknown as WoundCatalog;
  snapshot.wound_records = [
    record('wound-pressure', 'Repositioned', '08:40', {category: 'pressure_care', action: 'Right lateral repositioning'}),
    record('wound-check', 'Sacral reassessment', '09:00', {category: 'assessment', wound_id: 'W-01',
      site: 'Sacrum', stage: 'Stage 2', length_cm: '2.0', width_cm: '1.3'}),
    record('wound-first', 'Initial sacral assessment', '08:10', {category: 'assessment', wound_id: 'W-01',
      site: 'Sacrum', stage: 'Stage 2', length_cm: '2.2', width_cm: '1.4'}),
    record('wound-foam', 'Dressing changed', '09:15', {category: 'dressing', wound_id: 'W-01',
      dressing: 'Silicone foam', action: 'Changed'}),
  ];
  return snapshot;
}

function page(c: WoundCatalog) {
  return <>
    <WoundSummary catalog={c} requested={requested} current onOpen={() => {}}/>
    <WoundWorkspace catalog={c} requested={requested} current loading={false} onRefresh={async () => {}}/>
  </>;
}

beforeEach(() => {
  localStorage.clear();
});

it('shows the latest documented assessment and chronological wound and pressure-care records', async () => {
  const c = catalog();
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([]);
  render(page(c));
  const summary = screen.getByRole('region', {name: 'Wound care summary'});
  expect(within(summary).getByText(/Sacrum.*2.0 × 1.3 cm.*Dressing changed/)).toBeVisible();
  const timeline = screen.getByRole('region', {name: 'Wound and care timeline'});
  expect(within(timeline).getAllByRole('listitem').map(row => row.textContent)).toEqual([
    expect.stringMatching(/08:10.*Initial sacral assessment.*2.2 × 1.4 cm/),
    expect.stringMatching(/08:40.*Pressure care.*Repositioned.*Right lateral repositioning/),
    expect.stringMatching(/09:00.*Assessment.*W-01.*Sacral reassessment.*2.0 × 1.3 cm/),
    expect.stringMatching(/09:15.*Dressing changed.*Silicone foam/),
  ]);
  fireEvent.click(within(timeline).getByRole('button', {name: 'Open source for Dressing changed'}));
  expect(await screen.findByRole('dialog', {name: 'Dressing changed'})).toBeVisible();
});

function selectReview() {
  fireEvent.click(screen.getByRole('tab', {name: 'Review & plan'}));
}

function fillReview() {
  selectReview();
  fireEvent.change(screen.getByLabelText('Reviewer'), {target: {value: 'Fictional reviewer'}});
  fireEvent.change(screen.getByLabelText('Assessment'), {target: {value: 'Recorded wound and pressure care reviewed.'}});
  fireEvent.change(screen.getByLabelText('Next review'), {target: {value: '16:00 IST'}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
}

it('restores the saved review and retains its exact prior source after an assessment correction', async () => {
  const initial = catalog();
  const firstMount = render(page(initial));
  fillReview();
  await screen.findByText('Review saved in this browser.');
  firstMount.unmount();

  const restored = render(page(initial));
  const summary = screen.getByRole('region', {name: 'Wound care summary'});
  expect(await within(summary).findByText(/Next review 16:00 IST/)).toBeVisible();
  const changed = structuredClone(initial);
  changed.wound_records[1].fact.revision = '2';
  changed.wound_records[1].terminal_reference.version = '2';
  changed.wound_records[1].fact.length_cm = '2.1';
  changed.wound_records[1].digest = 'a'.repeat(64);
  restored.rerender(page(changed));
  expect(within(summary).getByText(/2.1 × 1.3 cm.*Review needed/)).toBeVisible();
  selectReview();
  expect(screen.getByText('Historical evidence review')).toBeVisible();

  const original = initial.wound_records[1];
  vi.spyOn(RF2Client.prototype, 'resolve').mockResolvedValue([original]);
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([original]);
  fireEvent.click(screen.getByText('Reviewed source revisions'));
  fireEvent.click(screen.getByRole('button', {name: 'wound-check · Revision 1'}));
  expect(await screen.findByRole('dialog')).toHaveTextContent('2.0 × 1.3 cm');
});

it('does not promote a previous measurement when the latest assessment is withdrawn', () => {
  const c = catalog();
  c.wound_records[1].fact.record_status = 'withdrawn';
  render(page(c));
  const summary = screen.getByRole('region', {name: 'Wound care summary'});
  expect(within(summary).getByText(/Latest assessment unconfirmed/)).toBeVisible();
  expect(within(summary).queryByText(/2.2 × 1.4 cm/)).toBeNull();
  expect(screen.getByText('Withdrawn source record')).toBeVisible();
});

it('keeps review current when only the shared snapshot watermark changes', async () => {
  const original = catalog();
  const view = render(page(original));
  fillReview();
  await screen.findByText('Review saved in this browser.');
  const next = structuredClone(original);
  next.cutoff.fact_watermark++;
  next.combined.context.scope.repository_cutoff.fact_watermark = next.cutoff.fact_watermark;
  next.wound_records.forEach(source => { source.cutoff = next.cutoff.fact_watermark; });
  view.rerender(page(next));
  const summary = screen.getByRole('region', {name: 'Wound care summary'});
  expect(within(summary).getByText(/Next review 16:00 IST/)).toBeVisible();
  expect(within(summary).queryByText(/Review needed/)).toBeNull();
});

it('keeps later reports and records from a different encounter out of the summary and timeline', () => {
  const c = catalog();
  c.wound_records.push(
    record('wound-reported-late', 'Late report', '09:45', {category: 'assessment', wound_id: 'W-01',
      site: 'Sacrum', length_cm: '8.0', width_cm: '7.0',
      times: {occurred: instant('09:45'), reported: instant('10:01'), available: instant('10:01')}}),
    record('wound-other-encounter', 'Other encounter', '09:50', {category: 'assessment', wound_id: 'W-01',
      site: 'Sacrum', length_cm: '6.0', width_cm: '7.0',
      binding: {target: {...fixture.weight.fact.binding.target, encounter_id: 'different'}}}),
  );
  render(page(c));
  const summary = screen.getByRole('region', {name: 'Wound care summary'});
  expect(within(summary).getByText(/2.0 × 1.3 cm/)).toBeVisible();
  expect(screen.queryByText('Late report')).toBeNull();
  expect(screen.queryByText('Other encounter')).toBeNull();
});
