import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {CompleteNcdcLibrary} from '../src/infectionLibrary/CompleteNcdcLibrary';
import complete from '../src/infectionLibrary/data/ncdc-complete-guidance.json';
import {infectionCatalogue} from '../src/infectionLibrary/catalogue';

function mount(){return render(<CompleteNcdcLibrary patient="synthetic-p1" encounter="synthetic-e1" data={complete}/>);}
function openSection(number:string){
 const section=complete.sections.find(s=>s.section===number)!;
 const entry=infectionCatalogue!.infections.find(i=>i.id===section.infectionId)!;
 fireEvent.change(screen.getByLabelText('Clinical group'),{target:{value:entry.groupId}});
 const list=screen.getByRole('complementary',{name:'Browse infections'});
 fireEvent.click(within(list).getAllByRole('button').find(b=>b.textContent?.startsWith(entry.name))!);
}
function row(index:number){
 const select=screen.getByLabelText('Clinical situation');
 fireEvent.change(select,{target:{value:(select.querySelectorAll('option')[index] as HTMLOptionElement).value}});
}
function supplement(){return screen.getByText(/^Further evidence & alternatives/).closest('details')!;}
function expand(){const details=supplement();fireEvent.click(details.querySelector('summary')!);details.open=true;return details;}

it('places a collapsed supplement after the unchanged NCDC source and keeps the external teicoplanin schedule separate',()=>{
 mount();openSection('1.1');row(2);
 const primary=screen.getByRole('region',{name:'First-line treatment'});
 const original=primary.textContent;
 const details=supplement();expect(details).not.toHaveAttribute('open');
 const source=screen.getByText(/NCDC.*Version 2.0.*PDF page/);
 expect(source.compareDocumentPosition(details)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 expand();
 const card=within(details).getByRole('region',{name:'Teicoplanin: additional dosing information'});
 expect(card).toHaveTextContent('12 mg/kg IV every 12 hours for 3–5 doses');
 expect(card).toHaveTextContent('12 mg/kg IV or IM once daily');
 expect(card).toHaveTextContent(/normal renal function/);
 expect(card).toHaveTextContent(/does not establish what NCDC intended/i);
 expect(within(card).getByRole('link',{name:/Read supporting source/})).toHaveAttribute('href','https://www.medicines.org.uk/emc/product/101956/smpc');
 expect(primary.textContent).toBe(original);
 expect(primary).not.toHaveTextContent('3–5 doses');
});

it('closes the supplement and removes context-specific information when the clinical situation changes',()=>{
 mount();openSection('1.1');row(2);expand();
 expect(supplement()).toHaveAttribute('open');
 row(0);expect(supplement()).not.toHaveAttribute('open');
 expect(screen.queryByRole('region',{name:'Teicoplanin: additional dosing information',hidden:true})).not.toBeInTheDocument();
 expect(screen.queryByText('Beta-lactam infusion in adult sepsis')).not.toBeInTheDocument();
 expect(screen.getByText('Endocarditis: organism and valve context')).toBeInTheDocument();
});

it('shows each shared reference once and clears expanded content on infection changes and unmatched searches',()=>{
 mount();openSection('1.1');row(2);
 const details=expand();
 const links=within(details).getAllByRole('link',{name:/Read supporting source/});
 expect(new Set(links.map(a=>a.getAttribute('href'))).size).toBe(links.length);
 openSection('9.7');expect(supplement()).not.toHaveAttribute('open');
 expect(screen.queryByText('Teicoplanin: additional dosing information')).not.toBeInTheDocument();
 expect(screen.getAllByText('Diabetic foot infection: duration and bone involvement')).toHaveLength(1);
 fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'no matching illness'}});
 expect(screen.queryByText(/^Further evidence & alternatives/)).not.toBeInTheDocument();
});

it('omits generic placeholders and unrelated external regimens for infections without a reviewed supplement',()=>{
 mount();openSection('12.5');
 expect(screen.queryByText(/^Further evidence & alternatives/)).not.toBeInTheDocument();
 openSection('19.1');
 expect(screen.queryByText(/^Further evidence & alternatives/)).not.toBeInTheDocument();
});

it('shows the intact NACO PID regimen with its own scope, source version and component durations',()=>{
 mount();openSection('6.6');const details=expand();
 expect(details).toHaveTextContent('NACO · 2024');
 expect(details).toHaveTextContent('Cefixime 800 mg orally once');
 expect(details).toHaveTextContent('Doxycycline 100 mg orally twice daily for 14 days');
 expect(details).toHaveTextContent('Metronidazole 400 mg orally twice daily for 14 days');
 expect(details).toHaveTextContent(/pregnancy|pregnant/i);
 expect(within(details).getAllByRole('link',{name:/Read supporting source/})).toHaveLength(1);
});

it('limits transplant HSV reference to its own row and never substitutes it for CMV or neonatal disease',()=>{
 mount();openSection('17.4');row(5);
 const details=expand();expect(details).toHaveTextContent('Acyclovir 5 mg/kg IV every 8 hours for 7–10 days');
 expect(details).toHaveTextContent(/not.*CNS|CNS.*different/i);
 row(7);expect(screen.queryByText(/^Further evidence & alternatives/)).not.toBeInTheDocument();
 openSection('19.1');expect(screen.queryByText('Acyclovir 5 mg/kg IV every 8 hours for 7–10 days')).not.toBeInTheDocument();
});

it('browses and expands supplementary evidence without source fetches, storage writes or patient actions',()=>{
 const fetchSpy=vi.fn();vi.stubGlobal('fetch',fetchSpy);
 const storage=vi.spyOn(Storage.prototype,'setItem');
 try{
  mount();openSection('1.1');row(2);expand();openSection('6.9');expand();
  expect(fetchSpy).not.toHaveBeenCalled();expect(storage).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:/save|prescribe|calculate|apply/i})).not.toBeInTheDocument();
 }finally{storage.mockRestore();vi.unstubAllGlobals();}
});
