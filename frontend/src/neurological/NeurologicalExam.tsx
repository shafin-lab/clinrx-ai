import {key, pin, type Evidence} from '../api/rf2Client';
import {asObject} from '../respiratory/respiratoryModel';
import {hasRecordedContent, medicationName, medicationsByExam, occurredAt, sourceNarrative, sourceStatus, sourceTime, text} from './model';

export type OpenSource = (source: Evidence, trigger: HTMLButtonElement) => void;

function component(label: string, value: unknown, reason = '') {
  if (value === 'untestable') return label + '-NT' + (reason ? ' (' + reason + ')' : '');
  return typeof value === 'number' ? label + value : label + ' not recorded';
}

export function examScale(source: Evidence) {
  const exam = asObject(source.fact.exam);
  return [component('E', exam.eye), component('V', exam.verbal, text(exam.verbal_reason)), component('M', exam.motor)].join(' / ');
}

export function rassText(source: Evidence) {
  const rass = asObject(source.fact.exam).rass;
  return typeof rass === 'number' ? String(rass).replace('-', '−') : 'not recorded';
}

export function ExamFindings({source}: {source: Evidence}) {
  if (!hasRecordedContent(source)) return <p>{sourceStatus(source)}</p>;
  const exam = asObject(source.fact.exam);
  return <>
    <p><strong>GCS {examScale(source)}</strong> · RASS {rassText(source)}</p>
    <p><strong>Pupils</strong> · {text(exam.pupils) || 'Not recorded'}</p>
    {source.fact.conflict === 'unresolved' && <p>Unresolved source conflict</p>}
    <p>{sourceNarrative(source)}</p>
  </>;
}

export function MedicationObservation({source, onOpenSource}: {source: Evidence; onOpenSource: OpenSource}) {
  const medication = asObject(source.fact.medication);
  const name = medicationName(source) || text(source.fact.title);
  const status = hasRecordedContent(source) && source.fact.conflict !== 'unresolved'
    ? text(medication.status) || 'status unknown' : [sourceStatus(source),
      source.fact.conflict === 'unresolved' ? 'Unresolved source conflict' : ''].filter(Boolean).join(' · ');
  return <li>
    <span><strong>{name} · {status}</strong> · {sourceTime(source)}</span>
    <button type="button" className="m13-link" onClick={event => onOpenSource(source, event.currentTarget)}>Open medication source</button>
  </li>;
}

export function ExamMedicationContext({exam, medications, onOpenSource}: {
  exam: Evidence; medications: Evidence[]; onOpenSource: OpenSource;
}) {
  const context = medicationsByExam(medications, occurredAt(exam));
  return <div className="m13-medication-context">
    <h4>Latest documented medication observations at or before this exam</h4>
    {context.length
      ? <><ul>{context.map(source => <MedicationObservation key={key(pin(source))} source={source} onOpenSource={onOpenSource}/>)}</ul>
          <small>Each status applies to its documented observation time.</small></>
      : <p>No timed medication status linked to this exam.</p>}
  </div>;
}

export function NeurologicalExam({exams, medications, onOpenSource}: {
  exams: Evidence[]; medications: Evidence[]; onOpenSource: OpenSource;
}) {
  return <section className="m13-card" aria-label="Serial neurological exam">
    <h3>Serial neurological exam</h3>
    {!exams.length && <p>No neurological exams recorded in this review period.</p>}
    {exams.map(exam => {
      const observedAt = occurredAt(exam);
      const examiner = text(asObject(exam.fact.provenance).actor);
      return <article key={key(pin(exam))}>
        <h4>{text(exam.fact.title) || 'Neurological exam'}</h4>
        <p>{observedAt ? <time dateTime={observedAt}>{observedAt}</time> : sourceTime(exam)}
          {examiner && ' · ' + examiner} · {sourceStatus(exam)}</p>
        <ExamFindings source={exam}/>
        <button type="button" onClick={event => onOpenSource(exam, event.currentTarget)}>Open exam source</button>
        {hasRecordedContent(exam) && <ExamMedicationContext exam={exam} medications={medications} onOpenSource={onOpenSource}/>}
      </article>;
    })}
  </section>;
}
