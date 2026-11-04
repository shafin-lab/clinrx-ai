import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor,cleanup} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import record from './fixtures/gastrointestinal-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import {GIEntry,giPendingKey} from '../src/gastrointestinal/GIEntry';
const c=fixture.catalog as unknown as Catalog;
beforeEach(()=>{localStorage.clear();HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};});afterEach(()=>cleanup());
it('records one original finding, withholds confirmation after response loss and looks up the exact pending request after remount',async()=>{
 let received:unknown;const transport={importGastrointestinal:async(_repo:string,f:unknown)=>{received=f;throw Error('Response lost');},lookupGastrointestinal:async(_repo:string,f:unknown)=>({status:'committed_match' as const,evidence:{fact:f} as Evidence})};
 const props={catalog:c,current:true,transport,onRefresh:async()=>{},onClose:()=>{},onGuardChange:()=>{}};const view=render(<GIEntry {...props}/>);
 fireEvent.change(screen.getByLabelText('Finding / report'),{target:{value:'Soft abdomen; tenderness reduced.'}});fireEvent.change(screen.getByLabelText('Observation / procedure time'),{target:{value:'2026-10-08T09:15'}});fireEvent.change(screen.getByLabelText('Recorded by'),{target:{value:'Demo clinician'}});
 fireEvent.click(screen.getByRole('button',{name:'Save GI finding'}));await screen.findByText(/Response lost/);expect(screen.queryByText('Source record saved.')).toBeNull();expect(localStorage.getItem(giPendingKey(c.repository))).toBeTruthy();view.unmount();
 render(<GIEntry {...props}/>);expect(screen.getByRole('button',{name:'Check pending save'})).toBeEnabled();fireEvent.click(screen.getByRole('button',{name:'Check pending save'}));await screen.findByText('Source record saved.');expect(localStorage.getItem(giPendingKey(c.repository))).toBeNull();expect((received as any).narrative).toBe('Soft abdomen; tenderness reduced.');
});
it('requires a correction reason and keeps predecessor identity intact',async()=>{
 let count=0;const transport={importGastrointestinal:async()=>{count++;return {} as Evidence;},lookupGastrointestinal:async()=>({status:'absent' as const})};
 render(<GIEntry catalog={c} current prior={{fact:record} as unknown as Evidence} transport={transport} onRefresh={async()=>{}} onClose={()=>{}}/>);fireEvent.click(screen.getByRole('button',{name:'Save GI finding'}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent(/correction reason/i));expect(count).toBe(0);
});

it('retains date-time input events when another field rerenders the form',()=>{
 const transport={importGastrointestinal:async()=>({} as Evidence),lookupGastrointestinal:async()=>({status:'absent' as const})};render(<GIEntry catalog={c} current transport={transport} onRefresh={async()=>{}} onClose={()=>{}}/>);
 const at=screen.getByLabelText('Observation / procedure time');fireEvent.input(at,{target:{value:'2026-10-08T09:30'}});fireEvent.change(screen.getByLabelText('Recorded by'),{target:{value:'Demo clinician'}});expect(at).toHaveValue('2026-10-08T09:30');
});
