import {useLayoutEffect, useRef, useState} from 'react';
import {RF2Client, key, pin, stable, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import {SourcePinnedReview, useSourcePinnedReview} from '../clinical/SourcePinnedReview';
import '../endocrine/endocrine.css';
import {GISource} from '../gastrointestinal/GISource';
import {laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryResultText} from '../gastrointestinal/laboratoryPresentation';
import {hasRecordedContent, sourceTime, sourceNarrative, sourceStatus} from '../neurological/model';
import {asObject} from '../respiratory/respiratoryModel';
import {catalogModel, savedPin, type Requested} from './catalogModel';
import './nutrition.css';

const tabs = ['Overview', 'Assessment & targets', 'Support & intake', 'Tolerance & review'] as const;
const groups = {
  'Assessment & targets': ['assessment', 'target'],
  'Support & intake': ['order', 'intake'],
  'Tolerance & review': ['tolerance', 'nutrition'],
};
type Draft = {reviewer: string; rationale: string; nextReview: string; plan: string};
type Transport = Pick<RF2Client, 'history' | 'resolve'>;

export function NutritionSummary({catalog, requested, current, guarded, onOpen}: {
  catalog?: Catalog; requested: Requested; current: boolean; guarded: boolean; onOpen: () => void;
}) {
  const model = catalogModel(catalog, requested);
  const saved = useSourcePinnedReview('M17', model.valid ? catalog : undefined, requested);
  if (!model.sources.length && !saved.reviews.length) return null;
  const review = current ? saved.reviews.find(model.matches) : undefined;
  const status = review ? 'Next review ' + review.draft.nextReview : saved.reviews.length ? 'Review needed' : '';
  return <section className="m17-card" aria-label="Nutrition summary">
    <div><h3>Nutrition</h3><p>{current && model.valid ? [model.records.length + ' linked nutrition records', status].filter(Boolean).join(' · ') : 'Evidence unconfirmed'}</p></div>
    <button type="button" disabled={guarded} onClick={onOpen}>Open Nutrition</button>
  </section>;
}

export function CatalogNutritionWorkspace({catalog, requested, current, guarded, transport}: {
  catalog?: Catalog; requested: Requested; current: boolean; guarded: boolean; transport?: Transport;
}) {
  const model = catalogModel(catalog, requested);
  const confirmed = current && model.valid;
  const saved = useSourcePinnedReview('M17', model.valid ? catalog : undefined, requested);
  const latest = confirmed && saved.reviews.find(model.matches);
  const [tab, setTab] = useState<typeof tabs[number]>('Overview');
  const [source, setSource] = useState<{evidence: Evidence; identity: string}>();
  const [client] = useState(() => transport ?? new RF2Client());
  const trigger = useRef<HTMLButtonElement>(null);
  const pending = useRef(0);
  const snapshot = useRef('');
  const identity = model.identity;
  useLayoutEffect(() => {
    snapshot.current = confirmed && !guarded ? identity : '';
    return () => { snapshot.current = ''; pending.current++; };
  }, [identity, confirmed, guarded]);

  function open(evidence: Evidence, button: HTMLButtonElement) {
    pending.current++;
    trigger.current = button;
    setSource({evidence, identity});
  }

  async function resolve(exact: Pin, button: HTMLButtonElement) {
    const token = ++pending.current;
    if (!catalog || snapshot.current !== identity ||
      !savedPin({...exact, kind: exact.reference.kind, id: exact.reference.id, version: exact.reference.version},
        catalog.repository, catalog.cutoff.fact_watermark)) throw Error('Unconfirmed source');
    const [evidence] = await client.resolve(catalog.repository, [exact]);
    if (token !== pending.current || snapshot.current !== identity || !button.isConnected) return;
    const target = evidence?.fact.binding.target;
    if (!evidence || target?.patient_id !== requested.patient || target.encounter_id !== requested.encounter ||
      stable(pin(evidence)) !== stable(exact)) throw Error('Exact revision unavailable');
    open(evidence, button);
  }

  const records = tab === 'Overview' ? model.records :
    model.records.filter(record => groups[tab].includes(String(record.fact.category)));
  function sourceButton(evidence: Evidence) {
    return <button type="button" onClick={event => open(evidence, event.currentTarget)}>Open source · Revision {evidence.fact.revision}</button>;
  }
  return <section className="m17-workspace" aria-label="Nutrition">
    <h2>Nutrition</h2>
    {!confirmed && <p role="status">Shared patient evidence is unconfirmed.</p>}
    <nav aria-label="M17 workspace">{tabs.map(label =>
      <button key={label} type="button" aria-current={tab === label ? 'page' : undefined}
        onClick={() => setTab(label)}>{label}</button>)}</nav>
    <section className="m17-card">
      <h3>{tab === 'Overview' ? 'Bedside summary' : tab}</h3>
      {latest && <p>{latest.draft.reviewer} · Next review {latest.draft.nextReview}</p>}
      {!records.length && <p>No linked findings for this view.</p>}
      {records.map(evidence => <article key={key(pin(evidence))}>
        <h4>{String(evidence.fact.title)}</h4>
        <p>{sourceTime(evidence)} · {sourceStatus(evidence)}</p>
        <p>{sourceNarrative(evidence)}</p>
        {sourceButton(evidence)}
      </article>)}
      {tab === 'Tolerance & review' && <section>
        <h4>Shared laboratory results</h4>
        {!model.labs.length && <p>No linked electrolyte or glucose results.</p>}
        {model.labs.map(evidence => <article key={key(pin(evidence))}>
          <h4>{String(asObject(evidence.fact.source_panel).raw_display ?? 'Laboratory report')}</h4>
          <p>{laboratoryCollection(evidence.fact).text} · {sourceStatus(evidence)}</p>
          {hasRecordedContent(evidence) && Array.isArray(evidence.fact.components) &&
            evidence.fact.components.map((raw, index) => {
              const component = asObject(raw);
              return <p key={index}>{String(asObject(component.test_code).raw_display ?? 'Result')} · {laboratoryResultText(component)}</p>;
            })}
          {sourceButton(evidence)}
        </article>)}
      </section>}
    </section>
    <div hidden={tab !== 'Tolerance & review'}>
      <SourcePinnedReview cardClassName="m17-card" catalog={catalog} requested={requested} model={model} current={confirmed} guarded={guarded}
        saved={saved} onOpenSource={open} onResolveSource={resolve}/>
    </div>
    {source?.identity === identity && <GISource key={key(pin(source.evidence))} evidence={source.evidence}
      current={confirmed && model.sources.some(row => key(pin(row)) === key(pin(source.evidence)) && row.digest === source.evidence.digest)}
      transport={client} onClose={() => { setSource(undefined); requestAnimationFrame(() => trigger.current?.focus()); }}/>}
  </section>;
}
