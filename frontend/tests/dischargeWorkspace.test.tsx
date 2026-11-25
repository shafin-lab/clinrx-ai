import {act, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {expect, test, vi} from 'vitest';
import type {AntibioticBundle} from '../src/api/antibioticClient';
import type {Catalog, Evidence} from '../src/api/rf2Client';
import {DischargeWorkspace, DischargeSummary} from '../src/discharge/DischargeWorkspace';
import {dischargeModel, type Inputs} from '../src/discharge/model';
import fixture from './fixtures/rf2-api.json';

const requested = {patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z'};
function plan(id: string, transition: string): Evidence {
  return {...fixture.weight, metadata: null,
    fact: {...fixture.weight.fact, kind: 'discharge_record', id, revision: '1',
      transition_id: id, transition, category: 'handover', destination: transition === 'icu_to_ward' ? 'Ward 3' : 'Home',
      state: 'planned', title: id + ' handover', narrative: 'Fictional handover pending.',
      record_status: 'recorded', report_status: 'final'},
    terminal_reference: {kind: 'discharge_record', id, version: '1'}} as Evidence;
}
function inputs(changed = false): Inputs {
  const catalog = {...structuredClone(fixture.catalog), discharge_records: [plan('transfer-01', 'icu_to_ward'), plan('home-01', 'home_discharge')]} as unknown as Catalog;
  if (changed) catalog.laboratory_reports = [{...fixture.weight, digest: 'f'.repeat(64),
    fact: {...fixture.weight.fact, kind: 'laboratory_report', id: 'new-creatinine', revision: '1'}} as Evidence];
  return {catalog, requested, devices: {status: 'ready', history: {episodes: [], procedures: [], outputs: []}},
    bundle: {renal: catalog, execution_enabled: false, micro: {assembly: {
      request: {scope: catalog.combined.context.scope}, snapshot: {items: []}}}} as unknown as AntibioticBundle,
    m10: {loading: false, snapshot: {repository: catalog.repository, cutoff: catalog.cutoff.fact_watermark,
      patient_id: requested.patient, encounter_id: requested.encounter, review_start: requested.start, review_end: requested.end,
      items: [], totals: {}, evidence: {}, execution_enabled: false}}};
}
async function saveReview(name: string) {
  fireEvent.click(screen.getByRole('button', {name: 'Review & handover'}));
  await waitFor(() => expect(screen.getByRole('button', {name: 'Save review'})).toBeEnabled());
  for (const [label, value] of Object.entries({Reviewer: name, Assessment: 'Reviewed shared evidence.', 'Next review': 'Next handover'}))
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
  expect(await screen.findByText('Review saved in this browser.')).toBeVisible();
}

test('keeps transfer and home reviews separate after reload and flags a new lab in both views', async () => {
  const initial = inputs();
  const first = render(<DischargeWorkspace {...initial} current guarded={false} onRefresh={async () => {}}/>);
  fireEvent.change(screen.getByLabelText('Transition'), {target: {value: 'transfer-01'}});
  await saveReview('Fictional transfer reviewer');
  fireEvent.change(screen.getByLabelText('Transition'), {target: {value: 'home-01'}});
  await saveReview('Fictional home reviewer');
  expect(screen.queryByText('Fictional transfer reviewer')).toBeNull();
  first.unmount();
  const page = (props: Inputs) => <><DischargeSummary {...props} current guarded={false} onOpen={() => {}}/>
    <DischargeWorkspace {...props} current guarded={false} onRefresh={async () => {}}/></>;
  const restored = render(page(initial));
  fireEvent.click(screen.getByRole('button', {name: 'Review & handover'}));
  expect(await screen.findByText('Matches current evidence')).toBeVisible();
  expect(screen.getByRole('heading', {name: 'Fictional home reviewer'})).toBeVisible();
  fireEvent.change(screen.getByLabelText('Transition'), {target: {value: 'transfer-01'}});
  expect(await screen.findByRole('heading', {name: 'Fictional transfer reviewer'})).toBeVisible();
  expect(screen.queryByRole('heading', {name: 'Fictional home reviewer'})).toBeNull();
  restored.rerender(page(inputs(true)));
  await waitFor(() => expect(screen.getAllByText('Transition review needed · Evidence changed.')).toHaveLength(2));
  expect(screen.getByText('Historical evidence review')).toBeVisible();
});

test('requires all shared feeds and refuses mismatched transition metadata', () => {
  const props = inputs();
  expect(dischargeModel(props).complete).toBe(true);
  expect(dischargeModel({...props, devices: {status: 'error'}}).complete).toBe(false);
  expect(dischargeModel({...props, m10: {loading: false, error: 'failed'}}).complete).toBe(false);
  expect(dischargeModel({...props, requested: {...requested, patient: 'another-patient'}}).complete).toBe(false);
  const extra = plan('conflict', 'icu_to_ward');
  extra.fact.transition_id = 'home-01';
  props.catalog!.discharge_records!.push(extra);
  expect(dischargeModel(props, 'home-01').complete).toBe(false);
});

test('does not label a course record as completed handover', () => {
  const props = inputs();
  const only = plan('course-only', 'home_discharge');
  only.fact.category = 'course';
  only.fact.state = 'completed';
  props.catalog!.discharge_records = [only];
  render(<DischargeSummary {...props} current guarded={false} onOpen={() => {}}/>);
  expect(screen.getByText('Handover not documented.')).toBeVisible();
  expect(screen.queryByText(/Recorded handover status/)).toBeNull();
});

test('keeps withdrawn transitions selectable and retains their saved review and device snapshot', async () => {
  const props = inputs();
  const page = (value: Inputs) => <DischargeWorkspace {...value} current guarded={false} onRefresh={async () => {}}/>;
  const view = render(page(props));
  fireEvent.change(screen.getByLabelText('Transition'), {target: {value: 'home-01'}});
  await saveReview('Fictional withdrawn-plan reviewer');
  const stored = Object.keys(localStorage).map(key => localStorage.getItem(key)).filter(Boolean).map(raw => JSON.parse(raw!));
  expect(stored.some(review => review.domain === 'M21' && review.snapshot.context?.transitionId === 'home-01' &&
    review.snapshot.context.deviceHistory.includes('episodes'))).toBe(true);
  const changed = inputs();
  changed.catalog!.discharge_records = changed.catalog!.discharge_records!.map(source => source.fact.transition_id === 'home-01'
    ? {...source, digest: 'e'.repeat(64), fact: {...source.fact, record_status: 'withdrawn', report_status: 'withdrawn'}} : source);
  view.rerender(page(changed));
  expect(screen.getByRole('option', {name: /home-01/})).toBeInTheDocument();
  expect(await screen.findByRole('heading', {name: 'Fictional withdrawn-plan reviewer'})).toBeVisible();
  expect(screen.getByText('Historical evidence review')).toBeVisible();
  expect(screen.getByRole('button', {name: 'Save review'})).toBeDisabled();
});

test('rejects a queued save if shared evidence changes before the lock is acquired', async () => {
  const props = inputs();
  const page = (value: Inputs) => <DischargeWorkspace {...value} current guarded={false} onRefresh={async () => {}}/>;
  const view = render(page(props));
  fireEvent.change(screen.getByLabelText('Transition'), {target: {value: 'home-01'}});
  fireEvent.click(screen.getByRole('button', {name: 'Review & handover'}));
  await waitFor(() => expect(screen.getByRole('button', {name: 'Save review'})).toBeEnabled());
  let release: (() => void) | undefined;
  vi.spyOn(navigator.locks, 'request').mockImplementation(((_name: string, callback: () => unknown) =>
    new Promise<unknown>((resolve, reject) => { release = () => {try {resolve(callback());} catch (error) {reject(error);}}; }
  )) as typeof navigator.locks.request);
  for (const [label, value] of Object.entries({Reviewer: 'Dr Queued', Assessment: 'Reviewed old sources.', 'Next review': 'Next round'}))
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  fireEvent.click(screen.getByRole('button', {name: 'Save review'}));
  await waitFor(() => expect(release).toBeTypeOf('function'));
  view.rerender(page(inputs(true)));
  await act(async () => release?.());
  expect(await screen.findByText(/Evidence changed before the review could be saved/)).toBeVisible();
  expect(localStorage.length).toBe(0);
});

test('withholds a conflicting pair of independently recorded handover states', () => {
  const props = inputs();
  const other = plan('second-home-handover', 'home_discharge');
  other.fact.transition_id = 'home-01';
  other.fact.state = 'cancelled';
  props.catalog!.discharge_records!.push(other);
  const model = dischargeModel(props, 'home-01');
  expect(model.handoverConflict).toBe(true);
  expect(model.complete).toBe(false);
  expect(model.records).toHaveLength(2);
});
