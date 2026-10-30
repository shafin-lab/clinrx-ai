import {fireEvent,render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {AntibioticReferences} from '../src/antibiotics/AntibioticReferences';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
it('puts the approved antibiotic profiles alongside retained NCDC infections without patient requests',async()=>{
 const request=vi.fn();vi.stubGlobal('fetch',request);
 try{
 render(<AntibioticReferences requested={requested} loading={false} onKidney={()=>{}}/>);
 expect(screen.getByRole('heading',{name:'Infections & treatment'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Antibiotics'}));
 expect(await screen.findByRole('heading',{name:'Meropenem',level:2})).toBeVisible();
 fireEvent.click(screen.getByRole('tab',{name:'Dosing'}));
 expect(screen.getByRole('table',{name:'Adult short-infusion dosing'})).toBeVisible();
 expect(request).not.toHaveBeenCalled();
 }finally{vi.unstubAllGlobals();}
});
it('retains the infection search when switching between reference collections',async()=>{
 render(<AntibioticReferences requested={requested} loading={false} onKidney={()=>{}}/>);
 fireEvent.change(screen.getByRole('searchbox',{name:'Find an infection'}),{target:{value:'bronchitis'}});
 expect(screen.getByRole('heading',{name:'Bronchitis'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Antibiotics'}));
 await screen.findByRole('heading',{name:'Meropenem',level:2});
 fireEvent.click(screen.getByRole('button',{name:'Infections & treatment'}));
 expect(screen.getByRole('searchbox',{name:'Find an infection'})).toHaveValue('bronchitis');
 expect(screen.getByRole('heading',{name:'Bronchitis'})).toBeVisible();
});
