import {pin, stable, type Catalog} from '../api/rf2Client';
import type {AntibioticBundle} from '../api/antibioticClient';
import type {SavedReview} from '../clinical/savedReviewStore';
import {microReference} from '../antibioticWorkflow/patientModel';
import {record} from '../demo/evidencePresentation';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {reviewPin} from '../nutrition/catalogModel';

export interface Requested {patient: string; encounter: string; start: string; end: string}
export function preventionModel(catalog: Catalog | undefined, bundle: AntibioticBundle | undefined, requested: Requested) {
  const scope = catalog?.combined.context.scope;
  const valid = !!catalog && !!scope && catalog.execution_enabled === false &&
    catalog.combined.execution_enabled === false && catalog.cutoff.repository_id === catalog.repository &&
    stable(scope.repository_cutoff) === stable(catalog.cutoff) &&
    scope.patient_id === requested.patient && scope.encounter_id === requested.encounter &&
    compare(scope.review_start, requested.start) === 0 && compare(scope.review_end, requested.end) === 0;
  const micro = valid && bundle?.renal === catalog && bundle.execution_enabled === false ? bundle.micro : undefined;
  const precautions = valid ? (catalog.precaution_records ?? []).filter(source => {
    const target = source.fact.binding.target;
    return source.fact.kind === 'precaution_record' && source.repository === catalog.repository &&
      target.patient_id === requested.patient && target.encounter_id === requested.encounter;
  }) : [];
  const items = (micro?.assembly.snapshot.items ?? []).filter(item => String(item.fact.kind).startsWith('microbiology_') ||
    ['blood_culture_set', 'blood_culture_bottle'].includes(String(item.fact.kind)));
  const pins = [...precautions.map(reviewPin), ...items.map(item => ({
    reference: microReference(item), expected_digest: item.expected_digest,
  }))];
  const signature = stable(['m20/v1', requested.patient, requested.encounter, requested.start, requested.end, catalog?.repository ?? '']);
  const identities = stable([
    precautions.map(source => [pin(source).reference, source.digest, source.superseded]).map(stable).sort(),
    items.map(item => [microReference(item), item.expected_digest, item.inclusion]).map(stable).sort(),
  ]);
  // Store the relevant evidence identity only. An unrelated encounter record can advance the watermark.
  const reviewSignature = stable([signature, identities]);
  const latest = new Map<string, {time: string; status: string; label: string}>();
  const unresolved = new Set<string>();
  for (const source of precautions) {
    const f = source.fact;
    if (source.superseded || f.record_status === 'withdrawn' || f.report_status === 'withdrawn') continue;
    const label = String(f.precaution);
    const key = label.trim().toLowerCase();
    const time = record(record(f.times).occurred).value;
    if (f.record_status !== 'recorded' || !['final', 'corrected'].includes(String(f.report_status)) ||
        f.conflict === 'unresolved' || typeof time !== 'string') {
      unresolved.add(key);
      continue;
    }
    const previous = latest.get(key);
    const order = previous ? compare(time, previous.time) : 1;
    if (order === 0 && previous?.status !== f.status) unresolved.add(key);
    if (order === 1) latest.set(key, {time, status: String(f.status), label});
  }
  const statuses = [...latest].filter(([key]) => !unresolved.has(key)).map(([, status]) => status);
  return {valid, micro, items, sources: precautions, statuses, unresolved: unresolved.size,
    signature: reviewSignature, identity: reviewSignature, pins,
    matches: (review: SavedReview<unknown>) => !!micro && review.snapshot.signature === reviewSignature};
}
