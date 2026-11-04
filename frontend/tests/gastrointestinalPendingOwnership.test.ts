import {afterEach,beforeEach,expect,it} from 'vitest';
import {reservePending,releasePending} from '../src/gastrointestinal/pendingJournal';
beforeEach(()=>{localStorage.clear();let tail=Promise.resolve();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,callback:()=>unknown)=>{const next=tail.then(callback);tail=next.then(()=>{},()=>{});return next;}}});});afterEach(()=>localStorage.clear());
it.each(['source','review'])('retains exact %s pending ownership across overlapping callers and late completion',async kind=>{
 const key='clinrx.m11.'+kind+'/same-scope',a={id:'A',text:'First exact request'},b={id:'B',text:'Second exact request'};await reservePending(key,a);
 await expect(reservePending(key,b)).rejects.toThrow(/another pending/i);expect(JSON.parse(localStorage.getItem(key)!)).toEqual(a);
 await releasePending(key,a);await reservePending(key,b);await releasePending(key,a);expect(JSON.parse(localStorage.getItem(key)!)).toEqual(b);
 // A late completion cannot erase B; a fresh tab can still recover its exact payload.
 expect(JSON.parse(localStorage.getItem(key)!)).toEqual({id:'B',text:'Second exact request'});
});
