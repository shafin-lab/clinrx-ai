import type { MicroExecution } from '../api/microTypes';
import { FactSummary, Notes, refText } from './MicroEvidence';
export function MicroResult({result:r}:{result:MicroExecution}) {
  const p=r.provenance;
  return <section aria-label="Microbiology protected result" className="micro-result">
    <h3>Protected descriptive review {r.governance.outcome}</h3>
    <p>Retained execution {r.execution_id}</p><p>Finalized: {r.finalized_at} · Ingested: {r.ingested_at}</p>
    {r.governance.outcome==='released'?<><p className="statement">{r.statement}</p><p>{p.inference.applicability}</p></>:<p>The descriptive statement is withheld from the main result. Original inference remains available in retained provenance.</p>}
    <h4>Governance reasons</h4><Notes items={r.governance.reasons}/><Notes items={p.recheck_reasons}/>
    <p>{p.inference.validation_limitations}</p><details><summary>Governance limitations and source disclosures</summary><Notes items={r.governance.limitations}/></details>
    <details><summary>Retained provenance · consumed versus final checked</summary>
      <p>This is the immutable execution record. Final checked evidence did not replace the original inference inputs.</p>
      <p>Original inference: {p.inference.id} / {p.inference.revision}</p><p>Method: {refText(p.inference.method)}</p>
      <p>Original inference statement: {p.inference.statement}</p><p>Applicability: {p.inference.applicability}</p><p>{p.inference.validation_limitations}</p><Notes items={[...p.inference.uncertainty,...p.inference.provenance.limitations]}/>
      <h4>Exact derived-from inputs</h4>{p.inference.inputs.map((r,i)=><p key={i}>{refText(r)}</p>)}
      {p.final_recheck.evidence.map((w,i)=><section className="micro-witness" key={w.role}><h4>{w.role}: {p.witness_statuses[i]==='current'?'Unchanged':'Corrected / changed'}</h4>
        <div className="micro-columns"><div><h5>Consumed</h5><p>{refText(w.consumed)}</p><p className="digest">Source digest: {w.source_digest}</p><p className="digest">Item digest: {w.item_digest}</p><FactSummary fact={p.consumed[i].fact}/></div><div><h5>Final checked</h5><p>{refText(w.terminal)}</p><p className="digest">Source digest: {w.terminal_source_digest}</p><p>Backend suitability: {w.suitability}</p><FactSummary fact={p.final_recheck.terminal_facts[i]}/></div></div>
      </section>)}
      <p>Specimen binding matches: {String(p.specimen_binding_matches)} · Isolate binding matches: {String(p.isolate_binding_matches)} · U↔D canonical identity matches: {String(p.antimicrobial_identity_matches)}</p>
      <h4>Repository cutoffs</h4>{([['Original',p.original_cutoff],['Inference persistence',p.inference_cutoff],['Protected final',p.final_recheck.final_cutoff]] as const).map(([label,c])=><p key={label}>{label}: {c.repository_id} / watermark {c.fact_watermark} / {c.captured_at}</p>)}
      <p>Governance policy: {refText(p.governance_policy)}</p><p>Decision: {refText(r.governance.decision_reference)}</p><p>Safety: {r.governance.safety_status} · Fidelity: {r.governance.fidelity_status} · Freshness: {r.governance.freshness_status} · Authority: {r.governance.authority_status}</p>
    </details>
  </section>;
}
