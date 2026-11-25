import {useEffect, useRef, useState} from 'react';
import {RF2Client, key, pin, stable, type Evidence, type Pin} from '../api/rf2Client';
import {SourcePinnedReview, useSourcePinnedReview} from '../clinical/SourcePinnedReview';
import {GISource} from '../gastrointestinal/GISource';
import {sourceTime, sourceStatus} from '../neurological/model';
import {record} from '../demo/evidencePresentation';
import {laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryResultText} from '../gastrointestinal/laboratoryPresentation';
import {microReference, recordSummary} from '../antibioticWorkflow/patientModel';
import {DeviceWorkspace} from '../devices/DeviceWorkspace';
import {transitionLabel, useDischargeModel, words, type Inputs} from './model';
import './discharge.css';

type Props = Inputs & {current: boolean; guarded: boolean};
const tabs = ['Summary', 'Medications', 'Care & follow-up', 'Review & handover'] as const;

export function DischargeSummary(props: Props & {onOpen: () => void}) {
  const model = useDischargeModel(props);
  const saved = useSourcePinnedReview('M21', model.valid ? props.catalog : undefined, props.requested);
  const reviews = saved.reviews.filter(review => review.snapshot.context?.transitionId === model.planId);
  const changed = props.current && model.complete && !!reviews[0] && !model.matches(reviews[0]);
  return <section className="m21-card" aria-label="Discharge and transfer summary">
    <h3>Discharge &amp; transfer</h3>
    {props.current && model.valid && model.planValid ? <>
      <p>{transitionLabel(model.plan!.fact.transition)} · {String(model.plan!.fact.destination)}</p>
      {model.handover ? <p>Recorded handover status · {words(model.handover.fact.state)} · {sourceTime(model.handover)}</p> : <p>Handover not documented.</p>}
      {changed && <p role="status">Transition review needed · Evidence changed.</p>}
      {reviews[0] && !changed && model.complete && <p>Review saved · {reviews[0].draft.reviewer}</p>}
    </> : <p>{model.valid && !model.plans.length ? 'No documented discharge or transfer plan.' : 'Transition evidence unconfirmed.'}</p>}
    <button type="button" disabled={props.guarded} onClick={props.onOpen}>Open Discharge &amp; transfer</button>
  </section>;
}

export function DischargeWorkspace(props: Props & {onRefresh: () => Promise<void>}) {
  const [selectedPlan, setPlan] = useState(() => new URLSearchParams(window.location.search).get('transition') ?? '');
  const model = useDischargeModel(props, selectedPlan);
  const [tab, setTab] = useState<typeof tabs[number]>('Summary');
  const saved = useSourcePinnedReview('M21', model.valid ? props.catalog : undefined, props.requested);
  const reviews = saved.reviews.filter(review => review.snapshot.context?.transitionId === model.planId);
  const confirmed = props.current && model.complete;
  const [client] = useState(() => new RF2Client());
  const [selected, select] = useState<{source: Evidence; identity: string}>();
  const trigger = useRef<HTMLButtonElement>(null);
  const pending = useRef(0);
  const currentIdentity = useRef('');
  useEffect(() => {
    currentIdentity.current = confirmed && !props.guarded ? model.identity : '';
    return () => { currentIdentity.current = ''; pending.current++; };
  }, [confirmed, props.guarded, model.identity]);
  function open(source: Evidence, button: HTMLButtonElement) {
    if (!confirmed || props.guarded) return;
    trigger.current = button;
    select({source, identity: model.identity});
  }
  async function resolve(exact: Pin, button: HTMLButtonElement) {
    const token = ++pending.current;
    const identity = model.identity;
    if (!confirmed || props.guarded || exact.repository !== props.catalog?.repository) throw Error('Evidence unconfirmed');
    const [source] = await client.resolve(exact.repository, [exact]);
    if (token !== pending.current || currentIdentity.current !== identity || !button.isConnected) return;
    if (!source || stable(pin(source)) !== stable(exact) || source.fact.binding.target.patient_id !== props.requested.patient ||
        source.fact.binding.target.encounter_id !== props.requested.encounter) throw Error('Exact source unavailable');
    open(source, button);
  }
  function evidence(source: Evidence) {
    const fact = source.fact;
    const components = Array.isArray(fact.components) ? fact.components : [];
    return <article key={key(pin(source))}>
      <h4>{String(fact.title ?? record(fact.source_panel).raw_display ?? fact.concept_id ?? fact.kind)}</h4>
      <p>{fact.kind === 'laboratory_report' ? laboratoryCollection(fact).text : sourceTime(source)} · {sourceStatus(source)}{source.superseded && ' · Superseded'}</p>
      {fact.record_status === 'withdrawn' ? <p>Withdrawn source record</p> : <>
        {typeof fact.narrative === 'string' && <p>{fact.narrative}</p>}
        {fact.kind === 'precaution_record' && <p>{String(fact.precaution)} · {words(fact.status)}</p>}
        {components.map((raw, i) => {const c = record(raw); return <p key={i}>{String(record(c.test_code).raw_display ?? c.mapped_concept)} · {laboratoryResultText(c)}</p>;})}
        {fact.kind === 'observation' && <p>{String(record(fact.value).value ?? fact.value ?? 'Value unavailable')} {String(record(record(fact.value).unit).raw ?? '')}</p>}
      </>}
      <button type="button" disabled={!confirmed || props.guarded} onClick={event => open(source, event.currentTarget)}>Open original source</button>
    </article>;
  }
  function transitionRecords(category: string) {
    const records = model.records.filter(source => source.fact.category === category);
    return records.length ? records.map(source => <div key={key(pin(source))}>
      {evidence(source)}
      <p>Recorded status · {words(source.fact.state)}</p>
      {!!source.fact.owner && <p>Owner · {String(source.fact.owner)}</p>}
      {!!source.fact.due && <p>Due · {String(source.fact.due)}</p>}
      {!!source.fact.medication_decision && <p>Recorded medication decision · {words(source.fact.medication_decision)}
        {' · '}{String(record(source.fact.medication_reference).id)} · revision {String(record(source.fact.medication_reference).version)}</p>}
    </div>) : <p>No {words(category)} information documented for this transition.</p>;
  }
  return <section className="m21-workspace" aria-label="Discharge and transfer">
    <h2>Discharge &amp; transfer</h2>
    <div className="m21-row">
      <label>Transition <select value={model.planId} disabled={props.guarded} onChange={event => {setPlan(event.target.value); select(undefined); const url = new URL(window.location.href); url.searchParams.set('transition', event.target.value); window.history.replaceState(window.history.state, '', url);}}>
        {!model.plans.length && <option value="">No documented transition</option>}
        {model.plans.map(id => {const plan = props.catalog?.discharge_records?.find(source => source.fact.transition_id === id && !source.superseded);
          return <option key={id} value={id}>{transitionLabel(plan?.fact.transition)} · {String(plan?.fact.destination ?? '')} · {id}</option>;})}
      </select></label>
      <button type="button" disabled={props.guarded} onClick={() => void props.onRefresh().catch(() => {})}>Refresh evidence</button>
    </div>
    {!confirmed && <p role="status">{model.handoverConflict ? 'Conflicting handover records need reconciliation.' : !model.planValid ? 'A confirmed transition plan is required.' : 'Shared evidence is loading or unconfirmed. Review saving is unavailable.'}</p>}
    {props.current && model.complete && reviews[0] && !model.matches(reviews[0]) &&
      <p className="m21-flag" role="status">Transition review needed · Evidence changed.</p>}
    <nav className="m21-tabs" aria-label="Discharge views">{tabs.map(label => <button type="button" key={label}
      aria-current={tab === label ? 'page' : undefined} onClick={() => setTab(label)}>{label}</button>)}</nav>
    {props.current && model.valid && <>
      {tab === 'Summary' && <>
        <section className="m21-card"><h3>Patient course</h3>{transitionRecords('course')}</section>
        <section className="m21-card"><h3>Shared patient evidence</h3>
          {['respiratory_record', 'laboratory_report', 'circulatory_', 'neurological_record', 'gastrointestinal_record',
            'reproductive_record', 'endocrine_record', 'wound_record', 'musculoskeletal_record', 'nutrition_record', 'precaution_record', 'observation'].map(kind => {
            const sources = model.sources.filter(source => source.fact.kind.startsWith(kind));
            const names: Record<string, string> = {respiratory_record: 'Respiratory', laboratory_report: 'Laboratory results',
              circulatory_: 'Cardiovascular', neurological_record: 'Neurological', gastrointestinal_record: 'GI and liver',
              reproductive_record: 'OBGYN', endocrine_record: 'Endocrine', wound_record: 'Skin and wounds',
              musculoskeletal_record: 'Mobility and rehabilitation', nutrition_record: 'Nutrition', precaution_record: 'Precautions', observation: 'Renal, fluid and other observations'};
            return <details key={kind}><summary>{names[kind]} · {sources.length} records</summary>
              {sources.length ? sources.map(evidence) : <p>No linked records in this view.</p>}</details>;
          })}
          <details><summary>Microbiology · {model.microItems.filter(item => String(item.fact.kind).startsWith('microbiology_')).length} records</summary>
            {!model.microConfirmed ? <p>Microbiology retrieval unconfirmed.</p> : model.microItems.filter(item => String(item.fact.kind).startsWith('microbiology_')).map(item =>
              <details key={stable(microReference(item))}><summary>{item.fact.kind} · {item.fact.id} · revision {item.fact.revision}</summary><pre>{JSON.stringify(item.fact, null, 2)}</pre></details>)}
          </details>
          <details><summary>Hematology and transfusion · {model.blood.length} records</summary>
            {!model.bloodConfirmed ? <p>Transfusion retrieval unconfirmed.</p> : model.blood.map(item =>
              <details key={stable([item.fact.kind, item.fact.id, item.fact.revision])}><summary>{item.fact.id} · revision {item.fact.revision}</summary><pre>{JSON.stringify(item.fact, null, 2)}</pre></details>)}
          </details>
          <details><summary>Devices and procedures · Encounter history</summary><DeviceWorkspace state={props.devices}/></details>
        </section>
      </>}
      {tab === 'Medications' && <section className="m21-card"><h3>Medication reconciliation</h3>{transitionRecords('reconciliation')}
        <details open><summary>Recorded antimicrobial prescriptions and administrations</summary>
          {!model.microConfirmed ? <p>Medication retrieval unconfirmed.</p> :
            model.microItems.filter(item => String(item.fact.kind).startsWith('antimicrobial_')).map(item => <article key={stable(microReference(item))}>
              <p>{recordSummary(item)}</p><details><summary>Original medication record · {item.fact.id} · revision {item.fact.revision}</summary><pre>{JSON.stringify(item.fact, null, 2)}</pre></details>
            </article>)}
        </details>
        <details><summary>Other medication orders and administrations</summary>{model.sources.filter(source =>
          ['medication_order', 'medication_administration'].includes(source.fact.kind)).map(evidence)}</details>
      </section>}
      {tab === 'Care & follow-up' && <><section className="m21-card"><h3>Care to continue</h3>{transitionRecords('care')}</section>
        <section className="m21-card"><h3>Pending results and follow-up</h3>{transitionRecords('pending')}</section></>}
      {tab === 'Review & handover' && <section className="m21-card"><h3>Documented handover</h3>{transitionRecords('handover')}
        <p>Completion follows the recorded clinician decision and receiving handover.</p></section>}
    </>}
    <div hidden={tab !== 'Review & handover'}>
      <SourcePinnedReview key={model.planId} catalog={props.catalog} requested={props.requested} model={model}
        current={confirmed} guarded={props.guarded} saved={{...saved, reviews}} cardClassName="m21-card" onOpenSource={open} onResolveSource={resolve}
        renderSavedContext={review => review.snapshot.context?.deviceHistory ? <details>
          <summary>Device and procedure history reviewed at save</summary>
          <pre>{review.snapshot.context.deviceHistory}</pre>
        </details> : null}/>
    </div>
    {selected && selected.identity === model.identity && confirmed && !props.guarded &&
      <GISource evidence={selected.source} current={!selected.source.superseded} transport={client} onClose={() => {select(undefined); trigger.current?.focus();}}/>}
  </section>;
}
