import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {expect, it, vi} from 'vitest';
import type {Catalog, Evidence} from '../src/api/rf2Client';
import {RF2Client} from '../src/api/rf2Client';
import {NeurologicalSummary, NeurologicalWorkspace} from '../src/neurological/NeurologicalWorkspace';
import fixture from './fixtures/rf2-api.json';

const requested = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
};
const at = (hhmm: string) => '2026-10-08T' + hhmm + ':00Z';
const instant = (hhmm: string) => ({status: 'known', precision: 'instant', value: at(hhmm)});

function record(catalog: Catalog, id: string, category: string, hhmm: string, fields: object): Evidence {
  return {
    ...fixture.weight,
    repository: catalog.repository,
    cutoff: catalog.cutoff.fact_watermark,
    superseded: false,
    fact: {
      ...fixture.weight.fact, id, revision: '1', kind: 'neurological_record',
      category, title: id, record_status: 'recorded', report_status: 'final',
      narrative: 'Fictional source findings for ' + id,
      times: {occurred: instant(hhmm), reported: instant(hhmm), available: instant(hhmm)},
      ...fields,
    },
    terminal_reference: {kind: 'neurological_record', id, version: '1'},
    metadata: null,
  };
}

function catalog(): Catalog {
  const c = structuredClone(fixture.catalog) as unknown as Catalog;
  c.neurological_records = [
    record(c, 'Early exam', 'exam', '08:10', {exam: {eye: 2, verbal: 'untestable', verbal_reason: 'intubated', motor: 5, rass: -3, pupils: 'Equal and reactive'}}),
    record(c, 'Later exam', 'exam', '09:30', {exam: {eye: 3, verbal: 'untestable', verbal_reason: 'intubated', motor: 6, rass: -1, pupils: 'Equal and reactive'}}),
    record(c, 'Propofol started', 'medication_status', '08:00', {medication: {name: 'Propofol', status: 'running'}}),
    record(c, 'Propofol pause', 'medication_status', '09:00', {medication: {name: 'Propofol', status: 'paused'}}),
    record(c, 'CT head', 'imaging', '08:32', {narrative: 'No acute intracranial haemorrhage reported.'}),
    record(c, 'Later medication', 'medication_status', '10:01', {medication: {name: 'Fentanyl', status: 'running'}}),
  ];
  const sodium = {
    source_component_id: 'sodium', test_code: {raw_display: 'Sodium'},
    mapping_status: 'mapped', mapped_concept: 'sodium', source_critical_flag: 'not_flagged',
    result: {kind: 'numeric', raw_value: '138', comparator: '=', unit: {raw_display: 'mmol/L'}},
  };
  c.laboratory_reports = [{
    ...record(c, 'Chemistry', 'exam', '08:20', {}),
    fact: {...record(c, 'Chemistry', 'exam', '08:20', {}).fact, kind: 'laboratory_report',
      times: {collected: instant('08:20'), reported: instant('08:40'), available: instant('08:40')}, components: [sodium]},
    terminal_reference: {kind: 'laboratory_report', id: 'Chemistry', version: '1'},
  }];
  c.medication_administrations = [{
    ...record(c, 'Completed midazolam', 'medication_status', '08:05', {}),
    fact: {
      ...fixture.weight.fact, id: 'Completed midazolam', revision: '1', kind: 'medication_administration',
      medication: {ingredient_ids: ['midazolam']}, route: 'IV',
      administered_dose: {basis: 'total_administered', amount: {value: '2', unit: {raw: 'mg'}}},
      administered_at: at('08:05'), time: {event: at('08:05'), recorded: at('08:06')},
    },
    terminal_reference: {kind: 'medication_administration', id: 'Completed midazolam', version: '1'},
  }];
  return c;
}

function chart(c: Catalog, scope = requested, current = true) {
  return <>
    <NeurologicalSummary catalog={c} requested={scope} current={current} onOpen={() => {}}/>
    <NeurologicalWorkspace catalog={c} requested={scope} current={current} loading={false} onRefresh={async () => {}}/>
  </>;
}

function openReview() {
  fireEvent.click(screen.getByRole('tab', {name: 'Review & plan'}));
}

function fillReview() {
  openReview();
  fireEvent.change(screen.getByLabelText('Reviewer'), {target: {value: 'Fictional clinician'}});
  fireEvent.change(screen.getByLabelText('Assessment'), {target: {value: 'Fictional neurological assessment'}});
  fireEvent.change(screen.getByLabelText('Next review'), {target: {value: '11:00 UTC'}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
}

it('shows shared exam components, contemporaneous medication records, and results', async () => {
  const c = catalog();
  const corrected = c.neurological_records![4];
  const older = {...corrected, superseded: true, fact: {...corrected.fact, revision: '0', narrative: 'Earlier CT wording'}};
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([older, corrected]);
  render(chart(c));
  expect(within(screen.getByRole('region', {name: 'Neurological summary'})).getByText(/E3 \/ V-NT \(intubated\) \/ M6/)).toBeVisible();
  expect(screen.queryByText('Fictional neurological assessment')).toBeNull();
  fireEvent.click(screen.getByRole('tab', {name: 'Serial exam'}));
  const serial = screen.getByRole('region', {name: 'Serial neurological exam'});
  const rows = within(serial).getAllByRole('article');
  expect(rows).toHaveLength(2);
  expect(within(rows[0]).getByText(/Propofol · paused/i)).toBeVisible();
  expect(within(rows[1]).getByText(/Propofol · running/i)).toBeVisible();
  expect(within(serial).queryByText(/Fentanyl/)).toBeNull();
  fireEvent.click(screen.getByText('Completed administrations'));
  expect(screen.getByText(/midazolam · 2 mg · IV/)).toBeVisible();
  fireEvent.click(screen.getByRole('tab', {name: 'Results & imaging'}));
  expect(screen.getByText('138 mmol/L')).toBeVisible();
  expect(screen.getByText('No acute intracranial haemorrhage reported.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', {name: 'Open imaging report'}));
  const source = screen.getByRole('dialog');
  expect(await within(source).findByText('Earlier CT wording')).toBeVisible();
});

it('restores the exact reviewed evidence after reload and retains it as historical after correction', async () => {
  const c = catalog();
  const original = render(chart(c));
  fillReview();
  await screen.findByText('Review saved in this browser.');
  original.unmount();

  const alternateRouteConfig = {...requested, unrelatedRouteFlag: true};
  const restored = render(chart(c, alternateRouteConfig));
  const summary = screen.getByRole('region', {name: 'Neurological summary'});
  expect(await within(summary).findByText(/Review due 11:00 UTC/)).toBeVisible();
  const updated = structuredClone(c);
  const exam = updated.neurological_records![1];
  exam.digest = 'a'.repeat(64);
  exam.fact = {...exam.fact, revision: '2'};
  exam.terminal_reference.version = '2';
  restored.rerender(chart(updated));
  expect(within(summary).queryByText(/Review due 11:00 UTC/)).toBeNull();
  expect(within(summary).getByText(/Review needed/)).toBeVisible();
  openReview();
  expect(screen.getByText('Historical evidence review')).toBeVisible();
  expect(screen.getByText('Fictional neurological assessment')).toBeVisible();

  const reviewed = c.neurological_records![1];
  vi.spyOn(RF2Client.prototype, 'resolve').mockResolvedValue([reviewed]);
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([reviewed]);
  fireEvent.click(screen.getByText('Reviewed source revisions'));
  fireEvent.click(screen.getByRole('button', {name: 'Later exam · Revision 1'}));
  const retainedSource = await screen.findByRole('dialog');
  expect(within(retainedSource).getByText(/Historical source/)).toBeVisible();
  expect(within(retainedSource).getByText('Later exam · Revision 1')).toBeVisible();
});

it('does not show another encounter’s evidence or report unconfirmed data as current', async () => {
  const c = catalog();
  const page = render(chart(c));
  fillReview();
  await screen.findByText('Review saved in this browser.');
  page.rerender(chart(c, requested, false));
  expect(within(screen.getByRole('region', {name: 'Neurological summary'})).getByText('Evidence unconfirmed')).toBeVisible();
  expect(screen.queryByText(/Review due 11:00 UTC/)).toBeNull();
  page.rerender(chart(c, {...requested, encounter: 'different-encounter'}));
  expect(screen.queryByText(/E3 \/ V-NT/)).toBeNull();
  expect(screen.queryByText('Fictional neurological assessment')).toBeNull();
  expect(screen.getByRole('button', {name: 'Save review'})).toBeDisabled();
});

it('uses the selected review period and excludes a report issued after its end', async () => {
  const c = catalog();
  c.neurological_records!.push(record(c, 'Delayed imaging', 'imaging', '08:20', {
    times: {occurred: instant('08:20'), reported: instant('09:40'), available: instant('09:40')},
    narrative: 'Imaging issued after the shorter review period.',
  }));
  const page = render(chart(c));
  fillReview();
  await screen.findByText('Review saved in this browser.');

  const shorter = {...requested, end: at('09:00')};
  const earlierCatalog = structuredClone(c);
  earlierCatalog.combined.context.scope.review_end = shorter.end;
  page.rerender(chart(earlierCatalog, shorter));
  const summary = screen.getByRole('region', {name: 'Neurological summary'});
  expect(within(summary).getByText(/E2 \/ V-NT.*Review needed/)).toBeVisible();
  expect(within(summary).queryByText(/Review due/)).toBeNull();
  expect(screen.getByText('Historical evidence review')).toBeVisible();
  fireEvent.click(screen.getByRole('tab', {name: 'Results & imaging'}));
  expect(screen.getByText('No acute intracranial haemorrhage reported.')).toBeVisible();
  expect(screen.queryByText('Imaging issued after the shorter review period.')).toBeNull();
});

it('rejects a save waiting for the browser lock when the exact evidence changes', async () => {
  let release: (() => void) | undefined;
  vi.spyOn(navigator.locks, 'request').mockImplementation(((_name: string, callback: () => unknown) =>
    new Promise<unknown>((resolve, reject) => {
      release = () => { try { resolve(callback()); } catch (error) { reject(error); } };
    })) as typeof navigator.locks.request);
  const c = catalog();
  const page = render(chart(c));
  fillReview();
  await waitFor(() => expect(release).toBeTypeOf('function'));
  const corrected = structuredClone(c);
  corrected.laboratory_reports[0].digest = 'b'.repeat(64);
  page.rerender(chart(corrected));
  await act(async () => release?.());
  expect(await screen.findByText(/Evidence changed before the review could be saved/)).toBeVisible();
  expect(localStorage.length).toBe(0);
});

it('identifies a disputed administration in the chart and its original source', async () => {
  const c = catalog();
  const entry = c.medication_administrations![0];
  entry.fact.conflict = 'unresolved';
  vi.spyOn(RF2Client.prototype, 'history').mockResolvedValue([entry]);
  render(chart(c));

  fireEvent.click(screen.getByRole('tab', {name: 'Serial exam'}));
  expect(screen.queryByText('Completed administrations')).toBeNull();
  fireEvent.click(screen.getByText('Administration records'));
  expect(screen.getByText('Unresolved source conflict')).toBeVisible();

  fireEvent.click(screen.getByRole('button', {name: 'Open administration record'}));
  const source = screen.getByRole('dialog', {name: 'Medication administration record'});
  await within(source).findByText('Version 1 · Latest at this cutoff');
  expect(within(source).getAllByText('Unresolved source conflict')).toHaveLength(2);
});
