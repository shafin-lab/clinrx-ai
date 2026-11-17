import {useEffect, useId, useRef, useState} from 'react';
import {key, pin, type Evidence, type RF2Client} from '../api/rf2Client';
import {sourceStatus, text} from '../neurological/model';
import {asObject} from '../respiratory/respiratoryModel';
import {displayEvent, endocrineEvent} from './model';

function Details({source}: {source: Evidence}) {
  const event = endocrineEvent(source.superseded ? {...source, superseded: false} : source);
  const status = sourceStatus(source);
  const actor = text(asObject(source.fact.provenance).actor);
  const note = text(source.fact.narrative);
  return <>
    <p>{[event?.time, status].filter(Boolean).join(' · ')}</p>
    {source.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
    {actor && <p>Recorded by {actor}</p>}
    {event && <p>{displayEvent(event)}</p>}
    {note && <p>{note}</p>}
    {typeof source.fact.correction_reason === 'string' && <p>Correction reason · {source.fact.correction_reason}</p>}
  </>;
}

export function EndocrineSource({source, client, current, confirmed, onClose}: {
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

  const title = text(source.fact.title) || (source.fact.kind === 'medication_order' ? 'Insulin order' : 'Insulin administration');
  return <dialog ref={dialog} aria-labelledby={id} onCancel={event => { event.preventDefault(); close(); }}>
    <header className="m14-heading">
      <h2 id={id}>{title}</h2>
      <button type="button" onClick={close}>Close source</button>
    </header>
    {!current && <p role="status">{confirmed ? 'Historical source revision' : 'Current evidence is unconfirmed.'}</p>}
    <p>{source.fact.id} · Revision {source.fact.revision}</p>
    {source.fact.record_status === 'withdrawn'
      ? <details><summary>Withdrawn source content</summary><Details source={source}/></details>
      : <Details source={source}/>}
    <h3>Recorded versions</h3>
    {failed && <p role="alert">Source history could not be confirmed. The selected revision is still available.</p>}
    {!history && !failed && <p role="status">Loading source history…</p>}
    {history?.map(version => <article key={key(pin(version))}>
      <h4>Version {version.fact.revision} · {version.superseded ? 'Superseded' : 'Latest at this cutoff'}</h4>
      <Details source={version}/>
      <details><summary>Complete original revision</summary><pre>{JSON.stringify(version.fact, null, 2)}</pre></details>
    </article>)}
    <details><summary>Exact source identity, timing &amp; provenance</summary>
      <pre>{JSON.stringify({reference: pin(source), source: source.fact.source_identity, patient: source.fact.binding,
        time: source.fact.times ?? source.fact.time, provenance: source.fact.provenance}, null, 2)}</pre>
    </details>
  </dialog>;
}
