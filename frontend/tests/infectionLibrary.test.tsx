import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {AntibioticReferences} from '../src/antibiotics/AntibioticReferences';
import {AntibioticWorkspace} from '../src/antibioticWorkflow/AntibioticWorkspace';

const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
function mount(){return render(<AntibioticReferences requested={requested} loading={false} onKidney={()=>{}}/>);}
function group(name:RegExp){const option=screen.getByRole('option',{name});fireEvent.change(screen.getByLabelText('Clinical group'),{target:{value:(option as HTMLOptionElement).value}});}

it('opens the infection library with 19 clinical groups and no medicine or CRRT browsing controls',()=>{
 mount();expect(screen.getByLabelText('Clinical group').querySelectorAll('option')).toHaveLength(19);
 expect(screen.getByLabelText('Find an infection')).toBeInTheDocument();
 expect(screen.queryByLabelText('Medicine group')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:/CRRT dosing reference|Medicine catalogue|Source library \(/i})).not.toBeInTheDocument();
 expect(screen.queryByRole('complementary',{name:'Antibiotic reference drawer'})).not.toBeInTheDocument();
});

it('finds pneumonia, selects its ward context and shows only the selected source-owned regimen',()=>{
 mount();group(/Respiratory/i);
 fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'community acquired pneumonia'}});
 fireEvent.click(screen.getByRole('button',{name:/Community.acquired pneumonia/i}));
 const context=screen.getByLabelText('Clinical situation');const ward=within(context).getByRole('option',{name:/inpatient ward/i});
 fireEvent.change(context,{target:{value:(ward as HTMLOptionElement).value}});
 const selected=screen.getByRole('region',{name:'Selected treatment guidance'});
 expect(selected).toHaveTextContent(/Ceftriaxone/i);expect(selected).toHaveTextContent(/2\s*g/i);
 expect(selected).not.toHaveTextContent(/JIPMER.*500/);
 expect(screen.getByText(/Reference only.*not a prescription/i)).toBeInTheDocument();
});

it('shows NCDC-only urinary guidance with no removed supplemental infections or source labels',()=>{
 mount();group(/Urinary/i);
 expect(screen.getByRole('button',{name:/Cystitis NCDC/i})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:/Pyelonephritis NCDC/i})).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:/Perinephric|Renal abscess/i})).not.toBeInTheDocument();
 expect(screen.getByRole('region',{name:'Infection-based antibiotic library'})).not.toHaveTextContent(/JIPMER/i);
});

it('clears the treatment panel when a search has no match and restores it when the query clears',()=>{
 mount();fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'no such infection 987654'}});
 expect(screen.getByRole('status')).toHaveTextContent(/No matching infections/i);
 expect(screen.queryByRole('region',{name:'Selected treatment guidance'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:''}});
 expect(screen.getByRole('region',{name:'Selected treatment guidance'})).toBeInTheDocument();
});

it('browses reference guidance without calling patient APIs, writing browser storage or creating a prescription',()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 const setItem=vi.spyOn(Storage.prototype,'setItem');
 try{mount();group(/Urinary/i);fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'renal abscess'}});
  expect(fetch).not.toHaveBeenCalled();expect(setItem).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:/Save|Prescribe|Create prescription|Calculate/i})).not.toBeInTheDocument();
 }finally{vi.unstubAllGlobals();}
});

it('remains generally browsable when the patient snapshot is stale, without claiming patient applicability',()=>{
 render(<AntibioticReferences requested={requested} loading={false} retrievalError="Stale snapshot" onKidney={()=>{}}/>);
 expect(screen.getByLabelText('Clinical group')).toBeEnabled();
 expect(screen.getByText(/not matched to this patient/i)).toBeInTheDocument();
});

it('opens the retained PDF belonging to the selected source rather than keeping the previous source link',()=>{
 mount();fireEvent.click(screen.getByText('Source details & treatment notes'));
 expect(screen.getByRole('link',{name:/Open retained source/})).toHaveAttribute('href',expect.stringMatching(/ncdc-2025\.pdf#page=/));
 group(/Urinary/i);fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'pyelonephritis'}});
 fireEvent.click(screen.getByText('Source details & treatment notes'));
 expect(screen.getByRole('link',{name:/Open retained source/})).toHaveAttribute('href',expect.stringMatching(/ncdc-2025\.pdf#page=46$/));
});

it('opens the library directly from its preview URL without starting an antibiotic entry',async()=>{
 window.history.replaceState(null,'','/?workspace=antibiotics&antibioticView=library');
 render(<AntibioticWorkspace loading={false} error="" requested={requested} onRefresh={async()=>{}} onGuardChange={()=>{}} onKidney={()=>{}}/>);
 expect(await screen.findByLabelText('Clinical group')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Reference library'})).toHaveAttribute('aria-pressed','true');
 expect(screen.queryByRole('heading',{name:/Record antibiotic source/i})).not.toBeInTheDocument();
});
