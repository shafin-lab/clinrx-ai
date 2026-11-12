import {useLayoutEffect, useRef, useState, type FormEvent} from 'react';
import {type Catalog, type Pin, pin} from '../api/rf2Client';
import type {ReviewScope, SavedReview} from '../clinical/savedReviewStore';
import {useSavedReviews} from '../clinical/useSavedReviews';
import type {OpenSource} from './NeurologicalExam';
import {type NeurologicalScope, type neurologicalModel} from './model';
import {asObject} from '../respiratory/respiratoryModel';

interface Draft {
  reviewer: string;
  nextReview: string;
  rationale: string;
  plan: string;
}

const blank: Draft = {reviewer: '', nextReview: '', rationale: '', plan: ''};

export function useNeurologicalReview(catalog: Catalog | undefined, requested: NeurologicalScope) {
  const scope: ReviewScope | undefined = catalog
    ? {domain: 'M13', patient: requested.patient, encounter: requested.encounter, repository: catalog.repository}
    : undefined;
  return {scope, ...useSavedReviews<Draft>(scope)};
}

export function NeurologicalReview({catalog, requested, model, current, guarded, saved, onOpenSource, onResolveSource}: {
  catalog?: Catalog; requested: NeurologicalScope; model: ReturnType<typeof neurologicalModel>;
  current: boolean; guarded: boolean; saved: ReturnType<typeof useNeurologicalReview>; onOpenSource: OpenSource;
  onResolveSource: (pin: Pin, trigger: HTMLButtonElement) => Promise<void>;
}) {
  const [draft, setDraft] = useState(blank);
  const [started, setStarted] = useState('');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [sourceError, setSourceError] = useState('');
  const busy = useRef(false);
  const latest = useRef('');
  const draftStale = !!started && started !== model.identity;

  useLayoutEffect(() => {
    latest.current = current && !guarded ? model.identity : '';
    return () => { latest.current = ''; };
  }, [current, guarded, model.identity]);

  function change(field: keyof Draft, value: string) {
    if (!started) setStarted(model.identity);
    setDraft(previous => ({...previous, [field]: value}));
    setStatus('');
    setError('');
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    setError('');
    setStatus('');
    const scope = saved.scope;
    if (!current || guarded || !scope || !catalog || !saved.ready || started !== model.identity || !model.pins.length) {
      setError('Review the current source records before saving.');
      return;
    }
    const cleaned = {
      reviewer: draft.reviewer.trim(), nextReview: draft.nextReview.trim(),
      rationale: draft.rationale.trim(), plan: draft.plan.trim(),
    };
    if (!cleaned.reviewer || !cleaned.rationale || !cleaned.nextReview) {
      setError('Enter the reviewer, assessment and next review.');
      return;
    }
    if (model.pins.length > 500) {
      setError('The evidence set exceeds the browser review limit.');
      return;
    }
    busy.current = true;
    setSaving(true);
    try {
      const review: SavedReview<Draft> = {
        ...scope, format: 'clinrx-local-review', version: 1, id: crypto.randomUUID(),
        period: {start: requested.start, end: requested.end},
        snapshot: {signature: model.signature, cutoff: catalog.cutoff, pins: model.pins},
        draft: cleaned, recordedAt: new Date().toISOString(),
      };
      await saved.save(review, () => latest.current === started);
      setDraft(blank);
      setStarted('');
      setStatus('Review saved in this browser.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Review could not be saved.');
    } finally {
      busy.current = false;
      setSaving(false);
    }
  }

  return <>
    <form className="m13-card" onSubmit={event => void submit(event)}>
      <h3>Author a review</h3>
      <p>Saved reviews are available in this browser for this encounter.</p>
      <fieldset disabled={saving || guarded || !current || !model.pins.length || !saved.ready}>
        <label>Reviewer<input required maxLength={120} value={draft.reviewer} onChange={e => change('reviewer', e.target.value)}/></label>
        <label>Next review<input required maxLength={250} value={draft.nextReview} onChange={e => change('nextReview', e.target.value)}/></label>
        <label>Assessment<textarea required maxLength={2000} value={draft.rationale} onChange={e => change('rationale', e.target.value)}/></label>
        <label>Plan &amp; missing information<textarea maxLength={2000} value={draft.plan} onChange={e => change('plan', e.target.value)}/></label>
        <button type="submit" disabled={draftStale}>{saving ? 'Saving…' : 'Save review'}</button>
        {started && <button type="button" onClick={() => { setDraft(blank); setStarted(''); setError(''); }}>Clear draft</button>}
      </fieldset>
      {draftStale && <p role="alert">Evidence changed after this draft began. Clear the draft and review the new sources.</p>}
      {(error || saved.issue) && <p role="alert">{error || saved.issue}</p>}
      {status && <p role="status">{status}</p>}
    </form>
    <section className="m13-card">
      <h3>Saved reviews</h3>
      {sourceError && <p role="alert">{sourceError}</p>}
      {!saved.reviews.length && <p>No review saved in this browser for this encounter.</p>}
      {saved.reviews.map(review => <article key={review.id}>
        <h4>{review.draft.reviewer}</h4>
        <p><strong>{current && model.matches(review) ? 'Matches current evidence' : 'Historical evidence review'}</strong> · Next review {review.draft.nextReview}</p>
        <p>{review.draft.rationale}</p>
        {review.draft.plan && <p>{review.draft.plan}</p>}
        <small>Period {review.period.start} → {review.period.end} · Saved {review.recordedAt}</small>
        <details><summary>Reviewed source revisions</summary><ul>{review.snapshot.pins.map((value, index) => {
          const stored = asObject(value);
          const source = model.sources.find(evidence => {
            const exact = pin(evidence);
            return exact.repository === stored.repository && exact.reference.kind === stored.kind &&
              exact.reference.id === stored.id && exact.reference.version === stored.version &&
              exact.digest === stored.digest && exact.ingestion === stored.ingestion;
          });
          const label = typeof stored.id === 'string' ? stored.id + ' · Revision ' + String(stored.version) : 'Retained source reference';
          const exact: Pin | undefined = current && typeof stored.repository === 'string' &&
            typeof stored.kind === 'string' && typeof stored.id === 'string' && typeof stored.version === 'string' &&
            typeof stored.digest === 'string' && typeof stored.ingestion === 'number' && typeof stored.cutoff === 'number'
            ? {repository: stored.repository, reference: {kind: stored.kind, id: stored.id, version: stored.version},
              digest: stored.digest, ingestion: stored.ingestion, cutoff: stored.cutoff} : undefined;
          return <li key={index}>{exact
            ? <button type="button" onClick={event => {
              setSourceError('');
              if (source) onOpenSource(source, event.currentTarget);
              else void onResolveSource(exact, event.currentTarget).catch(() =>
                setSourceError('The exact reviewed revision could not be retrieved.'));
            }}>{label}</button> : label}
            <details><summary>Exact reviewed reference</summary><pre tabIndex={0}>{JSON.stringify(value, null, 2)}</pre></details>
          </li>;
        })}</ul></details>
      </article>)}
    </section>
  </>;
}
