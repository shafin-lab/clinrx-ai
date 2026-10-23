import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
import type {EvidenceEntryClient} from '../src/api/evidenceEntryClient';
import {PatientWorkspace} from '../src/demo/PatientWorkspace';
vi.mock('../src/demo/usePatientEvidenceState',()=>({usePatientEvidenceState:()=>({loading:false,error:'',refresh:vi.fn()})}));
vi.mock('../src/respiratory/RespiratoryWorkspace',()=>({RespiratoryWorkspace:({onGuardChange}:{onGuardChange:(v:boolean)=>void})=><section aria-label="M9 test workspace"><input aria-label="M9 retained note"/><button onClick={()=>onGuardChange(true)}>Protect M9 draft</button><button onClick={()=>onGuardChange(false)}>Release M9 draft</button></section>}));
vi.mock('../src/transfusion/TransfusionWorkspace',()=>({TransfusionWorkspace:({onGuardChange}:{onGuardChange:(v:boolean)=>void})=><section aria-label="M10 test workspace"><button onClick={()=>onGuardChange(true)}>Protect M10 draft</button><button onClick={()=>onGuardChange(false)}>Release M10 draft</button></section>}));
const config={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z',releasedExample:'released',withheldExample:'withheld',hosted:true};
beforeEach(()=>{vi.stubEnv('VITE_SYNTHETIC_RF2','true');vi.stubEnv('VITE_SYNTHETIC_M10','true');vi.stubEnv('VITE_SYNTHETIC_ANTIBIOTICS','true');window.history.replaceState({},'', '/?workspace=respiratory');});
afterEach(()=>{vi.unstubAllEnvs();window.history.replaceState({},'','/');});
function setup(){render(<PatientWorkspace config={config} client={{} as CirculatoryClient} entry={{} as EvidenceEntryClient}/>);}
it('preserves the mounted respiratory view and its note when opening and leaving M10',async()=>{
 setup();const note=await screen.findByRole('textbox',{name:'M9 retained note'});fireEvent.change(note,{target:{value:'M9 review in progress'}});
 fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));await screen.findByRole('region',{name:'M10 test workspace'});
 fireEvent.click(screen.getByRole('button',{name:'Respiratory system'}));expect(screen.getByRole('textbox',{name:'M9 retained note'})).toHaveValue('M9 review in progress');
});
it('protects both module drafts from cross-module navigation',async()=>{
 setup();fireEvent.click(await screen.findByRole('button',{name:'Protect M9 draft'}));expect(screen.getByRole('button',{name:'Hematologic system'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Release M9 draft'}));fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));
 fireEvent.click(await screen.findByRole('button',{name:'Protect M10 draft'}));expect(screen.getByRole('button',{name:'Respiratory system'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Release M10 draft'}));expect(screen.getByRole('button',{name:'Respiratory system'})).toBeEnabled();
});
it('does not expose M10 in a deployment that has not enabled its gateway',async()=>{
 vi.stubEnv('VITE_SYNTHETIC_M10','false');setup();await screen.findByRole('region',{name:'M9 test workspace'});expect(screen.queryByRole('button',{name:'Hematologic system'})).not.toBeInTheDocument();
});
it('uses clinician-facing system labels while retaining the existing workspace routes',async()=>{
 setup();
 for(const label of ['Cardiovascular system','Renal system','Respiratory system','Hematologic system','Antimicrobials'])expect(screen.getByRole('button',{name:label})).toBeVisible();
 for(const oldLabel of ['Hemodynamic review','Kidney review','Respiratory & ABG','Blood & coagulation','Antibiotics','Antibiotic references'])expect(screen.queryByRole('button',{name:oldLabel})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Hematologic system'}));expect(await screen.findByRole('region',{name:'M10 test workspace'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Respiratory system'}));expect(screen.getByRole('region',{name:'M9 test workspace'})).toBeVisible();
});
