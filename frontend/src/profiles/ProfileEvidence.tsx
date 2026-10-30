import type {ClinicalFact,ClinicalTable,Profile,Reference} from './profileTypes';
export function uniqueReferences(refs:Reference[]){const seen=new Set<string>();return refs.filter(r=>{let key=r.url;try{const u=new URL(key);u.hash='';u.hostname=u.hostname.replace(/^www\./,'');key=u.toString().replace(/\/$/,'')}catch{/* Invalid URLs are rejected by the data assembly. */}if(seen.has(key))return false;seen.add(key);return true})}
export function Citations({profile,ids}:{profile:Profile;ids:string[]}){
 const refs=uniqueReferences(ids.map(id=>profile.references.find(r=>r.id===id)).filter((r):r is Reference=>!!r));
 if(!refs.length)return null;
 return <div className="rx-citations"><span>Sources</span>{refs.map((r,i)=><a key={r.id} href={r.url} target="_blank" rel="noreferrer" title={r.title}>{r.jurisdiction||'Reference'}{refs.length>1?` ${i+1}`:''} ↗</a>)}</div>
}
export function EvidenceTable({table,profile}:{table:ClinicalTable;profile:Profile}){
 return <section className="rx-evidence-block"><h3>{table.title}</h3><p className="rx-context">{table.context}</p><div className="rx-table-wrap"><table aria-label={table.title}><thead><tr>{table.columns.map((c,i)=><th scope="col" key={i}>{c}</th>)}</tr></thead><tbody>{table.rows.map((row,i)=><tr key={i}>{row.map((value,j)=><td key={j}>{value}</td>)}</tr>)}</tbody></table></div><Citations profile={profile} ids={table.source_ids}/></section>
}
export function FactTable({title,facts,profile}:{title:string;facts:ClinicalFact[];profile:Profile}){
 if(!facts.length)return null;
 return <section className="rx-evidence-block"><h3>{title}</h3><div className="rx-table-wrap"><table aria-label={title}><thead><tr><th scope="col">Parameter</th><th scope="col">Finding</th><th scope="col">Conditions</th></tr></thead><tbody>{facts.map((f,i)=><tr key={i}><th scope="row">{f.label}</th><td>{f.value}</td><td>{f.context}</td></tr>)}</tbody></table></div><Citations profile={profile} ids={facts.flatMap(f=>f.source_ids)}/></section>
}
