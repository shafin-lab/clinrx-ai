import {supplementaryFor, supplementarySources} from './supplementaryCatalogue';

export function SupplementaryEvidence({infectionId, rowId}: {infectionId: string; rowId?: string}) {
  const entries = supplementaryFor(infectionId, rowId);
  if (!entries.length) return null;

  return <details className="infection-supplement">
    <summary>Further evidence &amp; alternatives · {entries.length} {entries.length === 1 ? 'reference' : 'references'}</summary>
    <p className="infection-caption">Separate source guidance for further reading. NCDC remains unchanged; these references are not matched to this patient.</p>
    {entries.map(entry => {
      const source = supplementarySources[entry.sourceId];
      return <section className="infection-supplement-entry" aria-labelledby={`supplement-${entry.id}`} key={entry.id}>
        <div className="infection-supplement-heading">
          <h4 id={`supplement-${entry.id}`}>{entry.title}</h4>
          <span className="infection-badge">{entry.kind}</span>
        </div>
        <p className="infection-caption">{source.organisation} · {source.version}</p>
        <p><strong>Why this is shown:</strong> {entry.why}</p>
        <p><strong>Applies to:</strong> {entry.appliesTo}</p>
        <dl>{entry.details.map(detail => <div key={detail.label}><dt>{detail.label}</dt><dd>{detail.text}</dd></div>)}</dl>
        <p><strong>Difference from NCDC:</strong> {entry.difference}</p>
        <p><strong>Important limits:</strong> {entry.limits}</p>
        <p className="infection-caption">{source.title} · {entry.location}</p>
        <a href={source.url} target="_blank" rel="noopener noreferrer">Read supporting source ↗</a>
      </section>;
    })}
  </details>;
}
