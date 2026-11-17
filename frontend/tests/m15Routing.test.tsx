// @vitest-environment-options {"url":"http://127.0.0.1:5303/"}
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

it('navigates to the enabled wound care workspace and restores its route on reload', async () => {
  vi.stubEnv('VITE_SYNTHETIC_RF2', 'true');
  vi.stubEnv('VITE_SYNTHETIC_M15', 'true');
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));
  const workspace = <PatientWorkspace
    client={new RenalFluidClient(window.location.origin, config.patient, config.encounter)}
    entry={new EvidenceEntryClient()} config={config}
  />;
  const page = render(workspace);
  fireEvent.click(screen.getByRole('button', {name: /^Skin, Wounds and Pressure Care$/}));
  expect(new URL(window.location.href).searchParams.get('workspace')).toBe('wound-care');
  page.unmount();
  render(workspace);
  expect(screen.getByRole('button', {name: /^Skin, Wounds and Pressure Care$/})).toHaveAttribute('aria-current', 'page');
  expect(await screen.findByRole('heading', {name: /^Skin, Wounds and Pressure Care$/}, {timeout: 8000})).toBeVisible();
});
