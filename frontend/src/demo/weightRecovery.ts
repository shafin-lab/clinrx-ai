import {chartDefaults,pin,type Chart,type Draft,type Evidence,type Pin,stable} from '../api/rf2Client';
import {parseRF2JSON} from '../api/rf2JSON';
import {validateTransportSchema} from '../api/decoding';
import schemas from '../api/rf2Schemas.json';

export interface WeightScope {patient:string;encounter:string;repository:string}
export interface WeightForm {amount:string;unit:'kg'|'g';point:string;acquisition:'measured'|'reported'|'unknown';method:string;context:string;uncertainty:string;actor:string;reason:string}
export interface WeightRecovery {version:1;scope:WeightScope;form:WeightForm;predecessor:Pin|null;originalChart:Chart|null;pending:Draft|null}
export const weightStorageKey=(s:WeightScope)=>'clinrx.synthetic.weight-entry/v1/'+JSON.stringify([s.patient,s.encounter,s.repository]);
export const sameWeightScope=(a:WeightScope,b:WeightScope)=>stable(a)===stable(b);
export function weightSession(scope:WeightScope,source?:Evidence):WeightRecovery {
 if(scope.patient!=='synthetic-p1'||scope.encounter!=='synthetic-e1')throw Error('Only the synthetic encounter supports weight entry.');
 if(source&&(source.repository!==scope.repository||source.fact.binding.target.patient_id!==scope.patient||source.fact.binding.target.encounter_id!==scope.encounter||source.fact.kind!=='circulatory_event'||source.metadata?.chart?.category!=='weight'||source.superseded||source.fact.record_status!=='recorded'))throw Error('This weight must be corrected through its original owner.');
 const c=source?.metadata?.chart;
 return {version:1,scope,form:{amount:c?.amount??'',unit:c?.unit==='g'?'g':'kg',point:c?.point??'',acquisition:c?.acquisition??'unknown',method:c?.method??'',context:c?.source_context??'',uncertainty:c?.uncertainty??'',actor:'',reason:''},predecessor:source?pin(source):null,originalChart:c?structuredClone(c):null,pending:null};
}
export function weightDraft(s:WeightRecovery):Draft {
 const f=s.form;
 const required=[['Weight',f.amount],['Recorded by',f.actor],['Source context',f.context],['Uncertainty or limitations',f.uncertainty],[s.predecessor?'Reason for correction':'Reason for new entry',f.reason]].filter(([,v])=>!v.trim()).map(([label])=>label);
 if(required.length)throw Error('Complete: '+required.join(', ')+'.');
 if(!/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(f.amount))throw Error('Enter weight as a nonnegative decimal, for example 70.0000.');
 if(f.point&&(!/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/.test(f.point)||!Number.isFinite(Date.parse(f.point))))throw Error('Enter a recorded date and time with Z or an explicit offset, or leave it blank for unknown time.');
 const chart=weightChart(s);
 const d:Draft={repository:s.scope.repository,id:s.predecessor?.reference.id??crypto.randomUUID(),revision:crypto.randomUUID(),actor:f.actor,recorded_at:new Date().toISOString(),chart,note:null,predecessor:s.predecessor,reason:s.predecessor?f.reason:null};
 validateTransportSchema(d,schemas.roots.RF2Draft,schemas.definitions);
 return d;
}
function weightChart(s:WeightRecovery):Chart {
 const f=s.form;
 return {...chartDefaults,...(s.originalChart??{}),category:'weight',amount:f.amount,unit:f.unit,missing_reason:null,point:f.point||null,start:null,end:null,acquisition:f.acquisition,method:f.method||null,source_context:f.context,uncertainty:f.uncertainty,...(!s.predecessor?{source_record:null,source_version:null,new_collection_reason:f.reason,purpose:null}:{})};
}
/** Storage is untrusted. Never promote a recovered request straight to save. */
export function decodeWeightRecovery(raw:string,scope:WeightScope):WeightRecovery {
 if(raw.length>32768)throw Error('Recovery record exceeds the local limit.');
 const v=parseRF2JSON(raw) as WeightRecovery;
 const keys=(x:object,names:string[])=>x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join()===names.sort().join();
 if(!keys(v,['version','scope','form','predecessor','originalChart','pending'])||v.version!==1||!keys(v.scope,['patient','encounter','repository'])||!sameWeightScope(v.scope,scope)||scope.patient!=='synthetic-p1'||scope.encounter!=='synthetic-e1')throw Error('Recovery scope is invalid.');
 const names=['amount','unit','point','acquisition','method','context','uncertainty','actor','reason'];
 if(!keys(v.form,names)||names.some(k=>typeof v.form[k as keyof WeightForm]!=='string'||v.form[k as keyof WeightForm].length>512)||!['kg','g'].includes(v.form.unit)||!['measured','reported','unknown'].includes(v.form.acquisition))throw Error('Recovery form is invalid.');
 if((v.predecessor===null)!==(v.originalChart===null))throw Error('Recovery correction owner is incomplete.');
 if(v.predecessor){validateTransportSchema(v.predecessor,schemas.definitions.Pin,schemas.definitions);validateTransportSchema(v.originalChart,schemas.definitions.Chart,schemas.definitions);if(v.predecessor.repository!==scope.repository||v.predecessor.reference.kind!=='circulatory_event'||v.originalChart?.category!=='weight')throw Error('Recovery correction owner differs.');}
 if(v.pending){
  validateTransportSchema(v.pending,schemas.roots.RF2Draft,schemas.definitions);
  const d=v.pending;
  if(d.repository!==scope.repository||d.note!==null||!d.chart||stable(d.chart)!==stable(weightChart(v))||stable(d.predecessor)!==stable(v.predecessor)||v.predecessor&&d.id!==v.predecessor.reference.id||d.actor!==v.form.actor||d.reason!==(v.predecessor?v.form.reason:null))throw Error('Recovered request differs from its recorded form or owner.');
 }
 return v;
}
