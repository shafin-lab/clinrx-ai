import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import type {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {deviceHistoryRoute, type DeviceHistory} from '../src/devices/deviceHistory';

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  window.history.replaceState(null, '', '/');
});

it('opens procedure history from the overview and keeps output with the exact original episode after reload', async () => {
  vi.stubEnv('VITE_SYNTHETIC_RF2', 'true');
  vi.stubEnv('VITE_SYNTHETIC_M19', 'true');
  const context = {patient_id: 'synthetic-p1', encounter_id: 'synthetic-e1'};
  const source = {namespace: 'fixture', identifier: 'chart', version: '1'};
  const time = {value: null, lower: null, upper: null, precision: 'unknown'};
  const device = (id:string) => ({kind: 'device_episode', id, version: '1'});
  const output = (id:string) => ({kind: 'observation', id, version: '1'});
  const original = device('removed-drain');
  const replacement = device('replacement-drain');
  const episode = {context, source, device_type: 'Chest drain', site: null, laterality: null,
    indication: null, inserted: time, removed: time};
  const history: DeviceHistory = {
    episodes: [
      {...episode, reference: original, status: 'removed', replaces: null},
      {...episode, reference: replacement, status: 'in_place', replaces: original},
    ],
    procedures: [{
      reference: {kind: 'procedure_record', id: 'replace-drain', version: '1'},
      context, source, title: 'Chest drain replacement', status: 'performed', occurred: time,
      author: null, method: null, site: null, complications: null, follow_up: null,
      devices: [original, replacement], reports: [],
    }],
    outputs: [
      {context, output: output('historical-output'), device: original},
      {context, output: output('unresolved-output'), device: device('missing-drain')},
    ],
  };
  const fetchHistory = vi.fn(async (input: string) => input === deviceHistoryRoute
    ? new Response(JSON.stringify(history)) : new Response(null, {status: 404}));
  vi.stubGlobal('fetch', fetchHistory);
  const config = {patient: context.patient_id, encounter: context.encounter_id, hosted: true,
    start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z', releasedExample: '', withheldExample: ''};
  const client = {circulatoryState: vi.fn(async () => { throw Error('Fixture has no circulatory evidence'); })};
  const workspace = <PatientWorkspace client={client as unknown as CirculatoryClient}
    entry={{} as EvidenceEntryClient} config={config}/>;

  const first = render(workspace);
  fireEvent.click(screen.getByRole('button', {name: 'Open device and procedure history'}));
  await screen.findByRole('heading', {name: 'Chest drain replacement'});
  first.unmount();

  render(workspace);
  await screen.findByRole('heading', {name: 'Chest drain replacement'});
  const linked = screen.getByRole('list', {name: 'Associated device episodes'});
  const originalLink = within(linked).getByRole('link', {name: /removed-drain/});
  const originalEpisode = document.getElementById(decodeURIComponent(originalLink.getAttribute('href')!.slice(1)));
  expect(originalEpisode).toHaveTextContent('historical-output');
  const replacementLink = within(linked).getByRole('link', {name: /replacement-drain/});
  const replacementEpisode = document.getElementById(decodeURIComponent(replacementLink.getAttribute('href')!.slice(1)));
  expect(replacementEpisode).not.toHaveTextContent('historical-output');
  expect(screen.getByText(/unresolved-output/)).toHaveTextContent('Device reference unresolved');
  expect(fetchHistory.mock.calls.filter(([path]) => path === deviceHistoryRoute)).toHaveLength(2);
});
