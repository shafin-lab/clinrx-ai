import React from 'react';
// @ts-expect-error Node-only real Blob polyfill for the preserved browser.
import {Blob as NodeBlob} from 'node:buffer';
import {beforeAll,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import {ClinRxAntibioticProfileBrowser} from '../src/profiles/ClinRxAntibioticProfileBrowser';
beforeAll(()=>{vi.stubGlobal('Blob',NodeBlob)});
describe('expanded antibiotic profiles',()=>{
 it('keeps seven bedside sections and puts spectrum with uses',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Meropenem"/>);
  await screen.findByRole('heading',{name:'Meropenem',level:2});
  expect(screen.getAllByRole('tab')).toHaveLength(7);
  expect(screen.getByRole('tab',{name:'Uses & spectrum'})).toBeInTheDocument();
  expect(screen.getByRole('tab',{name:'Administration & monitoring'})).toBeInTheDocument();
 });
 it('shows dose, route, frequency and infusion together with conditions',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Meropenem"/>);
  await screen.findByRole('heading',{name:'Meropenem',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const table=await screen.findByRole('table',{name:'Adult short-infusion dosing'});
  for(const name of ['Dose','Route','Frequency','Infusion'])expect(within(table).getByRole('columnheader',{name})).toBeInTheDocument();
  expect(within(table).getByRole('row',{name:/Meningitis 2 g IV Every 8 h 15–30 min/})).toBeInTheDocument();
  expect(screen.getByText(/CrCl >50 mL\/min/)).toBeInTheDocument();
 });
 it('shows PK facts in-page with concise PK and PD headings',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Meropenem"/>);
  await screen.findByRole('heading',{name:'Meropenem',level:2});
  fireEvent.click(screen.getByRole('tab',{name:/PK/}));
  expect(await screen.findByText('≈0.25 L/kg')).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'PK'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'PD'})).toBeInTheDocument();
  expect(screen.queryByText(/What the body does/)).not.toBeInTheDocument();
 });
 it('keeps advanced dosing and complete original details expandable',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Meropenem"/>);
  await screen.findByRole('heading',{name:'Meropenem',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const toggle=screen.getByText('Extended infusion');
  expect(toggle.closest('details')).not.toHaveAttribute('open');
  fireEvent.click(toggle);expect(toggle.closest('details')).toHaveAttribute('open');
  const original=screen.getByText('Full source summaries').closest('details');
  expect(original).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText('Full source summaries'));
  expect(within(original!).getByText(/NTEP DR-TB regimen context/)).toBeInTheDocument();
 });
 it('removes the previous drug tables when opening a local antibiotic',async()=>{
  render(<ClinRxAntibioticProfileBrowser/>);
  await screen.findByRole('heading',{name:'Meropenem',level:2});
  fireEvent.click(screen.getByRole('button',{name:/Ofloxacin.*otic/i}));
  await screen.findByRole('heading',{name:/Ofloxacin.*otic/i,level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  expect(screen.queryByRole('table',{name:'Adult short-infusion dosing'})).not.toBeInTheDocument();
  expect(screen.queryByText('≈0.25 L/kg')).not.toBeInTheDocument();
  expect(screen.getByText(/systemic oral ofloxacin renal adjustment does not apply directly/i)).toBeInTheDocument();
 });
 it('does not substitute another drug for an unsupported exact identity',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Anidulafungin"/>);
  expect(await screen.findByText(/No dedicated profile matches Anidulafungin/)).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Meropenem',level:2})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Clear search'}));
  expect(within(screen.getByRole('navigation',{name:'Antibiotic directory'})).getAllByRole('button')).toHaveLength(94);
 });
 it('does not hide programme dosing when only a renal overlay is present',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Prothionamide"/>);
  await screen.findByRole('heading',{name:'Prothionamide',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const text=screen.getByText(/Adult dosing is 15–20 mg\/kg\/day PO/);
  expect(text.closest('details')).toBeNull();
 });
 it('keeps a contraindicating renal cutoff visible rather than behind full summaries',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Nitrofurantoin"/>);
  await screen.findByRole('heading',{name:'Nitrofurantoin',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const text=screen.getByText(/US label contraindicates CrCl <60 mL\/min/);
  expect(text.closest('details')).toBeNull();
 });

 it('keeps broader consequential interaction warnings visible beside selected rows',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Rifampicin"/>);
  await screen.findByRole('heading',{name:'Rifampicin',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Safety'}));
  const warning=screen.getByText(/Potent enzyme\/transporter induction affects antiretrovirals/);
  expect(warning.closest('details')).toBeNull();
 });
 it('keeps an accepted normalized combination identity visible',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="meropenemvaborbactam"/>);
  expect(await screen.findByRole('heading',{name:/Meropenem.*vaborbactam/,level:2})).toBeInTheDocument();
 });
 it('uses current CDC neurosyphilis dosing in the primary table',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Benzylpenicillin"/>);
  await screen.findByRole('heading',{name:'Benzylpenicillin (aqueous penicillin G)',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const row=screen.getByRole('row',{name:/Neurosyphilis.*3–4 million units/});
  expect(row).toHaveTextContent('18–24 million units/day');
 });
 it('shows the conventional amikacin ceiling for both adult schedules',async()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Amikacin"/>);
  await screen.findByRole('heading',{name:'Amikacin',level:2});
  fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
  const context=screen.getByText(/Both conventional adult schedules: maximum 1.5 g\/day/);
  expect(context.closest('details')).toBeNull();
 });
 it('opens the exact searched antibiotic before drugs that merely mention it',()=>{
  render(<ClinRxAntibioticProfileBrowser/>);
  fireEvent.click(screen.getByRole('tab',{name:'PK/PD'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Search antibiotics and profile details'}),{target:{value:'Rifampicin'}});
  expect(screen.getByRole('heading',{name:'Rifampicin',level:2})).toBeInTheDocument();
  expect(screen.getByRole('tab',{name:'Overview'})).toHaveAttribute('aria-selected','true');
  const directory=screen.getByRole('navigation',{name:'Antibiotic directory'});
  expect(within(directory).getAllByRole('button')[0]).toHaveTextContent('Rifampicin');
 });
 it('still opens a combination explicitly selected from exact-name search results',()=>{
  render(<ClinRxAntibioticProfileBrowser initialMedicine="Meropenem"/>);
  fireEvent.click(screen.getByRole('button',{name:/Meropenem.*vaborbactam/}));
  expect(screen.getByRole('heading',{name:'Meropenem-vaborbactam',level:2})).toBeInTheDocument();
 });

});
