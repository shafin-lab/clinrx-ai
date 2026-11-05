import {key,pin,type Evidence} from '../api/rf2Client';
import {type GILab} from './model';
import {respiratoryDisplayTime} from '../respiratory/RespiratorySupportTimeline';
/** Only show component IDs in the main table when a report repeats a mapped test. */
export function giRepeatedComponent(row:GILab,rows:GILab[]){return rows.filter(r=>r.concept===row.concept&&key(pin(r.evidence))===key(pin(row.evidence))).length>1?`Component ${String(row.component.source_component_id)}`:null;}
export function GIResultQuality({rows,onInspect,disabled=false}:{rows:GILab[];disabled?:boolean;onInspect:(e:Evidence,trigger:HTMLButtonElement)=>void}){
 const reports=new Map<string,{evidence:Evidence;components:Map<string,GILab>;time:string|null}>();
 for(const r of rows){if(r.component.source_critical_flag!==undefined&&r.component.source_critical_flag!=='unknown')continue;const id=key(pin(r.evidence)),group=reports.get(id)??{evidence:r.evidence,components:new Map<string,GILab>(),time:r.time};group.components.set(String(r.component.source_component_id),r);reports.set(id,group);}
 if(!reports.size)return null;
 return <details className="gi-quality-summary"><summary>Critical-flag status not supplied · {reports.size} report{reports.size===1?'':'s'}</summary><p>A missing source flag does not establish a normal result.</p>{[...reports].map(([id,r])=><div key={id}><small>{r.time?respiratoryDisplayTime(r.time):'Collection time not established'} · {r.evidence.fact.id} · {r.evidence.fact.revision}</small>{[...r.components].map(([component,row])=><p key={component}>{row.label} · {row.text} · Component {component}</p>)}<button type="button" className="gi-link" disabled={disabled} onClick={e=>onInspect(r.evidence,e.currentTarget)}>Source & history</button></div>)}</details>;
}
