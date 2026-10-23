import {useState} from 'react';
import { guidanceForMedicine, guidanceSource, nationalGuidance, guidanceCoverage } from './referenceData';
import { supplementalForMedicine, hasSupplementalDose, supplementalModeState, supplementalStateLabels } from './referenceData';
import { SupplementalRenalGuidance } from './SupplementalRenalGuidance';

function SourceLink({ sourceId, pages, row, section }:{sourceId:string;pages:number[];row?:number;section?:string}) {
  const source = guidanceSource(sourceId);
  if (!source) return null;
  return <a className="national-source-link" href={`${source.url}#page=${pages[0]}`} target="_blank" rel="noopener noreferrer">
    {sourceId === 'IN-G001' ? 'NCDC / ICMR 2025' : 'ICMR 2019 · older reference'}
    {section && ` · §${section}`}{row && ` · Table 14.1, row ${row}`} · PDF {pages.length > 1 ? 'pages' : 'page'} {pages.join(', ')} ↗
  </a>;
}

export function NationalDrugGuidance({ drug }:{drug:string}) {
  const record = guidanceForMedicine(drug);
  const supplemental = supplementalForMedicine(drug);
  const [expanded, setExpanded] = useState(false);
  if (!record) return <section className="national-drug-guidance"><h4>Drug-specific national guidance</h4><div className="library-empty"><span className="badge amber">Unreviewed · coverage gap</span><p>No national guidance is mapped to this unlisted medicine. Verify its identity, exact product and formulation before review. No dose is inferred.</p></div></section>;
  const contexts = record.indications.items;
  const group = record.combination_group;
  return <section className="national-drug-guidance" aria-label={`National guidance for ${drug}`}>
    <h4>Drug-specific evidence</h4>
    <div className="national-review-notice"><span className="badge amber">Unreviewed · not for clinical use</span><p>Source summaries for review. They do not select a dose for this patient or establish an approved hospital policy. The 2019 renal table is kept separate from the 2025 syndrome guidance.</p></div>
    <dl className="national-coverage-grid">
      <div><dt>Indication contexts</dt><dd>{contexts.length || 'Not mapped'}</dd></div>
      <div><dt>Renal reference</dt><dd>{hasSupplementalDose(supplemental, 'renal') ? 'Supplemental source tables' : supplemental?.renal.length ? 'Review notes / gap' : record.renal.sources.length ? '2019 · unreviewed' : 'Not located'}</dd></div>
      <div><dt>CRRT reference</dt><dd>{supplementalStateLabels[supplementalModeState(supplemental,'crrt')]}</dd></div>
      <div><dt>Monitoring</dt><dd>{record.monitoring.items.length ? 'Source-specific notes' : 'General points only'}</dd></div>
    </dl>
    <section className="national-field">
      <h4>Indications & syndrome contexts</h4>
      {contexts.length ? <><p>Listed source contexts for {drug}. A medicine may be an adjunct or part of a combination. Check the full row, patient group, route, organism and restrictions before interpretation.</p>
        <ul className="national-context-list">{contexts.slice(0, expanded ? contexts.length : 4).map((item, index) => <li key={`${item.section}-${index}`}>
          <b>{item.title}</b><p>{item.subgroup}</p><small>{item.role} · adult applicability requires confirmation</small>
          <SourceLink sourceId={item.source_id} pages={[item.page]} section={item.section} />
        </li>)}</ul>
        {contexts.length > 4 && <button type="button" className="text-button" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer contexts' : `Show all ${contexts.length} source contexts`}</button>}
      </> : <p>{group ? 'Confirm the exact product before assigning indications to this combination classification.' : 'No direct indication context was located for this medicine in the indexed national treatment sections. This is a coverage gap, not evidence that the medicine has no indication.'}</p>}
    </section>
    <section className="national-field">
      <h4>Renal dosing</h4>
      <SupplementalRenalGuidance record={supplemental} mode="renal" />
      <details className="national-historical-reference"><summary>Older national renal reference · ICMR 2019</summary>
      <span className="badge amber">{record.renal.dose_text ? 'Historical source dose · unreviewed' : record.renal.status.includes('withheld') ? 'Numeric adjustment withheld' : 'No numerical adjustment mapped'}</span>
      <p>{record.renal.summary}</p>
      {record.renal.dose_text && <details className="national-dose-reference"><summary>View the unreviewed 2019 renal reference</summary><p>{record.renal.dose_text}</p><small>Source transcription/synthesis only. Not assessed for this patient, changing renal function, current stocked product or local policy. No calculator or treatment decision uses these values.</small></details>}
      {record.renal.route_scope && <small>{record.renal.route_scope}</small>}
      {record.renal.sources.map(source => <SourceLink key={source.source_id} sourceId={source.source_id} pages={source.pages} row={source.row} />)}
      </details>
    </section>
    <section className="national-field national-crrt-gap">
      <h4>CRRT dosing</h4>
      <SupplementalRenalGuidance record={supplemental} mode="crrt" />
      <details className="national-historical-reference"><summary>National CRRT coverage & review context</summary><p>{record.crrt.summary}</p>
      {!group && <details><summary>Context required for a CRRT evidence review</summary><ul>{record.crrt.required_context.map(item => <li key={item}>{item}</li>)}</ul><small>ClinRx review checklist; these items are not a CRRT regimen from the national guideline.</small></details>}
      </details>
    </section>
    <section className="national-field">
      <h4>Monitoring & follow-up</h4>
      {record.monitoring.items.length ? <><span className="badge amber">Drug-specific source notes · unreviewed</span><ul>{record.monitoring.items.map(item => <li key={item}>{item}</li>)}</ul>{record.monitoring.sources.map(source => <SourceLink key={source.source_id} sourceId={source.source_id} pages={source.pages} row={source.row} />)}</> : <p>No medicine-specific toxicity-monitoring schedule is mapped from the indexed national sources. The general review points below do not replace one.</p>}
      <details className="national-general-monitoring"><summary>General national stewardship review points</summary><ul>{nationalGuidance.general_monitoring.items.map(item => <li key={item}>{item}</li>)}</ul><small>{nationalGuidance.general_monitoring.limit}</small><SourceLink sourceId={nationalGuidance.general_monitoring.source_id} pages={nationalGuidance.general_monitoring.pages} /></details>
    </section>
    <details className="library-provenance"><summary>Coverage & source provenance</summary><p>All {guidanceCoverage.entries} catalogue entries have explicit coverage states. {guidanceCoverage.indications} have national indication contexts; {guidanceCoverage.renal} have older renal-table notes, including {guidanceCoverage.renalDose} numerical references. No national CRRT dose is mapped. Search and extraction are not proof that a recommendation does not exist.</p><p>Retrieved {nationalGuidance.retrieved_date}. Source-table matching and summaries await clinical review. Raw table cells and hashes are retained locally for audit. Section links use physical PDF page numbers; full rows can continue onto subsequent pages.</p>{nationalGuidance.sources.map(source => <p key={source.id}>{source.title} · {source.version}<br /><small className="library-hash">SHA-256: {source.sha256}</small></p>)}</details>
  </section>;
}
