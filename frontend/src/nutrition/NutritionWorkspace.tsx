import {useEffect, useId, useRef, useState, type FormEvent} from 'react';
import {useSavedReviews} from '../clinical/useSavedReviews';
import type {SavedReview} from '../clinical/savedReviewStore';
import {records, scope, tabs} from './fictionalCase';
import './nutrition.css';

type Source = keyof typeof records;
type Draft = {reviewer: string; rationale: string; nextReview: string; plan: string};
const blank: Draft = {reviewer: '', rationale: '', nextReview: '', plan: ''};
const period = {start: '2026-11-17T06:00:00+05:30', end: '2026-11-18T16:00:00+05:30'};
const signature = JSON.stringify(records);

export function NutritionWorkspace() {
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
        return {reference: {kind: 'm17_fictional_source', id, version: '1'},
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

  return <section className="m17-workspace" aria-label="Nutrition">
    <h2>Nutrition</h2>
    <p>Fictional ICU encounter · 18 November 2026 · Times in IST</p>
    <nav aria-label="Nutrition workspace">
      {(Object.keys(tabs) as (keyof typeof tabs)[]).map(key =>
        <button key={key} type="button" aria-current={key === tab ? 'page' : undefined}
          onClick={() => setTab(key)}>{tabs[key]}</button>)}
    </nav>
{tab === "overview" && <section className="m17-card">
<article className="card summary"><h2>Bedside summary</h2>
<p><strong>Enteral feeding via nasogastric tube.</strong> During the completed 24-hour intake window, 920 of 1,200 mL prescribed formula was delivered. The intake chart records a four-hour pause for imaging.</p>
<div className="grid">
<div><h3>Assessment</h3><p>Dietitian identified recent reduced intake and recorded a 70 kg pre-admission weight for estimating needs.</p>{link("dietitian", "Open dietitian assessment")}</div>
<div><h3>Intake delivered</h3><p>1,380 kcal and 69 g protein from documented formula. See the chart for the reporting window and route.</p>{link("intake", "Open intake chart")}</div>
<div><h3>Next review</h3><p>Dietitian review at 16:00 IST. Reconcile post-restart delivery and repeat electrolyte results when available.</p>{link("review", "Open clinician review")}</div>
</div></article>
</section>}
{tab === "assessment" && <section className="m17-card"><h2>Nutrition assessment &amp; targets</h2>
<article className="row"><h3>Dietitian assessment</h3><p>17 Nov, 14:10. Patient reported eating about half of usual intake for six days before admission. Measured bedside weight was 74 kg with oedema documented. Dietitian used the reported 70 kg pre-admission weight as the estimate basis.</p>{link("dietitian", "Open dietitian assessment")}</article>
<article className="row"><h3>Recorded targets and method</h3><p>1,750–2,100 kcal/day and 84–105 g protein/day. Dietitian recorded weight-based estimates of 25–30 kcal/kg/day and 1.2–1.5 g/kg/day using 70 kg.</p>{link("dietitian", "Open target source")}</article>
</section>}
{tab === "delivery" && <section className="m17-card"><h2>Nutrition support &amp; intake</h2>
<div className="table-wrap"><table><caption>Completed 24-hour window · 17 Nov 06:00 to 18 Nov 06:00 IST</caption>
<thead><tr><th scope="col">Route</th><th scope="col">Prescribed</th><th scope="col">Documented delivery</th></tr></thead>
<tbody><tr><th scope="row">Enteral</th><td>1,200 mL · 1,800 kcal · 90 g protein</td><td>920 mL · 1,380 kcal · 69 g protein</td></tr>
<tr><th scope="row">Oral</th><td>Oral intake deferred pending swallow review</td><td>No oral intake recorded</td></tr>
<tr><th scope="row">Parenteral nutrition</th><td>No order recorded</td><td>No administration recorded</td></tr></tbody></table></div>
<p>Enteral values use the prescribed formula composition of 1.5 kcal and 0.075 g protein per mL. The intake chart records a 280 mL gap and documents the imaging pause separately.</p>
{link("order", "Open nutrition order")} {link("intake", "Open intake chart")}
</section>}
{tab === "review" && <section className="m17-card"><h2>Tolerance &amp; reassessment</h2>
<article className="row"><h3>Tolerance and interruption</h3><p>Feeds paused for imaging from 18:00 to 22:00 on 17 Nov, then restarted. Nursing documented no emesis overnight and a soft abdomen at 05:30. Swallow assessment remains pending.</p>{link("nursing", "Open nursing record")}</article>
<article className="row"><h3>Shared laboratory results</h3><p>Collected 18 Nov at 05:00, final at 05:45. Phosphate 0.72 mmol/L, magnesium 0.80 mmol/L, potassium 3.8 mmol/L.</p>{link("lab", "Open electrolyte report")}</article>
<article className="row"><h3>Clinician-authored review</h3><small>Dietitian Mira Desai · 09:10 IST · Next review 16:00 IST</small><p>Documented enteral delivery fell below the prescribed intake in the completed window. Reconcile delivery after restart, review repeat electrolytes when available, and check swallow assessment status at the next review.</p>{link("review", "Open clinician review")}</article>
</section>}
    <section className="m17-card" hidden={tab !== 'review'}>
        <h3>Clinician reviews</h3>
        {current && <p>{current.draft.reviewer} · Next review {current.draft.nextReview}</p>}
        <details><summary>Author a review</summary>
          <form onSubmit={event => void save(event)}>
            <p>Reviews are saved in this browser for this fictional encounter.</p>
            <fieldset disabled={saving || !saved.ready}>
              <label>Reviewer<input required maxLength={120} value={draft.reviewer} onChange={e => setDraft({...draft, reviewer: e.target.value})}/></label>
              <label>Assessment<textarea required maxLength={2000} value={draft.rationale} onChange={e => setDraft({...draft, rationale: e.target.value})}/></label>
              <label>Plan &amp; missing information<textarea maxLength={2000} value={draft.plan} onChange={e => setDraft({...draft, plan: e.target.value})}/></label>
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
              {matches ? <div className="m17-links">{(Object.keys(records) as Source[]).map(key => link(key, records[key][0]))}</div>
                : <pre>{JSON.stringify(review.snapshot.pins, null, 2)}</pre>}
            </details>
          </article>;
        })}
    </section>
    <dialog ref={dialog} aria-labelledby={titleId} onClose={() => {trigger.current?.focus(); setSource(undefined);}}>
      <h3 id={titleId}>{source && records[source][0]}</h3>
      <p>{source && records[source][1]}</p>
      <form method="dialog"><button>Close source</button></form>
    </dialog>
  </section>;
}
