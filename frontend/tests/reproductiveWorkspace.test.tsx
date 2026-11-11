import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import fixture from './fixtures/rf2-api.json';
import {ReproductiveWorkspace} from '../src/reproductive/ReproductiveWorkspace';
import type {Catalog,Evidence} from '../src/api/rf2Client';

const requested={patient:'synthetic-p1',encounter:'synthetic-e1',start:'2026-10-08T08:00:00Z',end:'2026-10-08T10:00:00Z'};
const at='2026-10-08T08:45:00Z';
const time={status:'known',precision:'instant',value:at};
function catalog(obstetric=true):Catalog {
 const c=structuredClone(fixture.catalog) as unknown as Catalog;
 const make=(id:string,category:string,title:string,narrative:string,pregnancy:object|null=null):Evidence=>({
  ...fixture.weight,repository:c.repository,cutoff:c.cutoff.fact_watermark,
  fact:{...fixture.weight.fact,kind:'reproductive_record',id,revision:'1',category,title,narrative,pregnancy,
   record_status:'recorded',report_status:'final',times:{occurred:time,reported:time,available:time}},
  terminal_reference:{kind:'reproductive_record',id,version:'1'},metadata:null,
 });
 c.reproductive_records=[
  make('phase','pregnancy_status','Recorded status','Fictional context',obstetric?
   {phase:'antepartum',gestational_weeks:32,gestational_days:4,fetus_count:1,dating_basis:'First-trimester ultrasound'}:{phase:'not_pregnant'}),
  make('assessment',obstetric?'fetal_assessment':'gynecology',obstetric?'Fetal assessment':'Heavy menstrual bleeding',
   obstetric?'Fetal cardiac activity documented.':'Bleeding history documented.'),
 ];
 return c;
}
function show(c:Catalog){return render(<ReproductiveWorkspace catalog={c} requested={requested} current loading={false} onRefresh={async()=>{}}/>);}
beforeEach(()=>localStorage.clear());
afterEach(()=>vi.restoreAllMocks());

it.each([true,false])('restores a saved source-bound review after remount (obstetric=%s)',async obstetric=>{
 const c=catalog(obstetric);
 const first=show(c);
 const overview=within(screen.getByRole('tabpanel',{name:'Overview'}));
 expect(overview.getByText(obstetric?'Fetal cardiac activity documented.':'Bleeding history documented.')).toBeVisible();
 expect(screen.getByText(obstetric?/32 weeks 4 days/:/Not pregnant/)).toBeVisible();
 fireEvent.click(screen.getByRole('tab',{name:'Review & plan'}));
 fireEvent.change(screen.getByLabelText('Reviewer'),{target:{value:'Fictional reviewer'}});
 fireEvent.change(screen.getByLabelText('Assessment'),{target:{value:'Fictional review assessment'}});
 fireEvent.change(screen.getByLabelText('Next review'),{target:{value:'11:00 UTC'}});
 fireEvent.click(screen.getByRole('button',{name:'Save review'}));
 await screen.findByText('Review saved');
 first.unmount();
 show(c);
 expect(await within(screen.getByRole('region',{name:'M12 review status'})).findByText('Fictional review assessment')).toBeVisible();
 fireEvent.click(screen.getByRole('tab',{name:'Review & plan'}));
 expect(screen.getByText('Matches current evidence')).toBeVisible();
});

it('keeps saved notes historical when an exact source revision changes',async()=>{
 const c=catalog();
 const first=show(c);
 fireEvent.click(screen.getByRole('tab',{name:'Review & plan'}));
 for(const [name,value] of [['Reviewer','Fictional reviewer'],['Assessment','Original evidence assessment'],['Next review','11:00 UTC']]){
  fireEvent.change(screen.getByLabelText(name),{target:{value}});
 }
 fireEvent.click(screen.getByRole('button',{name:'Save review'}));
 await screen.findByText('Review saved');
 first.unmount();
 c.reproductive_records![1].fact.revision='2';
 show(c);
 await waitFor(()=>expect(screen.getByText('Evidence changed · Review needed')).toBeVisible());
 fireEvent.click(screen.getByRole('tab',{name:'Review & plan'}));
 expect(screen.getByText('Historical evidence review')).toBeVisible();
 expect(screen.getByText('Original evidence assessment')).toBeVisible();
});

it('blocks a queued save if the source changes before the review lock is acquired',async()=>{
 let release:(()=>void)|undefined;
 vi.spyOn(navigator.locks,'request').mockImplementation(((_name:string,callback:()=>unknown)=>new Promise<unknown>((resolve,reject)=>{
  release=()=>{try{resolve(callback());}catch(e){reject(e);}};
 })) as typeof navigator.locks.request);
 const c=catalog(),first=show(c);
 fireEvent.click(screen.getByRole('tab',{name:'Review & plan'}));
 for(const [name,value] of [['Reviewer','Queued reviewer'],['Assessment','Queued assessment'],['Next review','11:00 UTC']]){
  fireEvent.change(screen.getByLabelText(name),{target:{value}});
 }
 fireEvent.click(screen.getByRole('button',{name:'Save review'}));
 await waitFor(()=>expect(release).toBeTypeOf('function'));
 const amended=structuredClone(c);amended.reproductive_records![1].fact.revision='2';
 first.rerender(<ReproductiveWorkspace catalog={amended} requested={requested} current loading={false} onRefresh={async()=>{}}/>);
 await act(async()=>release?.());
 expect(await screen.findByText(/Evidence changed before the review could be saved/)).toBeVisible();
 expect(localStorage.length).toBe(0);
});
