import {useEffect, useId, useRef, useState} from 'react';
import {key, pin, type Evidence, type RF2Client} from '../api/rf2Client';
import {sourceStatus, sourceTime, text} from '../neurological/model';
import {asObject} from '../respiratory/respiratoryModel';
import {woundCategory, woundMeasurements, woundStatus, woundTime, woundTitle} from './model';

export function WoundDetails({source}: {source: Evidence}) {
  const fact = source.fact;
  const notes = text(fact.narrative);
  const fields = [text(fact.site), text(fact.stage), woundMeasurements(source), text(fact.dressing), text(fact.action)];
  return <>
    {fields.some(Boolean) && <p>{fields.filter(Boolean).join(' · ')}</p>}
    {notes && !fields.includes(notes) && <p>{notes}</p>}
  </>;
}

function SourceDetails({source}: {source: Evidence}) {
  const actor = text(asObject(source.fact.provenance).actor);
  const status = woundStatus(source.superseded ? {...source, superseded: false} : source);
  return <>
    <p>{woundCategory(source)} · {woundTime(source)} · {sourceStatus(source)}</p>
    <p>Reported {sourceTime(source, 'reported')} · Available {sourceTime(source, 'available')}</p>
    {actor && <p>Recorded by {actor}</p>}
    {status && <p>{status}</p>}
    {source.fact.record_status === 'withdrawn' || source.fact.report_status === 'withdrawn'
      ? <details><summary>Withdrawn source content</summary><WoundDetails source={source}/></details>
      : <WoundDetails source={source}/>}
    {typeof source.fact.correction_reason === 'string' && <p>Correction reason · {source.fact.correction_reason}</p>}
  </>;
}

export function WoundSource({source, client, current, confirmed, onClose}: {
  source: Evidence;
  client: Pick<RF2Client, 'history'>;
  current: boolean;
  confirmed: boolean;
  onClose: () => void;
}) {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const [history, setHistory] = useState<Evidence[]>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (!dialog.current?.open) dialog.current?.showModal();
    void client.history(source).then(records => {
      if (active) setHistory(records);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [source, client]);

  function close() {
    dialog.current?.close();
    onClose();
  }

  return <dialog ref={dialog} aria-labelledby={id} onCancel={event => { event.preventDefault(); close(); }}>
    <header className="wound-heading">
      <h2 id={id}>{woundTitle(source)}</h2>
      <button type="button" onClick={close}>Close source</button>
    </header>
    {!current && <p role="status">{confirmed ? 'Historical source revision' : 'Current evidence is unconfirmed.'}</p>}
    <p>{source.fact.id} · Revision {source.fact.revision}</p>
    <SourceDetails source={source}/>
    <h3>Recorded versions</h3>
    {failed && <p role="alert">Source history could not be confirmed. The selected revision is still available.</p>}
    {!history && !failed && <p role="status">Loading source history…</p>}
    {history?.map(version => <article key={key(pin(version))}>
      <h4>Version {version.fact.revision} · {version.superseded ? 'Superseded' : 'Latest at this cutoff'}</h4>
      <SourceDetails source={version}/>
      <details><summary>Complete original revision</summary><pre>{JSON.stringify(version.fact, null, 2)}</pre></details>
    </article>)}
    <details><summary>Exact source identity, timing &amp; provenance</summary>
      <pre>{JSON.stringify({reference: pin(source), source: source.fact.source_identity, patient: source.fact.binding,
        time: source.fact.times, provenance: source.fact.provenance, conflict: source.fact.conflict,
      }, null, 2)}</pre>
    </details>
  </dialog>;
}
