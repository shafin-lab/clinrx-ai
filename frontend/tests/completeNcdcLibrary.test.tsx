import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {CompleteNcdcLibrary} from '../src/infectionLibrary/CompleteNcdcLibrary';
import {formatTreatment,validateCompleteGuidance} from '../src/infectionLibrary/completeNcdcModel';
import {infectionCatalogue} from '../src/infectionLibrary/catalogue';

const source={id:'ncdc',name:'NCDC',version:'November 2025',url:'https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf',sha256:'0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a'};
const row=(id:string,label:string,firstLine:string,alternative='',comments='')=>({id,label,firstLine,alternative,comments,pdfPages:[21]});
const section=(infectionId:string,number:string,rows:ReturnType<typeof row>[])=>({infectionId,section:number,name:infectionId,pdfPages:[21],rows,notes:[],figures:[],sourceText:'Original section'});
const severe='Vancomycin 15mg/kg IV\n12 hrly (maximum 1g 12\nh) for 4-6 weeks\n+\nMeropenem 1g IV q8h\nfor 4-6 weeks\nOr\nTeicoplanin 12mg/kg IV\n12 hrly x 3 doses\nfollowed by 6 - 12mg OD\nIV depending upon\nseverity\n+\nGentamicin 1mg/kg IM or\nIV 8 h for 4-6 weeks';
const data={source,sections:[section('ncdc-1-1','1.1',[
 row('native','Uncomplicated native valve','Penicillin G 4 million units IV every 4 hours for 4 weeks\nOr\nAmpicillin 2g IV every 4 hours for 4 weeks\n+\nGentamicin 1mg/kg IM or IV every 8 hours for first 2 weeks','Vancomycin 15mg/kg IV every 12 hours for 4-6 weeks','Obtain blood cultures.'),
 row('prosthetic','Uncomplicated prosthetic valve','Vancomycin 15mg/kg IV every 12 hours for 6 weeks\n+\nGentamicin 1mg/kg IM or IV every 8 hours for first 2 weeks','Daptomycin 10mg/kg every 24 hours\n+\nGentamicin 1mg/kg IM or IV every 8 hours for first 2 weeks'),
 row('severe','Complicated (In Severe Sepsis)',severe,'Daptomycin 10mg/kg IV OD\n+\nMeropenem 1g IV q8h\nDuration:4-6 weeks')]),
 section('ncdc-10-1','10.1',[row('non-heme','Non hematogenous osteomyelitis','Inj Cloxacillin 2g IV\nq6h','Amoxicillin-clavulanic acid 1g + 200mg q8h IV','Total duration 4-6 weeks')]),
 section('ncdc-10-2','10.2',[row('chronic','Acute on chronic (accompanied with fever)','Blood culture should be\nobtained before\nstarting antimicrobial therapy. Empirical therapy as\nper guidelines for acute\nosteomyelitis.','Same as in acute osteomyelitis','Surgical debridement and targeted treatment according to susceptibility.')])]};
const catalog={...infectionCatalogue!,infections:infectionCatalogue!.infections.filter(i=>data.sections.some(s=>s.infectionId===i.id))};
function mount(){return render(<CompleteNcdcLibrary patient="synthetic-p1" encounter="synthetic-e1" data={data} catalogue={catalog}/>);}
function group(name:RegExp){const select=screen.getByLabelText('Clinical group');const opt=within(select).getByRole('option',{name});fireEvent.change(select,{target:{value:(opt as HTMLOptionElement).value}});}
function context(name:RegExp,label='Clinical situation'){const select=screen.getByLabelText(label);const opt=within(select).getByRole('option',{name});fireEvent.change(select,{target:{value:(opt as HTMLOptionElement).value}});}
it('shows complete first-line OR combinations and separate alternatives without development jargon',()=>{
 mount();group(/Cardiovascular/);context(/Severe Sepsis/);
 const first=screen.getByRole('region',{name:'First-line treatment'});
 expect(first).toHaveTextContent(/Vancomycin.*Meropenem.*OR.*Teicoplanin.*Gentamicin/);
 expect(first).toHaveTextContent('12 hrly x 3 doses');
 expect(first).toHaveTextContent(/4-6 weeks/);
 expect(first).not.toHaveTextContent('Daptomycin');
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent(/Daptomycin.*Meropenem/);
 expect(screen.getByRole('region',{name:'Infection-based antibiotic library'})).not.toHaveTextContent(/source branch|No fixed regimen|Source review required/i);
 expect(first).toHaveTextContent(/weight basis.*not stated|not.*weight basis/i);
});
it('retains different component durations and route choices from the source row',()=>{
 mount();group(/Cardiovascular/);context(/prosthetic/);
 expect(screen.getByRole('region',{name:'First-line treatment'})).toHaveTextContent(/6 weeks.*IM or IV.*first 2 weeks/);
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent('every 24 hours');
});
it('resolves chronic referral to the existing acute row and clears old treatment on search changes',()=>{
 mount();group(/Musculoskeletal/);fireEvent.click(screen.getByRole('button',{name:/^Chronic Osteomyelitis/}));
 expect(screen.getByText(/Empirical treatment referenced from NCDC acute osteomyelitis/)).toBeInTheDocument();
 context(/Non hematogenous/,'Acute osteomyelitis context');
 expect(screen.getByRole('region',{name:'First-line treatment'})).toHaveTextContent('Cloxacillin 2g IV q6h');
 expect(screen.getByRole('region',{name:'Alternative treatment'})).toHaveTextContent('Amoxicillin-clavulanic');
 expect(screen.getByRole('region',{name:'Comments'})).toHaveTextContent('Surgical debridement');
 fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:'no matching illness'}});
 expect(screen.queryByRole('region',{name:'First-line treatment'})).not.toBeInTheDocument();
});
it('folds column wrapping while preserving standalone OR/PLUS and IM or IV wording',()=>{
 expect(formatTreatment('Drug A 1g\nIV q8h\nOr\nDrug B 2g\n+\nDrug C IM or\nIV q8h')).toEqual(['Drug A 1g IV q8h','OR','Drug B 2g','+','Drug C IM or IV q8h']);
});
it('rejects other sources and unsafe image paths before rendering',()=>{
 expect(validateCompleteGuidance(data)).toBe(true);
 expect(validateCompleteGuidance({...data,source:{...source,id:'other'}})).toBe(false);
 expect(validateCompleteGuidance({...data,sections:[{...data.sections[0],figures:[{imagePath:'https://example.com/a.png',pdfPage:21,caption:'X'}]}]})).toBe(false);
});
it('browses without patient fetches, storage writes or prescribing controls',()=>{
 const send=vi.fn();vi.stubGlobal('fetch',send);const storage=vi.spyOn(Storage.prototype,'setItem');
 try{mount();group(/Cardiovascular/);context(/prosthetic/);expect(send).not.toHaveBeenCalled();expect(storage).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:/Save|Prescribe|Calculate/})).not.toBeInTheDocument();}finally{vi.unstubAllGlobals();}
});
