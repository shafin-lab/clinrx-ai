import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it} from 'vitest';
import {CompleteNcdcLibrary} from '../src/infectionLibrary/CompleteNcdcLibrary';
import complete from '../src/infectionLibrary/data/ncdc-complete-guidance.json';

function mount(){render(<CompleteNcdcLibrary patient="synthetic-p1" encounter="synthetic-e1" data={complete}/>);}
function group(id:string){fireEvent.change(screen.getByLabelText('Clinical group'),{target:{value:id}});}
function search(query:string){fireEvent.change(screen.getByLabelText('Find an infection'),{target:{value:query}});}
function results(){return screen.getByRole('complementary',{name:'Browse infections'});}

it('places global search above the clinical-group selector',()=>{
 mount();
 expect(screen.getByLabelText('Find an infection').compareDocumentPosition(screen.getByLabelText('Clinical group'))&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it('finds bronchitis from a different selected group and identifies the result group',()=>{
 mount();group('group-1');search('bronchitis');
 const result=within(results()).getByRole('button',{name:/^Bronchitis/});
 expect(result).toHaveTextContent('Respiratory Tract Infections');
 expect(screen.getByRole('status')).toHaveTextContent(/across all clinical groups/);
 expect(screen.getByRole('heading',{name:'Bronchitis'})).toBeInTheDocument();
 expect(screen.getByRole('region',{name:'First-line treatment'})).toHaveTextContent('No antibiotics');
});

it('returns matching infections from multiple groups without duplicate results',()=>{
 mount();group('group-1');search('sepsis');
 const buttons=within(results()).getAllByRole('button');
 expect(buttons.some(button=>/Puerperal sepsis/.test(button.textContent??''))).toBe(true);
 expect(buttons.some(button=>/Infective Endocarditis/.test(button.textContent??''))).toBe(true);
 expect(new Set(buttons.map(button=>button.textContent)).size).toBe(buttons.length);
});

it('places an exact infection-name match before a substring from another clinical group',()=>{
 mount();group('group-1');search('cystitis');
 const buttons=within(results()).getAllByRole('button');
 expect(buttons[0]).toHaveTextContent(/^Cystitis/);
 expect(screen.getByRole('heading',{name:'Cystitis'})).toBeInTheDocument();
});

it('searches names and clinical situations case-insensitively and opens a result in its own group',()=>{
 mount();group('group-1');search('  PYeLoNePHRITIS  ');
 const result=within(results()).getByRole('button',{name:/^Pyelonephritis/});fireEvent.click(result);
 expect(screen.getByLabelText('Clinical group')).toHaveValue('group-5');
 expect(screen.getByRole('heading',{name:'Pyelonephritis'})).toBeInTheDocument();
 search('');expect(screen.getByRole('status')).toHaveTextContent('2 infections in this group');
});

it('returns to group browsing when a group is selected and clears stale supplementary context',()=>{
 mount();group('group-1');search('endocarditis');
 const situation=screen.getByLabelText('Clinical situation');
 fireEvent.change(situation,{target:{value:'ncdc-1-1-source-row-3'}});
 expect(screen.getByText('Teicoplanin: additional dosing information')).toBeInTheDocument();
 search('bronchitis');expect(screen.queryByText('Teicoplanin: additional dosing information')).not.toBeInTheDocument();
 group('group-5');expect(screen.getByLabelText('Find an infection')).toHaveValue('');
 expect(within(results()).getAllByRole('button')).toHaveLength(2);
 expect(screen.getByRole('status')).toHaveTextContent('2 infections in this group');
 search('no matching illness');expect(screen.queryByRole('region',{name:'First-line treatment'})).not.toBeInTheDocument();
 expect(screen.queryByText(/^Further evidence & alternatives/)).not.toBeInTheDocument();
});
