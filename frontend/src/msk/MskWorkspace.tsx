import {useEffect, useId, useRef, useState, type FormEvent} from 'react';
import {useSavedReviews} from '../clinical/useSavedReviews';
import type {SavedReview} from '../clinical/savedReviewStore';
import {records, scope, views} from './fictionalCase';
import './msk.css';

type Source = keyof typeof records;
type Draft = {reviewer: string; rationale: string; nextReview: string; plan: string};
const blank: Draft = {reviewer: '', rationale: '', nextReview: '', plan: ''};
const period = {start: '2026-11-15T00:00:00+05:30', end: '2026-11-17T12:00:00+05:30'};
const signature = JSON.stringify(records);
const tabs = {overview: 'Overview', msk: 'Musculoskeletal', rheum: 'Rheumatology', mobility: 'Mobility & rehab'} as const;

export function MskWorkspace() {
  const [tab, setTab] = useState<keyof typeof tabs>('overview');
  const [source, setSource] = useState<Source>();
  const [draft, setDraft] = useState(blank);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const mounted = useRef(false);
  const busy = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const saved = useSavedReviews<Draft>(scope);
  const current = saved.reviews.find(review => review.snapshot.signature === signature);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  function link(key: Source, label: string) {
    return <button type="button" key={key} onClick={event => {
      trigger.current = event.currentTarget;
      setSource(key);
      dialog.current?.showModal();
    }}>{label}</button>;
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || !saved.ready) return;
    setError('');
    setMessage('');
    const cleaned = {reviewer: draft.reviewer.trim(), rationale: draft.rationale.trim(),
      plan: draft.plan.trim(), nextReview: draft.nextReview.trim()};
    if (!cleaned.reviewer || !cleaned.rationale || !cleaned.nextReview) {
      setError('Enter a reviewer, assessment and next review.');
      return;
    }
    busy.current = true;
    setSaving(true);
    try {
      const pins = await Promise.all(Object.entries(records).map(async ([id, record]) => {
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(record)));
        return {reference: {kind: 'm16_fictional_source', id, version: '1'},
          expected_digest: Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')};
      }));
      const review: SavedReview<Draft> = {...scope, format: 'clinrx-local-review', version: 1,
        id: crypto.randomUUID(), recordedAt: new Date().toISOString(), period,
        snapshot: {signature, cutoff: period.end, pins}, draft: cleaned};
      await saved.save(review, () => mounted.current);
      setDraft(blank);
      setMessage('Review saved in this browser.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Review could not be saved.');
    } finally {
      busy.current = false;
      setSaving(false);
    }
  }

  return <section className="m16-workspace" aria-label="Musculoskeletal and rehabilitation">
    <h2>Musculoskeletal &amp; rehabilitation</h2>
    <p>Fictional orthopaedic encounter · 17 November 2026 · Times in IST</p>
    <nav aria-label="M16 workspace">
      {(Object.keys(tabs) as (keyof typeof tabs)[]).map(key =>
        <button key={key} type="button" aria-current={key === tab ? 'page' : undefined}
          onClick={() => setTab(key)}>{tabs[key]}</button>)}
    </nav>
    {tab === 'overview' ? <>
      <section className="m16-card">
        <h3>Bedside summary</h3>
        <p><strong>Postoperative day 2 after left ankle fixation.</strong> Left leg remains non-weight-bearing per the orthopaedic order.</p>
        <div className="m16-grid">
          <div><h4>Left ankle</h4><p>Toes warm with active movement at 08:20.</p>{link('ortho', 'Open orthopaedic exam')}</div>
          <div><h4>Right wrist</h4><p>Swelling and pain with grip. Rheumatology review pending.</p>{link('wrist', 'Open wrist assessment')}</div>
          <div><h4>Mobility</h4><p>Transferred with one-person assistance and a walker at 10:15. Stairs unassessed.</p>{link('pt', 'Open PT record')}</div>
        </div>
      </section>
      <section className="m16-card">
        <h3>Clinician review</h3>
        {current ? <p>{current.draft.reviewer} · Next review {current.draft.nextReview}</p> : <>
          <p>Fictional example · Dr Kavya Rao · 11:15 IST · Next review 16:00 IST</p>
          <p>Right wrist symptoms limited walker use. Recheck the wrist and confirm a suitable transfer aid with PT and OT. Stair assessment is pending.</p>
        </>}
        <details><summary>Author a review</summary>
          <form onSubmit={event => void save(event)}>
            <p>Reviews are saved in this browser for this fictional encounter.</p>
            <fieldset disabled={saving || !saved.ready}>
              <label>Reviewer<input required maxLength={120} value={draft.reviewer} onChange={e => setDraft({...draft, reviewer: e.target.value})}/></label>
              <label>Assessment<textarea required maxLength={2000} value={draft.rationale} onChange={e => setDraft({...draft, rationale: e.target.value})}/></label>
              <label>Plan &amp; barriers<textarea maxLength={2000} value={draft.plan} onChange={e => setDraft({...draft, plan: e.target.value})}/></label>
              <label>Next review<input required maxLength={250} value={draft.nextReview} onChange={e => setDraft({...draft, nextReview: e.target.value})}/></label>
              <button type="submit">{saving ? 'Saving…' : 'Save review'}</button>
            </fieldset>
          </form>
        </details>
        {message && <p role="status">{message}</p>}
        {(error || saved.issue) && <p role="alert">{error || saved.issue}</p>}
        <h4>Saved reviews</h4>
        {!saved.reviews.length && <p>No review saved in this browser.</p>}
        {saved.reviews.map(review => {
          const matches = review.snapshot.signature === signature;
          return <article key={review.id}>
            <h4>{review.draft.reviewer}</h4>
            <p>{matches ? 'Current fictional evidence' : 'Historical evidence review'} · Next review {review.draft.nextReview}</p>
            <p>{review.draft.rationale}</p><p>{typeof review.draft.plan === 'string' && review.draft.plan}</p>
            <details><summary>Reviewed source revisions</summary>
              {matches ? <div className="m16-links">{(Object.keys(records) as Source[]).map(key => link(key, records[key][0]))}</div>
                : <pre>{JSON.stringify(review.snapshot.pins, null, 2)}</pre>}
            </details>
          </article>;
        })}
      </section>
    </> : <section className="m16-card">
      <h3>{views[tab].heading}</h3>
      {views[tab].rows.map(row => <article key={row.title}>
        <h4>{row.title}</h4><p>{row.detail}</p>
        <div className="m16-links">{row.sources.map(([key, label]) => link(key, label))}</div>
      </article>)}
    </section>}
    <dialog ref={dialog} aria-labelledby={titleId} onClose={() => {trigger.current?.focus(); setSource(undefined);}}>
      <h3 id={titleId}>{source && records[source][0]}</h3>
      <p>{source && records[source][1]}</p>
      <form method="dialog"><button>Close source</button></form>
    </dialog>
  </section>;
}
