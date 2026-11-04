import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,waitFor,cleanup,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import record from './fixtures/gastrointestinal-record.json';
import type {Catalog} from '../src/api/rf2Client';
import {gastrointestinalModel} from '../src/gastrointestinal/model';
import {GIReview} from '../src/gastrointestinal/GIReview';
const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const catalog=()=>{const c=structuredClone(fixture.catalog) as unknown as Catalog;c.gastrointestinal_records=[{repository:c.repository,fact:structuredClone(record),canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:'gastrointestinal_record',id:record.id,version:'1'},superseded:false,metadata:null}];return c;};
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,callback:()=>unknown)=>callback()}});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function fill(){fireEvent.change(screen.getByLabelText('Reviewer'),{target:{value:'GI clinician'}});fireEvent.change(screen.getByLabelText('Assessment'),{target:{value:'Symptoms reviewed against original sources'}});fireEvent.change(screen.getByLabelText('Next review'),{target:{value:'At 16:00'}});}
it('saves one review, restores after remount and retains historical support after correction',async()=>{
 const c=catalog();const props={catalog:c,requested,model:gastrointestinalModel(c,requested),current:true};const view=render(<GIReview {...props}/>);fill();fireEvent.click(screen.getByRole('button',{name:'Save GI/liver review'}));await screen.findByText('Matches current evidence');view.unmount();
 const later=catalog();later.gastrointestinal_records![0].fact.revision='corrected';later.gastrointestinal_records![0].digest='b'.repeat(64);
 const next=render(<GIReview {...props}/>);expect(await screen.findByText('Matches current evidence')).toBeVisible();next.rerender(<GIReview {...props} catalog={later} model={gastrointestinalModel(later,requested)}/>);expect(await screen.findByText('Historical evidence review')).toBeVisible();expect(screen.getByText('Symptoms reviewed against original sources')).toBeVisible();
});
it('rejects a queued save when rendered relevant evidence changes before the lock is acquired',async()=>{
 let release:()=>void=()=>{};let queued=false;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(name:string,callback:()=>unknown)=>{if(name.startsWith('clinrx-local-review:')){queued=true;await new Promise<void>(r=>release=r);}return callback();}}});
 const c=catalog(),props={catalog:c,requested,model:gastrointestinalModel(c,requested),current:true};const view=render(<GIReview {...props}/>);fill();fireEvent.click(screen.getByRole('button',{name:'Save GI/liver review'}));await waitFor(()=>expect(queued).toBe(true));const later=catalog();later.gastrointestinal_records![0].fact.revision='2';later.gastrointestinal_records![0].digest='c'.repeat(64);view.rerender(<GIReview {...props} catalog={later} model={gastrointestinalModel(later,requested)}/>);await act(async()=>release());await screen.findByText(/Evidence changed before/);expect(screen.queryByText('Matches current evidence')).toBeNull();
});
it('withholds confirmation when browser storage fails',async()=>{
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});const c=catalog();render(<GIReview catalog={c} requested={requested} model={gastrointestinalModel(c,requested)} current/>);fill();fireEvent.click(screen.getByRole('button',{name:'Save GI/liver review'}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent(/storage/i));expect(screen.queryByText('Matches current evidence')).toBeNull();
});

it('recovers a written review after confirmation loss without appending a second review',async()=>{
 const c=catalog();let written=false,hideOnce=true;const originalSet=Storage.prototype.setItem,originalGet=Storage.prototype.getItem;
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(this:Storage,k:string,v:string){originalSet.call(this,k,v);if(k.startsWith('clinrx.local-review/v1/M11/'))written=true;});
 vi.spyOn(Storage.prototype,'getItem').mockImplementation(function(this:Storage,k:string){if(written&&hideOnce&&k.startsWith('clinrx.local-review/v1/M11/')){hideOnce=false;return null;}return originalGet.call(this,k);});
 render(<GIReview catalog={c} requested={requested} model={gastrointestinalModel(c,requested)} current/>);fill();fireEvent.click(screen.getByRole('button',{name:'Save GI/liver review'}));await screen.findByRole('button',{name:'Check pending review'});fireEvent.click(screen.getByRole('button',{name:'Check pending review'}));await screen.findByText('Matches current evidence');expect(Object.keys(localStorage).filter(k=>k.startsWith('clinrx.local-review/v1/M11/'))).toHaveLength(1);
});

it('preserves unreadable pending review bytes and blocks a replacement save',async()=>{
 const c=catalog(),k='clinrx.m11.review-pending/v1/'+[requested.patient,requested.encounter,c.repository].map(encodeURIComponent).join('/');localStorage.setItem(k,'{broken');
 render(<GIReview catalog={c} requested={requested} model={gastrointestinalModel(c,requested)} current/>);expect(screen.getByRole('alert')).toHaveTextContent(/unreadable/);expect(screen.getByRole('button',{name:'Save GI/liver review'})).toBeDisabled();expect(localStorage.getItem(k)).toBe('{broken');
});

it('does not claim a current match when saved pins are substituted without changing the signature',async()=>{
 const c=catalog(),props={catalog:c,requested,model:gastrointestinalModel(c,requested),current:true};const view=render(<GIReview {...props}/>);fill();fireEvent.click(screen.getByRole('button',{name:'Save GI/liver review'}));await screen.findByText('Matches current evidence');view.unmount();const k=Object.keys(localStorage).find(k=>k.startsWith('clinrx.local-review/v1/M11/'))!;const value=JSON.parse(localStorage.getItem(k)!);value.snapshot.pins[0].version='substituted';value.snapshot.pins[0].digest='d'.repeat(64);localStorage.setItem(k,JSON.stringify(value));render(<GIReview {...props}/>);expect(await screen.findByText('Historical evidence review')).toBeVisible();expect(screen.queryByText('Matches current evidence')).toBeNull();expect(localStorage.getItem(k)).toContain('substituted');
});

it('a second review editor cannot overwrite the first queued review journal',async()=>{
 let release:()=>void=()=>{},queued=false;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(name:string,callback:()=>unknown)=>{if(name.startsWith('clinrx-local-review:')){queued=true;await new Promise<void>(r=>release=r);}return callback();}}});
 const c=catalog(),props={catalog:c,requested,model:gastrointestinalModel(c,requested),current:true};const a=render(<GIReview {...props}/>),b=render(<GIReview {...props}/>);
 function complete(container:HTMLElement,label:string){const q=within(container);fireEvent.change(q.getByLabelText('Reviewer'),{target:{value:label}});fireEvent.change(q.getByLabelText('Assessment'),{target:{value:label+' assessment'}});fireEvent.change(q.getByLabelText('Next review'),{target:{value:'Next report'}});fireEvent.click(q.getByRole('button',{name:'Save GI/liver review'}));}
 complete(a.container,'Reviewer A');await waitFor(()=>expect(queued).toBe(true));const key=Object.keys(localStorage).find(k=>k.startsWith('clinrx.m11.review-pending/'))!,raw=localStorage.getItem(key);complete(b.container,'Reviewer B');await waitFor(()=>expect(within(b.container).getByRole('alert')).toHaveTextContent(/another pending/i));expect(localStorage.getItem(key)).toBe(raw);await act(async()=>release());await within(a.container).findByText('Matches current evidence');expect(localStorage.getItem(key)).toBeNull();
});
