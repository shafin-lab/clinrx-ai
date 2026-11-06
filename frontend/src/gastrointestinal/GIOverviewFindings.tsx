import type {ReactNode} from 'react';
import type {Evidence} from '../api/rf2Client';
import {compareRespiratoryInstants} from '../respiratory/exactTime';
import {giTime} from './model';
/** A later same-title observation changes presentation, never the original source or its status. */
export function GIOverviewFindings({records,renderRecord}:{records:Evidence[];renderRecord:(e:Evidence)=>ReactNode}){
 const groups=new Map<string,Evidence[]>();for(const e of records){const k=JSON.stringify([e.fact.category,e.fact.title]);groups.set(k,[...(groups.get(k)??[]),e]);}
 return <>{[...groups].map(([id,rows])=>{let latest:string|null=null;for(const e of rows){const time=giTime(e);if(time&&compareRespiratoryInstants(time,time)===0&&(!latest||(compareRespiratoryInstants(time,latest)??0)>0))latest=time;}
  const earlier=rows.filter(e=>{const time=giTime(e);return time&&latest&&compareRespiratoryInstants(time,latest)===-1;}).sort((a,b)=>-(compareRespiratoryInstants(giTime(a)!,giTime(b)!)??0));const retained=new Set(earlier);return <div className="gi-finding-group" key={id}>{rows.filter(e=>!retained.has(e)).map(renderRecord)}{earlier.length>0&&<details><summary>Earlier {String(rows[0].fact.title)} · {earlier.length}</summary>{earlier.map(renderRecord)}</details>}</div>;
 })}</>;
}
