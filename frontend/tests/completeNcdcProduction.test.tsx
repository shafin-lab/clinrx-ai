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
