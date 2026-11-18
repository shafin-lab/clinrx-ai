// @vitest-environment-options {"url":"http://127.0.0.1:5301/"}
import {afterEach, expect, it, vi} from 'vitest';
import {fireEvent, render, screen} from '@testing-library/react';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
import {RenalFluidClient} from '../src/api/renalFluidClient';
import {EvidenceEntryClient} from '../src/api/evidenceEntryClient';

const config = {
  patient: 'synthetic-p1', encounter: 'synthetic-e1',
  start: '2026-10-08T08:00:00Z', end: '2026-10-08T10:00:00Z',
  releasedExample: 'a', withheldExample: 'b', hosted: true,
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  window.history.replaceState(null, '', '/');
});

it('navigates to the enabled sedation workspace and restores its route on reload', async () => {
  vi.stubEnv('VITE_SYNTHETIC_RF2', 'true');
  vi.stubEnv('VITE_SYNTHETIC_M18', 'true');
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));
  const workspace = <PatientWorkspace
    client={new RenalFluidClient(window.location.origin, config.patient, config.encounter)}
    entry={new EvidenceEntryClient()} config={config}
  />;
  const page = render(workspace);
  fireEvent.click(screen.getByRole('button', {name: 'Pain, sedation and delirium'}));
  expect(new URL(window.location.href).searchParams.get('workspace')).toBe('sedation');
  page.unmount();
  render(workspace);
  expect(screen.getByRole('button', {name: 'Pain, sedation and delirium'})).toHaveAttribute('aria-current', 'page');
  expect(await screen.findByRole('heading', {name: 'Pain, sedation and delirium'}, {timeout: 8000})).toBeVisible();
}, 15000);

it('rejects the direct route when M18 is disabled', () => {
  vi.stubEnv('VITE_SYNTHETIC_RF2', 'true');
  vi.stubEnv('VITE_SYNTHETIC_M18', 'false');
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));
  window.history.replaceState(null, '', '/?workspace=sedation');
  render(<PatientWorkspace
    client={new RenalFluidClient(window.location.origin, config.patient, config.encounter)}
    entry={new EvidenceEntryClient()} config={config}
  />);
  expect(screen.queryByRole('button', {name: 'Pain, sedation and delirium'})).toBeNull();
  expect(new URL(window.location.href).searchParams.get('workspace')).toBe('overview');
});
