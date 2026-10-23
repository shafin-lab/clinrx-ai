import type {SupplementalRecord,SupplementalReference,ReferenceMode} from './referenceData';
import { supplementalSource, supplementalModeState } from './referenceData';

const referenceOrder:Record<string,number> = { numerical_reference: 0, no_adjustment_reference: 1, loading_only_reference: 2 };
const stateBadges:Record<string,string> = {
  dose_table: 'Source dose references · unreviewed',
  no_adjustment: 'No adjustment stated · unreviewed',
  loading_only: 'Loading reference only · maintenance needs TDM',
  review_gap: 'Evidence gap · no numerical regimen mapped',
  not_mapped: 'Evidence gap · no numerical regimen mapped',
};
function disclosureLabel(status:string) {
  if (status === 'numerical_reference') return 'View unreviewed source dosing table';
  if (status === 'loading_only_reference') return 'View unreviewed loading reference';
  if (status === 'no_adjustment_reference') return 'View unreviewed adjustment statement';
  return 'View source coverage / no-data table';
}

export function SupplementalRenalGuidance({ record, mode }:{record:SupplementalRecord|null;mode:ReferenceMode}) {
  const references:SupplementalReference[] = [...(record?.[mode] || [])].sort((a, b) => (referenceOrder[a.status] ?? 3) - (referenceOrder[b.status] ?? 3));
  const state = supplementalModeState(record, mode);
  return <div className="supplemental-guidance" aria-label={`Supplemental ${mode === 'renal' ? 'renal' : 'CRRT'} evidence`}>
    <span className="badge amber">{stateBadges[state]}</span>
    {!references.length && <p>{record?.gap || 'No supplemental reference mapped for this medicine.'}</p>}
    {references.length > 0 && <p className="supplemental-intro">{state === 'dose_table' ? 'Independent source protocols for review. Match the indication, formulation and assumptions in each card; doses and cutoffs can differ.' : state === 'no_adjustment' ? 'The source explicitly addresses renal adjustment. Usual dose selection, indication and exposure monitoring remain separate review steps.' : state === 'loading_only' ? 'An initial-dose reference is available. Subsequent doses require measured levels and specialist review; no fixed maintenance schedule is supplied.' : 'The sources below support a review pathway or document a gap. No CRRT dose is inferred from a native-renal or intermittent-HD schedule.'}</p>}
    {references.map((reference, index) => {
      const source = supplementalSource(reference.source_id);
      if(!source)return <p key={index}>Exact source metadata unavailable · reference withheld.</p>;
      return <article className="supplemental-source-card" key={`${reference.source_id}-${index}`}>
        <div className="supplemental-source-heading"><span className="badge">{source.type}</span><span className="badge amber">Unreviewed</span></div>
        <h5>{source.title}</h5>
        <small>{source.issuer} · {source.jurisdiction} · {source.version}</small>
        <p><b>Route & scope:</b> {reference.scope}</p>
        <div className="supplemental-assumptions"><b>Applies only under these source conditions</b><ul>{reference.assumptions.map(item => <li key={item}>{item}</li>)}</ul></div>
        {reference.tables.length > 0 && <details className="supplemental-dose-reference">
          <summary>{disclosureLabel(reference.status)}</summary>
          {reference.tables.map((table, tableIndex) => <div className="supplemental-table-section" key={tableIndex}>
            <p><b>{table.title}</b></p>
            <div className="supplemental-table-scroll" role="region" aria-label={`${source.title}: ${table.title}`} tabIndex={0}>
              <table><caption>{reference.scope}</caption><thead><tr>{table.headers.map((header, i) => <th scope="col" key={i}>{header}</th>)}</tr></thead>
                <tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.cells.map((cell, i) => i === 0 ? <th scope="row" key={i}>{cell}</th> : <td key={i}>{cell}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </div>)}
          <small>Reference transcription only. Not matched to this patient and not connected to the calculator or treatment record. q6h = every 6 hours; BID/TID/QID = 2/3/4 times daily; PO = oral; IV = intravenous.</small>
        </details>}
        {reference.notes.length > 0 && <ul className="supplemental-notes">{reference.notes.map(item => <li key={item}>{item}</li>)}</ul>}
        {reference.remaining_gap && <p className="supplemental-remaining-gap"><b>Still requires review:</b> {reference.remaining_gap}</p>}
        <a className="national-source-link" href={`${source.url}${reference.pages?.length ? `#page=${reference.pages[0]}` : ''}`} target="_blank" rel="noopener noreferrer">Open {reference.source_id} · {reference.locator} ↗</a>
        <details className="library-provenance"><summary>Source version & capture</summary><p>Retrieved {source.retrieved_date}. Foreign labels and institutional protocols supplement Indian guidance; institutional approval and stocked-product matching remain pending.</p><small className="library-hash">Retained capture SHA-256: {source.capture_sha256}</small></details>
      </article>;
    })}
  </div>;
}
