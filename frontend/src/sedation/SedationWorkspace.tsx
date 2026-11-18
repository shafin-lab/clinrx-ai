import {useRef, useState} from 'react';
import {key, pin, RF2Client, type Catalog, type Evidence} from '../api/rf2Client';
import {MedicationObservation, rassText} from '../neurological/NeurologicalExam';
import {NeurologicalSource} from '../neurological/NeurologicalSource';
import {hasRecordedContent, neurologicalModel, sourceStatus, sourceTime, type NeurologicalScope} from '../neurological/model';
import '../neurological/neurological.css';

export function SedationWorkspace({catalog, requested, current, loading, error, onRefresh}: {
  catalog?: Catalog;
  requested: NeurologicalScope;
  current: boolean;
  loading: boolean;
  error?: string;
  onRefresh: () => Promise<void>;
}) {
  const model = neurologicalModel(catalog, requested);
  const confirmed = current && !loading && !error && model.valid;
  const [client] = useState(() => new RF2Client());
  const [selected, setSelected] = useState<{source: Evidence; catalog: Catalog; period: string}>();
  const trigger = useRef<HTMLButtonElement>(null);
  const period = JSON.stringify([requested.patient, requested.encounter, requested.start, requested.end]);

  function openSource(source: Evidence, button: HTMLButtonElement) {
    if (!confirmed || !catalog) return;
    trigger.current = button;
    setSelected({source, catalog, period});
  }

  function closeSource() {
    setSelected(undefined);
    trigger.current?.focus();
  }

  return <section className="m13-workspace" aria-label="Pain, sedation and delirium">
    <h2>Pain, sedation and delirium</h2>
    <p>Review period {requested.start} to {requested.end}</p>
    <button type="button" disabled={loading} onClick={() => void onRefresh().catch(() => {})}>Refresh evidence</button>
    {loading && <p role="status">Loading shared evidence…</p>}
    {error && <p role="alert">{error}</p>}
    {!confirmed && !loading && <p role="status">Current evidence is unconfirmed.</p>}
    {confirmed && <>
      <p>Source cutoff {catalog?.cutoff.captured_at} · revision watermark {catalog?.cutoff.fact_watermark}</p>
      <section className="m13-card">
        <h3>Sedation observations</h3>
        {model.exams.length === 0 && <p>No neurological exam evidence in this review period.</p>}
        {model.exams.map(source => {
          const conflicted = source.fact.conflict === 'unresolved';
          const score = hasRecordedContent(source) && !conflicted ? rassText(source) : 'not recorded';
          return <article key={key(pin(source))}>
            <p><strong>{score === 'not recorded' ? 'RASS unavailable' : 'RASS ' + score}</strong> · <span>{sourceTime(source)}</span></p>
            <p>{sourceStatus(source)}{conflicted && ' · Unresolved source conflict'}</p>
            <button type="button" onClick={event => openSource(source, event.currentTarget)}>Open exam source</button>
          </article>;
        })}
        <p>Sedation target unavailable in the shared feed.</p>
      </section>
      <section className="m13-card">
        <h3>Medication status observations</h3>
        {model.medications.length > 0 ? <>
          <p>Each status applies to its documented observation time.</p>
          <ul>{model.medications.map(source =>
            <MedicationObservation key={key(pin(source))} source={source} onOpenSource={openSource}/>)}</ul>
        </> : <p>No neurological medication status evidence in this review period.</p>}
      </section>
    </>}
    <section className="m13-card">
      <h3>Pain and delirium</h3>
      <p>Pain assessment unavailable in the shared feed.</p>
      <p>Delirium assessment and assessability unavailable in the shared feed.</p>
    </section>
    {confirmed && selected && selected.catalog === catalog && selected.period === period &&
      <NeurologicalSource source={selected.source} client={client} current={!selected.source.superseded}
        historical={selected.source.superseded} onClose={closeSource}/>}
  </section>;
}
