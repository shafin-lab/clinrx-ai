import type {ExactRef} from '../api/circulatoryTypes';
import type {DeviceState, RecordedTime} from './deviceHistory';

const refKey = (ref: ExactRef) => JSON.stringify([ref.kind, ref.id, ref.version]);
const refLabel = (ref: ExactRef) => `${ref.id} · revision ${ref.version}`;
const episodeAnchor = (ref: ExactRef) => `device-${encodeURIComponent(refKey(ref))}`;
const statusLabel = (status: string) => status === 'in_place' ? 'in place' : status;

function timeLabel(time: RecordedTime) {
  if (time.lower && time.upper) return `${time.lower} to ${time.upper}`;
  if (!time.value) return 'Time unavailable';
  return time.precision === 'instant' ? time.value : `${time.value} (${time.precision})`;
}

export function DeviceWorkspace({state}: {state: DeviceState}) {
  if (state.status === 'loading') return <p role="status">Loading device and procedure history…</p>;
  if (state.status === 'error') return <p role="alert">Device and procedure history is unavailable.</p>;
  const {episodes, procedures, outputs} = state.history;
  const devices = new Map(episodes.map(episode => [refKey(episode.reference), episode]));
  const unresolved = outputs.filter(link => !link.device || !devices.has(refKey(link.device)));
  function deviceLink(ref: ExactRef) {
    const device = devices.get(refKey(ref));
    return device
      ? <a href={`#${encodeURIComponent(episodeAnchor(ref))}`}>{device.device_type} · {refLabel(ref)}</a>
      : <span>Device reference unresolved · {refLabel(ref)}</span>;
  }
  return <section aria-labelledby="device-workspace-heading">
    <h2 id="device-workspace-heading">Devices, Drains and Procedures</h2>
    <p>Recorded history for this encounter.</p>
    <h3>Procedure history</h3>
    {procedures.length ? <ul>{procedures.map(procedure => <li key={refKey(procedure.reference)}>
      <h4>{procedure.title}</h4>
      <p>{statusLabel(procedure.status)} · {timeLabel(procedure.occurred)}</p>
      {procedure.site && <p>Site · {procedure.site}</p>}
      {procedure.author && <p>Recorded operator · {procedure.author}</p>}
      {procedure.method && <p>Method · {procedure.method}</p>}
      {procedure.complications && <p>Recorded complications · {procedure.complications}</p>}
      {procedure.follow_up && <p>Follow-up · {procedure.follow_up}</p>}
      {procedure.devices.length > 0 && <ul aria-label="Associated device episodes">
        {procedure.devices.map(ref => <li key={refKey(ref)}>{deviceLink(ref)}</li>)}
      </ul>}
      {procedure.reports.length > 0 && <ul aria-label="Source reports">
        {procedure.reports.map(ref => <li key={refKey(ref)}>{refLabel(ref)}</li>)}
      </ul>}
      <details><summary>Procedure source</summary><p>{refLabel(procedure.reference)}</p>
        <p>{procedure.source.namespace} · {procedure.source.identifier} {procedure.source.version}</p>
      </details>
    </li>)}</ul> : <p>No procedure records available.</p>}
    <h3>Device episodes</h3>
    {episodes.length ? <ul>{episodes.map(episode => {
      const linked = outputs.filter(link => link.device && refKey(link.device) === refKey(episode.reference));
      return <li key={refKey(episode.reference)} id={episodeAnchor(episode.reference)}>
        <h4>{episode.device_type} · {episode.reference.id}</h4>
        <p>{statusLabel(episode.status)} · {refLabel(episode.reference)}</p>
        {(episode.site || episode.laterality) && <p>Site · {[episode.laterality, episode.site].filter(Boolean).join(' ')}</p>}
        {episode.indication && <p>Indication · {episode.indication}</p>}
        <p>Inserted · {timeLabel(episode.inserted)}</p>
        {episode.status === 'removed' && <p>Removed · {timeLabel(episode.removed)}</p>}
        {episode.replaces && <p>Replaces {deviceLink(episode.replaces)}</p>}
        {linked.length > 0 && <ul aria-label="Linked drain outputs">
          {linked.map(link => <li key={refKey(link.output)}>{refLabel(link.output)}</li>)}
        </ul>}
        <details><summary>Device source</summary><p>{episode.source.namespace} · {episode.source.identifier} {episode.source.version}</p></details>
      </li>;
    })}</ul> : <p>No device episodes available.</p>}
    {unresolved.length > 0 && <>
      <h3>Unresolved drain-output links</h3>
      <ul>{unresolved.map(link => <li key={refKey(link.output)}>
        {refLabel(link.output)} · {link.device ? deviceLink(link.device) : 'Device reference unavailable'}
      </li>)}</ul>
    </>}
  </section>;
}
