import { useEffect, useRef } from 'react';
import type { Execution, ExactReference, Cutoff } from '../api/types';
export const refLabel=(r:ExactReference)=>`${r.kind} · ${r.id} · revision ${r.version}`;
export function TextList({items}:{items:string[]}) { return <ul>{items.map((x,i)=><li key={i}>{x}</li>)}</ul>; }
function Prefix({label,value}:{label:string;value:Cutoff}) { return <div><h4>{label}</h4><dl><dt>Repository</dt><dd>{value.repository_id}</dd><dt>Fact watermark</dt><dd>{value.fact_watermark}</dd><dt>Captured</dt><dd>{value.captured_at}</dd></dl></div>; }
export function ProvenanceDrawer({result,onClose}:{result:Execution;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{ const previous=document.activeElement as HTMLElement|null; const node=dialog.current!; node.showModal(); node.querySelector('button')?.focus(); return ()=>{node.close();previous?.focus();}; },[]);
  const p=result.provenance;
  return <dialog ref={dialog} aria-labelledby="provenance-title" onCancel={onClose} className="drawer">
    <header className="section-heading"><div><span className="eyebrow">Retained evidence · direct dependencies only</span><h2 id="provenance-title">Why am I seeing this?</h2></div><button onClick={onClose}>Close provenance</button></header>
    <p>Historical synthetic audit information. This view uses the retained execution, not current patient state. Complete ancestry is not provided.</p>
    {([p.earlier_laboratory,p.later_laboratory,p.medication] as const).map((item,i)=><section className="audit-evidence" key={i}>
      <h3>{['A · Earlier laboratory','B · Later laboratory','M · Medication event'][i]}</h3>
      <p>{item.domain==='laboratory'?`${item.quantity.value} ${item.quantity.unit_raw}`:item.event_type==='medication_order'?'Medication order':'Medication administration'}</p>
      <dl><dt>Consumed revision</dt><dd>{refLabel(item.reference)}</dd><dt>Terminal revision</dt><dd>{refLabel(p.terminal_references[i])}</dd>
      <dt>Event</dt><dd>{item.time.event ?? 'Not recorded'}</dd><dt>Effective interval</dt><dd>{item.time.effective_start ?? 'Not recorded'} → {item.time.effective_end ?? 'Not recorded'}</dd>
      <dt>Source</dt><dd>{item.source.namespace} / {item.source.identifier} / {item.source.version ?? 'Version unknown'} ({item.source.channel})</dd>
      <dt>Provenance recorded</dt><dd>{item.provenance_recorded_at}</dd><dt>Ingested</dt><dd>{item.ingested_at}</dd></dl>
      <TextList items={[...item.disclosures,...item.provenance_limitations]}/>
    </section>)}
    <h3>Retained temporal relationship</h3>
    {result.governance.outcome==='released' && p.inference.statement ? <p>{p.inference.statement}</p>:<p>Inference statement withheld. Exact selected event times are shown above; no relationship is reconstructed in this view.</p>}
    <p>{p.inference.applicability}</p><p>Method: {refLabel(p.inference.method)}</p>
    <p>Consumed inference: {refLabel(p.inference.reference)}</p><p>Terminal inference: {refLabel(p.inference_terminal_reference)}</p>
    <h3>Direct derived_from dependencies</h3><ol>{p.direct_dependencies.map((edge,i)=><li key={i}>{refLabel(edge.target)} — {edge.relationship}</li>)}</ol>
    <Prefix label="Original input cutoff" value={p.input_cutoff}/><Prefix label="Inference cutoff" value={p.inference_cutoff}/><Prefix label="Protected final cutoff" value={p.final_cutoff}/>
    <h3>Final recheck: {p.final_recheck}</h3><TextList items={p.recheck_reasons}/>
    <h3>Governance: {result.governance.outcome}</h3><TextList items={result.governance.reasons}/>
    <dl><dt>Assessed</dt><dd>{result.governance.assessed_at ?? 'Not provided'}</dd><dt>Decided</dt><dd>{result.governance.decided_at}</dd><dt>Finalized</dt><dd>{result.finalized_at}</dd><dt>Execution ingested</dt><dd>{result.ingested_at}</dd></dl>
    <h3>Uncertainty</h3><TextList items={p.inference.uncertainty}/><h3>Limitations</h3><TextList items={[...p.inference.limitations,...result.governance.limitations,...result.context.limitations]}/>
  </dialog>;
}
