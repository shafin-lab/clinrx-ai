import { ApiFailure } from '../api/client';
import type { ExactReference } from '../api/types';
import type { Fact, Item, MicroState, RecordedTime } from '../api/microTypes';
export const refText=(r:ExactReference)=>`${r.kind} / ${r.id} / revision ${r.version}`;
export function factRef(f:Item['fact']):ExactReference { if(!f.kind)throw new ApiFailure('invalid_response');return {kind:f.kind,id:f.id,version:f.revision}; }
export const refKey=(r:ExactReference)=>JSON.stringify([r.kind,r.id,r.version]);
export function Notes({items}:{items:readonly string[]|undefined}) { return <ul>{items?.map((s,i)=><li key={i}>{s}</li>)}</ul>; }
function Time({label,time}:{label:string;time?:RecordedTime}) { return time?<p>{label}: <time>{time.value??([time.lower,time.upper].filter(Boolean).join(' → ')||'Not recorded')}</time> · {time.status} / {time.precision}</p>:null; }
export function FactSummary({fact:f}:{fact:Fact}) { return <>
  <p>{f.specimen_type?.raw_display??f.organism?.raw_display??f.antimicrobial?.raw_display??f.target?.raw_display??f.examination_type??f.kind}</p>
  {f.report&&<p>Report: {f.report.status} · disposition: {f.report.change}</p>}
  {f.identification_state&&<p>Identification: {f.identification_state}</p>}
  {(f.result_status||f.order_status||f.status||f.result||f.growth)&&<p>Recorded status: {f.result_status??f.order_status??f.status??f.result??f.growth}</p>}
  {f.mic&&<p>Recorded MIC: {f.mic.comparator} {f.mic.quantity.value} {f.mic.quantity.unit.raw}</p>}
  {f.interpretation&&<p>Source interpretation: {f.interpretation.raw} ({f.interpretation.category})</p>}
  {f.administered_dose&&<p>Recorded completed dose: {f.administered_dose.amount.value} {f.administered_dose.amount.unit.raw} · {f.administered_dose.basis}</p>}
  {f.prescribed_dose&&<p>Recorded ordered dose: {f.prescribed_dose.amount.value} {f.prescribed_dose.amount.unit.raw} · {f.prescribed_dose.basis}</p>}
  <Time label="Collected" time={f.collected}/><Time label="Received" time={f.received}/><Time label="Report available" time={f.report?.available}/><Time label="Reported" time={f.report?.reported}/><Time label="Administered" time={f.administered}/><Time label="Occurred" time={f.occurred}/><Time label="Created" time={f.created}/>
  {f.antimicrobial&&<details><summary>Recorded antimicrobial identity</summary><p>Raw: {f.antimicrobial.raw_display}</p><p>Canonical: {f.antimicrobial.canonical_id??'Not mapped'}</p><p>Mapping: {f.antimicrobial.mapping_status} · source version {f.antimicrobial.source_code.version??'Not recorded'}</p><p>Labels alone do not establish equivalence. The backend validates selected identities.</p></details>}
</>; }
export function ItemCard({item}:{item:Item}) { return <article className="micro-fact"><h5>{item.fact.id} · revision {item.fact.revision}</h5><FactSummary fact={item.fact}/><p>Inclusion: {item.inclusion.replaceAll('_',' ')}</p><details><summary>Exact source and provenance</summary><p>{refText(factRef(item.fact))}</p><p className="digest">Digest: {item.expected_digest}</p><p>Source: {item.fact.provenance.source.namespace} / {item.fact.provenance.source.identifier}</p><p>Recorded: {item.fact.provenance.recorded_at}</p><p>Ingested: {item.ingestion?.ingested_at??'Unavailable'}</p><p>Origin: {item.fact.origin} · verification {item.fact.verification} · conflict {item.fact.conflict}</p><Notes items={[...(item.disclosures??[]),...(item.fact.provenance.limitations??[])]}/></details></article>; }
export function MicroEvidence({view}:{view:MicroState}) {
  const s=view.assembly.snapshot;
  const micro=s.microbiology,anti=s.antimicrobial;
  const items=new Map((s.items??[]).map(i=>[refKey(factRef(i.fact)),i]));
  const card=(r:ExactReference)=>{const item=items.get(refKey(r));return item?<ItemCard key={refKey(r)} item={item}/>:<p key={refKey(r)}>Unavailable exact reference: {refText(r)}</p>;};
  // Only follow backend-provided reference views. No browser binding reconstruction.
  const grouped=new Set<string>();
  const specimens=micro?.specimens??[],isolates=micro?.isolates??[];
  for(const g of specimens) for(const r of [g.specimen,...(g.examinations??[]),...(g.cultures??[]),...(g.isolates??[]),...(g.molecular_results??[])]) grouped.add(refKey(r));
  for(const g of isolates) if(grouped.has(refKey(g.isolate))) for(const r of [...(g.susceptibilities??[]),...(g.resistance_findings??[])]) grouped.add(refKey(r));
  return <><h3>Microbiology</h3>{specimens.map(g=><details className="micro-group" key={refKey(g.specimen)}><summary>Specimen {g.specimen.id} · revision {g.specimen.version}</summary>{card(g.specimen)}
    {(g.examinations?.length??0)>0&&<><h4>Direct examinations</h4>{(g.examinations??[]).map(card)}</>}{(g.cultures?.length??0)>0&&<><h4>Culture reports</h4>{(g.cultures??[]).map(card)}</>}
    {(g.isolates??[]).map(r=>{const group=isolates.find(i=>refKey(i.isolate)===refKey(r));return <details className="micro-group" key={refKey(r)}><summary>Isolate {r.id} · revision {r.version}</summary>{card(r)}<h4>Susceptibility results</h4>{group?.susceptibilities?.map(card)}{(group?.resistance_findings?.length??0)>0&&<><h4>Resistance findings</h4>{group?.resistance_findings?.map(card)}</>}</details>;})}
    {(g.molecular_results?.length??0)>0&&<><h4>Molecular results</h4>{(g.molecular_results??[]).map(card)}</>}
  </details>)}
  {(micro?.references??[]).filter(r=>!grouped.has(refKey(r))).map(card)}
  <details><summary>Exact binding outcomes</summary>{view.assembly.bindings?.map((b,i)=><p key={i}>{refText(b.owner)} → {b.role}: {b.status} / {b.disposition}. Declared target: {b.declared?refText(b.declared):'None'}{(b.candidates?.length??0)>0&&` · Candidates: ${b.candidates?.map(refText).join('; ')}`}</p>)}</details>
  <h3>Antimicrobials</h3>{([['Orders',anti?.orders??[]],['Completed administrations',anti?.administrations??[]],['Non-delivery events',anti?.non_delivery??[]]] as const).map(([title,refs])=><details className="micro-group" key={title}><summary>{title} ({refs.length})</summary>{refs.map(card)}{refs.length===0&&<p>No retained records in this bounded view; this does not establish clinical absence.</p>}</details>)}
  <details><summary>Coverage and mapping issues</summary>{s.coverage?.map(c=><div key={c.domain}><p>{c.domain}: {c.mapping_support} / {c.retrieval}</p><Notes items={c.limitations}/></div>)}<Notes items={s.disclosures}/>{s.issues?.map((i,n)=><p key={n}>{refText(i.reference)}: {i.reason}</p>)}</details></>;
}
