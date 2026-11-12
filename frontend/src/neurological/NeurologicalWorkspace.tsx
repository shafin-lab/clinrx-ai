import {useId, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {key, pin, RF2Client, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import {GISource} from '../gastrointestinal/GISource';
import {ExamFindings, ExamMedicationContext, examScale, MedicationObservation, NeurologicalExam, rassText, type OpenSource} from './NeurologicalExam';
import {NeurologicalReview, useNeurologicalReview} from './NeurologicalReview';
import {NeurologicalSource} from './NeurologicalSource';
import {administrationText, neurologicalModel, occurredAt, sourceNarrative, sourceStatus, sourceTime, text, type NeurologicalScope} from './model';
import '../gastrointestinal/gastrointestinal.css';
import './neurological.css';

const tabs = ['Overview', 'Serial exam', 'Results & imaging', 'Review & plan'] as const;
type Model = ReturnType<typeof neurologicalModel>;
interface SharedProps {
  catalog?: Catalog;
  requested: NeurologicalScope;
  current: boolean;
}

function examSummary(model: Model) {
  if (model.latest) return 'GCS ' + examScale(model.latest) + ' · RASS ' + rassText(model.latest) + ' · ' + sourceTime(model.latest);
  return model.exams.length ? 'Latest exam unconfirmed' : 'No exam recorded in this period';
}

export function NeurologicalSummary({catalog, requested, current, onOpen}: SharedProps & {onOpen: () => void}) {
  const model = useMemo(() => neurologicalModel(catalog, requested), [catalog, requested]);
  const saved = useNeurologicalReview(model.valid ? catalog : undefined, requested);
  if (!model.sources.length) return null;
  const review = current ? saved.reviews.find(model.matches) : undefined;
  const reviewState = review ? ' · Review due ' + review.draft.nextReview : saved.reviews.length ? ' · Review needed' : '';
  return <section className="m13-summary" aria-label="Neurological summary">
    <div>
      <h3>Neurological system</h3>
      <p>{current ? examSummary(model) + reviewState : 'Evidence unconfirmed'}</p>
    </div>
    <button type="button" onClick={onOpen}>Open neurological workspace</button>
  </section>;
}

function SourceButton({source, onOpenSource, children}: {
  source: Evidence; onOpenSource: OpenSource; children: string;
}) {
  return <button type="button" onClick={event => onOpenSource(source, event.currentTarget)}>{children}</button>;
}

function ImagingReport({source, onOpenSource}: {source: Evidence; onOpenSource: OpenSource}) {
  return <article>
    <h4>{text(source.fact.title) || 'Imaging report'}</h4>
    <p>{sourceTime(source)} · {sourceStatus(source)}</p>
    <p>{sourceNarrative(source)}</p>
    {source.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
    <SourceButton source={source} onOpenSource={onOpenSource}>Open imaging report</SourceButton>
  </article>;
}

function Results({model, onOpenSource}: {model: Model; onOpenSource: OpenSource}) {
  return <>
    <section className="m13-card">
      <h3>Laboratory results</h3>
      {model.labs.length ? <table className="m13-laboratory">
        <thead><tr><th scope="col">Test</th><th scope="col">Recorded result</th><th scope="col">Specimen collection</th><th scope="col">Source</th></tr></thead>
        <tbody>{model.labs.map(row => <tr key={key(pin(row.source)) + row.component}>
          <th scope="row">{row.label}</th>
          <td>{row.value}{row.qualifications.map(item => <small key={item}>{item}</small>)}</td>
          <td>{row.collection.instant
            ? <time dateTime={row.collection.instant}>{row.collection.text}</time>
            : row.collection.text}</td>
          <td><small>{sourceStatus(row.source)}</small><SourceButton source={row.source} onOpenSource={onOpenSource}>Open lab report</SourceButton></td>
        </tr>)}</tbody>
      </table> : <p>No relevant mapped laboratory results in this review period.</p>}
    </section>
    <section className="m13-card">
      <h3>Imaging reports</h3>
      {model.imaging.length ? model.imaging.map(source =>
        <ImagingReport key={key(pin(source))} source={source} onOpenSource={onOpenSource}/>) : <p>No linked imaging reports in this review period.</p>}
    </section>
  </>;
}

function MedicationTimeline({model, onOpenSource}: {model: Model; onOpenSource: OpenSource}) {
  const uncertainAdministration = model.administrations.some(source => source.fact.conflict === 'unresolved');
  return <section className="m13-card">
    <h3>Sedation &amp; medication context</h3>
    {model.medications.length ? <details>
      <summary>Medication status history</summary>
      <p>Each status applies to its documented observation time.</p>
      <ul className="m13-medications">{model.medications.map(source =>
        <MedicationObservation key={key(pin(source))} source={source} onOpenSource={onOpenSource}/>)}</ul>
    </details> : <p>No linked medication status observations in this review period.</p>}
    {!!model.administrations.length && <details>
      <summary>{uncertainAdministration ? 'Administration records' : 'Completed administrations'}</summary>
      <ul>{model.administrations.map(source => <li key={key(pin(source))}>
        <p><strong>{administrationText(source)}</strong> · {sourceTime(source)}</p>
        {source.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
        <SourceButton source={source} onOpenSource={onOpenSource}>Open administration record</SourceButton>
      </li>)}</ul>
    </details>}
  </section>;
}

export function NeurologicalWorkspace({catalog, requested, current, loading, error, onRefresh, guarded = false}: SharedProps & {
  loading: boolean;
  error?: string;
  onRefresh: () => Promise<void>;
  guarded?: boolean;
}) {
  const model = useMemo(() => neurologicalModel(catalog, requested), [catalog, requested]);
  const [tab, setTab] = useState<typeof tabs[number]>('Overview');
  const [selected, setSelected] = useState<{source: Evidence; identity: string}>();
  const trigger = useRef<HTMLButtonElement>(null);
  const sourceRequest = useRef(0);
  const [client] = useState(() => new RF2Client());
  const tabPrefix = useId();
  const tabIndex = tabs.indexOf(tab);
  const confirmed = current && !loading && model.valid;
  const saved = useNeurologicalReview(model.valid ? catalog : undefined, requested);
  const review = confirmed ? saved.reviews.find(model.matches) : undefined;
  const scopeKey = JSON.stringify([catalog?.repository, requested.patient, requested.encounter, requested.start, requested.end]);
  const source = model.valid && selected?.identity === scopeKey ? selected.source : undefined;
  const sourceIsCurrent = confirmed && !!source && model.sources.some(evidence => key(pin(evidence)) === key(pin(source)) &&
    evidence.digest === source.digest && evidence.ingestion.ingestion_sequence === source.ingestion.ingestion_sequence);

  useLayoutEffect(() => () => { sourceRequest.current++; }, [confirmed, scopeKey]);

  function openSource(source: Evidence, button: HTMLButtonElement) {
    sourceRequest.current++;
    trigger.current = button;
    setSelected({source, identity: scopeKey});
  }

  async function resolveReviewedSource(exact: Pin, button: HTMLButtonElement) {
    if (!confirmed || exact.repository !== catalog?.repository) return;
    const request = ++sourceRequest.current;
    try {
      const [result] = await client.resolve(exact.repository, [exact]);
      if (request !== sourceRequest.current || !button.isConnected) return;
      const target = result.fact.binding.target;
      if (target.patient_id !== requested.patient || target.encounter_id !== requested.encounter) {
        throw new Error('Wrong encounter');
      }
      openSource(result, button);
    } catch (error) {
      if (request === sourceRequest.current) throw error;
    }
  }

  function closeSource() {
    sourceRequest.current++;
    setSelected(undefined);
    if (trigger.current?.isConnected) trigger.current.focus();
  }

  function changeTab(index: number) {
    setTab(tabs[index]);
    document.getElementById(tabPrefix + index)?.focus();
  }

  return <section className="m13-workspace" aria-label="Neurological system">
    <header className="m13-heading">
      <div><h2>Neurological system</h2><small>{requested.start} → {requested.end}</small></div>
      <button type="button" disabled={loading} onClick={() => void onRefresh().catch(() => {})}>Refresh evidence</button>
    </header>
    {!confirmed && <p role="status">{loading ? 'Loading patient evidence…' : 'Patient evidence is unconfirmed.'}{error && ' ' + error}</p>}
    <div className="m13-tabs" role="tablist" aria-label="Neurological workspace">
      {tabs.map((label, index) => <button key={label} id={tabPrefix + index} type="button" role="tab"
        aria-selected={tab === label} aria-controls={tabPrefix + '-panel'} tabIndex={tab === label ? 0 : -1}
        onClick={() => setTab(label)}
        onKeyDown={event => {
          const target = event.key === 'ArrowRight' ? (index + 1) % tabs.length :
            event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length :
            event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
          if (target !== null) {
            event.preventDefault();
            changeTab(target);
          }
        }}>{label}</button>)}
    </div>
    <div id={tabPrefix + '-panel'} role="tabpanel" aria-labelledby={tabPrefix + tabIndex}>
      {tab === 'Overview' && <section className="m13-card">
        <h3>Bedside summary</h3>
        <div className="m13-grid">
          <div>
            <h4>Latest exam</h4>
            {confirmed && model.latest ? <>
              <p>{sourceTime(model.latest)} · {sourceStatus(model.latest)}</p>
              <ExamFindings source={model.latest}/>
              <SourceButton source={model.latest} onOpenSource={openSource}>Open exam source</SourceButton>
              <ExamMedicationContext exam={model.latest} medications={model.medications} onOpenSource={openSource}/>
            </> : <p>{confirmed ? examSummary(model) : 'Evidence unconfirmed'}</p>}
          </div>
          <div>
            <h4>Results &amp; imaging</h4>
            {confirmed && model.imaging[0] && <ImagingReport source={model.imaging[0]} onOpenSource={openSource}/>}
            {confirmed && !!model.labs.length && <ul>{model.labs.slice(0, 4).map(row =>
              <li key={key(pin(row.source)) + row.component}>
                <strong>{row.label}</strong> {row.value} · {row.collection.text}
                {row.qualifications.map(item => <small key={item}>{item}</small>)}
              </li>)}</ul>}
            <button type="button" onClick={() => changeTab(2)}>Open results &amp; imaging</button>
          </div>
          <div>
            <h4>Clinician review</h4>
            {review ? <><p>{review.draft.rationale}</p><small>{review.draft.reviewer} · Next review {review.draft.nextReview}</small></>
              : <p>{!confirmed ? 'Evidence unconfirmed' : saved.reviews.length ? 'Evidence changed · Review needed' : 'Review not recorded'}</p>}
            <button type="button" onClick={() => changeTab(3)}>Open review</button>
          </div>
        </div>
      </section>}
      {tab === 'Serial exam' && confirmed && <>
        <NeurologicalExam exams={model.exams} medications={model.medications} onOpenSource={openSource}/>
        <MedicationTimeline model={model} onOpenSource={openSource}/>
      </>}
      {tab === 'Results & imaging' && confirmed && <Results model={model} onOpenSource={openSource}/>}
      <div hidden={tab !== 'Review & plan'}>
        <NeurologicalReview key={scopeKey} catalog={catalog} requested={requested} model={model}
          current={confirmed} guarded={guarded} saved={saved} onOpenSource={openSource} onResolveSource={resolveReviewedSource}/>
      </div>
    </div>
    {source?.fact.kind === 'laboratory_report' && <GISource evidence={source} transport={client} current={sourceIsCurrent} onClose={closeSource}/>}
    {source && source.fact.kind !== 'laboratory_report' && <NeurologicalSource key={key(pin(source))} source={source}
      client={client} current={sourceIsCurrent} historical={confirmed && !sourceIsCurrent || source.superseded} onClose={closeSource}/>}
  </section>;
}
