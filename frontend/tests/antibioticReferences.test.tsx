import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
// Retained legacy collection; the active entry point is covered in infectionLibrary.test.tsx.
import {AntibioticReferences} from '../src/antibiotics/LegacyAntibioticReferences';
import {assertUnreviewed,catalogue,library,nationalGuidance,supplementalGuidance,referenceDataValid,guidanceForMedicine,supplementalForMedicine,supplementalSource} from '../src/antibiotics/referenceData';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
function mount(){const onKidney=vi.fn();return {onKidney,...render(<AntibioticReferences requested={requested} loading={false} onKidney={onKidney}/>)};}
function select(name:string){fireEvent.change(screen.getByLabelText('Find a medicine'),{target:{value:name}});fireEvent.click(within(screen.getByRole('region',{name:'Antibiotic medicine catalogue'})).getByRole('button',{name:new RegExp('^'+name)}));}
it('retains all exact catalogue identities and independent unreviewed national/supplemental records',()=>{
 expect(referenceDataValid).toBe(true);expect(catalogue.records).toHaveLength(382);expect(library.records).toHaveLength(26);
 expect(nationalGuidance.executable).toBe(false);expect(supplementalGuidance.executable).toBe(false);
 for(const medicine of catalogue.records){
  const n=guidanceForMedicine(medicine.name)!,s=supplementalForMedicine(medicine.name)!;expect(n.medicine_id).toBe(medicine.id);expect(s.medicine_id).toBe(medicine.id);
  expect(n.clinical_use_eligible).toBe(false);expect(s.clinical_use_eligible).toBe(false);expect(n.review_status).toBe('unreviewed');
  for(const mode of ['renal','crrt'] as const)for(const ref of s[mode]){expect(ref.clinical_use_eligible).toBe(false);expect(ref.review_status).toBe('unreviewed');expect(supplementalSource(ref.source_id)).toBeDefined();expect(ref.assumptions.length).toBeGreaterThan(0);expect(ref.locator).toBeTruthy();}
  if(medicine.combination_group){expect(s.renal).toEqual([]);expect(s.crrt).toEqual([]);expect(n.renal.dose_text).toBeNull();}
 }
 expect(guidanceForMedicine('Unlisted medicine')).toBeNull();expect(supplementalForMedicine('Unlisted medicine')).toBeNull();
});
it('rejects any imported record that becomes reviewed, clinically eligible or executable',()=>{
 for(const bad of [{review_status:'approved'},{nested:[{clinical_use_eligible:true}]},{executable:true}])expect(()=>assertUnreviewed(bad)).toThrow();
});
it('opens source-specific CRRT cards with numerical references initially collapsed and leaves patient state untouched',()=>{
 const before=JSON.stringify([catalogue,nationalGuidance,supplementalGuidance]);const send=vi.fn();vi.stubGlobal('fetch',send);
 mount();select('Teicoplanin');const drawer=screen.getByRole('complementary',{name:'Antibiotic reference drawer'});
 expect(within(drawer).getByRole('heading',{name:'Teicoplanin'})).toBeInTheDocument();expect(drawer).toHaveTextContent('24-hour continuous CRRT');expect(drawer).toHaveTextContent('CN-CRRT-CONSENSUS-2024');
 for(const disclosure of drawer.querySelectorAll('.supplemental-dose-reference'))expect(disclosure).not.toHaveAttribute('open');
 expect(screen.queryByRole('button',{name:/Save|Prescribe|Calculate dose|Record.*review/i})).not.toBeInTheDocument();expect(send).not.toHaveBeenCalled();
 expect(JSON.stringify([catalogue,nationalGuidance,supplementalGuidance])).toBe(before);vi.unstubAllGlobals();
});
it('keeps library search separate from the inspected medicine and can return to kidney evidence',()=>{
 const {onKidney}=mount();select('Teicoplanin');fireEvent.click(screen.getByRole('button',{name:'Source library (26)'}));fireEvent.change(screen.getByLabelText('Find a drug, topic or source'),{target:{value:'meropenem'}});
 expect(within(screen.getByRole('complementary')).getByRole('heading',{name:'Teicoplanin'})).toBeInTheDocument();expect(screen.getByRole('region',{name:'Antibiotic source library'})).toHaveTextContent('all Unreviewed');
 fireEvent.click(screen.getByRole('button',{name:'Open kidney evidence ↗'}));expect(onKidney).toHaveBeenCalledOnce();
});
it('uses an explicit unlisted-medicine gap without inheriting another product reference',()=>{
 mount();fireEvent.change(screen.getByLabelText('Find a medicine'),{target:{value:'unlisted synthesis compound'}});fireEvent.click(screen.getByRole('button',{name:/Inspect unlisted medicine/}));const drawer=screen.getByRole('complementary');expect(drawer).toHaveTextContent('Unlisted medicine');expect(drawer).toHaveTextContent('No national guidance is mapped');expect(drawer.querySelectorAll('.supplemental-dose-reference')).toHaveLength(0);
});

it('contains no withdrawn supplemental source content',()=>{expect(JSON.stringify(supplementalGuidance)).not.toMatch(/JIPMER/i);});
