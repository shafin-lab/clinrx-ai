import {useId, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {key, pin, RF2Client, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import {SourcePinnedReview, useSourcePinnedReview} from '../clinical/SourcePinnedReview';
import {occurredAt, text} from '../neurological/model';
import {chartContentAvailable, shortWoundTime, woundCategory, woundMeasurements, woundModel, woundStatus, woundTime,
  woundTitle, type WoundModel, type WoundScope} from './model';
import {WoundDetails, WoundSource} from './WoundSource';
import './woundCare.css';

interface SharedProps {
  catalog?: Catalog;
  requested: WoundScope;
  current: boolean;
  guarded?: boolean;
}

const tabs = ['Bedside summary', 'Review & plan'] as const;
type OpenSource = (source: Evidence, trigger: HTMLButtonElement) => void;
type Wound = WoundModel['wounds'][number];

function latestFinding(wound: Wound) {
  if (!wound.latest || !chartContentAvailable(wound.latest)) return 'Latest assessment unconfirmed';
  const source = wound.latest;
  return [text(source.fact.site), woundMeasurements(source), text(source.fact.stage), woundTime(source),
    woundStatus(source)].filter(Boolean).join(' · ');
}

export function WoundSummary({catalog, requested, current, guarded, onOpen}: SharedProps & {onOpen: () => void}) {
  const model = useMemo(() => woundModel(catalog, requested), [catalog, requested]);
  const saved = useSourcePinnedReview('M15', model.valid ? catalog : undefined, requested);
  if (!model.sources.length && !saved.reviews.length) return null;
  const review = current ? saved.reviews.find(model.matches) : undefined;
  return <section className="wound-overview" aria-label="Wound care summary">
    <div>
      <h3>Skin, Wounds and Pressure Care</h3>
      {current ? <>
        {model.wounds.length ? model.wounds.map(wound => <p key={wound.id}>
          {wound.id} · {latestFinding(wound)}
          {wound.lastDressing && chartContentAvailable(wound.lastDressing) && ' · ' + woundTitle(wound.lastDressing)}
          {review ? ' · Next review ' + review.draft.nextReview : saved.reviews.length ? ' · Review needed' : ''}
        </p>) : <p>{model.pressureCare.length
          ? 'Pressure-care actions recorded' : 'No identified wound assessment in this period'}
          {review ? ' · Next review ' + review.draft.nextReview : saved.reviews.length ? ' · Review needed' : ''}</p>}
      </> : <p>Evidence unconfirmed</p>}
    </div>
    <button type="button" disabled={guarded} onClick={onOpen}>Open wound care</button>
  </section>;
}

function RecordTime({source}: {source: Evidence}) {
  const occurred = occurredAt(source);
  return occurred ? <time dateTime={occurred}>{woundTime(source)}</time> : woundTime(source);
}

function TimelineRows({sources, open}: {sources: Evidence[]; open: OpenSource}) {
  return <ol className="wound-timeline">
    {sources.map(source => {
      const status = woundStatus(source);
      const wound = text(source.fact.wound_id);
      return <li key={key(pin(source))}>
        <small><RecordTime source={source}/> · {woundCategory(source)}{wound && ' · Wound ' + wound}</small>
        <h4>{woundTitle(source)}</h4>
        {status && <p>{status}</p>}
        {chartContentAvailable(source) && <WoundDetails source={source}/>}
        <button type="button" aria-label={'Open source for ' + woundTitle(source)}
          onClick={event => open(source, event.currentTarget)}>Open source</button>
      </li>;
    })}
  </ol>;
}

export function WoundWorkspace({catalog, requested, current, guarded = false, loading, error, onRefresh}: SharedProps & {
  loading: boolean;
  error?: string;
  onRefresh: () => Promise<void>;
}) {
  const model = useMemo(() => woundModel(catalog, requested), [catalog, requested]);
  const [tab, setTab] = useState(0);
  const [selected, setSelected] = useState<{source: Evidence; scope: string}>();
  const trigger = useRef<HTMLButtonElement>(null);
  const sourceRequest = useRef(0);
  const [client] = useState(() => new RF2Client());
  const tabId = useId();
  const confirmed = current && !loading && model.valid;
  const saved = useSourcePinnedReview('M15', model.valid ? catalog : undefined, requested);
  const review = confirmed ? saved.reviews.find(model.matches) : undefined;
  const scope = JSON.stringify([catalog?.repository, requested.patient, requested.encounter, requested.start, requested.end]);
  const source = model.valid && selected?.scope === scope ? selected.source : undefined;
  const sourceIsCurrent = confirmed && !!source && model.pins.some(value => value.kind === source.fact.kind &&
    value.id === source.fact.id && value.version === source.fact.revision && value.digest === source.digest &&
    value.ingestion === source.ingestion.ingestion_sequence);

  useLayoutEffect(() => () => { sourceRequest.current++; }, [confirmed, guarded, scope]);

  function openSource(evidence: Evidence, button: HTMLButtonElement) {
    if (guarded) return;
    sourceRequest.current++;
    trigger.current = button;
    setSelected({source: evidence, scope});
  }

  async function resolveSource(exact: Pin, button: HTMLButtonElement) {
    if (!confirmed || guarded || exact.repository !== catalog?.repository || exact.reference.kind !== 'wound_record') return;
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

  return <section className="wound-workspace" aria-label="Skin, Wounds and Pressure Care">
    <header className="wound-heading">
      <div><h2>Skin, Wounds and Pressure Care</h2>
        <small>{shortWoundTime(requested.start)} → {shortWoundTime(requested.end)}</small></div>
      <button type="button" disabled={loading || guarded} onClick={() => void onRefresh().catch(() => {})}>Refresh evidence</button>
    </header>
    {!confirmed && <p role="status">{loading ? 'Loading patient evidence…' : 'Wound evidence is unconfirmed.'}{error && ' ' + error}</p>}
    <div className="wound-tabs" role="tablist" aria-label="Wound care workspace">
      {tabs.map((label, index) => <button key={label} id={tabId + index} type="button" role="tab"
        aria-selected={tab === index} aria-controls={tabId + '-panel'} tabIndex={tab === index ? 0 : -1}
        onClick={() => setTab(index)} onKeyDown={event => {
          const next = event.key === 'ArrowRight' || event.key === 'ArrowLeft' ? (index + 1) % tabs.length :
            event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
          if (next !== null) { event.preventDefault(); selectTab(next); }
        }}>{label}</button>)}
    </div>
    <div id={tabId + '-panel'} role="tabpanel" aria-labelledby={tabId + tab}>
      {tab === 0 && confirmed && <>
        <div className="wound-grid">
          <section className="wound-card">
            <h3>Latest wound assessments</h3>
            {!model.wounds.length && <p>No identified wound assessment in this period.</p>}
            {model.wounds.map(wound => <p key={wound.id}><strong>{wound.id}</strong> · {latestFinding(wound)}</p>)}
          </section>
          <section className="wound-card">
            <h3>Pressure care</h3>
            {model.pressureCare.length ? model.pressureCare.slice(-2).map(event => <p key={key(pin(event))}>
              {text(event.fact.action) || woundTitle(event)} · <RecordTime source={event}/>
            </p>) : <p>No confirmed pressure-care actions in this period.</p>}
          </section>
          <section className="wound-card">
            <h3>Clinician review</h3>
            <p>{review ? 'Next review ' + review.draft.nextReview :
              saved.reviews.length ? 'Evidence changed · Review needed' : 'Review not recorded'}</p>
            <button type="button" onClick={() => selectTab(1)}>Open review</button>
          </section>
        </div>
        <section className="wound-card" aria-label="Wound and care timeline">
          <h3>Wound and care timeline</h3>
          {!model.sources.length && <p>No wound or pressure-care records in this period.</p>}
          <fieldset disabled={guarded}>
            {!!model.sources.length && <TimelineRows sources={model.sources} open={openSource}/>}
          </fieldset>
        </section>
      </>}
      <div hidden={tab !== 1}>
        <SourcePinnedReview key={scope} cardClassName="wound-card" catalog={catalog} requested={requested} model={model}
          current={confirmed} guarded={guarded} saved={saved} onOpenSource={openSource} onResolveSource={resolveSource}/>
      </div>
    </div>
    {source && !guarded && <WoundSource key={key(pin(source))} source={source} client={client}
      current={sourceIsCurrent} confirmed={confirmed} onClose={closeSource}/>}
  </section>;
}
