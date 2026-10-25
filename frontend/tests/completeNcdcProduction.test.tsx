import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it} from 'vitest';
import {AntibioticReferences} from '../src/antibiotics/AntibioticReferences';
import complete from '../src/infectionLibrary/data/ncdc-complete-guidance.json';
import {validateCompleteGuidance} from '../src/infectionLibrary/completeNcdcModel';
import {infectionCatalogue} from '../src/infectionLibrary/catalogue';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const mount=()=>render(<AntibioticReferences requested={requested} loading={false} onKidney={()=>{}}/>);
function select(label:string,value:string){fireEvent.change(screen.getByLabelText(label),{target:{value}});}
it('activates complete NCDC guidance for all19groups instead of the earlier curated-only renderer',()=>{
 expect(validateCompleteGuidance(complete)).toBe(true);
 expect(complete.sections).toHaveLength(87);
 mount();expect(screen.getByLabelText('Clinical group').querySelectorAll('option')).toHaveLength(19);
 select('Clinical group','group-1');
 const situation=screen.getByLabelText('Clinical situation');
 const severe=within(situation).getByRole('option',{name:/severe sepsis/i});
 select('Clinical situation',(severe as HTMLOptionElement).value);
 const primary=screen.getByRole('region',{name:'First-line treatment'});
 expect(primary).toHaveTextContent(/Vancomycin.*Meropenem.*OR.*Teicoplanin.*Gentamicin/i);
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent(/Daptomycin.*Meropenem/i);
 expect(screen.getByRole('region',{name:'Infection-based antibiotic library'})).not.toHaveTextContent(/source branch|No fixed regimen/i);
});
it('renders every published structured NCDC treatment row without dropping source text',()=>{
 mount();
 for(const section of complete.sections){
  const entry=infectionCatalogue!.infections.find(i=>i.id===section.infectionId)!;
  select('Clinical group',entry.groupId);
  const list=screen.getByRole('complementary',{name:'Browse infections'});
  const button=within(list).getAllByRole('button').find(b=>b.textContent?.startsWith(entry.name));
  expect(button,section.section).toBeDefined();fireEvent.click(button!);
  for(const row of section.rows){
   if(section.rows.length>1)select('Clinical situation',row.id);
   const normalize=(s:string)=>s.replace(/\s+/g,'').toLocaleLowerCase();
   if(section.section==='10.2'){
    expect(normalize(screen.getByRole('region',{name:'Comments'}).textContent??'')).toContain(normalize(row.firstLine));
    continue;
   }
   for(const [title,value] of [['First-line treatment',row.firstLine],['Alternative treatment',row.alternative]]){
    const panel=screen.getByRole('region',{name:title});
    expect(normalize(panel.textContent??''),`${section.section}/${row.label}/${title}`).toContain(normalize(value));
   }
  }
  if(!section.rows.length)expect(screen.getAllByRole('img').length+section.notes.length).toBeGreaterThan(0);
 }
},60000);
function openSection(sectionNumber:string){
 const section=complete.sections.find(s=>s.section===sectionNumber)!;
 const entry=infectionCatalogue!.infections.find(i=>i.id===section.infectionId)!;
 select('Clinical group',entry.groupId);
 const button=within(screen.getByRole('complementary',{name:'Browse infections'})).getAllByRole('button').find(b=>b.textContent?.startsWith(entry.name))!;
 fireEvent.click(button);
}
it('keeps mild and moderate/severe MRSA cellulitis treatments in their own clinical situations',()=>{
 mount();openSection('9.3');
 const options=within(screen.getByLabelText('Clinical situation')).getAllByRole('option');
 const mild=options.find(o=>/MRSA/i.test(o.textContent??'')&&/Mild/i.test(o.textContent??''))!;
 expect(mild).toBeDefined();expect(mild).not.toHaveTextContent(/Moderate/i);
 select('Clinical situation',(mild as HTMLOptionElement).value);
 expect(screen.getByRole('region',{name:'First-line treatment'})).toHaveTextContent(/Trimethoprim.*800 mg\/160 mg BD/i);
 expect(screen.getByRole('region',{name:'First-line treatment'})).not.toHaveTextContent(/Vancomycin/i);
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent(/Doxycycline 100 mg q12h/i);
 expect(screen.getByRole('region',{name:'Alternative treatment'})).not.toHaveTextContent(/Linezolid/i);
 const severe=options.find(o=>/MRSA/i.test(o.textContent??'')&&/Moderate/i.test(o.textContent??''))!;
 select('Clinical situation',(severe as HTMLOptionElement).value);
 expect(screen.getByRole('region',{name:'First-line treatment'})).toHaveTextContent(/Vancomycin 15 to 20 mg\/kg\/dose every 8 to 12 hours/i);
 expect(screen.getByRole('region',{name:'First-line treatment'})).not.toHaveTextContent(/Trimethoprim/i);
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent(/Linezolid 600mg q12 h/i);
});
it('shows viral keratitis subtype context without inventing a heading-only treatment',()=>{
 mount();openSection('11.1');
 const options=within(screen.getByLabelText('Clinical situation')).getAllByRole('option');
 for(const subtype of ['Epithelial','Stromal','Endothelial']){
  const option=options.find(o=>o.textContent?.includes(subtype))!;
  expect(option).toHaveTextContent(/Viral Keratitis/i);
 }
 expect(options.some(o=>o.textContent?.trim()==='Viral Keratitis HSV is the most common cause of viral keratitis')).toBe(false);
});
it('shows the exact neonatal PDF120 table alongside the affected printed age criteria',()=>{
 mount();openSection('19.1');
 const image=screen.getAllByRole('img').find(i=>/PDF page 120/.test(i.getAttribute('alt')??'')&&!i.closest('details'));
 expect(image).toBeDefined();
});
