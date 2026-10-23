import type {DeviceProfile} from './types';

type Observation=Record<string,any>;
export function assayGroups(observations:Observation[],profile?:DeviceProfile) {
 const assays=[...new Set([...(profile?.channels.map(c=>c.assay)??[]),...observations.map(o=>String(o.assay))])];
 const order=['EXTEM','INTEM','FIBTEM','HEPTEM'];
 assays.sort((a,b)=>{const x=order.indexOf(a.split(' ')[0]),y=order.indexOf(b.split(' ')[0]);return (x<0?4:x)-(y<0?4:y);});
 return assays.map(assay=>{
  const channel=profile?.channels.find(c=>c.assay===assay),reported=observations.filter(o=>o.assay===assay);
  const missing:Observation[]=(channel?.parameters??[]).filter(p=>!reported.some(o=>o.parameter===p.name)).map(p=>({id:'unreported:'+assay+':'+p.name,assay,parameter:p.name,unit:p.unit,state:'not_reported',displayOnly:true}));
  const parameters=channel?.parameters.map(p=>p.name)??[];
  const results:Observation[]=[...reported,...missing].sort((a,b)=>{const x=parameters.indexOf(a.parameter),y=parameters.indexOf(b.parameter);return (x<0?parameters.length:x)-(y<0?parameters.length:y);});
  return {assay,label:channel?.label??assay,results};
 });
}

function resultText(o:Observation) {
 if(!['final','preliminary'].includes(o.state))return ({not_reported:'Not reported',pending:'Pending',not_measured:'Not measured',no_clot:'No clot formed'} as Record<string,string>)[o.state]??String(o.state??'unknown').replaceAll('_',' ');
 const comparator=({eq:'',lt:'<',le:'≤',gt:'>',ge:'≥'} as Record<string,string>)[o.comparator]??o.comparator??'';
 return `${comparator}${comparator?' ':''}${o.raw_value??o.value??'Not reported'}`;
}

export function VetResults({observations,profile}:{observations:Observation[];profile?:DeviceProfile}) {
 return <div className="m10-assays">{assayGroups(observations,profile).map(group=><section className="m10-assay" role="region" aria-label={group.assay} key={group.assay}>
  <h5>{group.assay}{group.label!==group.assay?' · '+group.label:''}</h5>
  <table><caption>{group.assay} parameters</caption><thead><tr><th>Parameter</th><th>Result</th><th>Original unit</th><th>Status</th></tr></thead><tbody>{group.results.map(o=><tr key={o.id}><th scope="row">{o.parameter}</th><td>{resultText(o)}</td><td>{o.unit??'—'}</td><td>{o.displayOnly?'Not reported':o.state}</td></tr>)}</tbody></table>
 </section>)}</div>;
}
