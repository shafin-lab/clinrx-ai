import {useEffect, useRef, useState} from 'react';
import {key, pin, type Evidence, type RF2Client} from '../api/rf2Client';
import {asObject} from '../respiratory/respiratoryModel';
import {ExamFindings} from './NeurologicalExam';
import {administrationText, medicationName, sourceStatus, sourceTime, text} from './model';

function SourceContent({source}: {source: Evidence}) {
  if (source.fact.kind === 'medication_administration') return <p>{administrationText(source)}</p>;
  const view = source.superseded ? {...source, superseded: false} : source;
  if (source.fact.category === 'exam') return <ExamFindings source={view}/>;
  return <>
    {source.fact.category === 'medication_status' &&
      <p>{medicationName(source)} · {text(asObject(source.fact.medication).status)}</p>}
    <p>{text(source.fact.narrative)}</p>
  </>;
}

export function NeurologicalSource({source, client, current, historical, onClose}: {
  source: Evidence; client: Pick<RF2Client, 'history'>; current: boolean; historical: boolean; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [history, setHistory] = useState<Evidence[]>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (!dialog.current?.open) dialog.current?.showModal();
    heading.current?.focus();
    void client.history(source).then(items => {
      if (active) setHistory(items);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [source, client]);

  function close() {
    dialog.current?.close();
    onClose();
  }

  const administration = source.fact.kind === 'medication_administration';
  const author = text(asObject(source.fact.provenance).actor);
  const title = administration ? 'Medication administration record' : text(source.fact.title);
  return <dialog ref={dialog} aria-labelledby="m13-source-heading" onCancel={event => {
    event.preventDefault();
    close();
  }}>
    <header className="m13-heading">
      <h2 ref={heading} tabIndex={-1} id="m13-source-heading">{title}</h2>
      <button type="button" onClick={close}>Close source</button>
    </header>
    {!current && <p role="status">{historical ? 'Historical source revision' : 'Current evidence is unconfirmed.'}</p>}
    <p>{source.fact.id} · Revision {source.fact.revision}</p>
    <p>{sourceTime(source)}{sourceStatus(source) && ' · ' + sourceStatus(source)}</p>
    {source.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
    {author && <p>Recorded by {author}</p>}
    {!administration && <p>Reported {sourceTime(source, 'reported')} · Available {sourceTime(source, 'available')}</p>}
    {source.fact.record_status === 'withdrawn'
      ? <details><summary>Withdrawn source content</summary><SourceContent source={source}/></details>
      : <SourceContent source={source}/>}
    <section className="m13-history">
      <h3>Recorded versions</h3>
      {!history && !failed && <p role="status">Loading source history…</p>}
      {failed && <p role="alert">Source history could not be confirmed. The selected revision is still available.</p>}
      {history?.map(version => <article key={key(pin(version))}>
        <h4>Version {version.fact.revision} · {version.superseded ? 'Superseded' : 'Latest at this cutoff'}</h4>
        <p>{sourceTime(version)}{sourceStatus(version) && ' · ' + sourceStatus(version)}</p>
        {version.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
        {version.fact.record_status === 'withdrawn'
          ? <details><summary>Withdrawn source content</summary><SourceContent source={version}/></details>
          : <SourceContent source={version}/>}
        {typeof version.fact.correction_reason === 'string' && <p>Correction reason {version.fact.correction_reason}</p>}
        <details><summary>Complete original revision</summary><pre tabIndex={0}>{JSON.stringify(version.fact, null, 2)}</pre></details>
      </article>)}
    </section>
    <details><summary>Exact source identity, timing &amp; provenance</summary>
      <pre tabIndex={0}>{JSON.stringify({
        reference: pin(source), source: source.fact.source_identity, patient: source.fact.binding,
        times: source.fact.times ?? source.fact.time, provenance: source.fact.provenance,
        uncertainty: source.fact.uncertainty, conflict: source.fact.conflict,
      }, null, 2)}</pre>
    </details>
  </dialog>;
}
