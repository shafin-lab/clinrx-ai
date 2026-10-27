import {expect,it} from 'vitest';
import fixture from './fixtures/rf2-api.json';
import respiratory from './fixtures/respiratory-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import type {RespiratoryRecord} from '../src/respiratory/respiratoryTypes';
import {respiratorySupportTimeline,supportAtTime} from '../src/respiratory/supportModel';
import {resolveRespiratoryEvaluation} from '../src/respiratory/respiratoryEvaluation';
import {calculateRespiratoryPhysiology} from '../src/respiratory/physiology';

const point=(value:string)=>({status:'known' as const,precision:'instant' as const,value,lower:null,upper:null,uncertainty:null});
function source(c:Catalog,id:string,at:string,type:string|null='hfnc',end:string|null=null):Evidence {
 const fact=structuredClone(respiratory) as RespiratoryRecord;fact.id=id;fact.category='support';fact.title=id;fact.context.sample_type='noninvasive';fact.context.oxygen_device=type;fact.context.ventilator_mode=null;
 fact.context.support_episode=type?{type:type as any,until:end?point(end):null}:null;
 fact.times.occurred=point(at);fact.times.available=point(at);fact.times.reported=point(at);fact.times.collected={...point(at),status:'not_recorded',precision:'unknown',value:null};fact.measurements=[{concept:'fio2',label:'FiO₂',result:{kind:'numeric',raw_value:'40',comparator:'=',unit:{namespace:'UCUM',code:'%',version:null,raw_display:'%'}},role:'set',quality:'usable',method:null}];
 return {repository:c.repository,fact,canonical_fact:JSON.stringify(fact),digest:'a'.repeat(64),ingestion:{repository_id:c.repository,ingestion_sequence:1},cutoff:c.cutoff.fact_watermark,terminal_reference:{kind:fact.kind,id,version:fact.revision},superseded:false,metadata:null};
}
function setup(){const c=structuredClone(fixture.catalog) as unknown as Catalog;c.respiratory_records=[];return c;}
it('keeps progression and setting changes once in source-time order, including earlier support',()=>{
 const c=setup();c.respiratory_records=[source(c,'vent','2026-10-08T09:40:00Z','invasive'),source(c,'room','2026-10-08T07:00:00Z','room_air'),source(c,'nasal','2026-10-08T08:00:00Z','nasal_cannula'),source(c,'hfnc','2026-10-08T09:00:00Z'),source(c,'hfnc-change','2026-10-08T09:20:00Z')];
 const before=JSON.stringify(c);expect(respiratorySupportTimeline(c).map(e=>e.fact.id)).toEqual(['room','nasal','hfnc','hfnc-change','vent']);expect(supportAtTime(c,'2026-10-08T09:05:00Z').source?.fact.id).toBe('hfnc');expect(supportAtTime(c,'2026-10-08T09:25:00Z').source?.fact.id).toBe('hfnc-change');expect(supportAtTime(c,'2026-10-08T09:40:00Z').source?.fact.id).toBe('vent');expect(JSON.stringify(c)).toBe(before);
});
it.each(['withdrawn','point','same-instant','overlap','unknown-time','conflict','expired'] as const)('withholds a current episode across %s evidence rather than reviving older support',cause=>{
 const c=setup(),old=source(c,'old','2026-10-08T08:00:00Z'),next=source(c,'new','2026-10-08T09:00:00Z','invasive');c.respiratory_records=[old,next];
 if(cause==='withdrawn'){next.fact.record_status='withdrawn';next.fact.report_status='withdrawn';}
 if(cause==='point')next.fact.context={...(next.fact as RespiratoryRecord).context,support_episode:null};
 if(cause==='same-instant')c.respiratory_records.push(source(c,'duplicate-time','2026-10-08T09:00:00Z','nasal_cannula'));
 if(cause==='overlap')(old.fact as RespiratoryRecord).context.support_episode!.until=point('2026-10-08T09:50:00Z');
 if(cause==='unknown-time')(next.fact as RespiratoryRecord).times.occurred={status:'unknown',precision:'unknown',value:null,lower:null,upper:null,uncertainty:null};
 if(cause==='conflict')next.fact.conflict='unresolved';
 if(cause==='expired')(next.fact as RespiratoryRecord).context.support_episode!.until=point('2026-10-08T09:10:00Z');
 expect(supportAtTime(c,'2026-10-08T09:15:00Z').status).not.toBe('matched');expect(supportAtTime(c,'2026-10-08T09:15:00Z').source).toBeUndefined();
});
it('keeps a point observation visible but does not extend it into a later gas',()=>{
 const c=setup();c.respiratory_records=[source(c,'point','2026-10-08T09:00:00Z',null)];expect(respiratorySupportTimeline(c)).toHaveLength(1);expect(supportAtTime(c,'2026-10-08T09:05:00Z').status).not.toBe('matched');expect(supportAtTime(c,'2026-10-08T09:00:00Z').source?.fact.id).toBe('point');
});
it('does not promote an old-cutoff source envelope into current support',()=>{const c=setup(),e=source(c,'stale','2026-10-08T09:00:00Z');e.cutoff--;c.respiratory_records=[e];expect(supportAtTime(c,'2026-10-08T09:05:00Z').status).toBe('unconfirmed');});
it('excludes a future-available correction and rejects foreign scope without mutating the source',()=>{
 const c=setup(),future=source(c,'future','2026-10-08T09:00:00Z');(future.fact as RespiratoryRecord).times.available=point('2026-10-08T10:01:00Z');c.respiratory_records=[future];expect(respiratorySupportTimeline(c)).toEqual([]);expect(supportAtTime(c,'2026-10-08T09:05:00Z').source).toBeUndefined();
 c.respiratory_records=[source(c,'foreign','2026-10-08T09:00:00Z')];c.respiratory_records[0].fact.binding.target.patient_id='other';expect(respiratorySupportTimeline(c)).toEqual([]);
});
it('uses an explicit episode automatically for a gas without creating a copied FiO2 measurement',()=>{
 const c=setup(),support=source(c,'hfnc','2026-10-08T08:50:00Z');const sample=source(c,'gas','2026-10-08T09:00:00Z');const f=sample.fact as RespiratoryRecord;f.category='blood_gas';f.context.sample_type='arterial';delete f.context.support_episode;f.context.settings_confirmed_at_sample=null;f.times.collected=point('2026-10-08T09:00:00Z');f.measurements=[];f.linked_sources=[];c.respiratory_records=[support,sample];const before=JSON.stringify(c),result=resolveRespiratoryEvaluation(f,c);expect(result.inputs.get('fio2')?.source.fact.id).toBe('hfnc');expect(JSON.stringify(c)).toBe(before);
});
it('calculates a sample P/F from an unambiguous documented episode without another confirmation click',()=>{
 const c=setup(),s=source(c,'hfnc','2026-10-08T08:50:00Z'),e=source(c,'gas','2026-10-08T09:00:00Z'),f=e.fact as RespiratoryRecord;
 f.category='blood_gas';delete f.context.support_episode;f.context.sample_type='arterial';f.context.settings_confirmed_at_sample=null;f.times.collected=point('2026-10-08T09:00:00Z');f.linked_sources=[];f.measurements=[{concept:'pao2',label:'PaO₂',role:'measured',quality:'usable',method:null,result:{kind:'numeric',raw_value:'84',comparator:'=',unit:{namespace:'UCUM',code:'mmHg',version:null,raw_display:'mmHg'}}}];c.respiratory_records=[s,e];
 expect(calculateRespiratoryPhysiology(f,resolveRespiratoryEvaluation(f,c)).find(r=>r.id==='pf_ratio')?.value).toBe('210');
});
it('keeps intubation in the timeline and does not carry HFNC through an intervening airway procedure',()=>{
 const c=setup(),h=source(c,'hfnc','2026-10-08T08:50:00Z'),e=source(c,'intubation','2026-10-08T09:10:00Z'),f=e.fact as RespiratoryRecord;f.category='procedure';delete f.context.support_episode;f.measurements=[{concept:'procedure_status',label:'Status',role:'reported',quality:'unknown',method:null,result:{kind:'narrative',raw_value:'Performed'}}];c.respiratory_records=[h,e];expect(respiratorySupportTimeline(c).map(x=>x.fact.id)).toEqual(['hfnc','intubation']);expect(supportAtTime(c,'2026-10-08T09:15:00Z').status).toBe('unconfirmed');
});
it('does not treat a planned extubation as a performed support transition',()=>{const c=setup(),h=source(c,'hfnc','2026-10-08T08:50:00Z'),e=source(c,'extubation','2026-10-08T09:10:00Z'),f=e.fact as RespiratoryRecord;f.category='liberation';delete f.context.support_episode;f.measurements=[{concept:'extubation_status',label:'Extubation status',role:'reported',quality:'unknown',method:null,result:{kind:'narrative',raw_value:'Planned'}}];c.respiratory_records=[h,e];expect(supportAtTime(c,'2026-10-08T09:15:00Z').source?.fact.id).toBe('hfnc');});
it('withholds continuing support across a performed airway event with unknown time',()=>{const c=setup(),h=source(c,'hfnc','2026-10-08T08:50:00Z'),e=source(c,'intubation','2026-10-08T09:10:00Z'),f=e.fact as RespiratoryRecord;f.category='procedure';delete f.context.support_episode;f.times.occurred={status:'unknown',precision:'unknown',value:null,lower:null,upper:null,uncertainty:null};f.measurements=[{concept:'procedure_status',label:'Status',role:'reported',quality:'unknown',method:null,result:{kind:'narrative',raw_value:'Performed'}}];c.respiratory_records=[h,e];expect(supportAtTime(c,'2026-10-08T09:15:00Z').status).toBe('unconfirmed');});
