import {useEffect, useRef, useState} from 'react';
import {AntibioticClient, type AntibioticBundle} from '../api/antibioticClient';
import {RF2Client, key, pin, stable, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import type {Item} from '../api/microTypes';
import {microReference, microTime} from '../antibioticWorkflow/patientModel';
import {SourcePinnedReview, useSourcePinnedReview} from '../clinical/SourcePinnedReview';
import {record} from '../demo/evidencePresentation';
import {GISource} from '../gastrointestinal/GISource';
import {sourceStatus, sourceTime} from '../neurological/model';
import {preventionModel, type Requested} from './model';
import '../endocrine/endocrine.css';

type Props = {catalog?: Catalog; bundle?: AntibioticBundle; requested: Requested; current: boolean; guarded: boolean};
const words = (value: unknown) => typeof value === 'string' ? value.replaceAll('_', ' ') : '';
function microTitle(item: Item) {
  const f = record(item.fact);
  return [record(f.organism).raw_display, record(f.specimen_type).raw_display,
    record(f.antimicrobial).raw_display, record(f.target).raw_display, record(f.mechanism).raw_display,
  ].filter(value => typeof value === 'string' && value).join(' · ') ||
    words(item.fact.kind).replace(/^microbiology /, '');
}

function reviewNeeded(saved: ReturnType<typeof useSourcePinnedReview>, model: ReturnType<typeof preventionModel>) {
  return !!model.micro && !!saved.reviews[0] && !model.matches(saved.reviews[0]);
}

export function PreventionSummary({catalog, bundle, requested, current, guarded, onOpen}: Props & {onOpen: () => void}) {
  const model = preventionModel(catalog, bundle, requested);
  const saved = useSourcePinnedReview('M20', model.valid ? catalog : undefined, requested);
  return <section className="m14-card" aria-label="Infection prevention summary">
    <h3>Infection prevention and control</h3>
    {current && model.valid ? <>
      {model.statuses.length > 0 ? <ul>{model.statuses.map(status =>
        <li key={status.label.toLowerCase()}>{status.label} · {words(status.status)} · {status.time}</li>)}</ul> :
        <p>No confirmed precaution status recorded.</p>}
      {!!model.unresolved && <p>Some precaution records need clarification.</p>}
      {reviewNeeded(saved, model) && <p role="status">Prevention review needed · Evidence changed.</p>}
    </> : <p>Precaution evidence unconfirmed.</p>}
    <button type="button" disabled={guarded} onClick={onOpen}>Open Infection Prevention and Control</button>
  </section>;
}

export function PreventionWorkspace({catalog, bundle, requested, current, guarded, onRefresh}: Props & {onRefresh: () => Promise<void>}) {
  const model = preventionModel(catalog, bundle, requested);
  const confirmed = current && model.valid && !!model.micro;
  const saved = useSourcePinnedReview('M20', model.valid ? catalog : undefined, requested);
  const [rf2] = useState(() => new RF2Client());
  const [antibiotics] = useState(() => new AntibioticClient());
  const [selected, select] = useState<{source: Evidence; catalog: Catalog}>();
  const [history, setHistory] = useState<{key: string; rows: unknown[]}>();
  const [historyError, setHistoryError] = useState('');
  const token = useRef(0);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    setHistory(undefined);
    setHistoryError('');
    return () => { token.current++; };
  }, [catalog, bundle, confirmed, guarded]);

  function open(source: Evidence, button: HTMLButtonElement) {
    if (!catalog || !confirmed || guarded) return;
    trigger.current = button;
    select({source, catalog});
  }

  async function resolve(exact: Pin, button: HTMLButtonElement) {
    if (!catalog || exact.repository !== catalog.repository) throw Error('Unconfirmed source');
    const pending = ++token.current;
    const [source] = await rf2.resolve(catalog.repository, [exact]);
    if (pending !== token.current || !button.isConnected) return;
    if (!source || stable(pin(source)) !== stable(exact)) throw Error('Exact revision unavailable');
    open(source, button);
  }

  async function inspect(item: Item) {
    if (!model.micro || !confirmed || guarded) return;
    const pending = ++token.current;
    setHistory(undefined);
    setHistoryError('');
    try {
      const rows = await antibiotics.history(model.micro, microReference(item));
      if (pending === token.current) setHistory({key: stable(microReference(item)), rows});
    } catch {
      if (pending === token.current) setHistoryError('Exact report history could not be confirmed.');
    }
  }

  return <section className="m14-workspace" aria-label="Infection Prevention and Control">
    <h2>Infection Prevention and Control</h2>
    <button type="button" disabled={guarded} onClick={() => void onRefresh().catch(() => {})}>Refresh evidence</button>
    <section className="m14-card">
      <h3>Documented precautions and isolation</h3>
      {(!current || !model.valid) ? <p>Precaution evidence unconfirmed.</p> :
        !model.sources.length ? <p>No precautions documented in the shared record.</p> :
        model.sources.map(source => <article key={key(pin(source))}>
          <h4>{String(source.fact.precaution)}</h4>
          <p>{source.superseded ? 'Superseded' : words(source.fact.status)} · {sourceTime(source)} · {sourceStatus(source)}</p>
          <p>{String(source.fact.narrative)}</p>
          <button type="button" disabled={!confirmed || guarded} onClick={event => open(source, event.currentTarget)}>Open precaution source</button>
        </article>)}
    </section>
    <section className="m14-card">
      <h3>Shared microbiology</h3>
      {(!confirmed) ? <p>Shared microbiology is unconfirmed. Refresh evidence before saving a review.</p> :
        !model.items.length ? <p>No linked microbiology in this review period.</p> :
        model.items.map(item => {
          const exact = microReference(item);
          const id = stable(exact);
          const fact = record(item.fact);
          const report = record(fact.report);
          return <article key={id}>
            <h4>{microTitle(item)}</h4>
            <p>{[words(fact.growth), words(record(fact.interpretation).category), words(fact.result), words(report.status),
              words(report.change), microTime(item), words(item.inclusion)].filter(Boolean).join(' · ')}</p>
            <details><summary>Source · {exact.id} · revision {exact.version}</summary>
              <pre tabIndex={0}>{JSON.stringify(item.fact, null, 2)}</pre>
              <button type="button" disabled={guarded} onClick={() => void inspect(item)}>Inspect microbiology history</button>
              {history?.key === id && <ul>{history.rows.map(raw => {
                const revision = record(record(raw).fact);
                return <li key={String(revision.revision)}><details><summary>Revision {String(revision.revision)}</summary>
                  <pre tabIndex={0}>{JSON.stringify(revision, null, 2)}</pre></details></li>;
              })}</ul>}
            </details>
          </article>;
        })}
      {historyError && <p role="alert">{historyError}</p>}
    </section>
    {confirmed && reviewNeeded(saved, model) && <p role="status">Prevention review needed · Evidence changed.</p>}
    <SourcePinnedReview catalog={catalog} requested={requested} model={model} current={confirmed} guarded={guarded}
      saved={saved} cardClassName="m14-card" onOpenSource={open} onResolveSource={resolve}/>
    {selected && selected.catalog === catalog && confirmed && !guarded &&
      <GISource current evidence={selected.source} transport={rf2} onClose={() => { select(undefined); trigger.current?.focus(); }}/>}
  </section>;
}
