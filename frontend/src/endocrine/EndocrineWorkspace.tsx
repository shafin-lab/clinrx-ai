import {useId, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {key, pin, RF2Client, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import {GISource} from '../gastrointestinal/GISource';
import {SourcePinnedReview, useSourcePinnedReview} from '../clinical/SourcePinnedReview';
import {EndocrineSource} from './EndocrineSource';
import {displayEvent, endocrineModel, type EndocrineModel, type EndocrineScope, type LabRow} from './model';
import '../gastrointestinal/gastrointestinal.css';
import './endocrine.css';

interface SharedProps {
  catalog?: Catalog;
  requested: EndocrineScope;
  current: boolean;
  guarded?: boolean;
}

export type OpenSource = (source: Evidence, trigger: HTMLButtonElement) => void;
const tabs = ['Bedside summary', 'Glucose & insulin', 'Other endocrine results', 'Review & plan'] as const;

function shortTime(value: string) {
  return value.replace(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):00(Z|[+-]\d{2}:\d{2})$/, '$1 · $2 $3');
}

function RecordedTime({row}: {row: {at: string | null; time: string}}) {
  return row.at ? <time dateTime={row.at}>{shortTime(row.at)}</time> : row.time;
}

function glucoseSummary(model: EndocrineModel) {
  const row = model.latest;
  return row ? [row.value, shortTime(row.time), row.specimenLabel, row.statusLabel].filter(Boolean).join(' · ')
    : 'Latest glucose unconfirmed';
}

export function EndocrineSummary({catalog, requested, current, guarded, onOpen}: SharedProps & {onOpen: () => void}) {
  const model = useMemo(() => endocrineModel(catalog, requested), [catalog, requested]);
  const saved = useSourcePinnedReview('M14', model.valid ? catalog : undefined, requested);
  if (!model.sources.length && !saved.reviews.length) return null;
  const review = current ? saved.reviews.find(model.matches) : undefined;
  const items = [glucoseSummary(model)];
  if (model.latestInsulin) items.push(model.latestInsulin.label + ' · ' + model.latestInsulin.status.replaceAll('_', ' '));
  if (review) items.push('Next review ' + review.draft.nextReview);
  else if (saved.reviews.length) items.push('Review needed');
  return <section className="m14-summary" aria-label="Endocrine summary">
    <div><h3>Endocrine</h3><p>{current ? items.join(' · ') : 'Evidence unconfirmed'}</p></div>
    <button type="button" disabled={guarded} onClick={onOpen}>Open Endocrine</button>
  </section>;
}

function SourceButton({source, open}: {source: Evidence; open: OpenSource}) {
  return <button type="button" onClick={event => open(source, event.currentTarget)}>Open source</button>;
}

function LabResult({row}: {row: LabRow}) {
  return <>
    <strong>{row.value}</strong>
    <small>{row.specimenLabel}</small>
    {row.statusLabel && row.statusLabel !== row.value && <small>{row.statusLabel}</small>}
    {row.qualifications.map(qualification => <small key={qualification}>{qualification}</small>)}
  </>;
}

function Timeline({model, open}: {model: EndocrineModel; open: OpenSource}) {
  return <section className="m14-card">
    <h3>Glucose, insulin and nutrition</h3>
    {!model.timeline.length ? <p>No relevant recorded events in this period.</p> :
      <div className="m14-scroll"><table aria-label="Glucose, insulin and nutrition timeline">
        <thead><tr><th scope="col">Source time</th><th scope="col">Glucose</th>
          <th scope="col">Insulin or nutrition event</th><th scope="col">Source</th></tr></thead>
        <tbody>{model.timeline.map(row => <tr key={row.id}>
          <td><RecordedTime row={row}/></td>
          <td>{row.kind === 'lab' && <LabResult row={row}/>}</td>
          <td>{row.kind === 'event' && <>{displayEvent(row)}
            {row.source.fact.conflict === 'unresolved' && <small>Unresolved source conflict</small>}</>}</td>
          <td><SourceButton source={row.source} open={open}/></td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}

function OtherResults({model, open}: {model: EndocrineModel; open: OpenSource}) {
  const groups = new Map<string, LabRow[]>();
  for (const row of model.otherLabs) {
    const group = groups.get(row.group);
    if (group) group.push(row);
    else groups.set(row.group, [row]);
  }
  return <section className="m14-card">
    <h3>Other endocrine results</h3>
    {!groups.size && <p>No linked endocrine results in this period.</p>}
    {Array.from(groups, ([group, rows]) => <section key={group} className="m14-results">
      <h4>{group}</h4>
      <ul>{rows.map(row => <li key={row.id}>
        <div><strong>{row.label}</strong> <LabResult row={row}/><small><RecordedTime row={row}/></small></div>
        <SourceButton source={row.source} open={open}/>
      </li>)}</ul>
    </section>)}
  </section>;
}

export function EndocrineWorkspace({catalog, requested, current, guarded = false, loading, error, onRefresh}: SharedProps & {
  loading: boolean;
  error?: string;
  onRefresh: () => Promise<void>;
}) {
  const model = useMemo(() => endocrineModel(catalog, requested), [catalog, requested]);
  const [tab, setTab] = useState(0);
  const [selected, setSelected] = useState<{source: Evidence; scope: string}>();
  const trigger = useRef<HTMLButtonElement>(null);
  const sourceRequest = useRef(0);
  const [client] = useState(() => new RF2Client());
  const tabId = useId();
  const confirmed = current && !loading && model.valid;
  const saved = useSourcePinnedReview('M14', model.valid ? catalog : undefined, requested);
  const review = confirmed ? saved.reviews.find(model.matches) : undefined;
  const scopeKey = JSON.stringify([catalog?.repository, requested.patient, requested.encounter, requested.start, requested.end]);
  const source = model.valid && selected?.scope === scopeKey ? selected.source : undefined;
  const sourceIsCurrent = confirmed && !!source && model.pins.some(value => value.kind === source.fact.kind &&
    value.id === source.fact.id && value.version === source.fact.revision && value.digest === source.digest &&
    value.ingestion === source.ingestion.ingestion_sequence);

  useLayoutEffect(() => () => { sourceRequest.current++; }, [confirmed, guarded, scopeKey]);

  function openSource(evidence: Evidence, button: HTMLButtonElement) {
    if (guarded) return;
    sourceRequest.current++;
    trigger.current = button;
    setSelected({source: evidence, scope: scopeKey});
  }

  async function resolveSource(exact: Pin, button: HTMLButtonElement) {
    if (!confirmed || guarded || exact.repository !== catalog?.repository) return;
    const request = ++sourceRequest.current;
    try {
      const [result] = await client.resolve(exact.repository, [exact]);
      if (request !== sourceRequest.current || !button.isConnected) return;
      const target = result?.fact.binding.target;
      if (!target || target.patient_id !== requested.patient || target.encounter_id !== requested.encounter) {
        throw new Error('Source belongs to a different encounter.');
      }
      openSource(result, button);
    } catch (cause) {
      if (request === sourceRequest.current) throw cause;
    }
  }

  function closeSource() {
    sourceRequest.current++;
    setSelected(undefined);
    const button = trigger.current;
    requestAnimationFrame(() => { if (button?.isConnected) button.focus(); });
  }

  function selectTab(index: number) {
    setTab(index);
    document.getElementById(tabId + index)?.focus();
  }

  return <section className="m14-workspace" aria-label="Endocrine">
    <header className="m14-heading">
      <div><h2>Endocrine</h2><small>{shortTime(requested.start)} → {shortTime(requested.end)}</small></div>
      <button type="button" disabled={loading || guarded} onClick={() => void onRefresh().catch(() => {})}>Refresh evidence</button>
    </header>
    {!confirmed && <p role="status">{loading ? 'Loading patient evidence…' : 'Patient evidence is unconfirmed.'}{error && ' ' + error}</p>}
    <div className="m14-tabs" role="tablist" aria-label="Endocrine workspace">
      {tabs.map((label, index) => <button key={label} id={tabId + index} type="button" role="tab"
        aria-selected={tab === index} aria-controls={tabId + '-panel'} tabIndex={tab === index ? 0 : -1}
        onClick={() => setTab(index)} onKeyDown={event => {
          const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length :
            event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length :
            event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
          if (next !== null) { event.preventDefault(); selectTab(next); }
        }}>{label}</button>)}
    </div>
    <div id={tabId + '-panel'} role="tabpanel" aria-labelledby={tabId + tab}>
      {tab === 0 && <section className="m14-card">
        <h3>Bedside summary</h3>
        <div className="m14-grid">
          <div><h4>Latest recorded glucose</h4>
            <p>{confirmed ? model.timeline.some(row => row.kind === 'lab') ? glucoseSummary(model) :
              'No glucose recorded in this period' : 'Evidence unconfirmed'}</p>
            {confirmed && model.trend && <><small>Same specimen type and units · Earlier to latest</small><p className="m14-trend">{model.trend}</p></>}
            <button type="button" onClick={() => selectTab(1)}>Open glucose &amp; insulin</button>
          </div>
          <div><h4>Insulin and nutrition</h4>
            {confirmed ? <>
              <p>{model.latestInsulin ? <>{displayEvent(model.latestInsulin)} · <RecordedTime row={model.latestInsulin}/></> :
                'No confirmed insulin administration or non-delivery event'}</p>
              {model.lastGiven && model.lastGiven !== model.latestInsulin && <small>
                Last confirmed administration · {model.lastGiven.label} · <RecordedTime row={model.lastGiven}/>
              </small>}
              <p>{model.latestFeed ? <>{displayEvent(model.latestFeed)} · <RecordedTime row={model.latestFeed}/></> :
                'No confirmed feeding status'}</p>
            </> : <p>Evidence unconfirmed</p>}
          </div>
          <div><h4>Clinician review</h4>
            <p>{!confirmed ? 'Evidence unconfirmed' : review ? 'Next review ' + review.draft.nextReview :
              saved.reviews.length ? 'Evidence changed · Review needed' : 'Review not recorded'}</p>
            <button type="button" onClick={() => selectTab(3)}>Open review</button>
          </div>
        </div>
      </section>}
      {tab === 1 && confirmed && <fieldset className="m14-readonly" disabled={guarded}><Timeline model={model} open={openSource}/></fieldset>}
      {tab === 2 && confirmed && <fieldset className="m14-readonly" disabled={guarded}><OtherResults model={model} open={openSource}/></fieldset>}
      <div hidden={tab !== 3}>
        <SourcePinnedReview cardClassName="m14-card" key={scopeKey} catalog={catalog} requested={requested} model={model}
          current={confirmed} guarded={guarded} saved={saved} onOpenSource={openSource} onResolveSource={resolveSource}/>
      </div>
    </div>
    {source && !guarded && (source.fact.kind === 'laboratory_report'
      ? <GISource key={key(pin(source))} evidence={source} transport={client} current={sourceIsCurrent} onClose={closeSource}/>
      : <EndocrineSource key={key(pin(source))} source={source} client={client}
        current={sourceIsCurrent} confirmed={confirmed} onClose={closeSource}/>)}
  </section>;
}
